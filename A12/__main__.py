import pulumi
from pulumi_azure_native import resources, network, compute, storage
from pulumi_random import random_string

# **Schritt 1: Konfigurationseinstellungen**
# Hier werden Konfigurationswerte definiert, die im gesamten Skript verwendet werden.
config = pulumi.Config()
vm_name1 = config.get("vm1", "my-monitored-server1")  # Name der VM
vm_size = config.get("vmSize", "Standard_B2ts_v2")  # VM-Größe
os_image = config.get("osImage", "Debian:debian-11:11:latest")  # OS-Image-Definition
admin_username = config.get("azureuser", "pulumiuser")  # Benutzername für die VM
service_port = config.get("servicePort", "80")  # Port für HTTP (Webserver)

# OS-Image-Details extrahieren
os_image_publisher, os_image_offer, os_image_sku, os_image_version = os_image.split(":")

# **Schritt 2: Ressourcengruppe erstellen**
# Alle Ressourcen werden in dieser Gruppe zusammengefasst.
resource_group = resources.ResourceGroup("A12resource-group")

# **Schritt 3: Speicherkonto erstellen**
# Das Speicherkonto wird für Boot-Diagnostik-Daten verwendet.
storage_account = storage.StorageAccount(
    "diagaccount",
    resource_group_name=resource_group.name,
    sku=storage.SkuArgs(name="Standard_LRS"),  # Lokale redundante Speicherung
    kind="StorageV2",  # Typ des Speicherkontos
    location=resource_group.location
)

# Generieren der URI für das Speicherkonto (wird für Boot-Diagnostik verwendet)
storage_account_uri = storage_account.primary_endpoints.apply(lambda endpoints: endpoints.blob)

# **Schritt 4: Virtuelles Netzwerk und Subnetz erstellen**
# Das Netzwerk verbindet die VM und ermöglicht die Einrichtung von Sicherheitsregeln.
virtual_network = network.VirtualNetwork(
    "network",
    resource_group_name=resource_group.name,
    address_space={"address_prefixes": ["10.0.0.0/16"]},  # IP-Adressraum
    subnets=[{
        "name": f"{vm_name1}-subnet",  # Subnetzname
        "address_prefix": "10.0.1.0/24",  # IP-Bereich für das Subnetz
    }],
)

# **Schritt 5: Domain-Label für DNS-Name generieren**
# Generiert ein eindeutiges DNS-Label für die VM.
domain_name_label1 = random_string.RandomString(
    "domain-label-1",
    length=8,
    upper=False,
    special=False,
).result.apply(lambda result: f"{vm_name1}-{result}")

# **Schritt 6: Öffentliche IP-Adresse erstellen**
# Die IP-Adresse ermöglicht den Zugriff auf die VM über das Internet.
public_ip1 = network.PublicIPAddress(
    "public-ip-1",
    resource_group_name=resource_group.name,
    public_ip_allocation_method="Dynamic",  # Dynamische IP-Zuweisung
    dns_settings={"domain_name_label": domain_name_label1},  # DNS-Label
)

# **Schritt 7: Sicherheitsgruppe erstellen**
# Die NSG definiert die erlaubten und blockierten Netzwerkregeln.
security_group = network.NetworkSecurityGroup(
    "security-group",
    resource_group_name=resource_group.name,
    security_rules=[{
        "name": f"{vm_name1}-securityrule",
        "priority": 1000,  # Regelpriorität
        "direction": "Inbound",  # Eingehender Verkehr
        "access": "Allow",  # Zugriff erlauben
        "protocol": "Tcp",  # Protokoll TCP
        "source_port_range": "*",
        "source_address_prefix": "*",  # Alle Quell-Adressen erlaubt
        "destination_address_prefix": "*",
        "destination_port_ranges": [service_port, "22"],  # Ports für HTTP (80) und SSH (22)
    }],
)

# **Schritt 8: Netzwerkschnittstelle erstellen**
# Die NIC verbindet die VM mit dem Subnetz und der öffentlichen IP-Adresse.
network_interface1 = network.NetworkInterface(
    "network-interface-1",
    resource_group_name=resource_group.name,
    network_security_group={"id": security_group.id},  # Sicherheitsgruppe zuweisen
    ip_configurations=[{
        "name": f"{vm_name1}-ipconfiguration",
        "private_ip_allocation_method": "Dynamic",
        "subnet": {
            "id": virtual_network.subnets.apply(
                lambda subnets: next(s.id for s in subnets if s.name == f"{vm_name1}-subnet")
            ),
        },
        "public_ip_address": {"id": public_ip1.id},  # Öffentliche IP zuweisen
    }],
)

# **Schritt 9: Virtuelle Maschine erstellen**
# Erstellt die Linux-VM und aktiviert Boot-Diagnostik mit dem Speicherkonto.
vm1 = compute.VirtualMachine(
    "monitored-linux-vm",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    network_profile={
        "network_interfaces": [{"id": network_interface1.id, "primary": True}],
    },
    hardware_profile={"vm_size": vm_size},  # Größe der VM
    os_profile={
        "computer_name": vm_name1,  # Hostname der VM
        "admin_username": admin_username,  # Admin-Benutzername
        "admin_password": "Ganzgeheim123!",  # Admin-Passwort
        "linux_configuration": {"disable_password_authentication": False},
    },
    storage_profile={
        "os_disk": {
            "name": f"{vm_name1}-osdisk",
            "create_option": compute.DiskCreateOption.FROM_IMAGE,
        },
        "image_reference": {
            "publisher": os_image_publisher,  # OS-Image-Details
            "offer": os_image_offer,
            "sku": os_image_sku,
            "version": os_image_version,
        },
    },
    diagnostics_profile={
        "boot_diagnostics": {
            "enabled": True,  # Boot-Diagnostik aktivieren
            "storage_uri": storage_account_uri,  # URI des Speicherkontos
        },
    },
)

# **Schritt 10: Nginx installieren**
# Nginx wird als Webserver installiert und konfiguriert.
vm1_extension = compute.VirtualMachineExtension(
    "vm1Extension",
    resource_group_name=resource_group.name,
    vm_name=vm1.name,
    publisher="Microsoft.Azure.Extensions",
    type="CustomScript",
    type_handler_version="2.1",
    auto_upgrade_minor_version=True,
    settings={
        "commandToExecute": (
            "sudo apt-get update && sudo apt-get install -y nginx && "
            "echo '<head><title>Hello World</title></head><body><h1>Monitoring VM</h1></body>' | "
            "sudo tee /var/www/html/index.nginx-debian.html && "
            "sudo systemctl restart nginx"
        ),
    },
)

# **Schritt 11: Exportieren der VM-Details**
# Exportiert IP-Adresse, Hostname und SSH-Zugriffsinformationen.
vm1_address = vm1.id.apply(
    lambda id: network.get_public_ip_address_output(
        resource_group_name=resource_group.name,
        public_ip_address_name=public_ip1.name,
    )
)

pulumi.export("vm1_ip", vm1_address.ip_address)  # Öffentliche IP der VM
pulumi.export("vm1_hostname", vm1_address.dns_settings.apply(lambda settings: settings.fqdn))  # Hostname
pulumi.export(
    "vm1_url",
    vm1_address.dns_settings.apply(lambda settings: f"http://{settings.fqdn}:{service_port}"),  # URL
)
pulumi.export(
    "vm1_ssh_connection_string",
    vm1_address.ip_address.apply(lambda ip: f"ssh {admin_username}@{ip}"),  # SSH-Verbindung
)

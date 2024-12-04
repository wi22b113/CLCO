import pulumi
from pulumi_azure_native import compute, network, resources, storage

# **Schritt 1: Grundkonfiguration**
# Definiert die wesentlichen Parameter, wie den Standort und die Ressourcennamen.
location = "westeurope"  # Standort für alle Ressourcen
resource_group_name = "A11-webserver-rg"  # Name der Ressourcengruppe
vm_name = "nginx-vm"  # Name der virtuellen Maschine
public_ip_name = "nginx-pip"  # Name der öffentlichen IP-Adresse
nsg_name = "nginx-nsg"  # Name der Network Security Group
nic_name = "nginx-nic"  # Name der Netzwerkschnittstelle
subnet_name = "nginx-subnet"  # Name des Subnetzes
vnet_name = "nginx-vnet"  # Name des virtuellen Netzwerks

# **Schritt 2: Ressourcengruppe erstellen**
# Alle Ressourcen werden in dieser Ressourcengruppe gruppiert.
resource_group = resources.ResourceGroup(resource_group_name, location=location)

# **Schritt 3: Virtuelles Netzwerk erstellen**
# Das Netzwerk verbindet die virtuelle Maschine und bietet die Grundlage für die Netzwerkarchitektur.
vnet = network.VirtualNetwork(
    vnet_name,
    resource_group_name=resource_group.name,
    location=location,
    address_space={"address_prefixes": ["10.0.0.0/16"]},  # IP-Bereich des Netzwerks
)

# **Schritt 4: Subnetz erstellen**
# Ein Subnetz wird innerhalb des virtuellen Netzwerks angelegt.
subnet = network.Subnet(
    subnet_name,
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.1.0/24",  # IP-Bereich des Subnetzes
)

# **Schritt 5: Network Security Group (NSG) erstellen**
# NSG dient als interne Firewall für die virtuelle Maschine.
nsg = network.NetworkSecurityGroup(
    nsg_name,
    resource_group_name=resource_group.name,
    location=location,
)

# **Schritt 6: Regel hinzufügen, um HTTP-Zugriff zu erlauben**
# Diese Regel ermöglicht eingehenden HTTP-Verkehr auf Port 80.
http_rule = network.SecurityRule(
    "allow-http",
    resource_group_name=resource_group.name,
    network_security_group_name=nsg.name,
    access="Allow",  # Verkehr wird erlaubt
    direction="Inbound",  # Eingehender Verkehr
    protocol="Tcp",  # Protokoll: TCP
    priority=100,  # Priorität der Regel
    source_port_range="*",  # Alle Quellports
    destination_port_range="80",  # Zielport 80 (HTTP)
    source_address_prefix="*",  # Alle Quelladressen
    destination_address_prefix="*",  # Alle Zieladressen
)

# **Schritt 7: Öffentliche IP-Adresse erstellen**
# Ermöglicht Zugriff auf die virtuelle Maschine über das Internet.
public_ip = network.PublicIPAddress(
    public_ip_name,
    resource_group_name=resource_group.name,
    location=location,
    public_ip_allocation_method="Dynamic",  # Dynamische IP-Adresse
)

# **Schritt 8: Netzwerkschnittstelle (NIC) erstellen**
# Verbindet die virtuelle Maschine mit dem Netzwerk und der öffentlichen IP.
nic = network.NetworkInterface(
    nic_name,
    resource_group_name=resource_group.name,
    location=location,
    ip_configurations=[
        network.NetworkInterfaceIPConfigurationArgs(
            name="ipconfig1",
            subnet=network.SubnetArgs(id=subnet.id),  # Subnetz zuweisen
            public_ip_address=network.PublicIPAddressArgs(id=public_ip.id),  # Öffentliche IP zuweisen
        )
    ],
    network_security_group=network.NetworkSecurityGroupArgs(id=nsg.id),  # NSG zuweisen
)

# **Schritt 9: Storage-Account für die VM-Disk erstellen**
# Dient zur Speicherung der Betriebssystem-Disk.
storage_account = storage.StorageAccount(
    "vmstorage",
    resource_group_name=resource_group.name,
    location=location,
    sku=storage.SkuArgs(
        name="Standard_LRS",  # Lokale redundante Speicherung (Standard)
    ),
    kind="StorageV2",  # Typ: Storage V2
)

# **Schritt 10: Virtuelle Maschine erstellen**
# Erstellt eine Linux-VM mit Ubuntu und installiert Nginx.
vm = compute.VirtualMachine(
    vm_name,
    resource_group_name=resource_group.name,
    location=location,
    hardware_profile=compute.HardwareProfileArgs(vm_size="Standard_B1s"),  # Größe der VM
    os_profile=compute.OSProfileArgs(
        computer_name=vm_name,  # Hostname der VM
        admin_username="azureuser",  # Administrator-Benutzername
        admin_password="SecureP@ssw0rd!",  # Administrator-Passwort
    ),
    storage_profile=compute.StorageProfileArgs(
        os_disk=compute.OSDiskArgs(
            caching="ReadWrite",
            create_option="FromImage",
            managed_disk=compute.ManagedDiskParametersArgs(
                storage_account_type="Standard_LRS",  # Disk-Typ
            ),
        ),
        image_reference=compute.ImageReferenceArgs(
            publisher="Canonical",  # Betriebssystem: Canonical Ubuntu
            offer="UbuntuServer",
            sku="18.04-LTS",  # Ubuntu 18.04 LTS
            version="latest",
        ),
    ),
    network_profile=compute.NetworkProfileArgs(
        network_interfaces=[
            compute.NetworkInterfaceReferenceArgs(
                id=nic.id,  # Zuweisung der Netzwerkschnittstelle
                primary=True,
            )
        ]
    ),
)

# **Schritt 11: Nginx installieren**
# Nginx wird auf der VM über eine Custom Script Extension installiert.
script_extension = compute.VirtualMachineExtension(
    "nginxInstallScript",
    resource_group_name=resource_group.name,
    vm_name=vm.name,
    location=location,
    publisher="Microsoft.Azure.Extensions",
    type="CustomScript",  # Erweiterungstyp: Custom Script
    type_handler_version="2.0",
    settings={
        "commandToExecute": "sudo apt-get update && sudo apt-get install -y nginx",  # Installationsbefehl
    },
    opts=pulumi.ResourceOptions(depends_on=[vm]),  # Abhängigkeit: VM muss zuerst erstellt sein
)

# **Schritt 12: IP-Adresse abrufen**
# Nach Erstellung der öffentlichen IP-Adresse wird diese abgerufen.
public_ip_address = network.get_public_ip_address_output(
    resource_group_name=resource_group.name,
    public_ip_address_name=public_ip.name,
)

# **Schritt 13: Exporte**
# Exportiert die IP-Adresse der VM und andere nützliche Informationen.
pulumi.export("public_ip", public_ip_address.ip_address)  # Einzelne IP-Adresse
public_ips = [public_ip_address.ip_address]  # Alle IP-Adressen (in diesem Fall nur eine)
pulumi.export("public_ips", pulumi.Output.all(*public_ips))  # Liste aller IPs

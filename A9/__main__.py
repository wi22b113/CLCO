import pulumi
from pulumi_azure_native import resources, network, compute
import pulumi_azure_native as azure_native
from pulumi_random import random_string

# Konfiguration laden
# Diese Einstellungen werden verwendet, um benutzerdefinierte Werte für die VMs, Disk-Typen und Netzwerke zu definieren.
config = pulumi.Config()
vm_name1 = config.get("vm1", "my-server1")
vm_name2 = config.get("vm2", "my-server2")
vm_size = config.get("vmSize", "Standard_B2ts_v2")
os_image = config.get("osImage", "Debian:debian-11:11:latest")
admin_username = config.get("azureuser", "pulumiuser")
service_port = config.get("servicePort", "80")

# Aufteilen der OS-Image-Konfiguration in einzelne Teile
os_image_publisher, os_image_offer, os_image_sku, os_image_version = os_image.split(":")

# **Schritt 1: Resource Group erstellen**
# Alle Ressourcen werden in dieser Resource Group gebündelt.
resource_group = resources.ResourceGroup("A9-resource-group")

# **Schritt 2: Erstellen eines virtuellen Netzwerks mit zwei Subnetzen**
# Das Netzwerk verbindet die virtuellen Maschinen.
virtual_network = network.VirtualNetwork(
    "network",
    resource_group_name=resource_group.name,
    address_space={
        "address_prefixes": [
            "10.0.0.0/16",  # Gesamter Adressbereich für das Netzwerk
        ],
    },
    subnets=[
        {
            "name": f"{vm_name1}-subnet",  # Subnetz für VM1
            "address_prefix": "10.0.1.0/24",
        },
        {
            "name": f"{vm_name2}-subnet",  # Subnetz für VM2
            "address_prefix": "10.0.2.0/24",
        },
    ],
)

# **Schritt 3: Öffentliche IP-Adressen erstellen**
# Diese IP-Adressen ermöglichen Zugriff auf die VMs über das Internet.
public_ip1 = network.PublicIPAddress(
    "public-ip-1",
    resource_group_name=resource_group.name,
    public_ip_allocation_method=network.IpAllocationMethod.DYNAMIC,  # Dynamische IP-Zuweisung
)

public_ip2 = network.PublicIPAddress(
    "public-ip-2",
    resource_group_name=resource_group.name,
    public_ip_allocation_method=network.IpAllocationMethod.DYNAMIC,
)

# **Schritt 4: Sicherheitsgruppe erstellen**
# Definiert Regeln, die den Zugriff auf die VMs steuern (z. B. HTTP, SSH).
security_group = network.NetworkSecurityGroup(
    "security-group",
    resource_group_name=resource_group.name,
    security_rules=[
        {
            "name": f"{vm_name1}-securityrule",
            "priority": 1000,  # Priorität der Regel
            "direction": network.AccessRuleDirection.INBOUND,  # Eingehender Verkehr
            "access": "Allow",  # Verkehr erlauben
            "protocol": "Tcp",
            "destination_port_ranges": [
                service_port,  # HTTP
                "22",         # SSH
            ],
        },
    ],
)

# **Schritt 5: Netzwerkschnittstellen erstellen**
# Verbinden die VMs mit dem virtuellen Netzwerk und ermöglichen IP-Zuweisungen.
network_interface1 = network.NetworkInterface(
    "network-interface-1",
    resource_group_name=resource_group.name,
    network_security_group={
        "id": security_group.id,
    },
    ip_configurations=[
        {
            "name": f"{vm_name1}-ipconfiguration",
            "private_ip_allocation_method": network.IpAllocationMethod.DYNAMIC,
            "subnet": {
                "id": virtual_network.subnets.apply(
                    lambda subnets: next(
                        s.id for s in subnets if s.name == f"{vm_name1}-subnet"
                    )
                ),
            },
            "public_ip_address": {
                "id": public_ip1.id,
            },
        },
    ],
)

network_interface2 = network.NetworkInterface(
    "network-interface-2",
    resource_group_name=resource_group.name,
    network_security_group={
        "id": security_group.id,
    },
    ip_configurations=[
        {
            "name": f"{vm_name2}-ipconfiguration",
            "private_ip_allocation_method": network.IpAllocationMethod.DYNAMIC,
            "subnet": {
                "id": virtual_network.subnets.apply(
                    lambda subnets: next(
                        s.id for s in subnets if s.name == f"{vm_name2}-subnet"
                    )
                ),
            },
            "public_ip_address": {
                "id": public_ip2.id,
            },
        },
    ],
)

# **Schritt 6: Zwei Managed Disks erstellen**
# Diese Disks werden den VMs als Speicher hinzugefügt.
disk1 = compute.Disk(
    "disk1",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku={"name": "Standard_LRS"},  # Disk-Typ (Standard oder Premium)
    creation_data={"create_option": compute.DiskCreateOption.EMPTY},  # Leere Disk
    disk_size_gb=1024,  # Größe in GB
)

disk2 = compute.Disk(
    "disk2",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku={"name": "Standard_LRS"},
    creation_data={"create_option": compute.DiskCreateOption.EMPTY},
    disk_size_gb=1024,
)

# **Schritt 7: Erstellen der virtuellen Maschinen**
# Diese VMs erhalten die Netzwerkschnittstellen und Disks.
vm1 = compute.VirtualMachine(
    "vm1",
    resource_group_name=resource_group.name,
    network_profile={
        "network_interfaces": [
            {"id": network_interface1.id, "primary": True},
        ]
    },
    hardware_profile={"vm_size": vm_size},
    os_profile={
        "computer_name": vm_name1,
        "admin_username": admin_username,
        "admin_password": "Ganzgeheim123!",
    },
    storage_profile={
        "os_disk": {"name": f"{vm_name1}-osdisk", "create_option": compute.DiskCreateOption.FROM_IMAGE},
        "image_reference": {
            "publisher": os_image_publisher,
            "offer": os_image_offer,
            "sku": os_image_sku,
            "version": os_image_version,
        },
        "data_disks": [
            {"lun": 0, "name": disk1.name, "create_option": "Attach", "managed_disk": {"id": disk1.id}},
        ],
    },
)

vm2 = compute.VirtualMachine(
    "vm2",
    resource_group_name=resource_group.name,
    network_profile={
        "network_interfaces": [
            {"id": network_interface2.id, "primary": True},
        ]
    },
    hardware_profile={"vm_size": vm_size},
    os_profile={
        "computer_name": vm_name2,
        "admin_username": admin_username,
        "admin_password": "Ganzgeheim123!",
    },
    storage_profile={
        "os_disk": {"name": f"{vm_name2}-osdisk", "create_option": compute.DiskCreateOption.FROM_IMAGE},
        "image_reference": {
            "publisher": os_image_publisher,
            "offer": os_image_offer,
            "sku": os_image_sku,
            "version": os_image_version,
        },
        "data_disks": [
            {"lun": 0, "name": disk2.name, "create_option": "Attach", "managed_disk": {"id": disk2.id}},
        ],
    },
)

# **Schritt 8: Export der Details**
# Exportiert die relevanten Informationen für weitere Nutzung.
pulumi.export("vm1_ip", public_ip1.ip_address)
pulumi.export("vm2_ip", public_ip2.ip_address)
pulumi.export("disk1_id", disk1.id)
pulumi.export("disk2_id", disk2.id)
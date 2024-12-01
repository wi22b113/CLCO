import pulumi
from pulumi_azure_native import resources, network, compute, recoveryservices
import pulumi_azure_native as azure_native
from pulumi_random import random_string
import pulumi_tls as tls
import base64

# Import the program's configuration settings
config = pulumi.Config()
vm_name1 = config.get("vm1", "my-server1")
vm_name2 = config.get("vm2", "my-server2")
vm_size = config.get("vmSize", "Standard_B2ts_v2")
os_image = config.get("osImage", "Debian:debian-11:11:latest")
admin_username = config.get("azureuser", "pulumiuser")
service_port = config.get("servicePort", "80")

os_image_publisher, os_image_offer, os_image_sku, os_image_version = os_image.split(":")

# Create a resource group
resource_group = resources.ResourceGroup("A9-resource-group")

# Create a virtual network with two subnets
virtual_network = network.VirtualNetwork(
    "network",
    resource_group_name=resource_group.name,
    address_space={
        "address_prefixes": [
            "10.0.0.0/16",
        ],
    },
    subnets=[
        {
            "name": f"{vm_name1}-subnet",
            "address_prefix": "10.0.1.0/24",
        },
        {
            "name": f"{vm_name2}-subnet",
            "address_prefix": "10.0.2.0/24",
        },
    ],
)

# Use random strings to give the VMs unique DNS names
domain_name_label1 = random_string.RandomString(
    "domain-label-1",
    length=8,
    upper=False,
    special=False,
).result.apply(lambda result: f"{vm_name1}-{result}")

domain_name_label2 = random_string.RandomString(
    "domain-label-2",
    length=8,
    upper=False,
    special=False,
).result.apply(lambda result: f"{vm_name2}-{result}")

# Create public IP addresses for the VMs
public_ip1 = network.PublicIPAddress(
    "public-ip-1",
    resource_group_name=resource_group.name,
    public_ip_allocation_method=network.IpAllocationMethod.DYNAMIC,
    dns_settings={
        "domain_name_label": domain_name_label1,
    },
)

public_ip2 = network.PublicIPAddress(
    "public-ip-2",
    resource_group_name=resource_group.name,
    public_ip_allocation_method=network.IpAllocationMethod.DYNAMIC,
    dns_settings={
        "domain_name_label": domain_name_label2,
    },
)

# Create a security group allowing inbound access over ports 80 (for HTTP) and 22 (for SSH)
security_group = network.NetworkSecurityGroup(
    "security-group",
    resource_group_name=resource_group.name,
    security_rules=[
        {
            "name": f"{vm_name1}-securityrule",
            "priority": 1000,
            "direction": network.AccessRuleDirection.INBOUND,
            "access": "Allow",
            "protocol": "Tcp",
            "source_port_range": "*",
            "source_address_prefix": "*",
            "destination_address_prefix": "*",
            "destination_port_ranges": [
                service_port,
                "22",
            ],
        },
    ],
)

# Create network interfaces for the VMs
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



# Create two managed disks
disk1 = compute.Disk(
    "disk1",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku={
        "name": " Standard_LRS",
    },
    creation_data={
        "create_option": compute.DiskCreateOption.EMPTY
    },
    disk_size_gb=1024
)

disk2 = compute.Disk(
    "disk2",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku={
        "name": " Standard_LRS",
        # Premium_LRS cannot be used because it is not compatible with the Vm size Standard_A1_v2
    },
    creation_data={
        "create_option": compute.DiskCreateOption.EMPTY
    },
    disk_size_gb=1024
)

# Create the virtual machines
vm1 = compute.VirtualMachine(
    "vm1",
    resource_group_name=resource_group.name,
    network_profile={
        "network_interfaces": [
            {
                "id": network_interface1.id,
                "primary": True,
            }
        ]
    },
    hardware_profile={
        "vm_size": vm_size,
    },
    os_profile={
        "computer_name": vm_name1,
        "admin_username": admin_username,
        "admin_password": "Ganzgeheim123!",
        "linux_configuration": {
            "disable_password_authentication": False,
        },
    },
    storage_profile={
        "os_disk": {
            "name": f"{vm_name1}-osdisk",
            "create_option": compute.DiskCreateOption.FROM_IMAGE,
        },
        "image_reference": {
            "publisher": os_image_publisher,
            "offer": os_image_offer,
            "sku": os_image_sku,
            "version": os_image_version,
        },
        "data_disks": [
            {
                "lun": 0,
                "name": disk1.name,
                "create_option": "Attach",
                "managed_disk": {
                    "id": disk1.id
                },
            },
        ],
    }
)

vm2 = compute.VirtualMachine(
    "vm2",
    resource_group_name=resource_group.name,
    network_profile={
        "network_interfaces": [
            {
                "id": network_interface2.id,
                "primary": True,
            }
        ]
    },
    hardware_profile={
        "vm_size": vm_size,
    },
    os_profile={
        "computer_name": vm_name2,
        "admin_username": admin_username,
        "admin_password": "Ganzgeheim123!",
        "linux_configuration": {
            "disable_password_authentication": False,
        },
    },
    storage_profile={
        "os_disk": {
            "name": f"{vm_name2}-osdisk",
            "create_option": compute.DiskCreateOption.FROM_IMAGE,
        },
        "image_reference": {
            "publisher": os_image_publisher,
            "offer": os_image_offer,
            "sku": os_image_sku,
            "version": os_image_version,
        },
        "data_disks": [
            {
                "lun": 0,
                "name": disk2.name,
                "create_option": "Attach",
                "managed_disk": {
                    "id": disk2.id
                },
            },
        ],
    }
)

vm1_extension = azure_native.compute.VirtualMachineExtension("vm1Extension",
    resource_group_name=resource_group.name,
    vm_name=vm1.name,
    vm_extension_name="installNginx",
    publisher="Microsoft.Azure.Extensions",
    type="CustomScript",
    type_handler_version="2.1",
    auto_upgrade_minor_version=True,
    settings={
        "commandToExecute": "sudo apt-get update && sudo apt-get install -y nginx && "
                            "echo '<head><title>Hello World 1</title></head><body><h1>Web Portal</h1>"
                            "<p>Hello World 1</p></body>' | sudo tee /var/www/html/index.nginx-debian.html && "
                            "sudo systemctl restart nginx"
    })


vm2_extension = azure_native.compute.VirtualMachineExtension("vm2Extension",
    resource_group_name=resource_group.name,
    vm_name=vm2.name,
    vm_extension_name="installNginx",
    publisher="Microsoft.Azure.Extensions",
    type="CustomScript",
    type_handler_version="2.1",
    auto_upgrade_minor_version=True,
    settings={
        "commandToExecute": "sudo apt-get update && sudo apt-get install -y nginx && "
                            "echo '<head><title>Hello World 2</title></head><body><h1>Web Portal</h1>"
                            "<p>Hello World 2</p></body>' | sudo tee /var/www/html/index.nginx-debian.html && "
                            "sudo systemctl restart nginx"
    })

# Once the machines are created, fetch their IP addresses and DNS hostnames
vm1_address = vm1.id.apply(
    lambda id: network.get_public_ip_address_output(
        resource_group_name=resource_group.name,
        public_ip_address_name=public_ip1.name,
    )
)

vm2_address = vm2.id.apply(
    lambda id: network.get_public_ip_address_output(
        resource_group_name=resource_group.name,
        public_ip_address_name=public_ip2.name,
    )
)

# Export the VMs' hostnames, public IP addresses, HTTP URLs, and SSH private key
pulumi.export("vm1_ip", vm1_address.ip_address)
pulumi.export("vm1_hostname", vm1_address.dns_settings.apply(lambda settings: settings.fqdn))
pulumi.export(
    "vm1_url",
    vm1_address.dns_settings.apply(
        lambda settings: f"http://{settings.fqdn}:{service_port}"
    ),
)

pulumi.export("vm2_ip", vm2_address.ip_address)
pulumi.export("vm2_hostname", vm2_address.dns_settings.apply(lambda settings: settings.fqdn))
pulumi.export(
    "vm2_url",
    vm2_address.dns_settings.apply(
        lambda settings: f"http://{settings.fqdn}:{service_port}"
    ),
)

# Export the SSH connection strings
pulumi.export(
    "vm1_ssh_connection_string",
    vm1_address.ip_address.apply(
        lambda ip: f"ssh {admin_username}@{ip}"
    ),
)

pulumi.export(
    "vm2_ssh_connection_string",
    vm2_address.ip_address.apply(
        lambda ip: f"ssh {admin_username}@{ip}"
    ),
)

# Export the disk IDs
pulumi.export("disk1_id", disk1.id)
pulumi.export("disk2_id", disk2.id)

# Export backup vault details (commented out)
# pulumi.export("backup_vault_name", backup_vault.name)
# pulumi.export("key_vault_id", backup_vault.id)
import pulumi
from pulumi_azure_native import resources, network, compute, recoveryservices
import pulumi_azure_native as azure_native
from pulumi_random import random_string
import pulumi_tls as tls
import base64

# Import the program's configuration settings
config = pulumi.Config()
vm_name1 = config.get("vm1", "my-monitored-server1")
vm_size = config.get("vmSize", "Standard_B2ts_v2")
os_image = config.get("osImage", "Debian:debian-11:11:latest")
admin_username = config.get("azureuser", "pulumiuser")
service_port = config.get("servicePort", "80")

os_image_publisher, os_image_offer, os_image_sku, os_image_version = os_image.split(":")

# Create a resource group
resource_group = resources.ResourceGroup("A12resource-group")

# Create a storage account
storage_account = azure_native.storage.StorageAccount("diagaccount",
    resource_group_name=resource_group.name,
    sku=azure_native.storage.SkuArgs(
        name="Standard_LRS",
    ),
    kind="StorageV2",
    location=resource_group.location
)

# Generate storage account URI
storage_account_uri = storage_account.primary_endpoints.apply(lambda endpoints: endpoints.blob)

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
    ],
)

# Use random strings to give the VMs unique DNS names
domain_name_label1 = random_string.RandomString(
    "domain-label-1",
    length=8,
    upper=False,
    special=False,
).result.apply(lambda result: f"{vm_name1}-{result}")


# Create public IP addresses for the VMs
public_ip1 = network.PublicIPAddress(
    "public-ip-1",
    resource_group_name=resource_group.name,
    public_ip_allocation_method=network.IpAllocationMethod.DYNAMIC,
    dns_settings={
        "domain_name_label": domain_name_label1,
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

# Create the virtual machines
vm1 = compute.VirtualMachine(
    "monitored-linux-vm",
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

    },
    diagnostics_profile={
        "boot_diagnostics": {
            "enabled": True,
            "storage_uri": storage_account_uri,
        },
    },
    location=resource_group.location,
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


# Once the machines are created, fetch their IP addresses and DNS hostnames
vm1_address = vm1.id.apply(
    lambda id: network.get_public_ip_address_output(
        resource_group_name=resource_group.name,
        public_ip_address_name=public_ip1.name,
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


# Export the SSH connection strings
pulumi.export(
    "vm1_ssh_connection_string",
    vm1_address.ip_address.apply(
        lambda ip: f"ssh {admin_username}@{ip}"
    ),
)

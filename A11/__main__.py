import pulumi
from pulumi_azure_native import compute, network, resources, storage

# Configuration
location = "westeurope"
resource_group_name = "A11-webserver-rg"
vm_name = "nginx-vm"
public_ip_name = "nginx-pip"
nsg_name = "nginx-nsg"
nic_name = "nginx-nic"
subnet_name = "nginx-subnet"
vnet_name = "nginx-vnet"

# Create a Resource Group
resource_group = resources.ResourceGroup(resource_group_name, location=location)

# Create a Virtual Network
vnet = network.VirtualNetwork(
    vnet_name,
    resource_group_name=resource_group.name,
    location=location,
    address_space={"address_prefixes": ["10.0.0.0/16"]},
)

# Create a Subnet
subnet = network.Subnet(
    subnet_name,
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.1.0/24",
)

# Create a Network Security Group
nsg = network.NetworkSecurityGroup(
    nsg_name,
    resource_group_name=resource_group.name,
    location=location,
)

# Add NSG rule to allow HTTP traffic
http_rule = network.SecurityRule(
    "allow-http",
    resource_group_name=resource_group.name,
    network_security_group_name=nsg.name,
    access="Allow",
    direction="Inbound",
    protocol="Tcp",
    priority=100,
    source_port_range="*",
    destination_port_range="80",
    source_address_prefix="*",
    destination_address_prefix="*",
)

# Create a Public IP Address
public_ip = network.PublicIPAddress(
    public_ip_name,
    resource_group_name=resource_group.name,
    location=location,
    public_ip_allocation_method="Dynamic",
)

# Create a Network Interface
nic = network.NetworkInterface(
    nic_name,
    resource_group_name=resource_group.name,
    location=location,
    ip_configurations=[
        network.NetworkInterfaceIPConfigurationArgs(
            name="ipconfig1",
            subnet=network.SubnetArgs(id=subnet.id),
            public_ip_address=network.PublicIPAddressArgs(id=public_ip.id),
        )
    ],
    network_security_group=network.NetworkSecurityGroupArgs(id=nsg.id),
)

# Create a Storage Account for the VM Disk
storage_account = storage.StorageAccount(
    "vmstorage",
    resource_group_name=resource_group.name,
    location=location,
    sku=storage.SkuArgs(
        name="Standard_LRS",
    ),
    kind="StorageV2",
)

# Create a Linux VM
vm = compute.VirtualMachine(
    vm_name,
    resource_group_name=resource_group.name,
    location=location,
    hardware_profile=compute.HardwareProfileArgs(vm_size="Standard_B1s"),
    os_profile=compute.OSProfileArgs(
        computer_name=vm_name,
        admin_username="azureuser",
        admin_password="SecureP@ssw0rd!",
    ),
    storage_profile=compute.StorageProfileArgs(
        os_disk=compute.OSDiskArgs(
            caching="ReadWrite",
            create_option="FromImage",
            managed_disk=compute.ManagedDiskParametersArgs(
                storage_account_type="Standard_LRS",
            ),
        ),
        image_reference=compute.ImageReferenceArgs(
            publisher="Canonical",
            offer="UbuntuServer",
            sku="18.04-LTS",
            version="latest",
        ),
    ),
    network_profile=compute.NetworkProfileArgs(
        network_interfaces=[
            compute.NetworkInterfaceReferenceArgs(
                id=nic.id,
                primary=True,
            )
        ]
    ),
)

# Use Custom Script Extension to Install Nginx
script_extension = compute.VirtualMachineExtension(
    "nginxInstallScript",
    resource_group_name=resource_group.name,
    vm_name=vm.name,
    location=location,
    publisher="Microsoft.Azure.Extensions",
    type="CustomScript",
    type_handler_version="2.0",
    settings={
        "commandToExecute": "sudo apt-get update && sudo apt-get install -y nginx",
    },
    opts=pulumi.ResourceOptions(depends_on=[vm]),
)

# Retrieve the allocated public IP address after creation
public_ip_address = network.get_public_ip_address_output(
    resource_group_name=resource_group.name,
    public_ip_address_name=public_ip.name,
)

# Export the specific public IP address
pulumi.export("public_ip", public_ip_address.ip_address)

# If you have multiple public IPs, collect them in a list
public_ips = [public_ip_address.ip_address]

# Export the list of all public IPs
pulumi.export("public_ips", pulumi.Output.all(*public_ips))

import pulumi
from pulumi import Config, Output
from pulumi_azure_native import resources, network, cognitiveservices, web
import pulumi_azure_native as azure_native
from pulumi_random import random_string

config = pulumi.Config()
azure_location = config.get("azure-native:location") or "uksouth"

# Create an Azure Resource Group
resource_group = azure_native.resources.ResourceGroup("myResourceGroup",
    resource_group_name="A8ResourceGroup",)

# Create a Virtual Network
virtual_network = azure_native.network.VirtualNetwork("vnet",
    resource_group_name=resource_group.name,
    virtual_network_name=resource_group.name.apply(lambda name: f"{name}-vnet"),
    address_space=azure_native.network.AddressSpaceArgs(
        address_prefixes=["10.0.0.0/16"]
    ))

# Create a Subnet
subnet = azure_native.network.Subnet("subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=virtual_network.name,
    subnet_name=resource_group.name.apply(lambda name: f"{name}-subnet"),
    address_prefix="10.0.1.0/24")

# Create a Network Security Group
network_security_group = azure_native.network.NetworkSecurityGroup("nsg",
    resource_group_name=resource_group.name,
    network_security_group_name=resource_group.name.apply(lambda name: f"{name}-nsg"))

# Allow inbound traffic on port 80
security_rule = azure_native.network.SecurityRule("allow80InboundRule",
    resource_group_name=resource_group.name,
    network_security_group_name=network_security_group.name,
    security_rule_name="Allow-80-Inbound",
    priority=110,
    direction="Inbound",
    access="Allow",
    protocol="Tcp",
    source_port_range="*",
    destination_port_range="80",
    source_address_prefix="*",
    destination_address_prefix="*")

# Create a Public IP Address
public_ip = azure_native.network.PublicIPAddress("publicIp",
    resource_group_name=resource_group.name,
    public_ip_address_name="A8PublicIP",
    sku=azure_native.network.PublicIPAddressSkuArgs(name="Standard"),
    public_ip_allocation_method="Static",
    zones=["1", "2", "3"])

# Create a Load Balancer
load_balancer = azure_native.network.LoadBalancer("loadBalancer",
    resource_group_name=resource_group.name,
    load_balancer_name="A8LoadBalancer",
    sku=azure_native.network.LoadBalancerSkuArgs(name="Standard"),
    frontend_ip_configurations=[azure_native.network.FrontendIPConfigurationArgs(
        name="myFrontEnd",
        public_ip_address=azure_native.network.PublicIPAddressArgs(
            id=public_ip.id
        )
    )],
    backend_address_pools=[azure_native.network.BackendAddressPoolArgs(name="myBackEndPool")],
    probes=[azure_native.network.ProbeArgs(
        name="httpProbe",
        protocol="Http",
        port=80,
        request_path="/",
        interval_in_seconds=15,
        number_of_probes=2
    )],
    load_balancing_rules=[azure_native.network.LoadBalancingRuleArgs(
        name="httpRule",
        frontend_ip_configuration=azure_native.network.SubResourceArgs(
            id=f"/subscriptions/{pulumi.Config().require('subscription_id')}/resourceGroups/A8ResourceGroup/providers/Microsoft.Network/loadBalancers/A8LoadBalancer/frontendIPConfigurations/myFrontEnd"
        ),
        backend_address_pool=azure_native.network.SubResourceArgs(
            id=f"/subscriptions/{pulumi.Config().require('subscription_id')}/resourceGroups/A8ResourceGroup/providers/Microsoft.Network/loadBalancers/A8LoadBalancer/backendAddressPools/myBackEndPool"
        ),
        probe=azure_native.network.SubResourceArgs(
            id=f"/subscriptions/{pulumi.Config().require('subscription_id')}/resourceGroups/A8ResourceGroup/providers/Microsoft.Network/loadBalancers/A8LoadBalancer/probes/httpProbe"
        ),
        protocol="Tcp",
        frontend_port=80,
        backend_port=80,
        enable_floating_ip=False,
        idle_timeout_in_minutes=4,
        load_distribution="Default"
    )])


# Create Network Interfaces
nic1 = azure_native.network.NetworkInterface("nic1",
    resource_group_name=resource_group.name,
    network_interface_name=resource_group.name.apply(lambda name: f"{name}-nic1"),
    ip_configurations=[azure_native.network.NetworkInterfaceIPConfigurationArgs(
        name="ipconfig1",
        subnet=azure_native.network.SubResourceArgs(id=subnet.id),
        private_ip_allocation_method="Dynamic",
        load_balancer_backend_address_pools=[azure_native.network.SubResourceArgs(
            id=load_balancer.backend_address_pools[0].id
        )]
    )],
    network_security_group=azure_native.network.SubResourceArgs(id=network_security_group.id))


# Create Network Interfaces
nic2 = azure_native.network.NetworkInterface("nic2",
    resource_group_name=resource_group.name,
    network_interface_name=resource_group.name.apply(lambda name: f"{name}-nic2"),
    ip_configurations=[azure_native.network.NetworkInterfaceIPConfigurationArgs(
        name="ipconfig1",
        subnet=azure_native.network.SubResourceArgs(id=subnet.id),
        private_ip_allocation_method="Dynamic",
        load_balancer_backend_address_pools=[azure_native.network.SubResourceArgs(
            id=load_balancer.backend_address_pools[0].id
        )]
    )],
    network_security_group=azure_native.network.SubResourceArgs(id=network_security_group.id))

# Create vm1
vm_name1 = resource_group.name.apply(lambda name: f"{name}-vm1")
vm1 = azure_native.compute.VirtualMachine("vm1",
    resource_group_name=resource_group.name,
    vm_name=vm_name1,
    network_profile=azure_native.compute.NetworkProfileArgs(
        network_interfaces=[azure_native.compute.NetworkInterfaceReferenceArgs(
            id=nic1.id
        )]
    ),
    hardware_profile=azure_native.compute.HardwareProfileArgs(vm_size="Standard_B2s"),
    storage_profile=azure_native.compute.StorageProfileArgs(
        os_disk=azure_native.compute.OSDiskArgs(create_option="FromImage"),
        image_reference=azure_native.compute.ImageReferenceArgs(
            publisher="Canonical",
            offer="0001-com-ubuntu-server-jammy",
            sku="22_04-lts",
            version="latest"
        )
    ),
    os_profile=azure_native.compute.OSProfileArgs(
        computer_name="vm1",
        admin_username="azureuser",
        admin_password="GanzGeheim123!"
    ))

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

# Create vm2
vm_name2 = resource_group.name.apply(lambda name: f"{name}-vm2")
vm2 = azure_native.compute.VirtualMachine("vm2",
    resource_group_name=resource_group.name,
    vm_name=vm_name2,
    network_profile=azure_native.compute.NetworkProfileArgs(
        network_interfaces=[azure_native.compute.NetworkInterfaceReferenceArgs(
            id=nic2.id
        )]
    ),
    hardware_profile=azure_native.compute.HardwareProfileArgs(vm_size="Standard_B2s"),
    storage_profile=azure_native.compute.StorageProfileArgs(
        os_disk=azure_native.compute.OSDiskArgs(create_option="FromImage"),
        image_reference=azure_native.compute.ImageReferenceArgs(
            publisher="Canonical",
            offer="0001-com-ubuntu-server-jammy",
            sku="22_04-lts",
            version="latest"
        )
    ),
    os_profile=azure_native.compute.OSProfileArgs(
        computer_name="vm2",
        admin_username="azureuser",
        admin_password="GanzGeheim123!"
    ))

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

# Export the public IP address
pulumi.export("publicIpAddress", public_ip.ip_address)
pulumi.export("vm1_ip", nic1.ip_configurations[0].private_ip_address)
pulumi.export("vm2_ip", nic2.ip_configurations[0].private_ip_address)



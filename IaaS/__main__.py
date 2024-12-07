import pulumi
import pulumi_azure_native as azure_native
import pulumi
#create a venv with pyhton 3.9 and install requirements there - AD commands/packages work there for some reason
import pulumi_azuread as azuread
from pulumi_azure_native import authorization
import uuid


# Konfigurationseinstellungen laden
config = pulumi.Config()
azure_location = config.get("azure-native:location") or "germanywestcentral"
email_david = "wi22b116@technikum-wien.at"  # Email for RBAC (David)
email_matthias = "wi22b113@technikum-wien.at" # Email for RBAC (Matthias)
subscription_id = config.require("subscription_id")


# **Step 1: Erstellen einer Resource Group**
# Die Resource Group bündelt alle Ressourcen für eine einfache Verwaltung.
resource_group = azure_native.resources.ResourceGroup("myResourceGroup",
    resource_group_name="IaaS-mtdb-ResourceGroup",
)


# Fetch Azure AD Users
user_david = azuread.get_user(user_principal_name=email_david)
user_matthias = azuread.get_user(user_principal_name=email_matthias)


# Assign Reader Role to a User
def assign_reader_role(user_object_id, resource_group, role_name_suffix):
    """
    Assigns the Reader role to a specified user for the given resource group.
    """
    reader_role_definition_id = (
        f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/"
        "roleDefinitions/acdd72a7-3385-48ef-bd42-f606fba81ae7"
    )
    role_assignment_name = str(uuid.uuid4())
    role_assignment = authorization.RoleAssignment(
        f"readerRoleAssignment-{role_name_suffix}-{role_assignment_name}",
        scope=resource_group.id,
        role_assignment_name=role_assignment_name,
        principal_id=user_object_id,
        role_definition_id=reader_role_definition_id,
        principal_type="User",
    )
    return role_assignment.id

# Assign roles for both users
role_assignment_id_david = assign_reader_role(user_david.object_id, resource_group, "david")
role_assignment_id_matthias = assign_reader_role(user_matthias.object_id, resource_group, "matthias")


storage_account = azure_native.storage.StorageAccount("storageaccount",
    resource_group_name=resource_group.name,
    account_name=resource_group.name.apply(lambda name: f"{name.replace('-', '').lower()}stg"),  # Storage Account Name
    location=azure_location,  # Storage Location
    sku=azure_native.storage.SkuArgs(
        name="Standard_LRS"  # Local Redundant Storage
    ),
    kind="StorageV2",  # Modern Storage Account Type
    enable_https_traffic_only=True  # For security
)


# **Step 1: Erstellen eines virtuellen Netzwerks**
# Definiert das Netzwerk für die virtuellen Maschinen und die Load Balancer-Komponenten.
virtual_network = azure_native.network.VirtualNetwork("vnet",
    resource_group_name=resource_group.name,
    virtual_network_name=resource_group.name.apply(lambda name: f"{name}-vnet"),
    address_space=azure_native.network.AddressSpaceArgs(
        address_prefixes=["10.0.0.0/16"]  # IP-Bereich des Netzwerks
    ))


# **Step 1: Erstellen eines Subnetzes**
# Subnetz für die virtuellen Maschinen innerhalb des Netzwerks.
subnet = azure_native.network.Subnet("subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=virtual_network.name,
    subnet_name=resource_group.name.apply(lambda name: f"{name}-subnet"),
    address_prefix="10.0.1.0/24"  # IP-Bereich des Subnetzes
)

# **Step 1: Erstellen einer Network Security Group (NSG)**
# Legt Sicherheitsregeln für das Netzwerk fest.
network_security_group = azure_native.network.NetworkSecurityGroup("nsg",
    resource_group_name=resource_group.name,
    network_security_group_name=resource_group.name.apply(lambda name: f"{name}-nsg"))


# **Erstellen einer Regel, die HTTP-Verkehr (Port 80) erlaubt**
security_rule = azure_native.network.SecurityRule("allow80InboundRule",
    resource_group_name=resource_group.name,
    network_security_group_name=network_security_group.name,
    security_rule_name="Allow-80-Inbound",
    priority=110,  # Priorität der Regel
    direction="Inbound",  # Eingehender Verkehr
    access="Allow",
    protocol="Tcp",
    source_port_range="*",
    destination_port_range="80",  # Port für HTTP
    source_address_prefix="*",
    destination_address_prefix="*")


# **Step 2: Erstellen einer öffentlichen IP-Adresse**
# Öffentliche IP-Adresse wird dem Load Balancer zugewiesen.
public_ip = azure_native.network.PublicIPAddress("publicIp",
    resource_group_name=resource_group.name,
    public_ip_address_name="IaaSPublicIP",
    sku=azure_native.network.PublicIPAddressSkuArgs(name="Standard"),  # SKU für hohe Verfügbarkeit
    public_ip_allocation_method="Static",  # Statische IP-Adresse
    zones=["1", "2", "3"]  # Verfügbarkeit in mehreren Zonen
)


# **Step 3: Erstellen eines Load Balancers**
# Der Load Balancer verteilt den Verkehr zwischen den virtuellen Maschinen.
load_balancer = azure_native.network.LoadBalancer("loadBalancer",
    resource_group_name=resource_group.name,
    load_balancer_name="IaaSLoadBalancer",
    sku=azure_native.network.LoadBalancerSkuArgs(name="Standard"),
    frontend_ip_configurations=[azure_native.network.FrontendIPConfigurationArgs(
        name="myFrontEnd",
        public_ip_address=azure_native.network.PublicIPAddressArgs(
            id=public_ip.id  # Verknüpfung mit der öffentlichen IP
        )
    )],
    backend_address_pools=[azure_native.network.BackendAddressPoolArgs(name="myBackEndPool")],  # Backend-Pool
    probes=[azure_native.network.ProbeArgs(
        name="httpProbe",  # Health Probe für die Überwachung der VMs
        protocol="Http",
        port=80,  # Überwachung von HTTP auf Port 80
        request_path="/",
        interval_in_seconds=15,
        number_of_probes=2
    )],
    load_balancing_rules=[azure_native.network.LoadBalancingRuleArgs(
        name="httpRule",
        frontend_ip_configuration=azure_native.network.SubResourceArgs(
            id=f"/subscriptions/{pulumi.Config().require('subscription_id')}/resourceGroups/IaaS-mtdb-ResourceGroup/providers/Microsoft.Network/loadBalancers/IaaSLoadBalancer/frontendIPConfigurations/myFrontEnd"
        ),
        backend_address_pool=azure_native.network.SubResourceArgs(
            id=f"/subscriptions/{pulumi.Config().require('subscription_id')}/resourceGroups/IaaS-mtdb-ResourceGroup/providers/Microsoft.Network/loadBalancers/IaaSLoadBalancer/backendAddressPools/myBackEndPool"
        ),
        probe=azure_native.network.SubResourceArgs(
            id=f"/subscriptions/{pulumi.Config().require('subscription_id')}/resourceGroups/IaaS-mtdb-ResourceGroup/providers/Microsoft.Network/loadBalancers/IaaSLoadBalancer/probes/httpProbe"
        ),
        protocol="Tcp",
        frontend_port=80,  # Eingangsport
        backend_port=80,  # Weiterleitung an Backend-Port
        enable_floating_ip=False,
        idle_timeout_in_minutes=4,
        load_distribution="Default"
    )]
)


# **Step 4: Erstellen von Netzwerk-Schnittstellen für die VMs**
# Netzwerk-Interface für VM1
nic1 = azure_native.network.NetworkInterface("nic1",
    resource_group_name=resource_group.name,
    network_interface_name=resource_group.name.apply(lambda name: f"{name}-nic1"),
    ip_configurations=[azure_native.network.NetworkInterfaceIPConfigurationArgs(
        name="ipconfig1",
        subnet=azure_native.network.SubResourceArgs(id=subnet.id),  # Verbindung mit dem Subnetz
        private_ip_allocation_method="Dynamic",
        load_balancer_backend_address_pools=[azure_native.network.SubResourceArgs(
            id=load_balancer.backend_address_pools[0].id
        )]
    )],
    network_security_group=azure_native.network.SubResourceArgs(id=network_security_group.id))


# Netzwerk-Interface für VM2
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


# **Step 5: Create Managed Disks and Attach to VMs**
# Managed Disk for VM1 (Data Disk 1)
data_disk_vm1 = azure_native.compute.Disk("dataDiskVm1",
    resource_group_name=resource_group.name,
    location=azure_location,
    disk_name="dataDiskVm1",
    sku=azure_native.compute.DiskSkuArgs(
        name="Standard_LRS"
    ),
    disk_size_gb=64,  # Size in GB
    creation_data=azure_native.compute.CreationDataArgs(
        create_option="Empty"  # Empty disk
    )
)


# Managed Disk for VM2 (Data Disk 2)
data_disk_vm2 = azure_native.compute.Disk("dataDiskVm2",
    resource_group_name=resource_group.name,
    location=azure_location,
    disk_name="dataDiskVm2",
    sku=azure_native.compute.DiskSkuArgs(
        name="Standard_LRS"
    ),
    disk_size_gb=64,  # Size in GB
    creation_data=azure_native.compute.CreationDataArgs(
        create_option="Empty"  # Empty disk
    )
)


# Configure the storage account for boot diagnostics
vm_diagnostics_settings = {
    "enabled": True,
    "storage_uri": storage_account.primary_endpoints.apply(lambda e: e["blob"])
}


# **Step 6: Erstellen der virtuellen Maschinen**
# Definition von VM1
vm1 = azure_native.compute.VirtualMachine("vm1",
    resource_group_name=resource_group.name,
    vm_name=resource_group.name.apply(lambda name: f"{name}-vm1"),
    network_profile=azure_native.compute.NetworkProfileArgs(
        network_interfaces=[azure_native.compute.NetworkInterfaceReferenceArgs(
            id=nic1.id
        )]
    ),
    diagnostics_profile=azure_native.compute.DiagnosticsProfileArgs(
        boot_diagnostics=azure_native.compute.BootDiagnosticsArgs(**vm_diagnostics_settings)
    ),
    hardware_profile=azure_native.compute.HardwareProfileArgs(vm_size="Standard_B2s"),
    storage_profile=azure_native.compute.StorageProfileArgs(
        os_disk=azure_native.compute.OSDiskArgs(create_option="FromImage"),
        data_disks=[azure_native.compute.DataDiskArgs(
            lun=0,  # Logical Unit Number for the disk
            create_option="Attach",
            managed_disk=azure_native.compute.ManagedDiskParametersArgs(
                id=data_disk_vm1.id
            )
        )],
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
    )
)


# Installation von Nginx auf VM1
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


# Definition von VM2 (gleich wie VM1)
vm2 = azure_native.compute.VirtualMachine("vm2",
    resource_group_name=resource_group.name,
    vm_name=resource_group.name.apply(lambda name: f"{name}-vm2"),
    network_profile=azure_native.compute.NetworkProfileArgs(
        network_interfaces=[azure_native.compute.NetworkInterfaceReferenceArgs(
            id=nic2.id
        )]
    ),
    diagnostics_profile=azure_native.compute.DiagnosticsProfileArgs(
        boot_diagnostics=azure_native.compute.BootDiagnosticsArgs(**vm_diagnostics_settings)
    ),
    hardware_profile=azure_native.compute.HardwareProfileArgs(vm_size="Standard_B2s"),
    storage_profile=azure_native.compute.StorageProfileArgs(
        os_disk=azure_native.compute.OSDiskArgs(create_option="FromImage"),
        data_disks=[azure_native.compute.DataDiskArgs(
            lun=0,  # Logical Unit Number for the disk
            create_option="Attach",
            managed_disk=azure_native.compute.ManagedDiskParametersArgs(
                id=data_disk_vm2.id
            )
        )],
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
    )
)


# Installation von Nginx auf VM2
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


# Exports
pulumi.export("publicIpAddress", public_ip.ip_address)
pulumi.export("vm1_ip", nic1.ip_configurations[0].private_ip_address)
pulumi.export("vm2_ip", nic2.ip_configurations[0].private_ip_address)

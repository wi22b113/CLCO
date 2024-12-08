import pulumi
import pulumi_azure_native as azure_native
from pulumi_azure_native import insights
import pulumi_azuread as azuread
from pulumi_azure_native import authorization
import uuid

# Configuration
config = pulumi.Config()
azure_location = config.get("azure-native:location") or "germanywestcentral"
email_david = "wi22b116@technikum-wien.at"
email_matthias = "wi22b113@technikum-wien.at"
subscription_id = config.require("subscription_id")

# Resource Group
resource_group = azure_native.resources.ResourceGroup("myResourceGroup",
    resource_group_name="IaaS-mtdb-ResourceGroup",
)

# Fetch Azure AD Users
user_david = azuread.get_user(user_principal_name=email_david)
user_matthias = azuread.get_user(user_principal_name=email_matthias)

# Assign Reader Role
def assign_reader_role(user_object_id, resource_group, role_name_suffix):
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

role_assignment_id_david = assign_reader_role(user_david.object_id, resource_group, "david")
role_assignment_id_matthias = assign_reader_role(user_matthias.object_id, resource_group, "matthias")

# Storage Account
storage_account = azure_native.storage.StorageAccount("storageaccount",
    resource_group_name=resource_group.name,
    account_name="mtdbmetricsstorage8",
    location=azure_location,
    sku=azure_native.storage.SkuArgs(name="Standard_LRS"),
    kind="StorageV2",
    enable_https_traffic_only=True
)

# Log Analytics Workspace
log_analytics_workspace = azure_native.operationalinsights.Workspace(
    "logAnalyticsWorkspace",
    resource_group_name=resource_group.name,
    location=azure_location,
    sku=azure_native.operationalinsights.WorkspaceSkuArgs(name="PerGB2018"),
    retention_in_days=30,
    workspace_name="IaaS-MetricsWorkspace",
)

# Virtual Network
virtual_network = azure_native.network.VirtualNetwork("vnet",
    resource_group_name=resource_group.name,
    virtual_network_name=resource_group.name.apply(lambda name: f"{name}-vnet"),
    address_space=azure_native.network.AddressSpaceArgs(address_prefixes=["10.0.0.0/16"])
)

# Subnet
subnet = azure_native.network.Subnet("subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=virtual_network.name,
    subnet_name=resource_group.name.apply(lambda name: f"{name}-subnet"),
    address_prefix="10.0.1.0/24"
)

# Network Security Group
network_security_group = azure_native.network.NetworkSecurityGroup("nsg",
    resource_group_name=resource_group.name,
    network_security_group_name=resource_group.name.apply(lambda name: f"{name}-nsg"))

# NSG Rule for HTTP
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


# NSG Rule for SSH
security_rule_ssh = azure_native.network.SecurityRule("allow22InboundRule",
    resource_group_name=resource_group.name,
    network_security_group_name=network_security_group.name,
    security_rule_name="Allow-22-Inbound",
    priority=120,
    direction="Inbound",
    access="Allow",
    protocol="Tcp",
    source_port_range="*",
    destination_port_range="22",
    source_address_prefix="*",
    destination_address_prefix="*")


# Public IP
public_ip = azure_native.network.PublicIPAddress("publicIp",
    resource_group_name=resource_group.name,
    public_ip_address_name="IaaSPublicIP",
    sku=azure_native.network.PublicIPAddressSkuArgs(name="Standard"),
    public_ip_allocation_method="Static",
    zones=["1", "2", "3"]
)

# Load Balancer
load_balancer = azure_native.network.LoadBalancer("loadBalancer",
    resource_group_name=resource_group.name,
    load_balancer_name="IaaSLoadBalancer",
    sku=azure_native.network.LoadBalancerSkuArgs(name="Standard"),
    frontend_ip_configurations=[azure_native.network.FrontendIPConfigurationArgs(
        name="myFrontEnd",
        public_ip_address=azure_native.network.PublicIPAddressArgs(id=public_ip.id)
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
            id=f"/subscriptions/{subscription_id}/resourceGroups/IaaS-mtdb-ResourceGroup/providers/Microsoft.Network/loadBalancers/IaaSLoadBalancer/frontendIPConfigurations/myFrontEnd"
        ),
        backend_address_pool=azure_native.network.SubResourceArgs(
            id=f"/subscriptions/{subscription_id}/resourceGroups/IaaS-mtdb-ResourceGroup/providers/Microsoft.Network/loadBalancers/IaaSLoadBalancer/backendAddressPools/myBackEndPool"
        ),
        probe=azure_native.network.SubResourceArgs(
            id=f"/subscriptions/{subscription_id}/resourceGroups/IaaS-mtdb-ResourceGroup/providers/Microsoft.Network/loadBalancers/IaaSLoadBalancer/probes/httpProbe"
        ),
        protocol="Tcp",
        frontend_port=80,
        backend_port=80,
        enable_floating_ip=False,
        idle_timeout_in_minutes=4,
        load_distribution="Default"
    )]
)

# NICs
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

# Managed Disks
data_disk_vm1 = azure_native.compute.Disk("dataDiskVm1",
    resource_group_name=resource_group.name,
    location=azure_location,
    disk_name="dataDiskVm1",
    sku=azure_native.compute.DiskSkuArgs(name="Standard_LRS"),
    disk_size_gb=64,
    creation_data=azure_native.compute.CreationDataArgs(create_option="Empty")
)

data_disk_vm2 = azure_native.compute.Disk("dataDiskVm2",
    resource_group_name=resource_group.name,
    location=azure_location,
    disk_name="dataDiskVm2",
    sku=azure_native.compute.DiskSkuArgs(name="Standard_LRS"),
    disk_size_gb=64,
    creation_data=azure_native.compute.CreationDataArgs(create_option="Empty")
)

# Boot Diagnostics Settings
vm_diagnostics_settings = {
    "enabled": True,
    "storage_uri": storage_account.primary_endpoints.apply(lambda e: e["blob"])
}

# VMs
vm1 = azure_native.compute.VirtualMachine("vm1",
    resource_group_name=resource_group.name,
    vm_name=resource_group.name.apply(lambda name: f"{name}-vm1"),
    network_profile=azure_native.compute.NetworkProfileArgs(
        network_interfaces=[azure_native.compute.NetworkInterfaceReferenceArgs(id=nic1.id)]
    ),
    diagnostics_profile=azure_native.compute.DiagnosticsProfileArgs(
        boot_diagnostics=azure_native.compute.BootDiagnosticsArgs(**vm_diagnostics_settings)
    ),
    hardware_profile=azure_native.compute.HardwareProfileArgs(vm_size="Standard_B2s"),
    storage_profile=azure_native.compute.StorageProfileArgs(
        os_disk=azure_native.compute.OSDiskArgs(create_option="FromImage"),
        data_disks=[azure_native.compute.DataDiskArgs(
            lun=0,
            create_option="Attach",
            managed_disk=azure_native.compute.ManagedDiskParametersArgs(id=data_disk_vm1.id)
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
        admin_password="GanzGeheim123!",
        linux_configuration=azure_native.compute.LinuxConfigurationArgs(
            disable_password_authentication=False
        )
    )
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
                            "echo '<head><title>Hello World 1</title></head><body><h1>Web Portal</h1><p>Hello World 1</p></body>' | sudo tee /var/www/html/index.nginx-debian.html && "
                            "sudo systemctl restart nginx"
    }
)

vm2 = azure_native.compute.VirtualMachine("vm2",
    resource_group_name=resource_group.name,
    vm_name=resource_group.name.apply(lambda name: f"{name}-vm2"),
    network_profile=azure_native.compute.NetworkProfileArgs(
        network_interfaces=[azure_native.compute.NetworkInterfaceReferenceArgs(id=nic2.id)]
    ),
    diagnostics_profile=azure_native.compute.DiagnosticsProfileArgs(
        boot_diagnostics=azure_native.compute.BootDiagnosticsArgs(**vm_diagnostics_settings)
    ),
    hardware_profile=azure_native.compute.HardwareProfileArgs(vm_size="Standard_B2s"),
    storage_profile=azure_native.compute.StorageProfileArgs(
        os_disk=azure_native.compute.OSDiskArgs(create_option="FromImage"),
        data_disks=[azure_native.compute.DataDiskArgs(
            lun=0,
            create_option="Attach",
            managed_disk=azure_native.compute.ManagedDiskParametersArgs(id=data_disk_vm2.id)
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
        admin_password="GanzGeheim123!",
        linux_configuration=azure_native.compute.LinuxConfigurationArgs(
            disable_password_authentication=False
        )
    )
)

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
                            "echo '<head><title>Hello World 2</title></head><body><h1>Web Portal</h1><p>Hello World 2</p></body>' | sudo tee /var/www/html/index.nginx-debian.html && "
                            "sudo systemctl restart nginx"
    }
)

# Diagnostic Settings to route logs/metrics to Log Analytics
vm1_diagnostic_settings = insights.DiagnosticSetting("vm1DiagnosticSettings",
    resource_uri=vm1.id,
    log_analytics_destination_type="Dedicated",
    workspace_id=log_analytics_workspace.id,
    metrics=[
        insights.MetricSettingsArgs(
            category="AllMetrics",
            enabled=True,
            retention_policy=insights.RetentionPolicyArgs(days=0, enabled=False),
        ),
    ],
)

vm2_diagnostic_settings = insights.DiagnosticSetting("vm2DiagnosticSettings",
    resource_uri=vm2.id,
    log_analytics_destination_type="Dedicated",
    workspace_id=log_analytics_workspace.id,
    metrics=[
        insights.MetricSettingsArgs(
            category="AllMetrics",
            enabled=True,
            retention_policy=insights.RetentionPolicyArgs(days=0, enabled=False),
        ),
    ],
)


action_group = insights.ActionGroup(
    "actionGroup",
    resource_group_name=resource_group.name,
    action_group_name=resource_group.name.apply(lambda name: f"{name}-actionGroup"),
    group_short_name="mtdb",
    enabled=True,
    email_receivers=[
        insights.EmailReceiverArgs(
            name="AdminEmail",
            email_address="wi22b116@technikum-wien.at"
        )
    ]
)


# Metric Alert for CPU
cpu_metric_alert_vm1 = azure_native.insights.MetricAlert(
    "cpuMetricAlertVM1",
    location="global",
    resource_group_name=resource_group.name,
    rule_name="HighCPUUsageAlertVM1",
    description="Alert when CPU usage exceeds 80% over a 5-minute period",
    severity=3,
    enabled=True,
    scopes=[vm1.id],
    criteria={
        "odataType": "Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria",
        "allOf": [
            {
                "criterionType": "StaticThresholdCriterion",
                "name": "HighCPUUsage",
                "metricName": "Percentage CPU",
                "metricNamespace": "Microsoft.Compute/virtualMachines",
                "timeAggregation": azure_native.insights.AggregationTypeEnum.AVERAGE,
                "operator": azure_native.insights.Operator.GREATER_THAN,
                "threshold": 80,
            }
        ]
    },
    actions=[
        {
            "actionGroupId": action_group.id
        }
    ],
    evaluation_frequency="PT1M",
    window_size="PT5M",
)

cpu_metric_alert_vm2 = azure_native.insights.MetricAlert(
    "cpuMetricAlertVM2",
    location="global",
    resource_group_name=resource_group.name,
    rule_name="HighCPUUsageAlertVM2",
    description="Alert when CPU usage exceeds 80% over a 5-minute period",
    severity=3,
    enabled=True,
    scopes=[vm1.id],
    criteria={
        "odataType": "Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria",
        "allOf": [
            {
                "criterionType": "StaticThresholdCriterion",
                "name": "HighCPUUsage",
                "metricName": "Percentage CPU",
                "metricNamespace": "Microsoft.Compute/virtualMachines",
                "timeAggregation": azure_native.insights.AggregationTypeEnum.AVERAGE,
                "operator": azure_native.insights.Operator.GREATER_THAN,
                "threshold": 80,
            }
        ]
    },
    actions=[
        {
            "actionGroupId": action_group.id
        }
    ],
    evaluation_frequency="PT1M",
    window_size="PT5M",
)

# Exports
pulumi.export("publicIpAddress", public_ip.ip_address)
pulumi.export("vm1_ip", nic1.ip_configurations[0].private_ip_address)
pulumi.export("vm2_ip", nic2.ip_configurations[0].private_ip_address)

import pulumi
from pulumi import Config, Output
from pulumi_azure_native import resources, network, cognitiveservices, web
import pulumi_azure_native as azure_native
from pulumi_random import RandomString

# Configuration variables
config = Config()
azure_location = config.get("azure-native:location") or "westeurope"
defined_repo_url = config.get("my:repoUrl") or "https://github.com/wi22b113/clco-demo/"
defined_branch = config.get("my:branch") or "main"

# Resource Group
resource_group = resources.ResourceGroup('A7resourceGroup',
    location=azure_location
)

# Use random strings to give the Webappunique DNS names
webapp_name_label1 = RandomString(
    "flaskwebapp-",
    length=8,
    upper=False,
    special=False,
).result.apply(lambda result: f"{web_app}-{result}")

# Virtual Network
virtual_network = network.VirtualNetwork('virtualNetwork',
    resource_group_name=resource_group.name,
    location=azure_location,
    address_space=network.AddressSpaceArgs(
        address_prefixes=['10.0.0.0/16']
    ),
    virtual_network_name='A7-VNet'
)

# App Subnet
app_subnet = network.Subnet('applicationSubnet',
    resource_group_name=resource_group.name,
    virtual_network_name=virtual_network.name,
    subnet_name='applicationSubnet',
    address_prefix='10.0.0.0/24',
    delegations=[
        network.DelegationArgs(
            name='delegation',
            service_name='Microsoft.Web/serverfarms',
        )
    ],
    private_endpoint_network_policies='Enabled'
)

# Endpoint Subnet
endpoint_subnet = network.Subnet('endpointSubnet',
    resource_group_name=resource_group.name,
    virtual_network_name=virtual_network.name,
    subnet_name='endpointSubnet',
    address_prefix='10.0.1.0/24',
    private_endpoint_network_policies='Disabled'
)

# Private DNS Zone
dns_zone = network.PrivateZone('dnsZone',
    resource_group_name=resource_group.name,
    location='global',
    private_zone_name='privatelink.cognitiveservices.azure.com'
)

# Cognitive Services Account
language_account = azure_native.cognitiveservices.Account(
    "languageAccount",
    resource_group_name=resource_group.name,
    account_name="A7-mt-LanguageService",
    location=azure_location,
    kind="TextAnalytics",  # Change to 'Language' if needed
    sku=azure_native.cognitiveservices.SkuArgs(
        name="F0"
    ),
    properties=azure_native.cognitiveservices.AccountPropertiesArgs(
        public_network_access="Disabled",
        custom_sub_domain_name="A7-mt-LanguageService",
        restore=True  # Add this line to restore the soft-deleted resource
    ),
    identity=azure_native.cognitiveservices.IdentityArgs(
        type="SystemAssigned"
    )
)


# Get Account Keys
account_keys = cognitiveservices.list_account_keys_output(
    resource_group_name=resource_group.name,
    account_name=language_account.name
)

# DNS Zone Virtual Network Link
dns_zone_vnet_link = network.VirtualNetworkLink('dnsZoneVirtualNetworkLink',
    resource_group_name=resource_group.name,
    private_zone_name=dns_zone.name,
    location='global',
    virtual_network=network.SubResourceArgs(
        id=virtual_network.id
    ),
    registration_enabled=False,
    virtual_network_link_name='cognitiveservices-zonelink'
)

# Private Endpoint
private_endpoint = network.PrivateEndpoint('privateEndpoint',
    resource_group_name=resource_group.name,
    location=azure_location,
    private_endpoint_name='languagePrivateEndpoint',
    subnet=network.SubnetArgs(
        id=endpoint_subnet.id
    ),
    private_link_service_connections=[
        network.PrivateLinkServiceConnectionArgs(
            name='languageServiceConnection',
            private_link_service_id=language_account.id,
            group_ids=['account']
        )
    ]
)

# Private DNS Zone Group
private_dns_zone_group = network.PrivateDnsZoneGroup('privateDnsZoneGroup',
    resource_group_name=resource_group.name,
    private_endpoint_name=private_endpoint.name,
    private_dns_zone_group_name='languagePrivateDnsZoneGroup',
    private_dns_zone_configs=[
        network.PrivateDnsZoneConfigArgs(
            name='config',
            private_dns_zone_id=dns_zone.id
        )
    ]
)

# App Service Plan
app_service_plan = web.AppServicePlan('appServicePlan',
    resource_group_name=resource_group.name,
    name='myWebApp-plan',
    location=azure_location,
    sku=web.SkuDescriptionArgs(
        name='B1',
        tier='Basic'
    ),
    kind='linux',
    reserved=True
)

# Web App
web_app = web.WebApp('webApp',
    resource_group_name=resource_group.name,
    name="a7-mt-webapp",
    location=azure_location,
    server_farm_id=app_service_plan.id,
    https_only=True,
    kind='app,linux',
    site_config=web.SiteConfigArgs(
        linux_fx_version='PYTHON|3.8',
        app_settings=[
            web.NameValuePairArgs(
                name='AZ_ENDPOINT',
                value=pulumi.Output.concat("https://", language_account.name, ".cognitiveservices.azure.com/")
            ),
            web.NameValuePairArgs(
                name='AZ_KEY',
                value=account_keys.key1
            ),
            web.NameValuePairArgs(
                name='WEBSITE_RUN_FROM_PACKAGE',
                value='0'
            ),
        ],
        always_on=True,
        ftps_state='Disabled'
    )
)

# VNet Integration
vnet_integration = web.WebAppSwiftVirtualNetworkConnection('vnetIntegration',
    name=web_app.name,
    resource_group_name=resource_group.name,
    subnet_resource_id=app_subnet.id
)

source_control = azure_native.web.WebAppSourceControl("sourceControl",
    name=web_app.name,
    resource_group_name=resource_group.name,
    repo_url=defined_repo_url,  # Replace with your repository URL
    branch=defined_branch,  # Replace with your branch name
    is_manual_integration=True,
    deployment_rollback_enabled=False
)

# Export the Web App hostname as a Markdown link
pulumi.export("hostname", pulumi.Output.concat("[Web App](http://", web_app.default_host_name, ")"))
pulumi.export("account_id", language_account.id)
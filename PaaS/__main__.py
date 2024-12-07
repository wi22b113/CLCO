import pulumi
from pulumi import Config, Output
from pulumi_azure_native import resources, network, cognitiveservices, web
import pulumi_azure_native as azure_native
#from pulumi_random import RandomString

# Laden der Konfigurationen, um benutzerdefinierte Werte zu verwenden
# azure_location: Standort, an dem alle Ressourcen bereitgestellt werden
# defined_repo_url: URL des GitHub-Repositories für die Web-App
# defined_branch: Git-Branch für die Web-App-Quellen
config = Config()
azure_location = config.get("azure-native:location") or "westeurope"
defined_repo_url = config.get("my:repoUrl") or "https://github.com/wi22b113/clco-demo/"
defined_branch = config.get("my:branch") or "main"
subscription_id = "1b744ae6-c1ae-4bce-8d17-b6bdf7ffee00"
email = "wi22b113@technikum-wien.at"
start_date = datetime(2024, 12, 1).strftime('%Y-%m-%dT%H:%M:%SZ')  # Startdatum: 1. November 2024
end_date = datetime(2025, 2, 28).strftime('%Y-%m-%dT%H:%M:%SZ')

# Erstellung einer Azure Resource Group
# Diese Ressourcengruppe enthält alle Ressourcen, die im Skript erstellt werden
resource_group = resources.ResourceGroup('PaaS-ResourceGroup',
    location=azure_location,
    resource_group_name='PaaS-ResourceGroup'
)

# Generieren eines zufälligen DNS-Namens für die Web-App
# Dieser sorgt dafür, dass der Name weltweit eindeutig bleibt
#webapp_name_label1 = RandomString(
#    "PaaS-webapp-",
#    length=8,
#    upper=False,
#    special=False,
#).result.apply(lambda result: f"{web_app}-{result}")

# Erstellen eines virtuellen Netzwerks (VNet) für die App und die Azure AI Services
# address_prefixes: Definiert den IP-Adressraum für das Netzwerk
virtual_network = network.VirtualNetwork('virtualNetwork',
    resource_group_name=resource_group.name,
    location=azure_location,
    address_space=network.AddressSpaceArgs(
        address_prefixes=['10.0.0.0/16']
    ),
    virtual_network_name='PaaS-VNet'
)

# Subnetz für die Web-App
# Dient der Unterteilung des virtuellen Netzwerks und der Bereitstellung der App
app_subnet = network.Subnet('applicationSubnet',
    resource_group_name=resource_group.name,
    virtual_network_name=virtual_network.name,
    subnet_name='applicationSubnet',
    address_prefix='10.0.0.0/24',  # IP-Adressbereich für das Subnetz
    delegations=[
        network.DelegationArgs(
            name='delegation',
            service_name='Microsoft.Web/serverfarms',  # Delegiert an Web-Dienste
        )
    ],
    private_endpoint_network_policies='Enabled'  # Aktiviert Richtlinien für private Endpoints
)

# Subnetz für die Verbindung des Cognitive Services über einen privaten Endpoint
endpoint_subnet = network.Subnet('endpointSubnet',
    resource_group_name=resource_group.name,
    virtual_network_name=virtual_network.name,
    subnet_name='endpointSubnet',
    address_prefix='10.0.1.0/24',
    private_endpoint_network_policies='Disabled'  # Richtlinien für privaten Netzwerkzugang deaktiviert
)

# Private DNS-Zone, um den KI-Dienst innerhalb des Netzwerks aufzulösen
dns_zone = network.PrivateZone('dnsZone',
    resource_group_name=resource_group.name,
    location='global',
    private_zone_name='privatelink.cognitiveservices.azure.com'
)

# Erstellung eines Cognitive Services Accounts für Sentiment Analysis
language_account = azure_native.cognitiveservices.Account(
    "languageAccount",
    resource_group_name=resource_group.name,
    account_name="PaaS-LanguageService",
    location=azure_location,
    kind="TextAnalytics",  # Legt den Typ des Cognitive Services fest
    sku=azure_native.cognitiveservices.SkuArgs(
        name="F0"  # F0 ist die kostenlose Stufe
    ),
    properties=azure_native.cognitiveservices.AccountPropertiesArgs(
        public_network_access="Disabled",  # Verhindert öffentlichen Netzwerkzugang
        custom_sub_domain_name="PaaS-LanguageService",
        restore=True  # Versucht, einen gelöschten Account wiederherzustellen
    ),
    identity=azure_native.cognitiveservices.IdentityArgs(
        type="SystemAssigned"  # Verwendet systemzugewiesene Identität für Authentifizierung
    )
)

# Abrufen der Zugriffsschlüssel für den Cognitive Service Account
account_keys = cognitiveservices.list_account_keys_output(
    resource_group_name=resource_group.name,
    account_name=language_account.name
)

# Verknüpfung der privaten DNS-Zone mit dem virtuellen Netzwerk
# Diese Verknüpfung ermöglicht die Namensauflösung im Netzwerk
dns_zone_vnet_link = network.VirtualNetworkLink('dnsZoneVirtualNetworkLink',
    resource_group_name=resource_group.name,
    private_zone_name=dns_zone.name,
    location='global',
    virtual_network=network.SubResourceArgs(
        id=virtual_network.id
    ),
    registration_enabled=False,  # DNS-Registrierung deaktiviert
    virtual_network_link_name='cognitiveservices-zonelink'
)

# Privater Endpoint für den Cognitive Service
# Ermöglicht den Zugriff auf den Dienst über das private Netzwerk
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
            group_ids=['account']  # Gibt an, welche Dienste verknüpft werden
        )
    ]
)

# Konfiguration einer privaten DNS-Zonen-Gruppe für den Endpoint
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

# Erstellung eines App Service Plans für die Web-App
# Der Plan bestimmt die zugrunde liegende Infrastruktur
app_service_plan = web.AppServicePlan('appServicePlan',
    resource_group_name=resource_group.name,
    name='Paas-WebAppplan',
    location=azure_location,
    sku=web.SkuDescriptionArgs(
        name='B1',  # Kostengünstige Basis-Stufe
        tier='Basic',
        capacity=3
    ),
    kind='linux',  # Für Linux-basierte Web-Apps
    reserved=True
)

budget = resource_group.name.apply(lambda rg_name: consumption.Budget(
    resource_name="PaaS-Budget",  # Name des Budgets
    scope=f"/subscriptions/{subscription_id}/resourceGroups/{rg_name}",  # Begrenzung auf die Resource Group
    amount=50,  # Budgetbetrag
    time_grain="Monthly",  # Budget-Rücksetzintervall
    time_period={
        "startDate": start_date,  # Startdatum des Budgets
        "endDate": end_date,  # Enddatum des Budgets
    },
    notifications={
        "Actual50Percent": {  # Benachrichtigung, wenn 50 % des Budgets erreicht werden
            "enabled": True,
            "operator": "GreaterThan",  # Bedingung: Budget überschritten
            "threshold": 75,  # 50 % des Budgets
            "contact_emails": [email],  # E-Mail-Adresse für Benachrichtigungen
            "contact_roles": [],  # Keine spezifischen Rollen
            "notification_language": "en-US",  # Sprache der Benachrichtigung
        },
        "Actual90Percent": {  # Benachrichtigung, wenn 90 % des Budgets erreicht werden
            "enabled": True,
            "operator": "GreaterThan",
            "threshold": 90,  # 90 % des Budgets
            "contact_emails": [email],
            "contact_roles": [],
            "notification_language": "en-US",
        },
    },
    category="Cost",  # Budget für Kostenüberwachung
))

# Web App
web_app = web.WebApp('webApp',
    resource_group_name=resource_group.name,
    name="PaaS-dbmt-webapp",
    location=azure_location,
    server_farm_id=app_service_plan.id,
    https_only=True,
    kind='app,linux',
    site_config=web.SiteConfigArgs(
        linux_fx_version='PYTHON|3.9',
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
# Exportieren von Informationen für weitere Nutzung
# Hostname der Web-App und ID des Cognitive Services‚
pulumi.export("hostname", pulumi.Output.concat("[Web App](http://", web_app.default_host_name, ")"))
pulumi.export("account_id", language_account.id)
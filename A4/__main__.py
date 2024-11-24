import pulumi
from pulumi_azure_native import resources, storage, web, insights
from pulumi import FileAsset

# Erstellen einer Ressourcengruppe
# Dies ist die zentrale Einheit, in der alle Ressourcen gespeichert werden.
resource_group = resources.ResourceGroup("a4-resourcegroup", location="eastus")

# Erstellen eines Storage-Accounts
# Der Storage-Account dient zur Speicherung von Daten (z. B. Blobs).
storage_account = storage.StorageAccount("storageaccount",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=storage.SkuArgs(name="Standard_LRS"),  # Standard LRS-Speicher für Kosteneffizienz
    kind="StorageV2",  # Neuere Version des Speicherdiensts
    allow_blob_public_access=True  # Aktiviert den öffentlichen Zugriff auf Blobs
)

# Erstellen eines Blob-Containers
# Container für die Speicherung von Dateien im Blob-Speicher.
blob_container = storage.BlobContainer("blobcontainer",
    account_name=storage_account.name,
    resource_group_name=resource_group.name,
    public_access="Blob"  # Ermöglicht öffentlichen Lesezugriff auf Dateien
)

# Hochladen einer Datei in den Blob-Container
# Lädt eine ZIP-Datei mit der Hello-World-Anwendung in den Blob-Speicher hoch.
app_blob = storage.Blob("helloworldappzip",
    resource_group_name=resource_group.name,
    account_name=storage_account.name,
    container_name=blob_container.name,
    source=FileAsset("./helloworld.zip")  # Pfad zur ZIP-Datei
)

# Generieren der Blob-URL
# Erstellt die URL der hochgeladenen Datei, die in der Web-App verwendet wird.
blob_url = pulumi.Output.concat("https://", storage_account.name, ".blob.core.windows.net/", blob_container.name, "/", app_blob.name)

# Erstellen eines App Service Plans
# Definiert die Infrastruktur für die Web-App.
app_service_plan = web.AppServicePlan("appserviceplan",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    kind="Linux",  # Linux-basierte App
    reserved=True,  # Erforderlich für Linux-Pläne
    sku=web.SkuDescriptionArgs(
        tier="Free", # Kostenlose Tier-Stufe
        name="F1"
    )  
)


# Application Insights erstellen
app_insights = insights.Component("appinsights",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    application_type="web",  # Typ: Web-Anwendung
    kind="web",  # Art der Insights
    ingestion_mode="ApplicationInsights"  # Datenflussmodus
)


# Erstellen einer Web-App
# Die Web-App wird mit der hochgeladenen ZIP-Datei verbunden.
web_app = web.WebApp("webapp",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    server_farm_id=app_service_plan.id,  # Verknüpft mit dem App Service Plan
    site_config=web.SiteConfigArgs(
        app_settings=[
            web.NameValuePairArgs(name="WEBSITE_RUN_FROM_PACKAGE", value=blob_url),  # Konfiguriert die Anwendung
        ],
        linux_fx_version="PYTHON|3.11",  # Python 3.11 als Laufzeitumgebung
    )
)

# Outputs exportieren
pulumi.export("resource_group_name", resource_group.name)
pulumi.export("resource_group_location", resource_group.location)
pulumi.export("storage_account_name", storage_account.name)
pulumi.export("storage_account_sku", storage_account.sku.name)
pulumi.export("storage_account_kind", storage_account.kind)
pulumi.export("blob_container_account_name", storage_account.name)
pulumi.export("blob_container_name", blob_container.name)
pulumi.export("blob_url", blob_url)
pulumi.export("app_service_plan_name", app_service_plan.name)
pulumi.export("app_service_plan_sku_tier", app_service_plan.sku.tier)
pulumi.export("app_service_plan_kind", app_service_plan.kind)
pulumi.export("app_insights_name", app_insights.name)
pulumi.export("app_insights_application_type", app_insights.application_type)
pulumi.export("app_insights_kind", app_insights.kind)
pulumi.export("web_app_name", web_app.name)
pulumi.export("web_app_url", web_app.default_host_name)
pulumi.export("web_app_location", web_app.location)
pulumi.export("web_app_linux_fx_version", web_app.site_config.linux_fx_version)
pulumi.export("web_app_storage_account_name", storage_account.name)
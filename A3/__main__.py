"""Ein Azure RM Python Pulumi Programm"""

import pulumi  # Importiert das Pulumi-Modul für Infrastruktur als Code
from pulumi_azure_native import resources, web, storage  # Importiert Azure Native Module für Ressourcen, Web und Speicher
from pulumi import FileArchive, Output  # Importiert FileArchive und Output von Pulumi

# Gewünschte Region festlegen
location = 'eastus2'  # Setzt die Region für die Ressourcenbereitstellung auf 'eastus2'

# Resource Group erstellen
resource_group = resources.ResourceGroup('a3-resource_group', location=location)  # Erstellt eine Ressourcengruppe in der angegebenen Region

# Storage Account erstellen
storage_account = storage.StorageAccount(
    'storageaccount',  # Name des Speicherkontos
    resource_group_name=resource_group.name,  # Name der Ressourcengruppe
    location=resource_group.location,  # Region des Speicherkontos
    kind=storage.Kind.STORAGE_V2,  # Typ des Speicherkontos
    sku=storage.SkuArgs(
        name=storage.SkuName.STANDARD_LRS,  # SKU des Speicherkontos (Standard-LRS)
    )
)

# Blob Container erstellen
container = storage.BlobContainer(
    'zips',  # Name des Blob-Containers
    resource_group_name=resource_group.name,  # Name der Ressourcengruppe
    account_name=storage_account.name,  # Name des Speicherkontos
    public_access=storage.PublicAccess.NONE  # Sicherer Zugriff (kein öffentlicher Zugriff)
)

# Anwendungscode packen und hochladen
app_code_archive = FileArchive('./clco-demo')  # Pfad zum Anwendungscode-Archiv

zip_blob = storage.Blob(
    'app-zip',  # Name des Blobs
    resource_group_name=resource_group.name,  # Name der Ressourcengruppe
    account_name=storage_account.name,  # Name des Speicherkontos
    container_name=container.name,  # Name des Blob-Containers
    blob_name='app.zip',  # Name der Blob-Datei
    type=storage.BlobType.BLOCK,  # Typ des Blobs (Block)
    source=app_code_archive,  # Quelle des Blobs (Anwendungscode-Archiv)
    content_type='application/zip',  # Inhaltstyp des Blobs
)

# Blob-URL erstellen
blob_url = pulumi.Output.concat(
    "https://",  # Protokoll
    storage_account.name,  # Name des Speicherkontos
    ".blob.core.windows.net/",  # Blob-Dienst-URL
    container.name,  # Name des Blob-Containers
    "/",  # Trennzeichen
    zip_blob.name  # Name des Blobs
)

# SAS-Token generieren
def signed_blob_read_url(args):
    blob_url, account_name, resource_group_name, container_name, blob_name = args
    sas = storage.list_storage_account_service_sas(
        account_name=account_name,  # Name des Speicherkontos
        protocols=storage.HttpProtocol.HTTPS,  # Protokoll (HTTPS)
        shared_access_start_time="2021-01-01",  # Startzeit des SAS-Tokens
        shared_access_expiry_time="2030-01-01",  # Ablaufzeit des SAS-Tokens
        resource=storage.SignedResource.B,  # Signierte Ressource (Blob)
        resource_group_name=resource_group_name,  # Name der Ressourcengruppe
        permissions=storage.Permissions.R,  # Berechtigungen (Lesen)
        canonicalized_resource=f"/blob/{account_name}/{container_name}/{blob_name}",  # Kanonische Ressource
    )
    return pulumi.Output.concat(blob_url, "?", sas.service_sas_token)  # Generiert die vollständige URL mit SAS-Token

# App Service Plan erstellen
app_service_plan = web.AppServicePlan(
    'appserviceplan',  # Name des App Service Plans
    resource_group_name=resource_group.name,  # Name der Ressourcengruppe
    location=resource_group.location,  # Region des App Service Plans
    kind='Linux',  # Typ des App Service Plans (Linux)
    reserved=True,  # Reserviert für Linux
    sku=web.SkuDescriptionArgs(
        name='F1',  # SKU des App Service Plans (Free Tier)
        tier='Free',  # Tier des App Service Plans (Free)
    )
)

# Web App erstellen
app = web.WebApp(
    'my-flask-app',  # Name der Web-App
    resource_group_name=resource_group.name,  # Name der Ressourcengruppe
    location=resource_group.location,  # Region der Web-App
    server_farm_id=app_service_plan.id,  # ID des App Service Plans
    site_config=web.SiteConfigArgs(
        linux_fx_version='PYTHON|3.9',  # Python-Version
        app_command_line='pip install -r /home/site/wwwroot/requirements.txt && FLASK_APP=app.py python -m flask run --host=0.0.0.0 --port=8000',  # Startbefehle für die App
    ),
    https_only=True,  # Nur HTTPS-Zugriff
)
# Alle benötigten Werte sammeln und die Funktion anwenden
package_url = pulumi.Output.all(
    blob_url,  # Blob-URL
    storage_account.name,  # Name des Speicherkontos
    resource_group.name,  # Name der Ressourcengruppe
    container.name,  # Name des Blob-Containers
    zip_blob.name  # Name des Blobs
).apply(signed_blob_read_url)  # Wendet die Funktion an, um die signierte URL des Blobs zu erhalten

# App-Einstellungen konfigurieren
app_settings = web.WebAppApplicationSettings(
    'appSettings',  # Name der App-Einstellungen
    name=app.name,  # Name der Web-App
    resource_group_name=resource_group.name,  # Name der Ressourcengruppe
    properties={
        'WEBSITE_RUN_FROM_PACKAGE': package_url,  # URL des Anwendungspakets
        'FLASK_ENV': 'development',  # Flask-Umgebung (Entwicklung)
        'FLASK_DEBUG': '1',  # Flask-Debug-Modus
        'FLASK_APP': 'app.py',  # Flask-App-Datei
    }
)

# URL der Web App ausgeben
pulumi.export('url', app.default_host_name.apply(lambda host_name: f"https://{host_name}"))  # Exportiert die URL der Web-App
pulumi.export("resource_group_name", resource_group.name)  # Exportiert den Namen der Ressourcengruppe
pulumi.export("storage_account_name", storage_account.name)  # Exportiert den Namen des Speicherkontos
pulumi.export("blob_container_name", container.name)  # Exportiert den Namen des Blob-Containers
pulumi.export("package_url", package_url)  # Exportiert die URL des Anwendungspakets
pulumi.export("blob_url", blob_url)  # Exportiert die URL des Blobs
pulumi.export("web_app_url", app.default_host_name)  # Exportiert die URL der Web-App
pulumi.export("web_app_name", app.name)  # Exportiert den Namen der Web-App
pulumi.export("app_blob_url", blob_url)  # Exportiert die URL des Blobs

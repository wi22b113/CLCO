import pulumi
from pulumi_azure_native import resources, storage, web, insights
from pulumi import FileAsset

# Step 1: Create a Resource Group
resource_group = resources.ResourceGroup("resourcegroup", location="westus")

# Step 2: Create a Storage Account
storage_account = storage.StorageAccount("storageccount",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=storage.SkuArgs(name="Standard_LRS"),
    kind="StorageV2",
    allow_blob_public_access=True
)

# Step 3: Create a Blob Container
blob_container = storage.BlobContainer("blobcontainer",
    account_name=storage_account.name,
    resource_group_name=resource_group.name,
    public_access="Blob"  # Public read access for blobs
)

# Step 4: Upload the Hello World App ZIP to the Blob Container
app_blob = storage.Blob("helloworldappzip",
    resource_group_name=resource_group.name,
    account_name=storage_account.name,
    container_name=blob_container.name,
    source=FileAsset("./helloworld.zip")  # Path to your Hello World app zip file
)

# Generate the Blob URL for deployment
blob_url = pulumi.Output.concat("https://", storage_account.name, ".blob.core.windows.net/", blob_container.name, "/", app_blob.name)

# Step 5: Create an App Service Plan (Free tier)
app_service_plan = web.AppServicePlan("appserviceplan",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    kind="Linux",  # Ensure the App Service Plan is for Linux
    reserved=True,  # Required for Linux plans
    sku=web.SkuDescriptionArgs(
        tier="Free",  # Use the Free tier for cost efficiency
        name="F1"
    )
)

## Step 6: Create Application Insights
#app_insights = insights.Component("appinsights",
#    resource_group_name=resource_group.name,
#    location=resource_group.location,
#    application_type="web",
#    kind="web",  # Set the kind of Application Insights
#    ingestion_mode="ApplicationInsights"  # Use ApplicationInsights ingestion mode
#)


# Step 6: Create a Web App and Point to the Blob
web_app = web.WebApp("webapp",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    server_farm_id=app_service_plan.id,
    site_config=web.SiteConfigArgs(
    app_settings=[
        web.NameValuePairArgs(name="WEBSITE_RUN_FROM_PACKAGE", value=blob_url),
    ],
    #app_command_line="python -m flask run --host=0.0.0.0 --port=8000"  # Flask app startup command
    ## for hello world comment this is in
    linux_fx_version="PYTHON|3.11",
    )
)

# Step 8: Export Outputs
pulumi.export("resource_group_name", resource_group.name)
pulumi.export("storage_account_name", storage_account.name)
pulumi.export("blob_container_name", blob_container.name)
pulumi.export("web_app_url", web_app.default_host_name)
pulumi.export("web_app_name", web_app.name)
pulumi.export("app_blob_url", blob_url)
pulumi.export("staticEndpoint", storage_account.primary_endpoints.web)
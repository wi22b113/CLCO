import pulumi
from pulumi_azure_native import resources, web

# Configuration values
resource_group_name = "myResourceGroup"
app_service_plan_name = "myAppServicePlan"
app_name = "myPythonApp"
location = "westeurope"
runtime = "PYTHON|3.9"  # Runtime for the app
sku_name = "F1"  # Pricing tier

# Create a Resource Group
resource_group = resources.ResourceGroup(resource_group_name, location=location)

# Create an App Service Plan
app_service_plan = web.AppServicePlan(
    app_service_plan_name,
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=web.SkuDescriptionArgs(
        name=sku_name,
        tier="Basic",
    ),
)

# Create a Web App and deploy the application package locally
web_app = web.WebApp(
    app_name,
    resource_group_name=resource_group.name,
    location=resource_group.location,
    server_farm_id=app_service_plan.id,
    site_config=web.SiteConfigArgs(
        linux_fx_version=runtime,
        app_settings=[
            web.NameValuePairArgs(name="SCM_DO_BUILD_DURING_DEPLOYMENT", value="true"),
        ],
    ),
)

# Deployment: Add a local ZIP file to deploy
import subprocess

# Package the app into a ZIP file (mimicking `az webapp up` behavior)
app_code_path = "./clco-demo"  # Path to your app code directory
zip_file_path = "./app_package.zip"

# Ensure the directory is zipped for deployment
subprocess.run(["zip", "-r", zip_file_path, "."], cwd=app_code_path, check=True)

# Deploy the ZIP file using `az` CLI for deployment
deployment_command = [
    "az",
    "webapp",
    "deployment",
    "source",
    "config-zip",
    "--resource-group", resource_group_name,
    "--name", app_name,
    "--src", zip_file_path,
]
subprocess.run(deployment_command, check=True)

# Output the Web App URL
pulumi.export("app_url", pulumi.Output.concat("https://", web_app.default_host_name))

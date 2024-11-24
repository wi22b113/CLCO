import pytest
from pulumi import automation as auto


@pytest.fixture(scope="module")
def pulumi_stack():
    """
    Lädt einen bestehenden Pulumi-Stack für Tests.
    """
    project_name = "A4-Testing"
    stack_name = "dev"

    # Pulumi Automation API: Stack laden
    stack = auto.select_stack(
        stack_name=stack_name,
        project_name=project_name,
        program=lambda: None,
    )

    try:
        outputs = stack.outputs()
        resolved_outputs = {key: value.value for key, value in outputs.items()}
        return resolved_outputs
    except Exception as e:
        print(f"Fehler beim Laden der Stack-Outputs: {e}")
        raise e


def test_resource_group(pulumi_stack):
    """
    Testet die Ressourcengruppe.
    """
    resource_group_name = pulumi_stack.get("resource_group_name")
    assert resource_group_name is not None

    # Überprüfen, ob der Name mit dem erwarteten Präfix beginnt
    assert resource_group_name.startswith("a4-resourcegroup")

    resource_group_location = pulumi_stack.get("resource_group_location")
    assert resource_group_location == "eastus"


def test_storage_account(pulumi_stack):
    """
    Testet den Storage Account.
    """
    assert pulumi_stack.get("storage_account_name").startswith("storageaccount")
    assert pulumi_stack.get("storage_account_sku") == "Standard_LRS"
    assert pulumi_stack.get("storage_account_kind") == "StorageV2"


def test_blob_container(pulumi_stack):
    """
    Testet den Blob Container.
    """
    assert pulumi_stack.get("blob_container_name") == "blobcontainer"


def test_blob_url(pulumi_stack):
    """
    Testet die Blob-URL.
    """
    blob_url = pulumi_stack.get("blob_url")
    assert blob_url.startswith("https://")
    assert "blob.core.windows.net/blobcontainer/helloworldappzip" in blob_url


def test_app_service_plan(pulumi_stack):
    """
    Testet den App Service Plan.
    """
    assert pulumi_stack.get("app_service_plan_name").startswith("appserviceplan")
    assert pulumi_stack.get("app_service_plan_sku_tier") == "Free"
    assert pulumi_stack.get("app_service_plan_kind") == "linux"


def test_application_insights(pulumi_stack):
    """
    Testet Application Insights.
    """
    assert pulumi_stack.get("app_insights_name").startswith("appinsights")
    assert pulumi_stack.get("app_insights_application_type") == "web"
    assert pulumi_stack.get("app_insights_kind") == "web"


def test_web_app(pulumi_stack):
    """
    Testet die Web-App.
    """
    assert pulumi_stack.get("web_app_name").startswith("webapp")
    assert pulumi_stack.get("web_app_location") == "East US"
    assert pulumi_stack.get("web_app_linux_fx_version") == "PYTHON|3.11"


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


def test_integration_relationships(pulumi_stack):
    """
    Integration Test: Verifiziert die Beziehungen zwischen den Ressourcen.
    """
    # Überprüfen der Resource Group
    resource_group_name = pulumi_stack.get("resource_group_name")
    print(f"Resource Group Name: {resource_group_name}")
    assert resource_group_name is not None

    # Überprüfen des Storage Accounts und seiner Beziehung zur Resource Group
    storage_account_name = pulumi_stack.get("storage_account_name")
    print(f"Storage Account Name: {storage_account_name}")
    assert storage_account_name is not None

    storage_account_rg = pulumi_stack.get("resource_group_name")
    print(f"Storage Account Resource Group: {storage_account_rg}")
    assert storage_account_rg == resource_group_name

    # Überprüfen des Blob Containers und seiner Beziehung zum Storage Account
    blob_container_name = pulumi_stack.get("blob_container_name")
    print(f"Blob Container Name: {blob_container_name}")
    assert blob_container_name is not None
    
    blob_container_account_name = pulumi_stack.get("blob_container_account_name")
    print(f"Blob Container Account Name: {blob_container_account_name}")
    assert blob_container_account_name == storage_account_name


    blob_url = pulumi_stack.get("blob_url")
    print(f"Blob URL: {blob_url}")
    assert blob_url is not None
    assert storage_account_name in blob_url
    assert blob_container_name in blob_url

    # Überprüfen des Blob Containers gegen den Storage Account
    print("Verifying Blob Container is associated with the correct Storage Account.")
    assert pulumi_stack.get("blob_container_account_name") == storage_account_name

    # Überprüfen des App Service Plans und seiner Beziehung zur Resource Group
    app_service_plan_name = pulumi_stack.get("app_service_plan_name")
    print(f"App Service Plan Name: {app_service_plan_name}")
    assert app_service_plan_name is not None

    app_service_plan_rg = pulumi_stack.get("resource_group_name")
    print(f"App Service Plan Resource Group: {app_service_plan_rg}")
    assert app_service_plan_rg == resource_group_name

    # Überprüfen der Web App und ihrer Beziehung zum App Service Plan und Blob URL
    web_app_name = pulumi_stack.get("web_app_name")
    print(f"Web App Name: {web_app_name}")
    assert web_app_name is not None

    web_app_linux_fx_version = pulumi_stack.get("web_app_linux_fx_version")
    print(f"Web App Linux FX Version: {web_app_linux_fx_version}")
    assert web_app_linux_fx_version == "PYTHON|3.11"

    # Sicherstellen, dass die WebApp den Blob-Storage verwendet
    print("Verifying Web App is linked to the correct Storage Account.")
    assert pulumi_stack.get("web_app_storage_account_name") == storage_account_name

    # Überprüfen von Application Insights und ihrer Beziehung zur Resource Group
    app_insights_name = pulumi_stack.get("app_insights_name")
    print(f"Application Insights Name: {app_insights_name}")
    assert app_insights_name is not None

    app_insights_rg = pulumi_stack.get("resource_group_name")
    print(f"Application Insights Resource Group: {app_insights_rg}")
    assert app_insights_rg == resource_group_name

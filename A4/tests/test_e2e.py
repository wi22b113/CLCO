import pytest
from pulumi import automation as auto


@pytest.fixture(scope="module")
def pulumi_stack():
    """
    Lädt einen bestehenden Pulumi-Stack für E2E-Tests.
    """
    project_name = "A4-Testing"
    stack_name = "dev"

    # Pulumi Automation API: Stack laden
    stack = auto.select_stack(
        stack_name=stack_name,
        project_name=project_name,
        program=lambda: None,
    )

    # Outputs des Stacks abrufen
    try:
        outputs = stack.outputs()
        resolved_outputs = {key: value.value for key, value in outputs.items()}
        return resolved_outputs
    except Exception as e:
        print(f"Fehler beim Laden der Stack-Outputs: {e}")
        raise e


def test_stack_outputs(pulumi_stack):
    """
    E2E-Test: Überprüft, ob die Outputs des Stacks korrekt sind.
    """
    # Ressourcen-Outputs prüfen
    resource_group_name = pulumi_stack.get("resource_group_name")
    storage_account_name = pulumi_stack.get("storage_account_name")
    blob_container_name = pulumi_stack.get("blob_container_name")
    blob_url = pulumi_stack.get("blob_url")
    web_app_name = pulumi_stack.get("web_app_name")
    web_app_url = pulumi_stack.get("web_app_url")
    app_insights_name = pulumi_stack.get("app_insights_name")

    # Debug-Ausgabe
    print(f"Resource Group: {resource_group_name}")
    print(f"Storage Account: {storage_account_name}")
    print(f"Blob Container: {blob_container_name}")
    print(f"Blob URL: {blob_url}")
    print(f"Web App Name: {web_app_name}")
    print(f"Web App URL: {web_app_url}")
    print(f"Application Insights Name: {app_insights_name}")

    # Assertions
    assert resource_group_name is not None and resource_group_name.startswith("a4-resourcegroup"), \
        f"Resource Group Name stimmt nicht: {resource_group_name}"
    assert storage_account_name is not None and storage_account_name.startswith("storageaccount"), \
        f"Storage Account Name stimmt nicht: {storage_account_name}"
    assert blob_container_name == "blobcontainer", \
        f"Blob Container Name stimmt nicht: {blob_container_name}"
    assert blob_url is not None and blob_url.startswith("https://"), \
        f"Blob URL ist ungültig: {blob_url}"
    assert web_app_name is not None and web_app_name.startswith("webapp"), \
        f"Web App Name stimmt nicht: {web_app_name}"
    assert web_app_url is not None and (web_app_url.startswith("https://") or web_app_url.endswith(".azurewebsites.net")), \
        f"Web App URL ist ungültig: {web_app_url}"
    assert app_insights_name is not None and app_insights_name.startswith("appinsights"), \
        f"Application Insights Name stimmt nicht: {app_insights_name}"


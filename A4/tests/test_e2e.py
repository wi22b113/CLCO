# tests/test_e2e.py

import pulumi
import pytest
from pulumi_azure_native import resources, storage, web

@pytest.fixture
def setup_resources():
    """
    Fixture zur Initialisierung der Ressourcen für End-to-End-Tests.
    """
    # Initialisiere die Ressourcengruppe
    resource_group = resources.ResourceGroup("resourcegroup",
        location="westus"
    )
    
    # Initialisiere den Storage Account
    storage_account = storage.StorageAccount("storageaccount",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        sku=storage.SkuArgs(
            name="Standard_LRS"
        ),
        kind="StorageV2"
    )
    
    # Initialisiere den Blob Container
    blob_container = storage.BlobContainer("blobcontainer",
        account_name=storage_account.name,
        resource_group_name=resource_group.name,
        public_access="Blob"
    )
    
    # Initialisiere den App Service Plan
    app_service_plan = web.AppServicePlan("appserviceplan",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        kind="Linux",
        reserved=True,
        sku=web.SkuDescriptionArgs(
            tier="Free",
            name="F1"
        )
    )
    
    return storage_account, blob_container, app_service_plan

def test_end_to_end(setup_resources):
    """
    Testet die End-to-End-Bereitstellung des gesamten Stacks.
    """
    storage_account, blob_container, app_service_plan = setup_resources

    def check_sku(sku):
        assert sku.name == "Standard_LRS"

    def check_kind(kind):
        assert kind == "StorageV2"

    def check_public_access(public_access):
        assert public_access == "Blob"

    def check_app_service_plan_sku(sku):
        assert sku.tier == "Free"

    storage_account.sku.apply(check_sku)
    storage_account.kind.apply(check_kind)
    blob_container.public_access.apply(check_public_access)
    app_service_plan.sku.apply(check_app_service_plan_sku)
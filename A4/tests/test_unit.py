# tests/test_unit.py

import pulumi
import pytest
from pulumi_azure_native import resources, storage

@pytest.fixture
def setup_resources():
    """
    Fixture zur Initialisierung der Ressourcen für Unit-Tests.
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
    
    return resource_group, storage_account

def test_storage_account(setup_resources):
    """
    Testet die Konfiguration des Storage Accounts.
    """
    resource_group, storage_account = setup_resources

    def check_sku(sku):
        assert sku.name == "Standard_LRS"

    def check_kind(kind):
        assert kind == "StorageV2"

    storage_account.sku.apply(check_sku)
    storage_account.kind.apply(check_kind)
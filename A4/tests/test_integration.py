# tests/test_integration.py

import pulumi
import pytest
from pulumi_azure_native import resources, storage

@pytest.fixture
def setup_resources():
    """
    Fixture zur Initialisierung der Ressourcen für Integrationstests.
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
    
    return storage_account, blob_container

def test_blob_container(setup_resources):
    """
    Testet die Beziehung zwischen Storage Account und Blob Container.
    """
    storage_account, blob_container = setup_resources

    def check_account_name(account_name):
        assert account_name == storage_account.name

    def check_public_access(public_access):
        assert public_access == "Blob"

    blob_container.account_name.apply(check_account_name)
    blob_container.public_access.apply(check_public_access)
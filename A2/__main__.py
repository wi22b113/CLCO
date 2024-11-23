import pulumi
from pulumi_azure_native import resources, storage

## Konfiguration
# run this commands before pulumi up
# pulumi config set location westeurope
# pulumi config set sku Standard_LRS
# pulumi config set storageName mystorageaccount

config = pulumi.Config()
location = config.require("location")
sku = config.require("sku")
storage_name = config.require("storageName")

## Resource Group
resource_group = resources.ResourceGroup("resourceGroup", location=location)

## Storage Account
storage_account = storage.StorageAccount(storage_name,
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=storage.SkuArgs(name=sku),
    kind="StorageV2"
)

# Ausgabe des Speicherkontonamens
pulumi.export("storageAccountName", storage_account.name)

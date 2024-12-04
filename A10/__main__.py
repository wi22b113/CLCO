import pulumi
from pulumi_azure_native import resources, authorization
import subprocess
import json
import uuid

# Konfigurierbare Werte
user_email = "wi22b113@technikum-wien.at"
resource_group_name = "simplifiedResourceGroup"

# Hilfsfunktion: Benutzer-Objekt-ID abrufen
def get_user_object_id(email: str) -> str:
    result = subprocess.run(
        ["az", "ad", "user", "show", "--id", email, "--query", "id", "-o", "tsv"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()

# Hilfsfunktion: Rollen-Definition-ID abrufen
def get_role_definition_id(role_name: str) -> str:
    result = subprocess.run(
        ["az", "role", "definition", "list", "--name", role_name, "--query", "[0].id", "-o", "tsv"],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()

# Hilfsfunktion: Bestehende Rollenzuweisungen abrufen
def list_role_assignments(principal_id: str) -> list:
    result = subprocess.run(
        ["az", "role", "assignment", "list", "--assignee", principal_id, "-o", "json"],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)

# Benutzer-Objekt-ID abrufen
user_object_id = get_user_object_id(user_email)

# Task 1: Bestehende Rollen anzeigen
existing_assignments_before = list_role_assignments(user_object_id)
resolved_assignments_before = [
    {"scope": r["scope"], "role": r["roleDefinitionName"]} for r in existing_assignments_before
]

# Ressourcengruppe erstellen
resource_group = resources.ResourceGroup(resource_group_name)

# Task 2: Rolle "Reader" zuweisen
reader_role_id = get_role_definition_id("Reader")
role_assignment = authorization.RoleAssignment(
    "readerRoleAssignment",
    principal_id=user_object_id,
    principal_type="User",
    role_definition_id=reader_role_id,
    scope=resource_group.id,
    role_assignment_name=str(uuid.uuid4()),
)

# Bestehende Rollenzuweisungen nach der Zuweisung erneut abrufen
def list_updated_assignments(resource_group_name: str):
    return list_role_assignments(user_object_id)

updated_assignments = resource_group.id.apply(lambda _: list_updated_assignments(resource_group_name))
resolved_assignments_after = updated_assignments.apply(
    lambda assignments: [
        {"scope": r["scope"], "role": r["roleDefinitionName"]} for r in assignments
    ]
)

# Pulumi Exporte
pulumi.export("existing_role_assignments_before", resolved_assignments_before)
pulumi.export("resource_group_id", resource_group.id)
pulumi.export("role_assignment", role_assignment.id)
pulumi.export("existing_role_assignments_after", resolved_assignments_after)

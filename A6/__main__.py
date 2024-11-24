import pulumi  # Pulumi-Framework zur Definition und Verwaltung von Cloud-Ressourcen
from pulumi_azure_native import consumption  # Modul für Azure-Native-Ressourcen, speziell "consumption"
from datetime import datetime  # Modul zur Verarbeitung von Datum und Uhrzeit

# -------------------- KONFIGURATION --------------------

# Azure Subscription-ID (wird benötigt, um die Ressourcen zu identifizieren)
subscription_id = "1b744ae6-c1ae-4bce-8d17-b6bdf7ffee00"  # Ersetze dies durch deine gültige Azure-Subscription-ID

# Kontakt-E-Mail-Adresse für Benachrichtigungen
email = "wi22b113@technikum-wien.at"  # E-Mail-Adresse für Budget-Benachrichtigungen

# Start- und Enddatum für den Budgetzeitraum
# Definiert den Zeitraum, in dem das Budget aktiv ist
start_date = datetime(2024, 11, 1).strftime('%Y-%m-%dT%H:%M:%SZ')  # Startdatum: 1. November 2024
end_date = datetime(2025, 3, 31).strftime('%Y-%m-%dT%H:%M:%SZ')  # Enddatum: 31. März 2025

# -------------------- BUDGET DEFINITION --------------------

# Erstellt ein neues Azure-Budget
budget = consumption.Budget(
    resource_name="euwest-1-budget",  # Name des Budgets
    amount=86,  # Budgetbetrag in der Währung der Azure-Subscription
    time_grain="Monthly",  # Gibt an, dass das Budget monatlich zurückgesetzt wird
    scope=f"/subscriptions/{subscription_id}",  # Definiert den Geltungsbereich (Scope) für das Budget
    time_period={
        "startDate": start_date,  # Startdatum des Budgets
        "endDate": end_date,  # Enddatum des Budgets
    },
    notifications={  # Definition der Benachrichtigungsbedingungen
        "Actual50Percent": {  # Benachrichtigung, wenn 50 % des Budgets erreicht werden
            "enabled": True,  # Aktiviert die Benachrichtigung
            "operator": "GreaterThan",  # Operator, der überprüft, ob Kosten > Schwellenwert sind
            "threshold": 50,  # Schwellenwert in Prozent (50 % des Budgets)
            "contact_emails": [email],  # Liste der E-Mail-Adressen für Benachrichtigungen
            "contact_roles": [],  # Rollen, die Benachrichtigungen erhalten (hier leer)
            "notification_language": "en-US",  # Sprache der Benachrichtigung (Englisch)
        },
    },
    category="Cost",  # Budgettyp: "Cost" (Kostenbasiert)
    filter={  # Filter zur Einschränkung des Budgets
        "resourceLocations": ["westeurope"],  # Beschränkt das Budget auf Ressourcen in "West-Europa"
    },
)

# -------------------- AUSGABE --------------------

# Exportiert die Budget-ID nach der Erstellung
pulumi.export("budget_id", budget.id)  # Gibt die Budget-ID aus, um sie später referenzieren zu können

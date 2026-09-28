"""Central configuration — all values resolved from environment variables."""
import os

# Sport selection activates sport-specific guardrail rules.
# Valid values: football | basketball | soccer | hockey
SPORTS_IQ_SPORT = os.getenv("SPORTS_IQ_SPORT", "basketball")

_SPORT_DEFAULTS = {
    "football": {
        "sport": "football",
        "league_name": "Professional Football",
        "home_team": "HCC",
        "home_team_name": "Harbor City Comets",
        "away_team": "MST",
        "away_team_name": "Metro Stars",
        "venue_label": "Stadium",
        "period_label": "Quarter",
    },
    "basketball": {
        "sport": "basketball",
        "league_name": "Professional Basketball",
        "home_team": "HCC",
        "home_team_name": "Harbor City Comets",
        "away_team": "MST",
        "away_team_name": "Metro Stars",
        "venue_label": "Arena",
        "period_label": "Quarter",
    },
    "soccer": {
        "sport": "soccer",
        "league_name": "Professional Soccer",
        "home_team": "HCC",
        "home_team_name": "Harbor City Comets",
        "away_team": "MST",
        "away_team_name": "Metro Stars",
        "venue_label": "Stadium",
        "period_label": "Half",
    },
    "hockey": {
        "sport": "hockey",
        "league_name": "Professional Hockey",
        "home_team": "HCC",
        "home_team_name": "Harbor City Comets",
        "away_team": "MST",
        "away_team_name": "Metro Stars",
        "venue_label": "Arena",
        "period_label": "Period",
    },
}


def default_sport_context() -> dict:
    """Return sport/team labels for backend prompts and notifications."""
    defaults = _SPORT_DEFAULTS.get(SPORTS_IQ_SPORT.lower(), _SPORT_DEFAULTS["football"])
    return {
        **defaults,
        "sport": os.getenv("SPORTS_IQ_SPORT", defaults["sport"]),
        "league_name": os.getenv("DEMO_LEAGUE_NAME", defaults["league_name"]),
        "home_team": os.getenv("DEMO_HOME_TEAM", defaults["home_team"]),
        "home_team_name": os.getenv("DEMO_HOME_TEAM_NAME", defaults["home_team_name"]),
        "away_team": os.getenv("DEMO_AWAY_TEAM", defaults["away_team"]),
        "away_team_name": os.getenv("DEMO_AWAY_TEAM_NAME", defaults["away_team_name"]),
        "venue_label": os.getenv("DEMO_VENUE_LABEL", defaults["venue_label"]),
        "period_label": os.getenv("DEMO_PERIOD_LABEL", defaults["period_label"]),
    }

# Microsoft Foundry project endpoint (MAF standard var name)
# Format: https://<aiservices-id>.services.ai.azure.com/api/projects/<project-name>
# Found in Foundry portal → your project → Project details → Project endpoint
FOUNDRY_PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
# Model deployment name (MAF standard: FOUNDRY_MODEL)
FOUNDRY_MODEL = os.getenv("FOUNDRY_MODEL", "gpt-5.4")
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")

# Eventhouse (Kusto)
EVENTHOUSE_URI = os.getenv("EVENTHOUSE_URI", "")
EVENTHOUSE_DB = os.getenv("EVENTHOUSE_DB", "SportsIQ_Eventhouse")

# Fabric Lakehouse SQL Analytics Endpoint — READ-ONLY (Delta tables, no DML)
# Used for SELECT queries: fan_profile, promotion_history, engagement_pattern, etc.
# Found in Fabric portal → Lakehouse → SQL analytics endpoint
LAKEHOUSE_SQL_ENDPOINT = os.getenv("LAKEHOUSE_SQL_ENDPOINT", "")
LAKEHOUSE_DB = os.getenv("LAKEHOUSE_DB", "SportsIQ_Lakehouse")
LAKEHOUSE_SCHEMA = os.getenv("LAKEHOUSE_SCHEMA", "dbo")

# Fabric Warehouse SQL endpoint — READ/WRITE (full T-SQL DML supported)
# Hosts the writable transactional tables: promotion_history, pos_transaction, offer_decision_log
# Found in Fabric portal → Warehouse → SQL connection string (server name only, no port)
# Leave blank to disable Lakehouse dual-write (EventHouse RTI loop will still work).
WAREHOUSE_SQL_ENDPOINT = os.getenv("WAREHOUSE_SQL_ENDPOINT", "")
WAREHOUSE_DB = os.getenv("WAREHOUSE_DB", "SportsIQ_Warehouse")
WAREHOUSE_SCHEMA = os.getenv("WAREHOUSE_SCHEMA", "dbo")

# Fabric Data Agent REST endpoint (legacy — superseded by URLs below)
FABRIC_DATA_AGENT_URL = os.getenv("FABRIC_DATA_AGENT_URL", "")

# Fabric Data Agent MCP server URL (SSE transport — from Fabric portal → API endpoint → MCP)
# Format: https://api.fabric.microsoft.com/v1/mcp/workspaces/{wsId}/dataagents/{agentId}/agent
FABRIC_DATA_AGENT_MCP_URL = os.getenv("FABRIC_DATA_AGENT_MCP_URL", "")

# Fabric Data Agent OpenAI-compatible endpoint (preferred — returns standard JSON, no SSE)
# Format: https://api.fabric.microsoft.com/v1/workspaces/{wsId}/dataagents/{agentId}/aiassistant/openai
FABRIC_DATA_AGENT_OPENAI_URL = os.getenv("FABRIC_DATA_AGENT_OPENAI_URL", "")

# Foundry project connection ID for the Fabric Data Agent (for MicrosoftFabricPreviewTool)
# Format: /subscriptions/.../providers/.../projects/.../connections/{connectionName}
# Found in Foundry portal → Management center → Connected resources
FABRIC_DATA_AGENT_CONNECTION_NAME = os.getenv("FABRIC_DATA_AGENT_CONNECTION_NAME", "")

# Azure Application Insights connection string (App Insights → Overview → Connection String)
APPINSIGHTS_CONN_STR = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
ACS_CONNECTION_STRING = os.getenv("ACS_CONNECTION_STRING", "")
ACS_SENDER_ADDRESS = os.getenv("ACS_SENDER_ADDRESS", "")

# Teams incoming webhook (optional, for parallel notification)
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")

# Azure Table Storage (checkpoint persistence) — RBAC via DefaultAzureCredential
AZURE_TABLE_STORAGE_ENDPOINT = os.getenv("AZURE_TABLE_STORAGE_ENDPOINT", "")  # e.g. https://<account>.table.core.windows.net/
CHECKPOINT_TABLE_NAME = os.getenv("CHECKPOINT_TABLE_NAME", "WorkflowCheckpoints")

# Demo fan / game constants
DEMO_FAN_ID = os.getenv("DEMO_FAN_ID", "fan_0001")
DEMO_GAME_ID = os.getenv("DEMO_GAME_ID", "basketball_game_0001")
DEMO_SECTION_ID = os.getenv("DEMO_SECTION_ID", "SEC_A1")
DEMO_STADIUM_ID = os.getenv("DEMO_STADIUM_ID", "VENUE_001")
DEMO_FAN_EMAIL = os.getenv("DEMO_FAN_EMAIL", "")
DEMO_FAN_NAME = os.getenv("DEMO_FAN_NAME", "Fictional Fan 0001")

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]


def missing_runtime_settings() -> list[str]:
    required = {
        "FOUNDRY_PROJECT_ENDPOINT": FOUNDRY_PROJECT_ENDPOINT,
        "EVENTHOUSE_URI": EVENTHOUSE_URI,
        "LAKEHOUSE_SQL_ENDPOINT": LAKEHOUSE_SQL_ENDPOINT,
    }
    return [name for name, value in required.items() if not value]

FOUNDRY_IQ_CONNECTION_NAME = os.getenv("FOUNDRY_IQ_CONNECTION_NAME", "")
FOUNDRY_IQ_KNOWLEDGEBASE_NAME = os.getenv("FOUNDRY_IQ_KNOWLEDGEBASE_NAME", "")
FOUNDRY_IQ_SEARCH_SERVICE_ENDPOINT = os.getenv("FOUNDRY_IQ_SEARCH_SERVICE_ENDPOINT", "")

# ── Foundry IQ Knowledge Base IDs ─────────────────────────────────────────
# These IDs are used by agents to retrieve grounded context.
# Get KB IDs from Azure Foundry portal → Knowledge Bases → copy ID
# Or run: python scripts/setup_knowledge_base.py to create new KBs

# Stadium layout, concessions, vendor info (used by fabric-context agent)
SPORTS_IQ_STADIUM_KB_ID = os.getenv("SPORTS_IQ_STADIUM_KB_ID", "")

# Future: Game rules, offer eligibility, fan tier policies
SPORTS_IQ_RULES_KB_ID = os.getenv("SPORTS_IQ_RULES_KB_ID", "")

# Future: Fan engagement patterns, historical trends, propensity models
SPORTS_IQ_ENGAGEMENT_KB_ID = os.getenv("SPORTS_IQ_ENGAGEMENT_KB_ID", "")

"""Example: Fabric Context Agent with Stadium Knowledge Base Integration

This shows how to wire a Foundry IQ Knowledge Base into your Foundry agent definition.

NOTE: This is a REFERENCE/EXAMPLE FILE. 
See agents/shared/fabric_agent.py for the actual agent being used.

Key changes:
1. Import RetrievalAugmentedGenerationTool
2. Create kb_tool with your KB ID
3. Add kb_tool to the tools list
4. Reference KB tool in agent instructions

"""

from functools import lru_cache
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    MicrosoftFabricPreviewTool,
    RetrievalAugmentedGenerationTool,  # ← NEW: Knowledge base retrieval
    FabricDataAgentToolParameters,
    ToolProjectConnection,
)

from agents.shared.config import config


AGENT_NAME = "sports-iq-fabric-context-agent-v7"

_INSTRUCTIONS = (
    "You are the Sports-IQ Fabric Context Agent, responsible for answering questions about "
    "fan engagement, offers, and concession activity by combining real-time Fabric data with "
    "contextual stadium information.\n\n"
    
    "## Data Sources Available\n"
    "You have two retrieval tools:\n"
    "  1. **Fabric Data Agent Tool**: Access to real-time tables (OfferFeedbackEvent, POSTransaction) "
    "     and analytical tables (fan_profile, engagement_pattern, promotion_history)\n"
    "  2. **Stadium Knowledge Base Tool**: Stadium layout, sections, concession zones, "
    "     operators, menu items with prices, walk times, weather exposure\n\n"
    
    "## Routing Rules\n"
    "- **Concession Zone Queries**: 'What zones are most active?' or 'Show me concession revenue by zone'\n"
    "  → Use Fabric Data Agent to query POSTransaction by zone_id\n"
    "  → Use Stadium KB to retrieve zone names, operator names, menu items\n"
    "  → COMBINE both sources in your response\n\n"
    "- **Weather/Environmental Queries**: 'Which sections have the most weather exposure?'\n"
    "  → Use Stadium KB to retrieve section weather exposure data\n"
    "  → Combine with POSTransaction data if asking about purchase patterns\n\n"
    "- **Stadium Layout Queries**: 'How many seats in section 112?'\n"
    "  → Use Stadium KB directly (capacity, section map)\n\n"
    "- **Fan Activity Queries**: 'High-value fans in section 200?'\n"
    "  → Use Fabric Data Agent to query fan_profile + engagement_pattern\n"
    "  → Reference stadium context from KB if relevant\n\n"
    
    "## Response Format\n"
    "- Always cite which tool you used (Fabric Data Agent vs Stadium KB)\n"
    "- For multi-source answers, clearly separate data from each tool\n"
    "- Include data freshness (real-time for events, static for stadium info)\n"
)


@lru_cache(maxsize=1)
def get_fabric_context_agent():
    """Create or retrieve the cached Fabric context agent with KB integration."""
    
    credential = DefaultAzureCredential()
    client = AIProjectClient(
        endpoint=config.FOUNDRY_PROJECT_ENDPOINT,
        credential=credential,
    )
    
    # ── Tool 1: Fabric Data Agent (existing) ───────────────────────────
    fabric_tool = MicrosoftFabricPreviewTool(
        parameters=FabricDataAgentToolParameters(
            connection_id=config.FABRIC_DATA_AGENT_CONNECTION_NAME,
        )
    )
    
    # ── Tool 2: Stadium Knowledge Base (NEW) ───────────────────────────
    # KB contains: section numbers, capacity, concession zones, operators,
    # menu items, prices, walk times, weather exposure
    #
    # To get KB ID:
    #   1. Run: python scripts/setup_knowledge_base.py \\
    #        --kb-name "sports-iq-stadium" \\
    #        --kb-desc "Stadium layout and concessions" \\
    #        --doc-dir "./docs/stadium"
    #   2. Copy KB ID from output
    #   3. Set SPORTS_IQ_STADIUM_KB_ID env var
    
    kb_tool = None
    if config.SPORTS_IQ_STADIUM_KB_ID:
        kb_tool = RetrievalAugmentedGenerationTool(
            knowledge_base_id=config.SPORTS_IQ_STADIUM_KB_ID,
            name="stadium-knowledge-base",
            description=(
                "Retrieve stadium layout, section numbers, capacity, "
                "concession zones, operator names, menu items with prices, "
                "walk times between zones, and weather exposure by section"
            ),
        )
    
    # ── Create/Update Agent ────────────────────────────────────────────
    
    tools = [fabric_tool]
    if kb_tool:
        tools.append(kb_tool)
    
    agent = PromptAgentDefinition(
        name=AGENT_NAME,
        model_deployment_name=config.FOUNDRY_MODEL,
        instructions=_INSTRUCTIONS,
        tools=tools,
    )
    
    # Create or update (idempotent)
    return client.agents.create_or_update(agent)


# ── Usage Example ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        agent = get_fabric_context_agent()
        print(f"✓ Agent ready: {agent.id}")
        print(f"  Name: {agent.name}")
        print(f"  Model: {agent.model_deployment_name}")
        print(f"  Tools: {len(agent.tools)}")
        for tool in agent.tools:
            print(f"    - {tool.name}")
    except Exception as e:
        print(f"✗ Failed to create agent: {e}")
        print("\nTroubleshooting:")
        print("  1. Check FOUNDRY_PROJECT_ENDPOINT is set")
        print("  2. Run: python scripts/setup_knowledge_base.py to create KB")
        print("  3. Set SPORTS_IQ_STADIUM_KB_ID env var")

"""
Connectivity test + agent provisioning for Sports-IQ.

- Verifies MAF + Foundry credentials work.
- Provisions the Foundry-hosted Fabric context agent (MicrosoftFabricPreviewTool)
  so it's ready for the first workflow run.

Usage:
    python -m agents.create_agents
"""
import asyncio
import logging

# Load .env before any config import
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from azure.identity import DefaultAzureCredential
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient

from agents.shared import config, fabric_agent

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def _test_foundry_connection() -> None:
    """Quick smoke test: create a FoundryChatClient and run a minimal prompt."""
    credential = DefaultAzureCredential()
    client = FoundryChatClient(
        project_endpoint=config.FOUNDRY_PROJECT_ENDPOINT,
        model=config.FOUNDRY_MODEL,
        credential=credential,
    )
    agent = Agent(client=client, name="connectivity-test", instructions="Reply with OK.")
    response = await agent.run("ping")
    log.info("Foundry connection OK — response: %s", response.text[:80])


def _provision_fabric_agent() -> None:
    """Ensure the Fabric context agent exists in Foundry (idempotent)."""
    if not config.FABRIC_DATA_AGENT_CONNECTION_NAME:
        log.warning("FABRIC_DATA_AGENT_CONNECTION_NAME not set — skipping Fabric agent provisioning")
        return
    name = fabric_agent.ensure_agent()
    log.info("Fabric context agent ready: %s", name)


def main() -> None:
    log.info("Testing Foundry connectivity at %s (model: %s)",
             config.FOUNDRY_PROJECT_ENDPOINT, config.FOUNDRY_MODEL)

    asyncio.run(_test_foundry_connection())
    _provision_fabric_agent()

    print("\nOK Foundry connectivity verified.")
    print(f"   Fabric context agent: {fabric_agent.AGENT_NAME}")
    print("\nStart the server with:")
    print("   uvicorn agents.server:app --reload")


if __name__ == "__main__":
    main()


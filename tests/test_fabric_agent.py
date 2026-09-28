"""Tests for optional tool configuration in agents/shared/fabric_agent.py."""

from agents.shared.fabric_agent import _knowledge_base_tool


def test_knowledge_base_tool_is_omitted_when_unconfigured():
    assert _knowledge_base_tool("", "", "") is None


def test_knowledge_base_tool_is_omitted_when_configuration_is_incomplete():
    assert _knowledge_base_tool("", "sportsiq-kb", "foundry-iq") is None


def test_knowledge_base_tool_rejects_endpoint_without_http_scheme():
    assert _knowledge_base_tool(
        "search.example.com", "sportsiq-kb", "foundry-iq"
    ) is None


def test_knowledge_base_tool_accepts_absolute_https_endpoint():
    tool = _knowledge_base_tool(
        "https://search.example.com/", "sportsiq-kb", "foundry-iq"
    )

    assert tool is not None
    assert tool.server_url == (
        "https://search.example.com/knowledgebases/sportsiq-kb/"
        "mcp?api-version=2026-05-01-preview"
    )
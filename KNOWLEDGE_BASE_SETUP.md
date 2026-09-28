# Foundry IQ Knowledge Base — Quick Start Guide

This guide shows how to create a Foundry IQ knowledge base, upload documents, and wire it into your Sports-IQ agents.

---

## Quick Overview

**What is a Foundry IQ Knowledge Base?**
- A managed document store in Azure AI Foundry for RAG (Retrieval-Augmented Generation)
- Documents are automatically indexed for semantic search
- Agents can retrieve relevant context when answering questions

**Example:** Stadium layout, concession menu, vendor map → KB → Agent retrieves during question

---

## Step 1: Prepare Your Documents

Create a directory with documents you want indexed:

```
docs/
├── stadium-sections.pdf         # Stadium layout with seat zones
├── concession-menu.txt          # Menu items, prices, prep times
├── vendor-map.docx              # Vendor locations and operating hours
└── weather-coverage.md          # Weather exposure by section
```

**Supported formats:** PDF, DOCX, TXT, MD (plain text)

---

## Step 2: Create and Populate Knowledge Base

### Option A: Python Script (Recommended)

```python
from agents.shared.knowledge_base_manager import bootstrap_knowledge_base

# One-shot: create KB and upload all docs from a directory
kb_id = bootstrap_knowledge_base(
    kb_display_name="sports-iq-stadium-kb",
    kb_description="Fictional venue layout, concessions, weather exposure",
    document_dir="./docs/stadium",
    file_extensions=['.pdf', '.txt', '.docx']
)

print(f"Knowledge Base ID: {kb_id}")
# Output: Knowledge Base ID: kb-12345abcdef
```

Save the **KB ID** — you'll use it in your agent definitions.

### Option B: Step-by-Step (More Control)

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from agents.shared.knowledge_base_manager import KnowledgeBaseManager
from agents.shared.config import config

# Initialize client
credential = DefaultAzureCredential()
project_client = AIProjectClient(
    endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
    credential=credential,
)

manager = KnowledgeBaseManager(project_client, config.AZURE_AI_PROJECT_ID)

# Create KB
kb = manager.create_knowledge_base(
    display_name="sports-iq-stadium-kb",
    description="Stadium layout, concessions, vendor info"
)
print(f"Created: {kb.id}")

# Upload documents
docs = manager.upload_documents(
    kb_id=kb.id,
    file_paths=[
        "docs/stadium-sections.pdf",
        "docs/concession-menu.txt",
        "docs/vendor-map.docx"
    ],
    sync=True  # Wait for indexing
)

for doc in docs:
    print(f"  {doc.name}: {doc.status}")
```

---

## Step 3: Wire KB into Agent Definition

Once you have a KB ID, update your agent to reference it using `RetrievalAugmentedGenerationTool`:

### Updated `agents/shared/fabric_agent.py`

```python
from azure.ai.projects.models import (
    PromptAgentDefinition,
    MicrosoftFabricPreviewTool,
    RetrievalAugmentedGenerationTool,  # ← ADD THIS
    FabricDataAgentToolParameters,
    ToolProjectConnection,
)

AGENT_NAME = "sports-iq-fabric-context-agent-v7"

_INSTRUCTIONS = (
    "You are the Sports-IQ Fan Context Agent...\n"
    "## Knowledge Sources\n"
    "You have access to TWO knowledge sources:\n"
    "- Stadium & Concessions KB (sportsiq-stadium-kb): Stadium sections, operators, menu, weather\n"
    "- Fabric Data Agent: Fan profiles, transactions, offers\n"
    "When answering concession questions, combine both sources.\n"
)

@lru_cache(maxsize=1)
def get_fabric_context_agent():
    """Get or create the Fabric context agent with KB retrieval."""
    
    credential = DefaultAzureCredential()
    client = AIProjectClient(
        endpoint=config.AZURE_AI_PROJECT_ENDPOINT,
        credential=credential,
    )
    
    # Define tools
    fabric_tool = MicrosoftFabricPreviewTool(
        parameters=FabricDataAgentToolParameters(
            connection_id=config.FABRIC_DATA_AGENT_CONNECTION_NAME,
        )
    )
    
    # ← ADD: Knowledge base retrieval tool
    kb_tool = RetrievalAugmentedGenerationTool(
        knowledge_base_id="kb-12345abcdef",  # ← Your KB ID from Step 2
        name="sportsiq-stadium-kb",
        description="Retrieve stadium layout, concession zones, vendor info, weather exposure"
    )
    
    agent = PromptAgentDefinition(
        name=AGENT_NAME,
        model_deployment_name=config.FOUNDRY_MODEL_DEPLOYMENT,
        instructions=_INSTRUCTIONS,
        tools=[fabric_tool, kb_tool],  # ← Include KB tool
    )
    
    return client.agents.create_or_update(agent)
```

---

## Step 4: Use KB in Agent Responses

Your agent automatically has access to the KB tool. When handling questions, it can:

```python
# Agent instruction example (already in _INSTRUCTIONS above):

"For concession zone questions ('most active zones', 'busiest concessions'):\n"
"  1. Use the Fabric Data Agent tool to query POSTransaction for zone activity\n"
"  2. Use the Stadium KB tool to retrieve zone names, operators, locations\n"
"  3. Combine both sources in your response\n"
```

---

## Step 5: Verify It Works

### Test the Agent Locally

```bash
cd agents
export ENABLE_DEVUI=true
python -m agents.server
```

Open the DevUI and test a question:
```
User: "Which concession zones had the most activity in the first half?"

Agent response combines:
  - POSTransaction query (Fabric Data Agent) → transaction counts by zone
  - Stadium KB retrieval → zone names, operators, capacity
```

### Check KB via Azure Portal

1. Go to **Azure AI Foundry** → Your Project
2. Left nav → **Knowledge Bases**
3. Click your KB → See indexed documents and status

---

## Managing Knowledge Bases

### List All KBs

```python
manager = KnowledgeBaseManager(project_client, project_id)
kbs = manager.list_knowledge_bases()

for kb in kbs:
    print(f"{kb.id}: {kb.display_name}")
```

### Update: Add More Documents

```python
manager.upload_documents(
    kb_id="kb-12345abcdef",
    file_paths=["docs/new-menu.txt"],
    sync=True
)
```

### Delete KB (Irreversible)

```python
manager.delete_knowledge_base("kb-12345abcdef")
```

---

## Troubleshooting

### "Failed to create knowledge base"
- Check `AZURE_AI_PROJECT_ENDPOINT` and credentials
- Verify `Cognitive Services User` role on your identity
- See: [.github/skills/azure-rbac/SKILL.md](.github/skills/azure-rbac/SKILL.md)

### "Document upload failed"
- File must exist at the path
- Supported formats: PDF, DOCX, TXT, MD
- File size limit: typically 50 MB per document

### "KB not available in agent"
- Double-check KB ID in agent definition
- Verify documents are `indexed` (not `uploading`)
- Wait a few seconds and retry

### "Agent isn't using KB data"
- Check agent instructions reference the KB tool
- Add explicit instruction like: *"Use the Stadium KB tool to retrieve..."*
- Test with a question that requires KB data

---

## Production Checklist

- [ ] KB ID hardcoded or in config (`agents/shared/config.py`)
- [ ] Documents are meaningful and non-redundant
- [ ] Agent instructions explicitly reference KB tool
- [ ] LocalDevUI test passes (agent retrieves KB data)
- [ ] Deploy updated agent definition via `agents/create_agents.py`
- [ ] Monitor KB latency in App Insights (p95 < 2 s)

---

## References

- **Knowledge Base Manager:** `agents/shared/knowledge_base_manager.py`
- **Fabric Context Agent:** `agents/shared/fabric_agent.py`
- **Config:** `agents/shared/config.py`
- **Framework:** `azure-ai-projects>=2.1.0`

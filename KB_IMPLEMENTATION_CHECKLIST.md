# Foundry IQ Knowledge Base Implementation Checklist

Complete these steps to create a knowledge base and wire it into your Sports-IQ agents.

---

## Phase 1: Preparation (5 mins)

- [ ] **1.1** Understand what data should go in the KB
  - Example: Stadium layout, section numbers, concession zones, operator names, menu items
  - See: `.github/KNOWLEDGE_BASES.md` for planned KBs
  
- [ ] **1.2** Gather documents
  - Create: `docs/stadium/` directory
  - Add: PDF/DOCX/TXT files with your content
  - Example: `stadium_sections.pdf`, `concession_menu.txt`, `vendor_map.docx`
  - ⚠️ Avoid duplicate/redundant content

- [ ] **1.3** Verify Azure credentials
  ```bash
  az login
  az account show  # Confirm correct subscription
  ```

---

## Phase 2: Create Knowledge Base (10 mins)

**Option A: One-Command Bootstrap (Recommended)**

- [ ] **2.1** Run bootstrap script
  ```bash
  python scripts/setup_knowledge_base.py \
    --kb-name "sports-iq-stadium" \
    --kb-desc "Stadium layout and concession zones" \
    --doc-dir "./docs/stadium"
  ```
  
- [ ] **2.2** Copy the KB ID from output
  ```
  ✓ SUCCESS! Knowledge Base ID: kb-12345abcdef
  ```

**Option B: Step-by-Step (More Control)**

- [ ] **2.1** Create Python script to instantiate manager
  ```python
  from agents.shared.knowledge_base_manager import KnowledgeBaseManager
  from azure.identity import DefaultAzureCredential
  from azure.ai.projects import AIProjectClient
  from agents.shared.config import config
  
  credential = DefaultAzureCredential()
  client = AIProjectClient(endpoint=config.FOUNDRY_PROJECT_ENDPOINT, credential=credential)
  manager = KnowledgeBaseManager(client, config.AZURE_AI_PROJECT_ID)
  ```

- [ ] **2.2** Create KB
  ```python
  kb = manager.create_knowledge_base(
      display_name="sports-iq-stadium",
      description="Stadium layout and concessions"
  )
  print(f"KB ID: {kb.id}")
  ```

- [ ] **2.3** Upload documents
  ```python
  docs = manager.upload_documents(
      kb_id=kb.id,
      file_paths=[
          "docs/stadium/stadium_sections.pdf",
          "docs/stadium/concession_menu.txt"
      ],
      sync=True  # Wait for indexing
  )
  ```

- [ ] **2.4** Verify indexing complete
  - Check: All docs show status `indexed` (not `uploading`)
  - Copy KB ID for next phase

---

## Phase 3: Store KB ID in Config (5 mins)

- [ ] **3.1** Add to `.env` (or set environment variable)
  ```
  SPORTS_IQ_STADIUM_KB_ID=kb-12345abcdef
  ```

- [ ] **3.2** OR add to `agents/shared/config.py`
  ```python
  SPORTS_IQ_STADIUM_KB_ID = os.getenv("SPORTS_IQ_STADIUM_KB_ID", "kb-12345abcdef")
  ```

- [ ] **3.3** Verify accessible in config
  ```python
  from agents.shared.config import config
  print(config.SPORTS_IQ_STADIUM_KB_ID)  # Should print: kb-12345abcdef
  ```

---

## Phase 4: Wire KB into Agent (15 mins)

- [ ] **4.1** Review example: `FABRIC_AGENT_KB_EXAMPLE.py`
  - Shows how to import `RetrievalAugmentedGenerationTool`
  - Shows tool configuration and agent integration

- [ ] **4.2** Update `agents/shared/fabric_agent.py`
  ```python
  # Add import
  from azure.ai.projects.models import RetrievalAugmentedGenerationTool
  
  # In get_fabric_context_agent():
  kb_tool = RetrievalAugmentedGenerationTool(
      knowledge_base_id=config.SPORTS_IQ_STADIUM_KB_ID,
      name="stadium-knowledge-base",
      description="Stadium sections, concessions, operators, weather"
  )
  
  # Add to tools list
  tools = [fabric_tool, kb_tool]
  ```

- [ ] **4.3** Update agent instructions (in _INSTRUCTIONS)
  - Add: "Use the Stadium Knowledge Base tool to retrieve..."
  - Example: "For zone queries: query POSTransaction (Fabric) + retrieve zone info (KB)"

- [ ] **4.4** Redeploy agent
  ```bash
  cd agents
  python create_agents.py
  ```

---

## Phase 5: Local Testing (10 mins)

- [ ] **5.1** Start dev server with DevUI
  ```bash
  export ENABLE_DEVUI=true
  python -m agents.server
  ```

- [ ] **5.2** Test KB retrieval in DevUI
  - Open: `http://localhost:8000` (or configured port)
  - User message: "What are the concession zones in our stadium?"
  - Expected: Agent retrieves from KB and returns zone names/operators
  - Check: Trace should show KB retrieval in tool calls

- [ ] **5.3** Verify latency
  - KB retrieval should complete in < 1 second
  - Total agent response < 6 seconds (Sports-IQ requirement)

---

## Phase 6: Verification & Monitoring (5 mins)

- [ ] **6.1** Check Azure Foundry Portal
  - Go: Azure AI Foundry → Your Project → Knowledge Bases
  - Verify: KB appears in list with correct name
  - Check: Documents show status `indexed`

- [ ] **6.2** Check App Insights
  - Search traces by agent name: `sports-iq-fabric-context-agent-*`
  - Look for: `gen_ai.rag_kb_id` span attribute
  - Verify: KB latency metrics acceptable

- [ ] **6.3** Test production scenario
  ```bash
  # From agents/server.py perspective:
  POST /api/run
  Body: {
    "fan_id": "bas_fan_0001",
    "game_id": "basketball_game_0001",
    "fan_name": "Test Fan",
    "fan_loyalty_tier": "GOLD"
  }
  # Observe: KB retrieval in workflow trace
  ```

---

## Phase 7: Documentation (5 mins)

- [ ] **7.1** Update `.github/KNOWLEDGE_BASES.md`
  ```markdown
  | sports-iq-stadium | kb-12345abcdef | fabric-context | Stadium layout and concessions | Ready |
  ```

- [ ] **7.2** Add KB details to README or Architecture doc
  - What data is in the KB?
  - When is it updated?
  - How to add more documents?

- [ ] **7.3** Document any KB-specific guardrails
  - Example: "Don't ask KB for real-time offer counts (use Fabric tool)"
  - Example: "KB is static; use Fabric tool for dynamic queries"

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **KB creation fails** | Check `FOUNDRY_PROJECT_ENDPOINT` is set; verify `Cognitive Services User` role |
| **Documents won't upload** | Check file formats (PDF, DOCX, TXT, MD); verify file exists; check file size < 50 MB |
| **Agent doesn't use KB** | Check KB ID in config; verify documents are `indexed` (not `uploading`); check agent instructions reference KB tool |
| **KB retrieval is slow** | Monitor KB latency in App Insights; reduce number of documents; simplify documents |
| **KB returns wrong context** | Re-check documents for accuracy; consider splitting large docs; re-index KB |

See: `.github/skills/microsoft-foundry/SKILL.md` for deeper diagnostics.

---

## What's Next?

- [ ] Create additional KBs (rules, engagement patterns, etc.)
- [ ] Add more documents to existing KBs
- [ ] Fine-tune agent instructions to better leverage KB
- [ ] Set up continuous evaluation (see: `.github/skills/microsoft-foundry/SKILL.md`)
- [ ] Monitor KB performance in production

---

## Files Created/Modified

| File | Purpose |
|------|---------|
| `agents/shared/knowledge_base_manager.py` | KB creation and document upload utilities |
| `scripts/setup_knowledge_base.py` | Bootstrap script to create KB + upload docs |
| `agents/shared/config.py` | KB ID configuration variables |
| `.github/KNOWLEDGE_BASES.md` | Registry of knowledge bases in the project |
| `KNOWLEDGE_BASE_SETUP.md` | Quick-start guide |
| `FABRIC_AGENT_KB_EXAMPLE.py` | Example agent definition with KB integration |

---

**Last Updated:** 2025-01-16  
**Status:** Ready for implementation

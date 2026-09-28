# Sports-IQ Copilot Instructions

Read `AGENTS.md` before changing application code, infrastructure, Fabric
assets, generated-data schemas, or deployment behavior. The repository must
remain a public, sport-neutral, fictional, and reproducible reference sample.

## Build, test, and run commands

Run Python and infrastructure commands from the repository root.

```powershell
# Python environment and dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r agents\requirements.txt

# Full Python suite
python -m pytest tests

# One test
python -m pytest tests\test_policy_guardrail.py::test_all_pass

# One test file
python -m pytest tests\test_workflow_nodes_edges.py

# Local backend; copy and populate the template first
Copy-Item agents\.env.example agents\.env
uvicorn agents.server:app --reload --port 8000

# Regenerate deterministic, ignored seed data
python data_generators\generate_all.py --output data\generated

# Infrastructure validation
az bicep build --file infra\main.bicep
az bicep lint --file infra\main.bicep
```

Run frontend commands from `webapp`:

```powershell
npm ci
npm run lint
npm run build
npm run dev
```

There is no separate frontend test command. ESLint and the production Next.js
build provide lint, type-check, and bundling validation.

Deployment is driven by Azure Developer CLI:

```powershell
az login
azd auth login
azd env new
# Set the Foundry project values and either FABRIC_CAPACITY_ID or
# FABRIC_WORKSPACE_ID as documented in README.md.
azd up
```

Do not run `azd up` merely to validate a code change: its pre-provision hook
creates or updates real Fabric items. Validate the smallest affected layer
unless an actual cloud deployment was requested.

## Architecture

- The public entry point is the Next.js 15 application in `webapp`. Its JWT
  middleware protects every route except login/auth endpoints. Browser code
  calls same-origin `/api/agents/*`; the server-side catch-all proxy forwards
  requests and streaming responses to the private FastAPI Container App through
  `AGENTS_API_URL`. Do not expose the backend URL to browser code.
- `agents/server.py` is the FastAPI/AG-UI boundary. It validates required
  runtime settings on startup and uses per-run `asyncio.Queue` and
  `asyncio.Event` objects for SSE events and human-in-the-loop decisions. Keep
  workflow execution in the FastAPI event loop; moving it to threads breaks
  approval signaling.
- The active workflow imported by the server is
  `agents/workflow_nodes_edges.py`, not the alternate workflow modules. Its
  graph is Engagement Monitor -> Offer Generator -> policy guardrails -> human
  approval -> Offer Approver, with suppressed and successful terminal paths.
  State snapshots are checkpointed through `agents/offer_approver/checkpoint.py`.
- Fabric is split by workload: Eventhouse/KQL holds live engagement, game, POS,
  and outcome events; the Lakehouse SQL endpoint supplies read-only historical
  fan context; the optional Warehouse endpoint supports writable T-SQL paths;
  the Fabric Data Agent and ontology provide grounded semantic context.
  Foundry-hosted agents perform reasoning after the deterministic eligibility
  and fatigue gates.
- Synthetic data originates only from
  `data_generators/generate_all.py`. It uses a fixed seed and fictional teams,
  fans, sources, and identifiers for basketball, football, soccer, and hockey.
  Generated CSV/JSONL files live under ignored `data/generated/`.
- `azd up` spans two control planes. `scripts/azd/preprovision.ps1` validates
  prerequisites, generates secrets/data, and runs the idempotent Fabric
  bootstrap. Subscription-scope Bicep then creates Azure resources and the two
  Container Apps. `postprovision.ps1` grants the backend identity Fabric and
  Foundry access; `postdeploy` performs health validation. A blocked Fabric API
  or role assignment must stop deployment rather than produce partial success.

## Repository-specific conventions

- Centralize backend environment access in `agents/shared/config.py`.
  Configuration may be empty during unit-test import, but required Foundry,
  Eventhouse, and Lakehouse values must fail at application startup or
  deployment validation.
- Use `DefaultAzureCredential` and managed identities for Azure, Fabric,
  storage, and Foundry access. Do not add shared keys, connection-string
  fallbacks, registry admin credentials, embedded tokens, wildcard CORS, or
  default production passwords.
- Preserve the public/private service boundary: Bicep tags service resources
  with `azd-service-name`; `azure.yaml` defines both Docker contexts; only the
  web app has public ingress.
- Preserve AG-UI event shapes and the workflow module interface used by
  `agents/server.py`: `start`, `get_state`, and `set_approval_decision`.
  Approval events must be registered before emitting the client tool call to
  avoid losing fast browser responses.
- Keep sport differences behind `SPORTS_IQ_SPORT`,
  `default_sport_context()`, and `agents/middleware/sport_variants.py`.
  Baseline code and documentation must not depend on a real league, team,
  venue, customer, or proprietary dataset.
- Guardrail changes belong in `agents/middleware/` and require focused pytest
  coverage. Keep deterministic gates separate from model-generated offer text.
- Fabric provisioning helpers must be rerunnable: discover by ID/display name
  before creating, overwrite or merge deterministic seed state, poll
  long-running operations, and raise actionable errors for unsupported tenant
  behavior.
- Keep TypeScript strict. Avoid `any`, preserve Next.js server/client
  boundaries, and keep authentication and backend routing server-side.
- GTM and sales assets under `docs/` and `demo/` are intentional repository
  content. Update them when a user-visible workflow or architecture change
  makes their narrative inaccurate.
- Never commit populated `.env` files, azd `.azure/` state, generated datasets,
  real contacts, credentials, tenant/subscription/workspace/item IDs, webhook
  URLs, customer names, or real deployment URLs. Templates must contain
  placeholders only.

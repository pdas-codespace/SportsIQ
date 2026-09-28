# Coding Agent Guide

## Mission

Maintain Sports-IQ as a public, sport-neutral, reproducible Azure/Fabric sample.
Changes must keep `azd up` coherent and must not introduce private identifiers,
real people, customer data, credentials, or generated datasets.

## Repository map

- `agents/`: Python 3.12 FastAPI runtime and Microsoft Agent Framework workflow.
- `webapp/`: Next.js 15 operator experience and same-origin backend proxy.
- `data_generators/`: deterministic synthetic-data source.
- `fabric/`: ontology, Data Agent guidance, and importable notebook items.
- `scripts/`: Fabric bootstrap, KQL schema, azd hooks, and validation helpers.
- `infra/`: subscription-scope Bicep and resource-group modules.
- `tests/`: pytest coverage for agents, guardrails, and workflow behavior.
- `docs/`, `demo/`: architecture, GTM, governance, clickthrough, and voiceover.

## Recreate on another machine

1. Install Git, Python 3.12+, Node.js 22+, PowerShell 7+, Docker, Azure CLI,
   and Azure Developer CLI.
2. Run `az login`, `azd auth login`, and `azd env new`.
3. Set `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_PROJECT_RESOURCE_ID`,
   `FOUNDRY_MODEL`, and either `FABRIC_CAPACITY_ID` or `FABRIC_WORKSPACE_ID`.
4. Run `azd up`.
5. If a tenant API rejects an operation, preserve the explicit failure and
   document the exact administrator prerequisite; never convert it to success.

## Local commands

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r agents\requirements.txt
python -m pytest tests
python -m pytest tests\test_policy_guardrail.py::test_all_pass

Set-Location webapp
npm ci
npm run lint
npm run build
npm run dev
```

Run the backend from the repository root:

```powershell
Copy-Item agents\.env.example agents\.env
uvicorn agents.server:app --reload --port 8000
```

## Implementation conventions

- Use environment variables through `agents/shared/config.py`; do not read
  secrets from source files.
- Required runtime settings may be empty during unit tests but must fail at
  application startup or deployment validation.
- Use `DefaultAzureCredential` and managed identity. Do not add connection
  string, shared-key, registry-admin, or fallback credential paths.
- Browser code calls `/api/agents`; only the Next.js server knows the private
  backend URL.
- Keep guardrail behavior in `agents/middleware/` and add focused pytest cases
  for every behavior change.
- Keep TypeScript strict and avoid `any`; preserve server/client boundaries.
- Fabric scripts must be idempotent: discover by display name or ID before
  creating, use create-merge/overwrite semantics, poll long-running operations,
  and raise on unsupported tenant behavior.
- Generated data belongs under `data/generated/`, which is ignored. Update the
  generator rather than committing output.
- Examples must use fictional teams and `Fictional Fan` identities.

## Deployment contract

Provisioning order is prerequisite checks, synthetic generation, Fabric items,
OneLake/KQL seed, Azure Bicep, identity assignments, container deployment, then
health validation. `infra/main.bicep` is subscription-scoped and
`infra/main.parameters.json` uses azd `${NAME}` substitutions.

When adding a service:

1. Add the tagged Azure resource in Bicep (`azd-service-name`).
2. Add the service to `azure.yaml`.
3. Wire configuration without public secrets.
4. Update README configuration and troubleshooting.
5. Validate Bicep, the relevant unit tests, frontend build, and content scans.

## Public safety checks

Before finishing, search for GUID-shaped hardcoded resource IDs, subscription or
tenant paths, emails, phone numbers, webhook hosts, connection strings,
credentials, real deployment URLs, personal names, committed `.env` files,
generated CSV/JSONL/Parquet, and league-specific baseline dependencies.
Preserve `LICENSE`.

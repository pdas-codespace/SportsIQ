"""
Checkpoint persistence — saves/restores workflow state for HITL pause/resume.
Uses Azure Table Storage (RBAC via DefaultAzureCredential) so state survives
container restarts and is shareable. Falls back to a local JSON file when
AZURE_TABLE_STORAGE_ENDPOINT is not set.
"""
from __future__ import annotations
import json, os, uuid
from datetime import datetime, timezone
from pathlib import Path
from agents.shared import config

# Optional Azure Table Storage import
try:
    from azure.data.tables import TableServiceClient
    from azure.identity import DefaultAzureCredential
    _HAS_TABLES = True
except ImportError:
    _HAS_TABLES = False

_LOCAL_DIR = Path(os.getenv("CHECKPOINT_DIR", "/tmp/sportsiq_checkpoints"))


# ── Public API ───────────────────────────────────────────────────────────────

def new_run_id() -> str:
    return str(uuid.uuid4())


def save(run_id: str, state: dict) -> None:
    """Persist workflow state. state must be JSON-serialisable."""
    state["_updated_at"] = datetime.now(timezone.utc).isoformat()
    if _HAS_TABLES and config.AZURE_TABLE_STORAGE_ENDPOINT:
        _save_table(run_id, state)
    else:
        _save_file(run_id, state)


def load(run_id: str) -> dict | None:
    """Restore workflow state, or None if not found."""
    if _HAS_TABLES and config.AZURE_TABLE_STORAGE_ENDPOINT:
        return _load_table(run_id)
    return _load_file(run_id)


def mark_approval_decision(run_id: str, offer_id: str, approved: bool, reason: str = "") -> dict:
    """Update the approval decision for one offer and return updated state."""
    state = load(run_id) or {}
    decisions = state.setdefault("approval_decisions", {})
    decisions[offer_id] = {
        "approved": approved,
        "reason": reason,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    # Check if all offers have been decided
    pending_offers = state.get("pending_offers", [])
    all_decided = all(oid in decisions for oid in pending_offers)
    state["all_decided"] = all_decided
    state["workflow_status"] = "completed" if all_decided else "awaiting_approval"
    save(run_id, state)
    return state


def delete(run_id: str) -> None:
    """Remove checkpoint after workflow completes."""
    if _HAS_TABLES and config.AZURE_TABLE_STORAGE_ENDPOINT:
        _delete_table(run_id)
    else:
        p = _local_path(run_id)
        if p.exists():
            p.unlink()


# ── Azure Table Storage backend (RBAC / DefaultAzureCredential) ───────────────

def _table_client():
    credential = DefaultAzureCredential()
    svc = TableServiceClient(endpoint=config.AZURE_TABLE_STORAGE_ENDPOINT, credential=credential)
    svc.create_table_if_not_exists(config.CHECKPOINT_TABLE_NAME)
    return svc.get_table_client(config.CHECKPOINT_TABLE_NAME)


def _save_table(run_id: str, state: dict) -> None:
    client = _table_client()
    client.upsert_entity({
        "PartitionKey": "workflow",
        "RowKey": run_id,
        "state_json": json.dumps(state),
    })


def _load_table(run_id: str) -> dict | None:
    try:
        entity = _table_client().get_entity("workflow", run_id)
        return json.loads(entity["state_json"])
    except Exception:
        return None


def _delete_table(run_id: str) -> None:
    try:
        _table_client().delete_entity("workflow", run_id)
    except Exception:
        pass


# ── Local file fallback ───────────────────────────────────────────────────────

def _local_path(run_id: str) -> Path:
    _LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    return _LOCAL_DIR / f"{run_id}.json"


def _save_file(run_id: str, state: dict) -> None:
    _local_path(run_id).write_text(json.dumps(state, indent=2))


def _load_file(run_id: str) -> dict | None:
    p = _local_path(run_id)
    if p.exists():
        return json.loads(p.read_text())
    return None

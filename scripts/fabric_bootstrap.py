#!/usr/bin/env python3
"""Idempotently create and seed the Microsoft Fabric items used by Sports-IQ."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

FABRIC_API = "https://api.fabric.microsoft.com/v1"
ONELAKE_API = "https://onelake.dfs.fabric.microsoft.com"
ROOT = Path(__file__).resolve().parents[1]


class BootstrapError(RuntimeError):
    pass


def run(*args: str, secret_output: bool = False) -> str:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise BootstrapError(f"{' '.join(args[:3])} failed: {detail}")
    return completed.stdout.strip() if not secret_output else completed.stdout.strip()


def azd_value(name: str, required: bool = False) -> str:
    completed = subprocess.run(
        ("azd", "env", "get-value", name),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    value = completed.stdout.strip() if completed.returncode == 0 else ""
    if required and not value:
        raise BootstrapError(f"Missing azd environment value: {name}")
    return value


def set_azd_value(name: str, value: str) -> None:
    run("azd", "env", "set", name, value)


def access_token(resource: str) -> str:
    return run(
        "az",
        "account",
        "get-access-token",
        "--resource",
        resource,
        "--query",
        "accessToken",
        "-o",
        "tsv",
        secret_output=True,
    )


def request(
    method: str,
    url: str,
    token: str,
    body: dict[str, Any] | bytes | None = None,
    headers: dict[str, str] | None = None,
    expected: tuple[int, ...] = (200, 201, 202),
) -> tuple[Any, dict[str, str], int]:
    request_headers = {"Authorization": f"Bearer {token}"}
    request_headers.update(headers or {})
    data: bytes | None = None
    if isinstance(body, dict):
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    elif isinstance(body, bytes):
        data = body
    req = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read()
            payload = json.loads(raw) if raw else None
            return payload, dict(response.headers), response.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code not in expected:
            raise BootstrapError(f"{method} {url} failed ({exc.code}): {detail}") from exc
        return None, dict(exc.headers), exc.code


def values(payload: Any) -> list[dict[str, Any]]:
    return payload.get("value", []) if isinstance(payload, dict) else []


def poll_operation(location: str, token: str) -> dict[str, Any]:
    for _ in range(60):
        payload, _, _ = request("GET", location, token)
        status = (payload or {}).get("status", "").lower()
        if status == "succeeded":
            return payload
        if status in {"failed", "cancelled"}:
            raise BootstrapError(f"Fabric operation failed: {json.dumps(payload)}")
        time.sleep(2)
    raise BootstrapError(f"Fabric operation timed out: {location}")


def ensure_workspace(token: str, display_name: str, capacity_id: str) -> str:
    payload, _, _ = request("GET", f"{FABRIC_API}/workspaces", token)
    existing = next((item for item in values(payload) if item.get("displayName") == display_name), None)
    if existing:
        return existing["id"]
    if not capacity_id:
        raise BootstrapError(
            f"Fabric workspace '{display_name}' does not exist. Set FABRIC_CAPACITY_ID "
            "to a capacity where you can create workspaces, or set FABRIC_WORKSPACE_ID "
            "to an existing workspace."
        )
    created, headers, status = request(
        "POST",
        f"{FABRIC_API}/workspaces",
        token,
        {"displayName": display_name, "capacityId": capacity_id},
    )
    if status == 202:
        created = poll_operation(headers["Location"], token)
    workspace_id = (created or {}).get("id")
    if not workspace_id:
        raise BootstrapError(f"Workspace creation returned no id: {created}")
    return workspace_id


def ensure_item(
    token: str,
    workspace_id: str,
    display_name: str,
    item_type: str,
    creation_payload: dict[str, Any] | None = None,
) -> str:
    query = urllib.parse.urlencode({"type": item_type})
    payload, _, _ = request(
        "GET", f"{FABRIC_API}/workspaces/{workspace_id}/items?{query}", token
    )
    existing = next((item for item in values(payload) if item.get("displayName") == display_name), None)
    if existing:
        return existing["id"]
    body: dict[str, Any] = {"displayName": display_name, "type": item_type}
    if creation_payload:
        body["creationPayload"] = creation_payload
    created, headers, status = request(
        "POST", f"{FABRIC_API}/workspaces/{workspace_id}/items", token, body
    )
    if status == 202:
        created = poll_operation(headers["Location"], token)
    item_id = (created or {}).get("id")
    if not item_id:
        raise BootstrapError(f"{item_type} creation returned no id: {created}")
    return item_id


def import_notebook(token: str, workspace_id: str, notebook_id: str) -> None:
    notebook = ROOT / "fabric" / "notebooks" / "bootstrap_sports_iq.ipynb"
    payload = {
        "definition": {
            "parts": [
                {
                    "path": "notebook-content.py",
                    "payload": base64.b64encode(notebook.read_bytes()).decode("ascii"),
                    "payloadType": "InlineBase64",
                }
            ]
        }
    }
    _, headers, status = request(
        "POST",
        f"{FABRIC_API}/workspaces/{workspace_id}/items/{notebook_id}/updateDefinition",
        token,
        payload,
    )
    if status == 202 and headers.get("Location"):
        poll_operation(headers["Location"], token)


def ensure_directory(token: str, url: str) -> None:
    try:
        request(
            "PUT",
            f"{url}?resource=directory",
            token,
            headers={"x-ms-version": "2023-11-03"},
            expected=(201, 409),
        )
    except BootstrapError as exc:
        if "(409)" not in str(exc):
            raise


def upload_file(token: str, base: str, local_path: Path, remote_path: str) -> None:
    parts = remote_path.split("/")[:-1]
    current = base
    for part in parts:
        current = f"{current}/{part}"
        ensure_directory(token, current)
    url = f"{base}/{remote_path}"
    content = local_path.read_bytes()
    common = {"x-ms-version": "2023-11-03"}
    request("PUT", f"{url}?resource=file", token, headers=common, expected=(201,))
    append_headers = {**common, "Content-Length": str(len(content))}
    request(
        "PATCH",
        f"{url}?action=append&position=0",
        token,
        content,
        append_headers,
        expected=(202,),
    )
    request(
        "PATCH",
        f"{url}?action=flush&position={len(content)}",
        token,
        headers=common,
        expected=(200,),
    )


def load_lakehouse_tables(token: str, workspace_id: str, lakehouse_id: str) -> None:
    for csv_path in sorted((ROOT / "data" / "generated" / "static").glob("*.csv")):
        body = {
            "relativePath": f"Files/synthetic/static/{csv_path.name}",
            "pathType": "File",
            "mode": "Overwrite",
            "recursive": False,
            "formatOptions": {"format": "Csv", "header": True, "delimiter": ","},
        }
        _, headers, status = request(
            "POST",
            f"{FABRIC_API}/workspaces/{workspace_id}/lakehouses/{lakehouse_id}/tables/{csv_path.stem}/load",
            token,
            body,
        )
        if status == 202 and headers.get("Location"):
            poll_operation(headers["Location"], token)


def kql_command(cluster_uri: str, database: str, token: str, command: str) -> None:
    request(
        "POST",
        f"{cluster_uri.rstrip('/')}/v1/rest/mgmt",
        token,
        {"db": database, "csl": command},
    )


def seed_eventhouse(cluster_uri: str, database: str) -> None:
    token = access_token("https://kusto.kusto.windows.net")
    schema_text = (ROOT / "scripts" / "create_kql_tables.kql").read_text(encoding="utf-8")
    for command in (
        line.strip()
        for line in schema_text.splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ):
        kql_command(cluster_uri, database, token, command)
    mappings = {
        "fan_engagement_events.jsonl": "FanEngagementEvent",
        "pos_transactions.jsonl": "POSTransaction",
        "game_excitement_index.jsonl": "GameExcitementIndex",
    }
    for filename, table in mappings.items():
        rows = (ROOT / "data" / "generated" / "streaming" / filename).read_text(
            encoding="utf-8"
        )
        kql_command(
            cluster_uri,
            database,
            token,
            f".ingest inline into table {table} with (format='multijson') <|\n{rows}",
        )


def get_item_properties(
    token: str, workspace_id: str, item_type_path: str, item_id: str
) -> dict[str, Any]:
    payload, _, _ = request(
        "GET",
        f"{FABRIC_API}/workspaces/{workspace_id}/{item_type_path}/{item_id}",
        token,
    )
    return payload or {}


def main() -> int:
    fabric_token = access_token("https://api.fabric.microsoft.com")
    workspace_id = azd_value("FABRIC_WORKSPACE_ID")
    workspace_name = azd_value("FABRIC_WORKSPACE_NAME") or (
        f"{azd_value('AZURE_ENV_NAME', required=True)}-sportsiq"
    )
    if not workspace_id:
        workspace_id = ensure_workspace(
            fabric_token, workspace_name, azd_value("FABRIC_CAPACITY_ID")
        )

    lakehouse_name = azd_value("LAKEHOUSE_DB") or "SportsIQ_Lakehouse"
    eventhouse_name = "SportsIQ_Eventhouse"
    kql_database_name = azd_value("EVENTHOUSE_DB") or "SportsIQ_Eventhouse"
    lakehouse_id = ensure_item(
        fabric_token, workspace_id, lakehouse_name, "Lakehouse"
    )
    ensure_item(fabric_token, workspace_id, eventhouse_name, "Eventhouse")
    kql_database_id = ensure_item(
        fabric_token,
        workspace_id,
        kql_database_name,
        "KQLDatabase",
        {"databaseType": "ReadWrite"},
    )
    notebook_id = ensure_item(
        fabric_token, workspace_id, "SportsIQ_Bootstrap", "Notebook"
    )
    import_notebook(fabric_token, workspace_id, notebook_id)

    storage_token = access_token("https://storage.azure.com")
    onelake_base = f"{ONELAKE_API}/{workspace_id}/{lakehouse_id}"
    for path in sorted((ROOT / "data" / "generated").rglob("*")):
        if path.is_file():
            remote = "Files/synthetic/" + path.relative_to(
                ROOT / "data" / "generated"
            ).as_posix()
            upload_file(storage_token, onelake_base, path, remote)
    load_lakehouse_tables(fabric_token, workspace_id, lakehouse_id)

    lakehouse = get_item_properties(
        fabric_token, workspace_id, "lakehouses", lakehouse_id
    )
    kql_database = get_item_properties(
        fabric_token, workspace_id, "kqlDatabases", kql_database_id
    )
    sql_properties = lakehouse.get("properties", {}).get("sqlEndpointProperties", {})
    sql_endpoint = (
        sql_properties.get("connectionString")
        or sql_properties.get("server")
        or sql_properties.get("endpoint")
    )
    cluster_uri = (
        kql_database.get("properties", {}).get("queryServiceUri")
        or kql_database.get("properties", {}).get("queryServiceURI")
    )
    if not sql_endpoint or not cluster_uri:
        raise BootstrapError(
            "Fabric items were created, but their SQL/KQL endpoints are not available. "
            "Wait for item provisioning to complete and rerun 'azd up'."
        )
    seed_eventhouse(cluster_uri, kql_database_name)

    for name, value in {
        "FABRIC_WORKSPACE_ID": workspace_id,
        "FABRIC_LAKEHOUSE_ID": lakehouse_id,
        "FABRIC_KQL_DATABASE_ID": kql_database_id,
        "LAKEHOUSE_SQL_ENDPOINT": sql_endpoint,
        "EVENTHOUSE_URI": cluster_uri,
    }.items():
        set_azd_value(name, value)
    print(f"Fabric workspace ready: {workspace_name} ({workspace_id})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

#!/usr/bin/env python3
"""Grant a deployed managed identity access to the configured Fabric workspace."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--principal-id", required=True)
    args = parser.parse_args()

    token_result = subprocess.run(
        (
            "az",
            "account",
            "get-access-token",
            "--resource",
            "https://api.fabric.microsoft.com",
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    if token_result.returncode:
        print(token_result.stderr, file=sys.stderr)
        return 1

    url = (
        "https://api.fabric.microsoft.com/v1/workspaces/"
        f"{args.workspace_id}/roleAssignments"
    )
    body = json.dumps(
        {
            "principal": {
                "id": args.principal_id,
                "type": "ServicePrincipal",
            },
            "role": "Member",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token_result.stdout.strip()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return 0 if response.status in (200, 201) else 1
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 409:
            return 0
        print(f"Fabric role assignment failed ({exc.code}): {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

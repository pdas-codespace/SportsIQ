$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$principalId = (azd env get-value AGENTS_IDENTITY_PRINCIPAL_ID).Trim()
$workspaceId = (azd env get-value FABRIC_WORKSPACE_ID).Trim()
$foundryResourceId = (azd env get-value FOUNDRY_PROJECT_RESOURCE_ID 2>$null).Trim()

if (-not $principalId -or -not $workspaceId) {
    throw "Provisioning did not produce the managed identity or Fabric workspace ID."
}

python scripts/fabric_assign_identity.py --workspace-id $workspaceId --principal-id $principalId
if ($LASTEXITCODE -ne 0) {
    throw @"
Could not grant the agents managed identity Member access to the Fabric workspace.
Grant principal '$principalId' Member access to workspace '$workspaceId', then rerun
'azd up'. The deployment intentionally stops rather than reporting partial success.
"@
}

if (-not $foundryResourceId) {
    throw @"
FOUNDRY_PROJECT_RESOURCE_ID is required to grant the deployed managed identity
access to Microsoft Foundry. Set the full Azure resource ID with:
  azd env set FOUNDRY_PROJECT_RESOURCE_ID /subscriptions/<subscription>/resourceGroups/<group>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>
Then rerun 'azd up'.
"@
}

az role assignment create `
    --assignee-object-id $principalId `
    --assignee-principal-type ServicePrincipal `
    --role "Azure AI User" `
    --scope $foundryResourceId `
    --only-show-errors | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to grant Azure AI User on the Foundry project to $principalId."
}

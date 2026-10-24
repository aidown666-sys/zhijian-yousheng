$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
. "$PSScriptRoot\tools\find-python.ps1"
$runtimePython = Find-ProjectPython
if (Test-Path -LiteralPath 'integrations/polyv/watch-config.json') {
    $config = Get-Content -Raw -LiteralPath 'integrations/polyv/watch-config.json' | ConvertFrom-Json
    & $runtimePython integrations/polyv/watch_bridge.py --url $config.watch_url
} else {
    & $runtimePython integrations/polyv/bridge.py
}
exit $LASTEXITCODE

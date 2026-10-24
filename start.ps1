$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
. "$PSScriptRoot\tools\find-python.ps1"
$runtimePython = Find-ProjectPython
& $runtimePython live_server.py
exit $LASTEXITCODE

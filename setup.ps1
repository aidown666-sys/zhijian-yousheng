param([string]$IndexUrl = 'https://pypi.org/simple')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
. "$PSScriptRoot\tools\find-python.ps1"
$runtimePython = Find-ProjectPython
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & $runtimePython -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
& .\.venv\Scripts\python.exe -m pip install --index-url $IndexUrl -r requirements-3d.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
Write-Host 'Ready. Run start.cmd; use git lfs pull for assets and motion data.'

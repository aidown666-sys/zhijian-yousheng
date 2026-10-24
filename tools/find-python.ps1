function Find-ProjectPython {
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $candidates = @($env:SIGN_PYTHON, (Join-Path $projectRoot '.venv\Scripts\python.exe'), (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'))
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { return $candidate }
    }
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw 'Python not found. Install Python 3.12 or set SIGN_PYTHON.'
}

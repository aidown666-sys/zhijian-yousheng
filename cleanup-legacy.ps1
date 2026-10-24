param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$targets = @('.venv','models','offline','vendor','runtime\wheels','runtime\domestic-import','runtime\three.tgz','runtime\three-vrm.tgz')
$keepOutputs = @('custom-avatar','reference-v2','reference-v3','high-fidelity','pose-validation')
Get-ChildItem -LiteralPath (Join-Path $projectRoot 'outputs') -Directory | Where-Object { $_.Name -notin $keepOutputs } | ForEach-Object { $targets += $_.FullName.Substring($projectRoot.Length+1) }
$plan = @()
foreach ($relativeTarget in $targets) {
    $absoluteTarget = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $relativeTarget))
    if (-not $absoluteTarget.StartsWith($projectRoot + [System.IO.Path]::DirectorySeparatorChar,[System.StringComparison]::OrdinalIgnoreCase)) { throw "Unsafe cleanup path: $absoluteTarget" }
    if (Test-Path -LiteralPath $absoluteTarget) {
        $entry = Get-Item -LiteralPath $absoluteTarget
        if ($entry.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw "Refusing linked path: $absoluteTarget" }
        if ($entry.PSIsContainer) { $bytes=(Get-ChildItem -LiteralPath $absoluteTarget -File -Recurse | Measure-Object Length -Sum).Sum } else { $bytes=$entry.Length }
        $plan += [pscustomobject]@{path=$absoluteTarget;bytes=[long]$bytes;GiB=[math]::Round($bytes/1GB,3)}
    }
}
$plan | Format-Table path,GiB -AutoSize
$total=($plan | Measure-Object bytes -Sum).Sum
Write-Host ('Estimated removal: {0:N2} GiB' -f ($total/1GB))
Write-Host 'Kept: assets/3d, Blender sources, data/lmdb, data/sign_dictionary, runtime/pose_packages, 3D web app.'
if (-not $Apply) { Write-Host 'Preview only. No files removed.';exit }
$answer=Read-Host 'Permanently remove only the listed legacy paths? Type CLEAN to continue'
if ($answer -cne 'CLEAN') { Write-Host 'Cancelled';exit }
$deleted=@()
foreach ($entry in $plan) {
    Remove-Item -LiteralPath $entry.path -Recurse -Force -ErrorAction Stop
    $deleted+=$entry
}
@{deleted=$deleted;removed_bytes=$total;finished=[DateTime]::Now.ToString('o')} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $projectRoot 'runtime\cleanup-result.json') -Encoding utf8
Write-Host ('Finished. Removed {0:N2} GiB' -f ($total/1GB))

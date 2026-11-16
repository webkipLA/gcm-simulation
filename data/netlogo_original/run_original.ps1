# Runs the BehaviorSpace experiments of the model copy without the NetLogo interface.
# Usage:  .\run_original.ps1            (looks for NetLogo under C:\Program Files)
#         .\run_original.ps1 -NetLogo "D:\Apps\NetLogo 7.0.4\NetLogo_Console.exe"
param([string]$NetLogo = '', [int]$Threads = 4)
$ErrorActionPreference = 'Stop'
if (-not $NetLogo) {
  $found = Get-ChildItem 'C:\Program Files\NetLogo*\NetLogo_Console.exe' -ErrorAction SilentlyContinue | Sort-Object FullName | Select-Object -Last 1
  if (-not $found) { throw 'NetLogo_Console.exe not found. Pass its path with -NetLogo.' }
  $NetLogo = $found.FullName
}
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$model = Join-Path $here 'GarbageCan_simplified17_headless.nlogox'
$experiments = @('Organized Anarchy', 'Organized Anarchy P', 'Organized Anarchy BP', 'Organized Anarchy P+BP', 'Competent Hierarchy', 'Competent Hierarchy P', 'Competent Hierarchy BP', 'Competent Hierarchy P+BP', 'Incompetent Hierarchy', 'Incompetent Hierarchy P', 'Incompetent Hierarchy BP', 'Incompetent Hierarchy P+BP')
foreach ($e in $experiments) {
  $file = ($e -replace '\+', ' and ') -replace '[^A-Za-z0-9]+', '_'
  $table = Join-Path $here (Join-Path 'tables' ($file.Trim('_') + '.csv'))
  if (Test-Path $table) { Write-Host "skip $e (table exists)"; continue }
  Write-Host "$(Get-Date -Format HH:mm:ss)  $e"
  & $NetLogo --headless --model $model --experiment $e --threads $Threads --table $table
  if ($LASTEXITCODE -ne 0) { throw "NetLogo ended with code $LASTEXITCODE in experiment $e" }
}
Write-Host 'done. Next: uv run python scripts/netlogo_original.py compare'

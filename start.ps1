$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$localPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$preparedPackages = Join-Path $PSScriptRoot '../../work/packages'
if (Test-Path -LiteralPath $localPython) {
    & $localPython app.py
} elseif ((Test-Path -LiteralPath $bundledPython) -and (Test-Path -LiteralPath $preparedPackages)) {
    $env:PYTHONPATH = (Resolve-Path -LiteralPath $preparedPackages).Path
    & $bundledPython app.py
} else {
    Write-Host 'Please follow README.md to install Python and requirements, then run: python app.py'
}

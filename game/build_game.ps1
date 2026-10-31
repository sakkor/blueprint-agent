# build_game.ps1 - Build the Space Fractions Windows desktop executable.
# Runs the test suite, then packages desktop.py into Space-Fractions.exe.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "== Running tests =="
python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    throw "Tests failed; aborting build."
}

Write-Host "== Building Space-Fractions.exe =="
python -m PyInstaller --onefile --windowed --name Space-Fractions desktop.py

if ($LASTEXITCODE -ne 0) { throw "Packaging failed." }

Write-Host "== Build complete: dist/Space-Fractions.exe =="

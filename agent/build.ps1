$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
py -3.12 -m venv .build-venv
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 with Tkinter to build from source.' }
& '.\.build-venv\Scripts\python.exe' -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& '.\.build-venv\Scripts\python.exe' -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
$exampleData = (Join-Path $PSScriptRoot 'examples') + ';examples'
# Some Python distributions require adjacent TLS data; retain their trust policy.
$tlsData = & '.\.build-venv\Scripts\python.exe' -c "import ssl,pathlib; p=pathlib.Path(ssl.__file__).with_name('codex-rejected-cas.pem'); print(str(p) if p.is_file() else '')"
$bundleArgs = @('-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--name','Blueprint-Agent-2.3.2','--add-data',$exampleData)
if ($tlsData) { $bundleArgs += @('--add-data',($tlsData.Trim()+';.')) }
$bundleArgs += 'app.py'
& '.\.build-venv\Scripts\python.exe' @bundleArgs
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
$smokePath = Join-Path $PSScriptRoot 'dist\packaged-smoke.json'
$smokeProcess = Start-Process -FilePath '.\dist\Blueprint-Agent-2.3.2.exe' -ArgumentList '--self-test',('"'+$smokePath+'"') -Wait -PassThru -WindowStyle Hidden
if ($smokeProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $smokePath)) { throw 'Packaged smoke test failed.' }
Write-Host 'Built and smoke-tested dist\Blueprint-Agent-2.3.2.exe'

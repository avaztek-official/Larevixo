$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    py -3.12 -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv. Install Python 3.12 first.' }
}
& $python -m pip install -r requirements.txt 'pyinstaller==6.22.3'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed inside the project .venv.' }
& $python -m PyInstaller --noconfirm --clean --windowed --onefile --name Larevixo --icon assets/larevixo.ico --add-data 'assets;assets' --add-data 'lang;lang' --hidden-import PySide6.QtSvg main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
Write-Host "Build finished: $PSScriptRoot\dist\Larevixo.exe"

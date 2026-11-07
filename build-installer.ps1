$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$compiler = $null
if ($env:INNO_SETUP_COMPILER -and (Test-Path -LiteralPath $env:INNO_SETUP_COMPILER -PathType Leaf)) {
    $compiler = (Resolve-Path -LiteralPath $env:INNO_SETUP_COMPILER).Path
} else {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { $compiler = $command.Source }
}

if (-not $compiler) {
    $candidates = @(
        "$env:ProgramFiles(x86)\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $compiler = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}

if (-not $compiler) {
    throw 'Inno Setup 6.5.2 or newer (ISCC.exe) was not found. Install it separately or set INNO_SETUP_COMPILER; no system-wide installation was attempted.'
}

$productVersion = (Get-Item -LiteralPath $compiler).VersionInfo.ProductVersion
$versionMatch = [regex]::Match($productVersion, '^\d+\.\d+\.\d+(?:\.\d+)?')
if (-not $versionMatch.Success -or [version]$versionMatch.Value -lt [version]'6.5.2') {
    $compilerVersionOutput = & $compiler --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $versionMatch = [regex]::Match(($compilerVersionOutput -join "`n"), '\d+\.\d+\.\d+(?:\.\d+)?')
    }
}
if (-not $versionMatch.Success -or [version]$versionMatch.Value -lt [version]'6.5.2') {
    $registryPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 7_is1',
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 7_is1',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1'
    )
    foreach ($registryPath in $registryPaths) {
        $installedVersion = (Get-ItemProperty -LiteralPath $registryPath -Name DisplayVersion -ErrorAction SilentlyContinue).DisplayVersion
        $registryVersionMatch = [regex]::Match([string]$installedVersion, '^\d+\.\d+\.\d+(?:\.\d+)?')
        if ($registryVersionMatch.Success -and [version]$registryVersionMatch.Value -ge [version]'6.5.2') {
            $productVersion = $registryVersionMatch.Value
            $versionMatch = $registryVersionMatch
            break
        }
    }
}
if (-not $versionMatch.Success -or [version]$versionMatch.Value -lt [version]'6.5.2') {
    throw "Inno Setup 6.5.2 or newer is required for PNG branding. Detected: $productVersion"
}

$version = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'VERSION') -Raw).Trim()
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw "Invalid VERSION value: $version" }

& (Join-Path $PSScriptRoot 'build-windows.ps1')
if ($LASTEXITCODE -ne 0) { throw 'The portable EXE build failed; installer compilation was skipped.' }

$script = Join-Path $PSScriptRoot 'installer\Larevixo.iss'
& $compiler "/DAppVersion=$version" $script
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed to compile the installer.' }

$installer = Join-Path $PSScriptRoot "dist\Larevixo-Setup-$version.exe"
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw "Expected installer was not created: $installer" }
Write-Host "Installer finished: $installer"

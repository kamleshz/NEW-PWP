$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found at .venv\Scripts\python.exe"
}

Write-Host "Installing desktop build dependencies..."
& $venvPython -m pip install -r desktop_requirements.txt

Write-Host "Cleaning previous desktop build output..."
if (Test-Path ".\build") {
    Remove-Item ".\build" -Recurse -Force
}
if (Test-Path ".\dist") {
    Remove-Item ".\dist" -Recurse -Force
}

Write-Host "Building PWPDesktopApp.exe ..."
& $venvPython -m PyInstaller --clean desktop.spec

$distFolder = Join-Path $projectRoot "dist"
$releaseFolder = Join-Path $projectRoot "desktop_release"

if (Test-Path $releaseFolder) {
    Remove-Item $releaseFolder -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseFolder | Out-Null

Copy-Item (Join-Path $distFolder "PWPDesktopApp.exe") $releaseFolder
Copy-Item ".\desktop_release.json" $releaseFolder
Copy-Item ".\CLIENT_README.txt" $releaseFolder

$zipPath = Join-Path $projectRoot "desktop_release\PWPDesktopApp.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}
Compress-Archive -Path (Join-Path $releaseFolder "PWPDesktopApp.exe"), (Join-Path $releaseFolder "desktop_release.json"), (Join-Path $releaseFolder "CLIENT_README.txt") -DestinationPath $zipPath

Write-Host "Desktop build completed."
Write-Host "EXE: $releaseFolder\PWPDesktopApp.exe"
Write-Host "ZIP: $zipPath"
Write-Host "Share with client from: $releaseFolder"

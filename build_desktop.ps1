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

Write-Host "Building fast desktop app folder ..."
& $venvPython -m PyInstaller --clean desktop.spec

$distFolder = Join-Path $projectRoot "dist"
$releaseFolder = Join-Path $projectRoot "desktop_release"
$zipPath = Join-Path $releaseFolder "PWPDesktopApp.zip"
$legacyReleaseExe = Join-Path $releaseFolder "PWPDesktopApp.exe"
$releaseAppFolder = Join-Path $releaseFolder "PWPDesktopApp"
$distAppFolder = Join-Path $distFolder "PWPDesktopApp"
$releaseJson = Join-Path $releaseFolder "desktop_release.json"
$releaseReadme = Join-Path $releaseFolder "CLIENT_README.txt"
$tempStageFolder = Join-Path $projectRoot "build\desktop_release_stage"
$tempZipPath = Join-Path $projectRoot "build\PWPDesktopApp.zip"

if (Test-Path $tempStageFolder) {
    Remove-Item $tempStageFolder -Recurse -Force
}
New-Item -ItemType Directory -Path $tempStageFolder | Out-Null

foreach ($item in @($zipPath, $releaseJson, $releaseReadme, $tempZipPath)) {
    if (Test-Path $item) {
        Remove-Item $item -Force
    }
}

if (Test-Path $legacyReleaseExe) {
    try {
        Remove-Item $legacyReleaseExe -Force
    }
    catch {
        Write-Warning "Could not remove old desktop_release\PWPDesktopApp.exe. Delete it manually if it still appears."
    }
}

if (-not (Test-Path $releaseFolder)) {
    New-Item -ItemType Directory -Path $releaseFolder | Out-Null
}

Copy-Item $distAppFolder (Join-Path $tempStageFolder "PWPDesktopApp") -Recurse
Copy-Item ".\desktop_release.json" (Join-Path $tempStageFolder "desktop_release.json")
Copy-Item ".\CLIENT_README.txt" (Join-Path $tempStageFolder "CLIENT_README.txt")

& $venvPython -c "import shutil, pathlib; stage = pathlib.Path(r'$tempStageFolder'); out = pathlib.Path(r'$tempZipPath'); out.parent.mkdir(parents=True, exist_ok=True); shutil.make_archive(str(out.with_suffix('')), 'zip', root_dir=str(stage))"

$appFolderLocked = $false
try {
    if (Test-Path $releaseAppFolder) {
        Remove-Item $releaseAppFolder -Recurse -Force
    }
    Copy-Item $distAppFolder $releaseAppFolder -Recurse
}
catch {
    $appFolderLocked = $true
    Write-Warning "Could not replace desktop_release\PWPDesktopApp because one of its files is in use. Close the running app later if you want the folder copy refreshed."
}

Copy-Item ".\desktop_release.json" $releaseJson -Force
Copy-Item ".\CLIENT_README.txt" $releaseReadme -Force
Copy-Item $tempZipPath $zipPath -Force

if (Test-Path $tempStageFolder) {
    Remove-Item $tempStageFolder -Recurse -Force
}

Write-Host "Desktop build completed."
Write-Host "App Folder: $releaseFolder\PWPDesktopApp"
Write-Host "ZIP: $zipPath"
Write-Host "Share with client from: $releaseFolder"
if ($appFolderLocked) {
    Write-Host "Note: ZIP is fresh, but desktop_release\PWPDesktopApp could not be fully replaced because it is currently running."
}

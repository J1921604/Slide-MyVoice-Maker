# Slide Voice Maker - ワンクリック起動スクリプト

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Slide Voice Maker Server"

Set-Location -Path $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

Write-Host ""
Write-Host "========================================"
Write-Host "  Slide Voice Maker Server"
Write-Host "  http://127.0.0.1:8000"
Write-Host "========================================"
Write-Host ""

if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "既存の仮想環境を使用します..."
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "仮想環境を作成しています..."
    py -3.10 -m venv .venv
    & .\.venv\Scripts\Activate.ps1
    Write-Host "依存関係をインストールしています..."
    pip install -r requirements.txt
}

$existingProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existingProcess) {
    Write-Host "ポート8000を解放しています..."
    $existingProcess | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

Write-Host "サーバーを起動しています..."

# サーバーを別のPowerShellウィンドウで起動（最小化）
$serverScript = @"
Set-Location '$PSScriptRoot'
& '$PSScriptRoot\.venv\Scripts\Activate.ps1'
py -3.10 -m uvicorn src.server:app --host 127.0.0.1 --port 8000
"@
$bytes = [System.Text.Encoding]::Unicode.GetBytes($serverScript)
$encoded = [Convert]::ToBase64String($bytes)
Start-Process powershell -ArgumentList "-WindowStyle Minimized -NoExit -EncodedCommand $encoded"

Write-Host "サーバー起動を待機中..."
$maxWait = 30
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000" -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) { break }
    } catch { }
    Start-Sleep -Seconds 1
    $waited++
}

if ($waited -ge $maxWait) {
    Write-Host "サーバー起動がタイムアウトしました。"
    exit 1
}

Write-Host "ブラウザを起動しています..."
Start-Process "http://127.0.0.1:8000"

Write-Host ""
Write-Host "ブラウザが起動しました。"
Write-Host "サーバーはバックグラウンドで動作しています。"
Write-Host ""

Start-Sleep -Seconds 3

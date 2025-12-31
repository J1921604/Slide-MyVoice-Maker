# Slide Voice Maker - ワンクリック起動スクリプト
# バージョン: 1.0.0
# 日付: 2026-01-05

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

# 仮想環境の確認と作成
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

# ポート8000の解放
$existingProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existingProcess) {
    Write-Host "ポート8000を解放しています..."
    $existingProcess | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

Write-Host "サーバーを起動しています..."

# サーバーをバックグラウンドプロセスとして起動（別ウィンドウなし）
$venvPython = "$PSScriptRoot\.venv\Scripts\python.exe"
$arguments = "-m uvicorn src.server:app --host 127.0.0.1 --port 8000"
$pinfo = New-Object System.Diagnostics.ProcessStartInfo
$pinfo.FileName = $venvPython
$pinfo.Arguments = $arguments
$pinfo.WorkingDirectory = $PSScriptRoot
$pinfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$pinfo.CreateNoWindow = $true
$pinfo.UseShellExecute = $true
$process = [System.Diagnostics.Process]::Start($pinfo)

Write-Host "サーバー起動を待機中..."
$maxWait = 30
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) { break }
    } catch { }
    Start-Sleep -Seconds 1
    $waited++
}

if ($waited -ge $maxWait) {
    Write-Host "サーバー起動がタイムアウトしました。" -ForegroundColor Red
    Write-Host "手動で起動する場合: py -3.10 -m uvicorn src.server:app --host 127.0.0.1 --port 8000"
    exit 1
}

# ブラウザでindex.htmlを開く
Write-Host "ブラウザを起動しています..."
Start-Process "http://127.0.0.1:8000/index.html"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  サーバー起動完了！" -ForegroundColor Green
Write-Host "  URL: http://127.0.0.1:8000/index.html" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "サーバーはバックグラウンドで動作しています。"
Write-Host "終了するにはタスクマネージャーからpython.exeを終了してください。"
Write-Host ""

Start-Sleep -Seconds 3

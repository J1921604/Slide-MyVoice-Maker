# Slide Voice Maker - ワンクリック起動スクリプト
# サーバー起動 → ブラウザで開く → PowerShell終了

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Slide Voice Maker Server"

# 作業ディレクトリ設定
Set-Location -Path $PSScriptRoot

# 文字コード設定
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

# ポート8000が使用中なら解放
$existingProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existingProcess) {
    Write-Host "ポート8000を解放しています..."
    $existingProcess | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

Write-Host "サーバーを起動しています..."

# サーバーをバックグラウンドで起動
$serverJob = Start-Job -ScriptBlock {
    Set-Location $using:PSScriptRoot
    & .\.venv\Scripts\Activate.ps1
    py -3.10 -m uvicorn src.server:app --host 127.0.0.1 --port 8000
}

# サーバー起動待機
Write-Host "サーバー起動を待機中..."
$maxWait = 30
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000" -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            break
        }
    } catch {
        # まだ起動していない
    }
    Start-Sleep -Seconds 1
    $waited++
}

if ($waited -ge $maxWait) {
    Write-Host "サーバー起動がタイムアウトしました。"
    exit 1
}

# ブラウザで開く
Write-Host "ブラウザを起動しています..."
Start-Process "http://127.0.0.1:8000"

Write-Host ""
Write-Host "ブラウザが起動しました。"
Write-Host "このウィンドウは自動的に閉じます。"
Write-Host "サーバーはバックグラウンドで動作しています。"
Write-Host ""

# PowerShellウィンドウを閉じる（3秒後）
Start-Sleep -Seconds 3

# FFmpeg インストール手順（Windows）

## 概要
Coqui TTS（XTTS v2）で自分の声を使った音声生成を行うには、TorchCodecが必要です。TorchCodecはFFmpegの共有ライブラリ（DLL）を使用するため、Windows環境では「full-shared」版のFFmpegをインストールする必要があります。

## 前提条件
- Windows 10/11
- Python 3.10
- 7-Zip がインストール済み（winget でインストール可能）

## インストール手順

### 1. FFmpeg full-shared版のダウンロード

公式ビルドサイトから最新のfull-shared版をダウンロードします：

**ダウンロード先**: https://www.gyan.dev/ffmpeg/builds/

- 「ffmpeg-*-git-*-full_build.7z」というファイル名のものを選択
- 例: `ffmpeg-2025-12-31-git-38e89fe502-full_build.7z`

### 2. 7-Zipのインストール（未インストールの場合）

PowerShellで以下を実行：

```powershell
winget install -e --id 7zip.7zip
```

### 3. FFmpegの展開

ダウンロードしたファイルをC:\ffmpegに展開します：

```powershell
# ダウンロードファイルのパス（適宜変更）
$zip = 'C:\Users\ユーザー名\Downloads\ffmpeg-2025-12-31-git-38e89fe502-full_build.7z'

# C:\ffmpegに展開
& 'C:\Program Files\7-Zip\7z.exe' x $zip -oC:\ffmpeg -y
```

### 4. 展開後のフォルダ構造確認

展開後、以下のような構造になります：

```
C:\ffmpeg\
└── ffmpeg-YYYY-MM-DD-git-xxxxxx-full_build\
    ├── bin\
    │   ├── ffmpeg.exe
    │   ├── ffplay.exe
    │   ├── ffprobe.exe
    │   ├── avcodec-*.dll
    │   ├── avformat-*.dll
    │   ├── avutil-*.dll
    │   └── その他の DLL ファイル
    ├── doc\
    └── presets\
```

### 5. ffmpeg.exeの場所を特定

```powershell
# ffmpeg.exeを検索
Get-ChildItem 'C:\ffmpeg' -Recurse -Filter ffmpeg.exe | Select-Object FullName
```

出力例：
```
FullName
--------
C:\ffmpeg\ffmpeg-2025-12-31-git-38e89fe502-full_build\bin\ffmpeg.exe
```

### 6. PATH環境変数への追加

#### 6-1. 現在のPowerShellセッションで即時有効化

```powershell
# 見つかったbinフォルダのパスを設定（上記の出力から取得）
$ffbin = 'C:\ffmpeg\ffmpeg-2025-12-31-git-38e89fe502-full_build\bin'

# 現在のセッションのPATHに追加
$env:PATH += ";$ffbin"

# 動作確認
ffmpeg -version
```

#### 6-2. ユーザー環境変数に永続的に追加

```powershell
# ユーザー環境変数のPATHに追加（既存のPATHを上書きしない）
[Environment]::SetEnvironmentVariable(
    'PATH',
    [Environment]::GetEnvironmentVariable('PATH','User') + ";$ffbin",
    'User'
)
```

**注意**: 環境変数の変更は新しいPowerShellウィンドウで有効になります。現在のウィンドウでは上記の `$env:PATH +=` で即座に使えます。

### 7. インストール確認

新しいPowerShellウィンドウを開いて確認：

```powershell
ffmpeg -version
```

以下のような出力が表示されれば成功です：

```
ffmpeg version 2025-12-31-git-38e89fe502-full_build-www.gyan.dev
Copyright (c) 2000-2025 the FFmpeg developers
built with gcc 15.2.0 (Rev8, Built by MSYS2 project)
configuration: --enable-gpl --enable-version3 --enable-static ...
libavutil      60. 21.102 / 60. 21.102
libavcodec     62. 23.102 / 62. 23.102
libavformat    62.  8.102 / 62.  8.102
...
```

## TorchCodecのインストール

FFmpegの準備ができたら、TorchCodecをインストールします：

```powershell
# プロジェクトディレクトリに移動
cd C:\Users\h-ham\spec-kit\11_Slide-MyVoice-Maker

# 仮想環境有効化（.venvがある場合）
.\.venv\Scripts\Activate.ps1

# TorchCodecのインストール
pip install --no-cache-dir torchcodec
```

## 動作確認

音声生成スクリプトを実行して、Coqui TTSが正常に動作するか確認：

```powershell
py -3.10 src\voice\voice_generator.py
```

成功時の出力例：
```
音声モデルを初期化中...
初期化完了！
音声生成中: こんにちは、お母さん。今日も元気ですか？
speaker_wavを読み込みました: ...\sample.wav
生成完了: ...\output\test_voice.wav
```

## トラブルシューティング

### エラー: "Could not load libtorchcodec"

**原因**: FFmpegのDLLがPATHから見えていない

**対処法**:
1. `ffmpeg -version` が動作するか確認
2. 新しいPowerShellウィンドウで再試行（環境変数の反映）
3. システム再起動後に再試行

### エラー: "FFmpeg version X: Could not load this library"

**原因**: FFmpegのバージョンが対応していない、またはshared DLLが不足

**対処法**:
1. 「full_build」版（**full-shared版ではない場合がある**）を使用しているか確認
2. 最新の安定版FFmpegをダウンロード（バージョン7または8推奨）
3. DLLファイルがbinフォルダに存在するか確認：
   ```powershell
   Get-ChildItem 'C:\ffmpeg\...\bin' -Filter *.dll
   ```

### TorchCodecとPyTorchのバージョン互換性

以下の組み合わせが推奨されます：

| TorchCodec | PyTorch | Python |
|------------|---------|--------|
| 0.9.x      | 2.9.x   | 3.10-3.14 |
| 0.8.x      | 2.9.x   | 3.10-3.13 |

現在のバージョン確認：
```powershell
pip show torch torchcodec
```

## 参考リンク

- [TorchCodec公式ドキュメント](https://github.com/pytorch/torchcodec)
- [FFmpeg公式サイト](https://www.ffmpeg.org/)
- [Gyan.dev FFmpeg Builds](https://www.gyan.dev/ffmpeg/builds/)
- [TorchCodec互換性表](https://github.com/pytorch/torchcodec?tab=readme-ov-file#installing-torchcodec)

## 更新履歴

- 2026-01-03: 初版作成（FFmpeg 2025-12-31ビルド、TorchCodec 0.9.1対応）

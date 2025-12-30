# Slide Voice Maker

PDFスライドと原稿CSVから、AI音声ナレーション付き動画（WebM）を自動生成するツールです。

## 🌐 GitHub Pages

**Web版**: https://j1921604.github.io/Slide-Voice-Maker/

ブラウザ上でPDFと原稿CSVをアップロードし、動画を生成できます。

## 🚀 クイックスタート

### ワンクリック実行（Windows）

```batch
run.bat
```

または PowerShell:

```powershell
.\run.ps1
```

### 手動実行

```bash
# Python 3.10で実行
py -3.10 src\main.py

# オプション指定
py -3.10 src\main.py --input input --output output --script input\原稿.csv
```

## 📋 必要条件

- **Python 3.10.11** (推奨)
- **FFmpeg** (imageio-ffmpegで自動インストール)
- 依存パッケージ: `pip install -r requirements.txt`

## 📁 ファイル構成

```
Slide-Voice-Maker/
├── index.html          # GitHub Pages用Webアプリ
├── requirements.txt    # Python依存パッケージ
├── run.bat             # ワンクリック実行スクリプト(Windows)
├── run.ps1             # PowerShell実行スクリプト
├── input/
│   ├── *.pdf           # 入力PDFファイル
│   └── 原稿.csv        # ナレーション原稿
├── output/
│   ├── *.webm          # 生成された動画
│   └── temp/           # 一時ファイル
├── src/
│   ├── main.py         # メインスクリプト
│   └── processor.py    # PDF処理・動画生成
└── .github/
    └── workflows/
        ├── generate-video.yml  # 動画生成ワークフロー
        └── deploy-pages.yml    # GitHub Pages自動デプロイ
```

## 📝 原稿CSV形式

```csv
index,script
0,"最初のスライドの原稿テキストをここに記載します。"
1,"2番目のスライドの原稿です。複数行も可能です。"
2,"3番目のスライドの原稿。"
```

- **index**: スライド番号（0から開始）
- **script**: 読み上げ原稿テキスト
- **文字コード**: UTF-8（BOM付き推奨）、Shift_JIS、EUC-JP対応

## ⚙️ 環境変数設定

動画生成のパラメータを環境変数で調整できます：

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `USE_VP8` | `1` | VP8使用（高速）。`0`でVP9（高品質）。 |
| `VP9_CPU_USED` | `8` | エンコード速度（0-8、大きいほど高速） |
| `VP9_CRF` | `40` | 品質（大きいほど低品質・高速） |
| `OUTPUT_FPS` | `15` | 出力FPS |
| `OUTPUT_MAX_WIDTH` | `1280` | 出力最大幅（px） |
| `SLIDE_RENDER_SCALE` | `1.5` | PDF→画像の解像度倍率 |
| `SILENCE_SLIDE_DURATION` | `5` | 原稿なしスライドの表示秒数 |

## 🔧 GitHub Actions

### 自動デプロイ

`main`ブランチへのpush時に自動的に：
1. GitHub Pagesにindex.htmlをデプロイ
2. input/フォルダ内のPDF変更時に動画を自動生成

### 手動実行

GitHubリポジトリの「Actions」タブから「Generate Video from PDF」ワークフローを手動実行できます。

## 🎬 使い方

### ローカル実行

1. `input/`フォルダにPDFファイルを配置
2. `input/原稿.csv`にナレーション原稿を作成
3. `run.bat`をダブルクリック（または`py -3.10 src\main.py`を実行）
4. `output/`フォルダに動画ファイルが生成されます

### Web版（GitHub Pages）

1. https://j1921604.github.io/Slide-Voice-Maker/ にアクセス
2. PDFファイルをアップロード
3. 原稿CSVを読み込み（または直接入力）
4. 「音声生成」→「WebM出力」で動画をダウンロード

## 📊 パフォーマンス改善

動画生成が遅い場合：

1. **VP8コーデック使用**（デフォルト有効）
   ```
   set USE_VP8=1
   ```

2. **解像度を下げる**
   ```
   set OUTPUT_MAX_WIDTH=960
   set SLIDE_RENDER_SCALE=1.0
   ```

3. **FPSを下げる**（静止画ベースなので問題なし）
   ```
   set OUTPUT_FPS=10
   ```

## 🐛 トラブルシューティング

### 文字化けする場合

原稿CSVをUTF-8（BOM付き）で保存してください。メモ帳の場合：
- 「名前を付けて保存」→ 文字コード: `UTF-8 (BOM付き)`

### FFmpegエラー

imageio-ffmpegが自動でFFmpegをダウンロードしますが、問題がある場合は手動インストール：
```bash
pip install --upgrade imageio-ffmpeg
```

### 音声が生成されない

Edge TTSはインターネット接続が必要です。ネットワークを確認してください。

## 📄 ライセンス

MIT License

## 🙏 クレジット

- [Edge TTS](https://github.com/rany2/edge-tts) - Microsoft Edge音声合成
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF処理
- [MoviePy](https://zulko.github.io/moviepy/) - 動画編集（フォールバック用）

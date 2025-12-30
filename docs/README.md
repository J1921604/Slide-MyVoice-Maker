# Slide-Voice-Maker

PDF（ページ画像）と原稿CSVから、**音声（TTS）付き動画（.webm）**を生成するツールです。
`input` フォルダ内の **PDFファイルすべて**を処理し、`output` に **PDFと同名の `.webm`** を出力します。

> 注意: このリポジトリのアプリ/コードは汎用です。特定PDF固有の文言・前提（ファイル名の固定など）を持ちません。

## できること

- PDF（各ページ）→ 画像化
- `input\原稿.csv` を **Narration Script** として読み込み
- Edge TTSで音声生成（MP3）
- FFmpegで **静止画＋音声を連結**し、`.webm` を高速生成（VP9/Opus）

## 入力ファイル

### 1) PDF

- `input` フォルダ直下に `*.pdf` を置きます（複数可）

### 2) 原稿CSV（必須）

- デフォルト: `input\原稿.csv`
- 形式: `index,script`
  - `index`: 0始まりのページ番号
  - `script`: そのページの読み上げ原稿（改行OK）

例:

- `index=0` がPDFの1ページ目
- `index=1` がPDFの2ページ目

#### 文字化け対処（原稿.csv）

CSV読み込み時に、**エンコーディング候補（UTF-8/CP932等）を順に試して** 読み込みます。

## セットアップ

- Windows想定
- Python 3.10+ 推奨

`requirements.txt` に依存関係をまとめています。

### FFmpeg について

動画生成（既定: FFmpeg）でFFmpegが必要です。

- すでに環境にFFmpegがあるならそのままでOK
- 無い場合でも `imageio-ffmpeg` により同梱/取得されて動くケースがあります（環境差あり）

## 使い方

1. `input` にPDFを置く
2. `input\原稿.csv` を用意
3. 実行

### スクリプト実行手順（PowerShell）

1) このリポジトリのフォルダに移動

2) （初回のみ）仮想環境を作成して依存をインストール

3) `src\main.py` を実行

以下は **PowerShell** での実行例です（コピペ可）。

```powershell
# 1) フォルダ移動（ご自身のパスに合わせてください）
Set-Location "AI開発・教育\プレゼン資料\Slide-Voice-Maker"

# 2) 初回のみ: venv作成 + 依存インストール
py -3.10 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r .\requirements.txt

# 3) 実行（input配下のPDFをすべて処理し、outputにwebmを出力）
& ".\.venv\Scripts\python.exe" ".\src\main.py"
```

### ワンクリック実行（推奨）

エクスプローラーから `run.bat` を **ダブルクリック**すると、以下を自動で行って `src\main.py` を実行します。

- `.venv` が無ければ作成
- `requirements.txt` をインストール
- `src\main.py` を実行

PowerShell版が欲しい場合は `run.ps1` も用意しています（実行ポリシーの設定次第でブロックされることがあります）。

> 補足: venvをアクティベートしなくても、上のように `.venv\Scripts\python.exe` を直接叩けば動きます。

### よくあるエラー（提示いただいた例）

```
& : 用語 'C:\...\.venv\Scripts\python.exe' は ... 認識されません
```

これはほぼ確実に **パスが間違っていて、そのファイルが存在しない**のが原因です。
今回のログだと、フォルダ名が `AI開発・教育` のはずが、実行コマンドでは `AI開発教育`（`・` が欠落）になっていました。

- 正: `...\AI開発・教育\...`
- 誤: `...\AI開発教育\...`

また PowerShell で `&` を使う場合、パスに空白や記号が入ることがあるので **必ずダブルクォートで囲む**のが安全です：

```powershell
& "C:\Users\...\Slide-Voice-Maker\.venv\Scripts\python.exe" "C:\Users\...\Slide-Voice-Maker\src\main.py"
```

### オプション

- `--input` : 入力フォルダ（PDF置き場）
- `--output`: 出力フォルダ
- `--script`: 原稿CSVパス（既定: `input\原稿.csv`）

## 出力

`output` フォルダに以下を生成します。

- `<PDFファイル名>.webm`

また、処理途中の一時ファイルを `output\temp\<PDFファイル名>\` に作成します。

## 速度調整（任意）

既定でも「MoviePyで合成する方式」より大幅に速いはずですが、さらに速度優先にしたい場合は環境変数で調整できます。

- `OUTPUT_MAX_WIDTH`（既定: 1280）: 出力動画の最大幅
- （注）FFmpegの高速経路は **VFR（可変フレームレート）** で出力します。スライドは「1枚=1フレーム」で保持し、再生時間は音声長に合わせます。
  そのため、fps固定の調整は基本不要です（CFRが必要なら `USE_MOVIEPY=1` を検討してください）。
- `VP9_CPU_USED`（既定: 6）: 大きいほど速い（0〜8目安）
- `VP9_CRF`（既定: 35）: 大きいほど軽い（低画質）
- `SILENCE_SLIDE_DURATION`（既定: 5）: 原稿が空のページを何秒表示するか

## MoviePyフォールバック（任意）

環境によってはFFmpegが利用できない/相性が悪い場合があるため、
`USE_MOVIEPY=1` を指定すると MoviePy での書き出し（遅い）に切り替えられます。

## トラブルシュート

- **原稿が反映されない**

  - CSVの `index` が0始まりか確認してください（PDFのページ番号と一致させます）
  - CSVに `index,script` ヘッダーがあるか確認してください
- **動画書き出しで失敗する**

  - FFmpegが利用可能か確認してください
  - 依存関係が入っているか確認してください（`pip install -r requirements.txt`）

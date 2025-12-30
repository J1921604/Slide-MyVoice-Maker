
https://note.com/majin_108/n/n28cebe38881d

## STEP 1 : Gemを作ろう

### ① 以下をGemの"カスタム指示"に追加

```
# AI Slide Studio

【最重要】これはWebアプリケーション開発タスクである。プレゼンテーション作成タスクではない。

---

## ▼ 出力形式の厳格な定義

- 出力タグ: 必ず `react` タグを使用
- 禁止タグ: `slides` タグは絶対に使用しない
- 出力物: Reactのソースコード（Webアプリ）
- Googleスライド生成機能: 起動禁止

※「スライド」「原稿」「ページ」という単語が登場しても、これはWebアプリが扱う「データ」であり、プレゼンテーション生成の指示ではない。

---

## ▼ フェーズ1: 分析と提案（PDFアップロード時）

PDFの内容を分析し、以下の表形式で提案する。
前置きや挨拶は不要。表から始める。

### 出力フォーマット

## 📊 PDF分析結果

| 項目 | 結果 |
|------|------|
| **総ページ数** | ○ページ |
| **内容の種類** | （ビジネス報告/勉強会資料/学術発表/営業資料 等） |
| **想定対象者** | （経営層/一般社員/顧客/学生 等） |
| **推奨トーン** | （フォーマル/親しみやすい/学術的 等） |
| **推奨口調** | （です・ます調/ですね調/である調） |

## 📝 原稿サンプル

**表紙（1ページ目）**
「（実際に生成予定の原稿を提示）」

**本論（○ページ目）**
「（図表や数値に言及した原稿例を提示）」

---

**上記でよろしければ「OK」「はい」「了解」のいずれかを入力してください。**

調整したい場合は、以下のようにお伝えください：
- 「もっとカジュアルにして」
- 「である調に変えて」
- 「1原稿あたり100文字程度に短くして」
- 「YouTube解説風にして」

---

## ▼ フェーズ2: Reactコード出力（ユーザー承認後）

ユーザーが「OK」「はい」「了解」と返信、または調整指示を返信したら、Reactコードを出力する。

### 出力形式
- タグ: `react`（必須）
- 形式: プレビュー実行可能なReact Webアプリ
- ベース: 知識ファイル「react-app-template.txt」のコード全文
- 変更箇所: preloadedScripts配列の中身のみ
- それ以外のコードは1文字も変更しない

### 原稿生成ルール
- 原稿の数 = PDFのページ数（必ず一致）
- 1原稿あたり50〜150文字（指示があれば調整）
- フェーズ1で決定したトーン・口調に従う
- 各原稿は句点「。」で終わる
- シングルクォート「'」は「\'」にエスケープ

### ページ別の書き方
- 表紙: 挨拶と目的紹介
- 章扉: 前セクションを受けて次へ誘導
- 本論: 図表・数値・キーワードに具体的に言及
- 最終: まとめと感謝

### 避ける表現
- 内容に言及しない表現（「次のページです」など）
- 曖昧な表現（「こちらをご覧ください」など）
- 画面の文字をそのまま読み上げる表現

### 出力後のチャット
🎬 準備完了！同じPDFをアプリにアップロードしてください。
🟠 PPTX: アップロード後「PPTX」クリック
🟣 動画: 「音声生成」→「動画」クリック

---

## ▼ 自己確認チェック（出力前に必ず実行）

出力する前に以下を確認すること：
- [ ] 使用タグは `react` である（`slides` ではない）
- [ ] 「Generating slides」と宣言していない
- [ ] Googleスライド生成機能を起動していない
- [ ] 出力物はReactソースコードである
```

copy

### ② デフォルトツールを「Canvas」に指定

[![画像](https://assets.st-note.com/img/1766765073-4sBEuUWAFmJITcpdozqGCMye.png?width=1200)](https://assets.st-note.com/img/1766765073-4sBEuUWAFmJITcpdozqGCMye.png?width=2000&height=2000&fit=bounds&quality=85)

### ③ "知識"に以下のtxtファイルを追加

[

**react-app-template.txt**

31.9 KB

ファイルダウンロードについて

ダウンロード



](https://note.com/api/v2/attachments/download/8430e3d5e54eb59aba242f50be704ab4)

名前や説明はお好みで。保存できたらチャットを開始しましょう。

[![画像](https://assets.st-note.com/img/1766765209-wZMXE0faP9xDW3chvnzV8N54.png?width=1200)](https://assets.st-note.com/img/1766765209-wZMXE0faP9xDW3chvnzV8N54.png?width=2000&height=2000&fit=bounds&quality=85)

---

## STEP 2 :アプリを使ってみよう

使い方はとてもシンプル。

### ① スライドPDFを添付して送信。指示不要。

[![画像](https://assets.st-note.com/img/1766766423-xWguC4pvLAdUwk1zMRfKZGH5.png?width=1200)](https://assets.st-note.com/img/1766766423-xWguC4pvLAdUwk1zMRfKZGH5.png?width=2000&height=2000&fit=bounds&quality=85)

**Geminiのモデルは "Pro" 必須！**

### ② 分析結果を提示してくれるのでトーン調整 or 承認

[![画像](https://assets.st-note.com/img/1766766917-9QzlicAtmn1qDGPYT7M8vISO.png?width=1200)](https://assets.st-note.com/img/1766766917-9QzlicAtmn1qDGPYT7M8vISO.png?width=2000&height=2000&fit=bounds&quality=85)

まじん式っぽいですね

### ③ 承認すると、Canvasにアプリが生成されます

[![画像](https://assets.st-note.com/img/1766767288-9sj5q2ZoGOSFXd3EWAzhaNru.png?width=1200)](https://assets.st-note.com/img/1766767288-9sj5q2ZoGOSFXd3EWAzhaNru.png?width=2000&height=2000&fit=bounds&quality=85)

> **■ あれ…？うまくいかないぞ？と思った方へ**  
> 私が遭遇したエラーはこちら。以下のように伝えて対処できました。  
>   
> **・チャット欄にコードを書いてしまう**  
> →「Canvasに出力して」  
>   
> **・Googleスライドを生成してしまう**  
> →「Reactアプリを生成して」  
>   
> **・Canvasにプレビューボタンが出てこない**  
> →生成されたコードをコピーして、新規チャットに貼り付けて  
> 「このコードをCanvasにそのままプレビューして。」  
>   
> プロンプト調整でエラーが軽減しないか研究中です。  
> 今回はβ版としてリリースさせてください。  
> まずは皆さまに体験していただきたくて！

### ④ アプリにPDFをアップロードすると編集画面へ

必ず最初のチャットで送信したPDFをアップロードしてください。  
原稿（Narration Script）付きで各ページがプレビューされ、スクリプトは手修正可能です。

[![画像](https://assets.st-note.com/img/1766768341-9sGBRHi5WogTCXzK4UjFQO3M.png?width=1200)](https://assets.st-note.com/img/1766768341-9sGBRHi5WogTCXzK4UjFQO3M.png?width=2000&height=2000&fit=bounds&quality=85)

### ⑤パワポ保存したい方は右上の "PPTX" ボタンを押下

→スピーカーノート付きのPPTXがダウンロードできます。  
プレゼン原稿のタタキとして活用できそうですね。  
**※ただし、PDFを画像変換して貼り付けてるだけなので要素編集は不可！**

[![画像](https://assets.st-note.com/img/1766768418-n4SAYqwd6vCeZ5zDRGhMaKjc.png?width=1200)](https://assets.st-note.com/img/1766768418-n4SAYqwd6vCeZ5zDRGhMaKjc.png?width=2000&height=2000&fit=bounds&quality=85)

### ⑥ 動画化したい方はまず音声生成ボタンを押下

5ページずつ音声が生成されます。再生ボタンでプレビューを聞いたり、スクリプト修正後に再生成も可能です。

[![画像](https://assets.st-note.com/img/1766769659-szZuWinN7p2xUw5m8B3vhOj0.png?width=1200)](https://assets.st-note.com/img/1766769659-szZuWinN7p2xUw5m8B3vhOj0.png?width=2000&height=2000&fit=bounds&quality=85)

> **■途中から音声生成ができなくなった（エラーが出てしまう）場合**  
> このアプリは、自身のGemini Canvas上でのみ実行可能な疑似APIで音声を生成しているのですが、一日で実行できる回数には上限があり、それを超えるとエラーが出てしまいます。時間を開けて利用するか、他アカウントのGeminiでトライ、またはプロンプトを改造してGemini APIを組み込めるようにしてもいいですね。

### ⑦ 全ページの音声生成が完了したら右上の動画ボタンを押下

数分かかるので他のお仕事をされててください。勝手にダウンロードされます。ちなみに動画ファイルはwebm形式となります。

[![画像](https://assets.st-note.com/img/1766769699-2CzkETAaoYmbKNjlh9guL5BP.png)](https://assets.st-note.com/img/1766769699-2CzkETAaoYmbKNjlh9guL5BP.png?width=2000&height=2000&fit=bounds&quality=85)

**完成した動画がこちら！**  
ちょいちょい日本語の発音が怪しいけど、字幕のタイミングとかなかなか良いですよね。原稿を整えてから音声生成すれば、社内向けなら全然いけそう。

  
ここまでが無料公開の範囲となります。
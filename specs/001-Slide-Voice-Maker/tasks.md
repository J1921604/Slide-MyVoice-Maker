# タスク一覧: Slide Voice Maker

**入力**: `/specs/001-Slide-Voice-Maker/` からの設計ドキュメント
**前提条件**: plan.md（必須）、spec.md（必須）、data-model.md、contracts/
**バージョン**: 1.1.0
**開始日**: 2026-01-05

## 形式: `[ID] [P?] [ストーリー?] 説明`

- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[US1]**: ユーザーストーリー1（解像度選択）
- **[US2]**: ユーザーストーリー2（temp上書き更新）
- **[US3]**: ユーザーストーリー3（Web版対応）

---

## 実装スケジュール

```mermaid
gantt
    title 実装スケジュール
    dateFormat YYYY-MM-DD
    axisFormat %m/%d
    excludes weekends

    section Phase 1 セットアップ
    T001-T003 プロジェクト準備           :done, p1, 2026-01-05, 1d

    section Phase 2 基盤実装
    T004-T006 基盤実装                   :done, p2, after p1, 1d

    section Phase 3 解像度選択 US1
    T007-T012 解像度選択機能             :done, p3, after p2, 2d

    section Phase 4 temp上書き US2
    T013-T016 temp上書き機能             :done, p4, after p3, 1d

    section Phase 5 Web版対応 US3
    T017-T020 Web版対応                  :done, p5, after p4, 2d

    section Phase 6 仕上げ
    T021-T025 テスト検証・ドキュメント   :active, p6, after p5, 1d
```

---

## Phase 1: セットアップ

**目的**: プロジェクト構造確認と仕様ドキュメント作成

- [x] T001 specs/001-Slide-Voice-Maker/フォルダを作成
- [x] T002 [P] spec.md（機能仕様書）を作成
- [x] T003 [P] plan.md（実装計画）を作成

**チェックポイント**: ドキュメント準備完了 ✅

---

## Phase 2: 基盤（ブロッキング前提条件）

**目的**: 解像度選択・temp管理の共通インフラ構築

**⚠️ 重要**: このフェーズが完了するまでユーザーストーリー作業は開始不可

- [x] T004 src/main.pyにRESOLUTION_MAP定数を定義（720p/1080p/1440p→幅ピクセル）
- [x] T005 [P] src/main.pyに--resolution引数をargparseに追加
- [x] T006 [P] 環境変数OUTPUT_MAX_WIDTHへの変換処理を実装

**チェックポイント**: 基盤準備完了 - ユーザーストーリー実装を開始可能 ✅

---

## Phase 3: ユーザーストーリー1 - 解像度選択（優先度: P1）🎯 MVP

**目標**: ユーザーが動画生成前に出力解像度（720p/1080p/1440p）を選択可能にする

**独立テスト**: `py -3.10 src/main.py --resolution 1080p`を実行し、出力動画の解像度が1920x1080であることをFFprobeで確認

### ユーザーストーリー1の実装

- [x] T007 [US1] src/main.pyで--resolution引数をパースしRESOLUTION_MAPから幅を取得
- [x] T008 [US1] src/main.pyで取得した幅をos.environ["OUTPUT_MAX_WIDTH"]に設定
- [x] T009 [US1] src/processor.pyの_get_output_max_width()が環境変数を正しく読み取ることを確認
- [x] T010 [US1] 無効な解像度値の場合は720p（デフォルト）にフォールバックするバリデーション追加
- [x] T011 [P] [US1] run.batに解像度パラメータ受け渡し対応
- [x] T012 [P] [US1] run.ps1に解像度パラメータ受け渡し対応

**チェックポイント**: 解像度選択機能が独立して動作 ✅

---

## Phase 4: ユーザーストーリー2 - temp上書き更新（優先度: P1）

**目標**: 毎回の実行時にtempフォルダを自動クリアし、古いファイルを残さない

**独立テスト**: 2回連続で動画生成を実行し、output/temp/内に1回目のファイルが残っていないことを確認

### ユーザーストーリー2の実装

- [x] T013 [US2] src/processor.pyにclear_temp_folder(temp_dir)関数を追加
- [x] T014 [US2] clear_temp_folder()内でshutil.rmtree()とos.makedirs()を使用
- [x] T015 [US2] process_pdf_and_script()の冒頭でclear_temp_folder()を呼び出し
- [x] T016 [P] [US2] PermissionError時のエラーハンドリングとログ出力追加

**チェックポイント**: temp上書き機能が独立して動作 ✅

---

## Phase 5: ユーザーストーリー3 - Web版対応（優先度: P2）

**目標**: GitHub Pages版（index.html）でも解像度選択が可能

**独立テスト**: index.htmlで解像度ドロップダウンから1440pを選択し、動画エクスポートで2560x1440のWebMがダウンロードされることを確認

### ユーザーストーリー3の実装

- [x] T017 [US3] index.htmlにRESOLUTION_OPTIONS配列を定義（label, value, width, height）
- [x] T018 [US3] index.htmlにselectedResolution React stateを追加（デフォルト: '720p'）
- [x] T019 [US3] index.htmlに解像度選択ドロップダウンUIを追加（Tailwind CSS）
- [x] T020 [US3] exportVideo()関数でgetResolutionDimensions()を呼び出しcanvasサイズを動的設定

**チェックポイント**: Web版解像度選択が独立して動作 ✅

---

## Phase 6: 仕上げとクロスカッティング関心事

**目的**: E2Eテスト実行、ドキュメント更新、最終検証

- [x] T021 [P] README.mdに解像度オプションのドキュメントを追加
- [x] T022 [P] specs/001-Slide-Voice-Maker/quickstart.mdを更新
- [x] T023 ローカルE2Eテスト実行（py -3.10 src/main.py --resolution 1080p）
- [x] T024 GitHub Pages動作確認（https://j1921604.github.io/Slide-Voice-Maker/）
- [x] T025 mainブランチへのマージとブランチ削除

**チェックポイント**: 全機能テスト・ドキュメント完了

---

## 依存関係と実行順序

### フェーズ依存関係

```mermaid
flowchart TD
    P1[Phase 1<br>セットアップ] --> P2[Phase 2<br>基盤]
    P2 --> P3[Phase 3<br>US1 解像度選択]
    P2 --> P4[Phase 4<br>US2 temp上書き]
    P2 --> P5[Phase 5<br>US3 Web版対応]
    P3 --> P6[Phase 6<br>仕上げ]
    P4 --> P6
    P5 --> P6
```

### ユーザーストーリー依存関係

- **ユーザーストーリー1（P1）**: 基盤（Phase 2）完了後に開始可能 - 他のストーリーへの依存なし
- **ユーザーストーリー2（P1）**: 基盤（Phase 2）完了後に開始可能 - US1とは独立
- **ユーザーストーリー3（P2）**: 基盤（Phase 2）完了後に開始可能 - US1/US2とは独立してテスト可能

### 並列実行可能タスク

| Phase | 並列実行可能タスク |
|-------|-------------------|
| Phase 1 | T002, T003 |
| Phase 2 | T005, T006 |
| Phase 3 | T011, T012 |
| Phase 4 | T016 |
| Phase 6 | T021, T022 |

---

## 並列例: ユーザーストーリー1

```bash
# run.bat/run.ps1対応を同時に起動:
タスク: "run.batに解像度パラメータ受け渡し対応"
タスク: "run.ps1に解像度パラメータ受け渡し対応"
```

## 並列例: 基盤完了後

```bash
# 基盤完了後、3つのユーザーストーリーを並列開始可能:
チームA: "ユーザーストーリー1 - 解像度選択"
チームB: "ユーザーストーリー2 - temp上書き"
チームC: "ユーザーストーリー3 - Web版対応"
```

---

## 実装戦略

### MVP優先（ユーザーストーリー1のみ）

1. Phase 1: セットアップを完了 ✅
2. Phase 2: 基盤を完了 ✅
3. Phase 3: ユーザーストーリー1を完了 ✅
4. **停止して検証**: 解像度選択機能を独立してテスト ✅
5. 準備ができたらデプロイ/デモ

### インクリメンタルデリバリー

1. セットアップ + 基盤を完了 → 基盤準備完了 ✅
2. ユーザーストーリー1を追加 → 独立してテスト → デプロイ/デモ（MVP!）✅
3. ユーザーストーリー2を追加 → 独立してテスト → デプロイ/デモ ✅
4. ユーザーストーリー3を追加 → 独立してテスト → デプロイ/デモ ✅
5. 各ストーリーは前のストーリーを壊さずに価値を追加

---

## タスク進捗サマリー

```mermaid
pie title タスク進捗状況
    "完了" : 25
```

| 項目 | 数値 |
|------|------|
| 総タスク数 | 25 |
| 完了 | 25 |
| 未着手 | 0 |

---

## 注意事項

- Python 3.10.11を使用（`py -3.10`）
- UTF-8エンコーディング必須
- 土日・年末年始（12/27-1/4）はスケジュール対象外
- 各チェックポイントで動作確認を実施
- [P] タスク = 異なるファイル、依存関係なし
- [US*] ラベルはトレーサビリティのためタスクを特定のユーザーストーリーにマップ

## 完了条件

1. すべてのタスクが完了状態になっていること
2. ローカルE2Eテスト（T023）が成功すること
3. GitHub Pages動作確認（T024）が成功すること
4. mainブランチへのマージ（T025）が完了すること

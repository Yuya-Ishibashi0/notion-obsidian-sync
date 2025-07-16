# Notion-Obsidian同期ツール

NotionのページをObsidianに自動同期する、使いやすいツールです。

## 🎯 このツールでできること

- **自動同期**: NotionのページをMarkdownファイルとしてObsidianに自動変換・同期
- **一方向同期**: NotionからObsidianへの安全な一方向同期（Obsidianでの編集が上書きされません）
- **リッチコンテンツ対応**: 画像、表、コードブロック、リンクなどを適切に変換
- **スケジュール実行**: 定期的な自動同期で常に最新の状態を維持

## 🚀 はじめに

### 必要なもの
- Python 3.8以上
- NotionのAPIトークン
- Obsidianボルト（フォルダ）

### インストール

1. **依存関係をインストール**
   ```bash
   pip install -r requirements.txt
   ```

2. **設定ファイルを作成**
   ```bash
   python main.py config --create
   ```

3. **環境変数を設定**
   `.env`ファイルを作成し、以下を記入：
   ```
   NOTION_API_TOKEN=your_notion_api_token_here
   NOTION_DATABASE_ID=your_database_id_here
   OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
   ```

## 📖 使い方

### 基本的な使い方

1. **接続テスト**
   ```bash
   python main.py test
   ```

2. **同期プレビュー**（実際の同期前に確認）
   ```bash
   python main.py preview
   ```

3. **全ページを同期**
   ```bash
   python main.py sync
   ```

### よく使うコマンド

| コマンド | 説明 |
|---------|------|
| `python main.py sync` | 全ページを同期 |
| `python main.py sync --page-id ABC123` | 特定のページのみ同期 |
| `python main.py sync --since 2024-01-01` | 指定日以降に更新されたページを同期 |
| `python main.py sync --dry-run` | 実際の同期は行わず、プレビューのみ表示 |
| `python main.py test` | 接続テスト |
| `python main.py status` | 同期状態の確認 |
| `python main.py config --validate` | 設定ファイルの検証 |

## ⚙️ 設定

### 基本設定（config.yaml）

```yaml
notion:
  api_token: ${NOTION_API_TOKEN}
  database_id: ${NOTION_DATABASE_ID}

obsidian:
  vault_path: ${OBSIDIAN_VAULT_PATH}
  subfolder: "notion-sync"  # オプション

sync:
  file_naming: "{title}"
  include_properties: true
  overwrite_existing: true
  batch_size: 10
```

### 高度な設定

- **ファイル名のパターン**: `{title}`, `{id}`, `{date}`を組み合わせ可能
- **変換品質レベル**: `strict`（厳密）、`standard`（標準）、`lenient`（寛容）
- **サポートされていないブロックの処理**: スキップ、プレースホルダー、警告のみ

## 🔧 Notion APIの設定

1. [Notion Developers](https://developers.notion.com/)にアクセス
2. 「New integration」をクリック
3. 統合名を入力し、ワークスペースを選択
4. 「Submit」をクリックしてAPIトークンを取得
5. 同期したいデータベースで「Share」→統合を追加

## 📁 ファイル構造

同期後のObsidianボルトの構造例：
```
your-vault/
├── notion-sync/
│   ├── ページタイトル1.md
│   ├── ページタイトル2.md
│   └── ...
└── その他のObsidianファイル
```

各Markdownファイルには以下が含まれます：
- YAMLフロントマター（Notionのプロパティ）
- 変換されたページコンテンツ

## 🔄 自動実行の設定

### macOS/Linux（cron）
```bash
# 毎時0分に同期実行
0 * * * * cd /path/to/notion-obsidian-sync && python main.py sync
```

### Windows（タスクスケジューラー）
1. タスクスケジューラーを開く
2. 「基本タスクの作成」を選択
3. トリガーと実行するプログラムを設定

## ❓ よくある質問

### Q: Obsidianで編集したファイルはどうなりますか？
A: このツールは一方向同期なので、Obsidianでの編集は上書きされません。ただし、Notionで同じページが更新された場合は、Notionの内容で上書きされます。

### Q: どのようなNotionコンテンツがサポートされていますか？
A: テキスト、見出し、リスト、画像、表、コードブロック、リンクなどの基本的な要素をサポートしています。データベースビューなど一部の要素は代替表現に変換されます。

### Q: エラーが発生した場合はどうすればよいですか？
A: `python main.py test`で接続を確認し、ログファイル（sync.log）でエラーの詳細を確認してください。

### Q: 大量のページがある場合の処理時間は？
A: バッチ処理とキャッシュ機能により効率的に処理されます。初回は時間がかかりますが、2回目以降は変更されたページのみが処理されます。

## 🛠️ トラブルシューティング

### 接続エラー
- APIトークンが正しく設定されているか確認
- データベースに統合が追加されているか確認
- インターネット接続を確認

### ファイル書き込みエラー
- Obsidianボルトパスが正しいか確認
- ディスクの空き容量を確認
- ファイル権限を確認

### 変換エラー
- Notionページの内容を確認
- 設定ファイルの変換品質レベルを調整
- ログファイルで詳細なエラー情報を確認

## 📞 サポート

問題が発生した場合は、以下の情報と共にお問い合わせください：
- エラーメッセージ
- 設定ファイルの内容（APIトークンは除く）
- ログファイル（sync.log）の関連部分

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

**注意**: このツールはNotionの公式ツールではありません。使用は自己責任でお願いします。
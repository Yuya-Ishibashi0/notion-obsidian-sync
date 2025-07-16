#!/usr/bin/env python3
"""
Notion-Obsidian同期ツール
メインエントリーポイント
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from utils.config_loader import ConfigLoader, ConfigLoadError
from services.sync_orchestrator import SyncOrchestrator
from models.config import AppConfig


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """ログ設定をセットアップ"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # ログフォーマット
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # ルートロガー設定
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー（指定されている場合）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


def create_argument_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを作成"""
    parser = argparse.ArgumentParser(
        description="Notion-Obsidian同期ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s sync                    # 全ページを同期
  %(prog)s sync --page-id abc123   # 特定ページを同期
  %(prog)s test                    # 接続テスト
  %(prog)s preview                 # 同期プレビュー
  %(prog)s config --validate       # 設定検証
  %(prog)s config --create         # デフォルト設定作成
        """
    )
    
    # 共通オプション
    parser.add_argument(
        "-c", "--config",
        help="設定ファイルのパス（デフォルト: config.yaml）"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="詳細ログを出力"
    )
    parser.add_argument(
        "--log-file",
        help="ログファイルのパス"
    )
    
    # サブコマンド
    subparsers = parser.add_subparsers(dest="command", help="利用可能なコマンド")
    
    # syncコマンド
    sync_parser = subparsers.add_parser("sync", help="同期を実行")
    sync_parser.add_argument(
        "--page-id",
        help="同期する特定ページのID"
    )
    sync_parser.add_argument(
        "--filter",
        help="フィルター条件（JSON形式）"
    )
    sync_parser.add_argument(
        "--since",
        help="指定日時以降に更新されたページのみ同期（YYYY-MM-DD形式）"
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際の同期は行わず、プレビューのみ表示"
    )
    sync_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="進捗表示を無効化"
    )
    
    # testコマンド
    test_parser = subparsers.add_parser("test", help="接続テスト")
    test_parser.add_argument(
        "--detailed",
        action="store_true",
        help="詳細なテスト結果を表示"
    )
    
    # previewコマンド
    preview_parser = subparsers.add_parser("preview", help="同期プレビュー")
    preview_parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="プレビューするページ数（デフォルト: 10）"
    )
    
    # configコマンド
    config_parser = subparsers.add_parser("config", help="設定管理")
    config_group = config_parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument(
        "--validate",
        action="store_true",
        help="設定ファイルを検証"
    )
    config_group.add_argument(
        "--create",
        action="store_true",
        help="デフォルト設定ファイルを作成"
    )
    config_group.add_argument(
        "--show",
        action="store_true",
        help="現在の設定を表示"
    )
    config_parser.add_argument(
        "--output",
        help="出力ファイルのパス（--createで使用）"
    )
    
    # statusコマンド
    status_parser = subparsers.add_parser("status", help="同期状態を確認")
    status_parser.add_argument(
        "--detailed",
        action="store_true",
        help="詳細な統計情報を表示"
    )
    
    # cleanupコマンド
    cleanup_parser = subparsers.add_parser("cleanup", help="失敗ファイルのクリーンアップ")
    cleanup_parser.add_argument(
        "--force",
        action="store_true",
        help="確認なしで実行"
    )
    
    return parser


def load_config(config_path: Optional[str]) -> AppConfig:
    """設定を読み込み"""
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_config(config_path)
        return config
    except ConfigLoadError as e:
        print(f"❌ 設定読み込みエラー: {e}", file=sys.stderr)
        sys.exit(1)


def progress_callback(current: int, total: int, page_title: str):
    """進捗表示コールバック"""
    percentage = (current / total) * 100 if total > 0 else 0
    print(f"\r進捗: {current}/{total} ({percentage:.1f}%) - {page_title[:50]}", end="", flush=True)


def command_sync(args, config: AppConfig) -> int:
    """同期コマンドの実行"""
    try:
        orchestrator = SyncOrchestrator(config)
        
        # ドライランの場合はプレビューのみ
        if args.dry_run:
            print("🔍 同期プレビューを実行中...")
            preview = orchestrator.get_sync_preview(max_pages=20)
            
            print(f"📊 同期対象: {preview['total_pages_in_database']}ページ")
            if preview['potential_conflicts']:
                print(f"⚠️  競合の可能性: {len(preview['potential_conflicts'])}件")
            
            print("\n📝 プレビューページ:")
            for page in preview['preview_pages'][:10]:
                print(f"  - {page['title']} -> {page['estimated_filename']}")
            
            return 0
        
        # 実際の同期実行
        print("🚀 同期を開始します...")
        
        # 進捗コールバックの設定
        callback = None if args.no_progress else progress_callback
        
        if args.page_id:
            # 単一ページ同期
            print(f"📄 ページID {args.page_id} を同期中...")
            success = orchestrator.sync_single_page(args.page_id)
            if success:
                print("\n✅ 単一ページ同期完了")
                return 0
            else:
                print("\n❌ 単一ページ同期失敗")
                return 1
                
        elif args.since:
            # 日時フィルター同期
            try:
                since_date = datetime.strptime(args.since, "%Y-%m-%d")
                print(f"📅 {args.since}以降に更新されたページを同期中...")
                result = orchestrator.sync_pages_modified_after(since_date, callback)
            except ValueError:
                print("❌ 日付形式が正しくありません（YYYY-MM-DD形式で入力してください）", file=sys.stderr)
                return 1
                
        elif args.filter:
            # フィルター同期
            try:
                import json
                filter_dict = json.loads(args.filter)
                print("🔍 フィルター条件で同期中...")
                result = orchestrator.sync_pages_by_filter(filter_dict, callback)
            except json.JSONDecodeError:
                print("❌ フィルター条件のJSON形式が正しくありません", file=sys.stderr)
                return 1
                
        else:
            # 全ページ同期
            print("📚 全ページを同期中...")
            result = orchestrator.sync_all_pages(callback)
        
        # 結果表示
        if not args.no_progress:
            print()  # 進捗表示の改行
            
        summary = result.get_summary()
        
        if summary['success_rate'] == 100:
            print(f"✅ 同期完了: {summary['successful_pages']}/{summary['total_pages']}ページ")
        else:
            print(f"⚠️  同期完了（一部エラー）: {summary['successful_pages']}/{summary['total_pages']}ページ")
            print(f"   エラー: {summary['error_count']}件, 警告: {summary['warning_count']}件")
        
        print(f"⏱️  処理時間: {summary['duration_seconds']:.1f}秒")
        
        # レポート生成
        report = orchestrator.create_sync_report(result)
        report_file = f"sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 詳細レポート: {report_file}")
        
        return 0 if summary['error_count'] == 0 else 1
        
    except Exception as e:
        print(f"❌ 同期エラー: {e}", file=sys.stderr)
        return 1


def command_test(args, config: AppConfig) -> int:
    """テストコマンドの実行"""
    try:
        orchestrator = SyncOrchestrator(config)
        
        print("🔍 接続テストを実行中...")
        test_result = orchestrator.test_sync_connection()
        
        if test_result["overall_status"]:
            print("✅ 接続テスト成功")
        else:
            print("❌ 接続テスト失敗")
        
        if args.detailed:
            print("\n📊 詳細結果:")
            checks = {
                "notion_connection": "Notion API接続",
                "database_access": "データベースアクセス",
                "obsidian_vault": "Obsidianボルト",
                "file_write_permission": "ファイル書き込み権限"
            }
            
            for check, description in checks.items():
                status = "✅" if test_result[check] else "❌"
                print(f"  {status} {description}")
            
            if test_result["errors"]:
                print("\n❌ エラー:")
                for error in test_result["errors"]:
                    print(f"  - {error}")
            
            if test_result["warnings"]:
                print("\n⚠️  警告:")
                for warning in test_result["warnings"]:
                    print(f"  - {warning}")
        
        return 0 if test_result["overall_status"] else 1
        
    except Exception as e:
        print(f"❌ テストエラー: {e}", file=sys.stderr)
        return 1


def command_preview(args, config: AppConfig) -> int:
    """プレビューコマンドの実行"""
    try:
        orchestrator = SyncOrchestrator(config)
        
        print(f"🔍 同期プレビューを実行中（最大{args.max_pages}ページ）...")
        preview = orchestrator.get_sync_preview(args.max_pages)
        
        print(f"\n📊 データベース統計:")
        print(f"  総ページ数: {preview['total_pages_in_database']}")
        print(f"  プレビュー対象: {len(preview['preview_pages'])}ページ")
        
        if preview['potential_conflicts']:
            print(f"\n⚠️  ファイル名競合の可能性: {len(preview['potential_conflicts'])}件")
            for conflict in preview['potential_conflicts'][:5]:
                print(f"  - {conflict}")
        
        print(f"\n📝 プレビューページ:")
        for page in preview['preview_pages']:
            print(f"  📄 {page['title']}")
            print(f"     ファイル名: {page['estimated_filename']}")
            if page['last_edited']:
                print(f"     最終更新: {page['last_edited']}")
            print()
        
        if preview['warnings']:
            print("⚠️  警告:")
            for warning in preview['warnings']:
                print(f"  - {warning}")
        
        return 0
        
    except Exception as e:
        print(f"❌ プレビューエラー: {e}", file=sys.stderr)
        return 1


def command_config(args, config_path: Optional[str]) -> int:
    """設定コマンドの実行"""
    try:
        config_loader = ConfigLoader()
        
        if args.validate:
            # 設定検証
            if not config_path:
                config_path = config_loader._find_config_file()
                if not config_path:
                    print("❌ 設定ファイルが見つかりません", file=sys.stderr)
                    return 1
            
            print(f"🔍 設定ファイルを検証中: {config_path}")
            validation = config_loader.validate_config_file(config_path)
            
            if validation["is_valid"]:
                print("✅ 設定ファイルは有効です")
            else:
                print("❌ 設定ファイルに問題があります")
                
                if validation["errors"]:
                    print("\nエラー:")
                    for error in validation["errors"]:
                        print(f"  - {error}")
                
                if validation["warnings"]:
                    print("\n警告:")
                    for warning in validation["warnings"]:
                        print(f"  - {warning}")
                
                if validation["missing_env_vars"]:
                    print(f"\n未設定の環境変数: {', '.join(validation['missing_env_vars'])}")
            
            return 0 if validation["is_valid"] else 1
            
        elif args.create:
            # デフォルト設定作成
            output_path = args.output or "config.yaml"
            print(f"📝 デフォルト設定ファイルを作成中: {output_path}")
            
            config_loader.create_default_config(output_path)
            print("✅ デフォルト設定ファイルを作成しました")
            print("\n次の手順:")
            print("1. 設定ファイルを編集してNotion APIトークンとデータベースIDを設定")
            print("2. Obsidianボルトパスを設定")
            print("3. 環境変数NOTION_API_TOKENを設定")
            
            return 0
            
        elif args.show:
            # 現在の設定表示
            config = load_config(config_path)
            
            print("📋 現在の設定:")
            print(f"  Notion API Token: {'設定済み' if config.notion.api_token else '未設定'}")
            print(f"  Database ID: {config.notion.database_id}")
            print(f"  Obsidian Vault: {config.obsidian.vault_path}")
            if config.obsidian.subfolder:
                print(f"  Subfolder: {config.obsidian.subfolder}")
            print(f"  Batch Size: {config.sync.batch_size}")
            print(f"  Log Level: {config.logging.level}")
            
            # 包括的検証結果も表示
            validation_summary = config.get_validation_summary()
            print(f"\n{validation_summary}")
            
            return 0
        
    except Exception as e:
        print(f"❌ 設定コマンドエラー: {e}", file=sys.stderr)
        return 1


def command_status(args, config: AppConfig) -> int:
    """ステータスコマンドの実行"""
    try:
        orchestrator = SyncOrchestrator(config)
        
        print("📊 同期状態を確認中...")
        stats = orchestrator.get_sync_statistics()
        
        if "error" in stats:
            print(f"❌ 統計取得エラー: {stats['error']}")
            return 1
        
        print("\n📈 統計情報:")
        print(f"  データベース総ページ数: {stats['database_stats']['total_pages']}")
        print(f"  ローカルMarkdownファイル数: {stats['file_system_stats']['total_markdown_files']}")
        print(f"  同期カバレッジ: {stats['sync_coverage']['coverage_percentage']:.1f}%")
        
        if args.detailed:
            print(f"\n💾 ファイルシステム:")
            print(f"  総サイズ: {stats['file_system_stats']['total_size_mb']:.2f}MB")
            print(f"  平均ファイルサイズ: {stats['file_system_stats']['average_file_size']:.0f}バイト")
            print(f"  有効ファイル: {stats['file_system_stats']['valid_files']}")
            print(f"  無効ファイル: {stats['file_system_stats']['invalid_files']}")
            
            if stats['sync_coverage']['missing_pages'] > 0:
                print(f"\n⚠️  未同期ページ: {stats['sync_coverage']['missing_pages']}ページ")
            
            if stats['sync_coverage']['extra_files'] > 0:
                print(f"⚠️  余分なファイル: {stats['sync_coverage']['extra_files']}ファイル")
        
        return 0
        
    except Exception as e:
        print(f"❌ ステータス確認エラー: {e}", file=sys.stderr)
        return 1


def command_cleanup(args, config: AppConfig) -> int:
    """クリーンアップコマンドの実行"""
    try:
        orchestrator = SyncOrchestrator(config)
        
        if not args.force:
            response = input("失敗したファイルをクリーンアップしますか？ (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("クリーンアップをキャンセルしました")
                return 0
        
        print("🧹 失敗ファイルのクリーンアップを実行中...")
        result = orchestrator.cleanup_failed_files()
        
        print(f"✅ クリーンアップ完了:")
        print(f"  チェック済みファイル: {result['checked_files']}")
        print(f"  削除ファイル: {len(result['deleted_files'])}")
        print(f"  バックアップファイル: {len(result['backup_files'])}")
        
        if result['errors']:
            print(f"\n❌ エラー:")
            for error in result['errors']:
                print(f"  - {error}")
            return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ クリーンアップエラー: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """メイン関数"""
    try:
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # ログレベル設定
        log_level = "DEBUG" if args.verbose else "INFO"
        setup_logging(log_level, args.log_file)
        
        # コマンドが指定されていない場合
        if not args.command:
            parser.print_help()
            return 1
        
        # 設定コマンドは特別扱い（設定ファイルが不要な場合があるため）
        if args.command == "config":
            return command_config(args, args.config)
        
        # その他のコマンドは設定ファイルが必要
        try:
            config = load_config(args.config)
        except SystemExit:
            return 1
        
        # 設定の包括的検証
        validation = config.validate_comprehensive()
        if not validation["is_valid"]:
            print("❌ 設定に問題があります:", file=sys.stderr)
            for error in validation["errors"]:
                print(f"  - {error}", file=sys.stderr)
            return 1
        
        # 警告があれば表示
        if validation["warnings"]:
            print("⚠️  警告:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")
        
        # コマンド実行
        if args.command == "sync":
            return command_sync(args, config)
        elif args.command == "test":
            return command_test(args, config)
        elif args.command == "preview":
            return command_preview(args, config)
        elif args.command == "status":
            return command_status(args, config)
        elif args.command == "cleanup":
            return command_cleanup(args, config)
        else:
            print(f"❌ 未知のコマンド: {args.command}", file=sys.stderr)
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  操作がキャンセルされました", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"❌ 予期しないエラーが発生しました: {e}", file=sys.stderr)
        logging.getLogger(__name__).exception("予期しないエラー")
        return 1


if __name__ == "__main__":
    sys.exit(main())
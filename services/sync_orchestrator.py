"""
同期オーケストレーター
Notion-Obsidian同期プロセス全体を調整するクラス
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.config import AppConfig
from models.notion import NotionPage, NotionPageContent
from models.markdown import MarkdownConversionResult
from services.notion_client import NotionClient
from services.data_processor import DataProcessor
from utils.file_manager import FileManager


class SyncResult:
    """同期結果を表すクラス"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.total_pages = 0
        self.successful_pages = 0
        self.failed_pages = 0
        self.skipped_pages = 0
        self.conversion_results: List[MarkdownConversionResult] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def add_error(self, error: str) -> None:
        """エラーを追加"""
        self.errors.append(error)
        
    def add_warning(self, warning: str) -> None:
        """警告を追加"""
        self.warnings.append(warning)
        
    def complete(self) -> None:
        """同期完了時に呼び出す"""
        self.end_time = datetime.now()
        
    @property
    def duration(self) -> float:
        """同期にかかった時間（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
        
    @property
    def success_rate(self) -> float:
        """成功率（%）"""
        if self.total_pages == 0:
            return 0.0
        return (self.successful_pages / self.total_pages) * 100
        
    def get_summary(self) -> Dict[str, Any]:
        """同期結果のサマリーを取得"""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration,
            "total_pages": self.total_pages,
            "successful_pages": self.successful_pages,
            "failed_pages": self.failed_pages,
            "skipped_pages": self.skipped_pages,
            "success_rate": self.success_rate,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "has_errors": len(self.errors) > 0,
            "has_warnings": len(self.warnings) > 0
        }


class SyncOrchestrator:
    """同期オーケストレーター"""
    
    def __init__(self, config: AppConfig):
        """
        初期化
        
        Args:
            config: アプリケーション設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # コンポーネントを初期化
        self.notion_client = NotionClient(
            config.notion.api_token,
            config.notion.database_id
        )
        self.data_processor = DataProcessor(config.sync.conversion)
        self.file_manager = FileManager(
            config.obsidian.vault_path,
            config.obsidian.subfolder
        )
        
    def sync_single_page(self, page_id: str) -> bool:
        """
        単一ページの同期
        
        Args:
            page_id: 同期するページのID
            
        Returns:
            同期成功時True
        """
        try:
            self.logger.info(f"単一ページ同期開始: {page_id}")
            
            # ページコンテンツを取得
            page_content = self.notion_client.get_page_content(page_id)
            
            # Markdownに変換
            conversion_result = self.data_processor.convert_page_to_markdown(
                page_content,
                self.config.sync.file_naming,
                self.config.sync.include_properties
            )
            
            # ファイルに書き込み
            success = self.file_manager.write_markdown_file(
                conversion_result.markdown_file,
                self.config.sync.overwrite_existing
            )
            
            if success:
                self.logger.info(f"単一ページ同期完了: {page_content.page.title}")
                return True
            else:
                self.logger.error(f"ファイル書き込み失敗: {conversion_result.markdown_file.filename}")
                return False
                
        except Exception as e:
            self.logger.error(f"単一ページ同期エラー (ID: {page_id}): {str(e)}")
            return False
    
    def test_sync_connection(self) -> Dict[str, Any]:
        """
        同期接続テスト
        
        Returns:
            テスト結果の辞書
        """
        test_results = {
            "notion_connection": False,
            "obsidian_vault": False,
            "database_access": False,
            "file_write_permission": False,
            "overall_status": False,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Notion接続テスト
            if self.notion_client.test_connection():
                test_results["notion_connection"] = True
                self.logger.info("Notion接続テスト: 成功")
            else:
                test_results["errors"].append("Notion APIに接続できません")
                
            # データベースアクセステスト
            try:
                db_info = self.notion_client.get_database_info()
                test_results["database_access"] = True
                self.logger.info(f"データベースアクセステスト: 成功 ({db_info.title})")
            except Exception as e:
                test_results["errors"].append(f"データベースにアクセスできません: {str(e)}")
                
            # Obsidianボルト検証
            vault_issues = self.file_manager.validate_vault_structure()
            if not vault_issues:
                test_results["obsidian_vault"] = True
                self.logger.info("Obsidianボルト検証: 成功")
            else:
                test_results["obsidian_vault"] = False
                for issue in vault_issues:
                    test_results["warnings"].append(f"ボルト問題: {issue}")
                    
            # ファイル書き込み権限テスト
            try:
                test_file_path = self.file_manager.sync_path / ".sync_test.tmp"
                test_file_path.write_text("テスト")
                test_file_path.unlink()
                test_results["file_write_permission"] = True
                self.logger.info("ファイル書き込み権限テスト: 成功")
            except Exception as e:
                test_results["errors"].append(f"ファイル書き込み権限がありません: {str(e)}")
                
            # 総合判定
            test_results["overall_status"] = (
                test_results["notion_connection"] and
                test_results["database_access"] and
                test_results["obsidian_vault"] and
                test_results["file_write_permission"]
            )
            
            return test_results
            
        except Exception as e:
            test_results["errors"].append(f"接続テスト中にエラーが発生しました: {str(e)}")
            return test_results
    
    def get_sync_preview(self, max_pages: int = 5) -> Dict[str, Any]:
        """
        同期プレビューを取得（実際の同期は行わない）
        
        Args:
            max_pages: プレビューするページの最大数
            
        Returns:
            プレビュー情報の辞書
        """
        try:
            self.logger.info(f"同期プレビュー開始 (最大{max_pages}ページ)")
            
            # ページ一覧を取得
            pages = self.notion_client.get_database_pages(page_size=max_pages)
            
            preview_info = {
                "total_pages_in_database": len(pages),
                "preview_pages": [],
                "estimated_files": [],
                "potential_conflicts": [],
                "warnings": []
            }
            
            # プレビュー用にページ情報を処理
            for page in pages[:max_pages]:
                page_info = {
                    "id": page.id,
                    "title": page.title,
                    "last_edited": page.last_edited_time.isoformat() if page.last_edited_time else None,
                    "estimated_filename": self.data_processor._generate_filename(page, self.config.sync.file_naming)
                }
                preview_info["preview_pages"].append(page_info)
                preview_info["estimated_files"].append(page_info["estimated_filename"])
            
            # ファイル名競合チェック
            from models.markdown import MarkdownFile
            dummy_files = [MarkdownFile(filename=f) for f in preview_info["estimated_files"]]
            conflicts = self.file_manager.check_file_conflicts(dummy_files)
            
            if conflicts:
                preview_info["potential_conflicts"] = list(conflicts.keys())
                preview_info["warnings"].append(f"{len(conflicts)}件のファイル名競合が予想されます")
            
            self.logger.info(f"同期プレビュー完了: {len(pages)}ページ検出")
            return preview_info
            
        except Exception as e:
            self.logger.error(f"同期プレビューエラー: {str(e)}")
            return {
                "error": str(e),
                "total_pages_in_database": 0,
                "preview_pages": [],
                "estimated_files": [],
                "potential_conflicts": [],
                "warnings": [f"プレビュー取得エラー: {str(e)}"]
            }
    
    def validate_sync_prerequisites(self) -> Dict[str, Any]:
        """
        同期の前提条件を検証
        
        Returns:
            検証結果の辞書
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "checks": {
                "config_valid": False,
                "notion_accessible": False,
                "vault_writable": False,
                "no_critical_conflicts": False
            }
        }
        
        try:
            # 設定検証
            try:
                self.config.validate()
                validation_result["checks"]["config_valid"] = True
            except Exception as e:
                validation_result["errors"].append(f"設定エラー: {str(e)}")
                validation_result["is_valid"] = False
            
            # Notion接続確認
            if self.notion_client.test_connection():
                validation_result["checks"]["notion_accessible"] = True
            else:
                validation_result["errors"].append("Notionに接続できません")
                validation_result["is_valid"] = False
            
            # ボルト書き込み確認
            vault_issues = self.file_manager.validate_vault_structure()
            critical_issues = [issue for issue in vault_issues if "権限" in issue or "存在しません" in issue]
            
            if not critical_issues:
                validation_result["checks"]["vault_writable"] = True
            else:
                for issue in critical_issues:
                    validation_result["errors"].append(f"ボルトエラー: {issue}")
                validation_result["is_valid"] = False
            
            # 非クリティカルな問題は警告として追加
            non_critical_issues = [issue for issue in vault_issues if issue not in critical_issues]
            for issue in non_critical_issues:
                validation_result["warnings"].append(f"ボルト警告: {issue}")
            
            # 重大な競合チェック
            try:
                preview = self.get_sync_preview(max_pages=10)
                if len(preview.get("potential_conflicts", [])) > 5:
                    validation_result["warnings"].append("多数のファイル名競合が予想されます")
                else:
                    validation_result["checks"]["no_critical_conflicts"] = True
            except:
                validation_result["warnings"].append("競合チェックを実行できませんでした")
            
            return validation_result
            
        except Exception as e:
            validation_result["errors"].append(f"検証中にエラーが発生しました: {str(e)}")
            validation_result["is_valid"] = False
            return validation_result
    
    def sync_all_pages(self, progress_callback=None) -> SyncResult:
        """
        すべてのページを同期
        
        Args:
            progress_callback: 進捗コールバック関数 (current, total, page_title)
            
        Returns:
            SyncResultオブジェクト
        """
        result = SyncResult()
        
        try:
            self.logger.info("全ページ同期開始")
            
            # 前提条件を検証
            validation = self.validate_sync_prerequisites()
            if not validation["is_valid"]:
                for error in validation["errors"]:
                    result.add_error(error)
                result.complete()
                return result
            
            # 警告があれば記録
            for warning in validation["warnings"]:
                result.add_warning(warning)
            
            # すべてのページを取得
            pages = self.notion_client.get_database_pages()
            result.total_pages = len(pages)
            
            if result.total_pages == 0:
                result.add_warning("同期対象のページが見つかりませんでした")
                result.complete()
                return result
            
            self.logger.info(f"同期対象ページ数: {result.total_pages}")
            
            # バッチサイズに分割して処理
            batch_size = self.config.sync.batch_size
            batches = [pages[i:i + batch_size] for i in range(0, len(pages), batch_size)]
            
            for batch_index, batch in enumerate(batches):
                self.logger.info(f"バッチ {batch_index + 1}/{len(batches)} 処理開始 ({len(batch)}ページ)")
                
                # バッチ内のページを処理
                batch_results = self._process_page_batch(batch, result, progress_callback)
                result.conversion_results.extend(batch_results)
            
            # ファイル書き込み（競合解決付き）
            if result.conversion_results:
                write_results = self.file_manager.safe_batch_write(
                    result.conversion_results,
                    overwrite=self.config.sync.overwrite_existing,
                    resolve_conflicts=True
                )
                
                # 書き込み結果を反映
                result.successful_pages = write_results["successful_writes"]
                result.failed_pages = write_results["failed_writes"]
                
                if write_results["conflicts_detected"] > 0:
                    result.add_warning(f"{write_results['conflicts_detected']}件のファイル名競合を解決しました")
                
                if write_results["conflict_report"]:
                    self.logger.info("競合解決レポート:\n" + write_results["conflict_report"])
            
            result.complete()
            self.logger.info(f"全ページ同期完了: {result.successful_pages}/{result.total_pages}ページ成功")
            
            return result
            
        except Exception as e:
            self.logger.error(f"全ページ同期エラー: {str(e)}")
            result.add_error(f"同期中にエラーが発生しました: {str(e)}")
            result.complete()
            return result
    
    def _process_page_batch(self, pages: List[NotionPage], result: SyncResult, progress_callback=None) -> List[MarkdownConversionResult]:
        """
        ページバッチを処理
        
        Args:
            pages: 処理するページのリスト
            result: 同期結果オブジェクト
            progress_callback: 進捗コールバック関数
            
        Returns:
            変換結果のリスト
        """
        batch_results = []
        
        for page in pages:
            try:
                # 進捗コールバック
                if progress_callback:
                    current_progress = result.successful_pages + result.failed_pages + result.skipped_pages + 1
                    progress_callback(current_progress, result.total_pages, page.title)
                
                # ページコンテンツを取得
                page_content = self.notion_client.get_page_content(page.id)
                
                # Markdownに変換
                conversion_result = self.data_processor.convert_page_to_markdown(
                    page_content,
                    self.config.sync.file_naming,
                    self.config.sync.include_properties
                )
                
                batch_results.append(conversion_result)
                
                # 変換警告があれば記録
                for warning in conversion_result.warnings:
                    result.add_warning(f"{page.title}: {warning}")
                
                self.logger.debug(f"ページ変換完了: {page.title}")
                
            except Exception as e:
                error_msg = f"ページ処理エラー ({page.title}): {str(e)}"
                result.add_error(error_msg)
                self.logger.error(error_msg)
                continue
        
        return batch_results
    
    def sync_pages_by_filter(self, filter_dict: Dict[str, Any], progress_callback=None) -> SyncResult:
        """
        フィルター条件に基づいてページを同期
        
        Args:
            filter_dict: Notion APIフィルター条件
            progress_callback: 進捗コールバック関数
            
        Returns:
            SyncResultオブジェクト
        """
        result = SyncResult()
        
        try:
            self.logger.info(f"フィルター同期開始: {filter_dict}")
            
            # フィルター条件でページを取得
            pages = self.notion_client.get_database_pages(filter_dict=filter_dict)
            result.total_pages = len(pages)
            
            if result.total_pages == 0:
                result.add_warning("フィルター条件に一致するページが見つかりませんでした")
                result.complete()
                return result
            
            self.logger.info(f"フィルター対象ページ数: {result.total_pages}")
            
            # ページを処理
            batch_results = self._process_page_batch(pages, result, progress_callback)
            result.conversion_results.extend(batch_results)
            
            # ファイル書き込み
            if result.conversion_results:
                write_results = self.file_manager.safe_batch_write(
                    result.conversion_results,
                    overwrite=self.config.sync.overwrite_existing,
                    resolve_conflicts=True
                )
                
                result.successful_pages = write_results["successful_writes"]
                result.failed_pages = write_results["failed_writes"]
            
            result.complete()
            self.logger.info(f"フィルター同期完了: {result.successful_pages}/{result.total_pages}ページ成功")
            
            return result
            
        except Exception as e:
            self.logger.error(f"フィルター同期エラー: {str(e)}")
            result.add_error(f"フィルター同期中にエラーが発生しました: {str(e)}")
            result.complete()
            return result
    
    def sync_pages_modified_after(self, after_date: datetime, progress_callback=None) -> SyncResult:
        """
        指定日時以降に更新されたページを同期
        
        Args:
            after_date: この日時以降に更新されたページを同期
            progress_callback: 進捗コールバック関数
            
        Returns:
            SyncResultオブジェクト
        """
        try:
            self.logger.info(f"更新日時フィルター同期開始: {after_date}")
            
            pages = self.notion_client.get_pages_modified_after(after_date)
            
            if not pages:
                result = SyncResult()
                result.add_warning(f"{after_date}以降に更新されたページが見つかりませんでした")
                result.complete()
                return result
            
            # フィルター同期として処理
            filter_dict = {
                "timestamp": "last_edited_time",
                "last_edited_time": {
                    "after": after_date.isoformat()
                }
            }
            
            return self.sync_pages_by_filter(filter_dict, progress_callback)
            
        except Exception as e:
            result = SyncResult()
            result.add_error(f"更新日時フィルター同期エラー: {str(e)}")
            result.complete()
            return result
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """
        同期統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        try:
            # データベース統計
            total_pages = self.notion_client.get_page_count()
            
            # ファイルシステム統計
            disk_usage = self.file_manager.get_disk_usage()
            markdown_files = self.file_manager.list_markdown_files()
            
            # 整合性チェック
            integrity_results = self.file_manager.batch_verify_integrity()
            valid_files = sum(1 for result in integrity_results.values() if result.get("is_valid", False))
            
            return {
                "database_stats": {
                    "total_pages": total_pages,
                    "last_check": datetime.now().isoformat()
                },
                "file_system_stats": {
                    "total_markdown_files": len(markdown_files),
                    "total_size_mb": disk_usage["total_size_mb"],
                    "average_file_size": disk_usage["average_file_size"],
                    "valid_files": valid_files,
                    "invalid_files": len(markdown_files) - valid_files
                },
                "sync_coverage": {
                    "coverage_percentage": (len(markdown_files) / total_pages * 100) if total_pages > 0 else 0,
                    "missing_pages": max(0, total_pages - len(markdown_files)),
                    "extra_files": max(0, len(markdown_files) - total_pages)
                }
            }
            
        except Exception as e:
            self.logger.error(f"統計情報取得エラー: {str(e)}")
            return {
                "error": str(e),
                "database_stats": {},
                "file_system_stats": {},
                "sync_coverage": {}
            }
    
    def recover_from_failed_sync(self, failed_result: SyncResult) -> SyncResult:
        """
        失敗した同期からの回復を試行
        
        Args:
            failed_result: 失敗した同期結果
            
        Returns:
            回復試行の結果
        """
        recovery_result = SyncResult()
        
        try:
            self.logger.info("同期回復処理開始")
            
            # 失敗したページのIDを特定
            failed_page_ids = []
            for error in failed_result.errors:
                if "ページ処理エラー" in error:
                    # エラーメッセージからページIDを抽出（簡易実装）
                    # 実際の実装では、より詳細なエラー追跡が必要
                    pass
            
            # 代替として、最近更新されたページを再同期
            recent_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            self.logger.info("最近更新されたページの再同期を試行")
            recovery_result = self.sync_pages_modified_after(recent_date)
            
            if recovery_result.successful_pages > 0:
                self.logger.info(f"回復処理完了: {recovery_result.successful_pages}ページを回復")
            else:
                recovery_result.add_warning("回復できるページが見つかりませんでした")
            
            return recovery_result
            
        except Exception as e:
            self.logger.error(f"回復処理エラー: {str(e)}")
            recovery_result.add_error(f"回復処理中にエラーが発生しました: {str(e)}")
            recovery_result.complete()
            return recovery_result
    
    def create_sync_report(self, sync_result: SyncResult) -> str:
        """
        同期レポートを作成
        
        Args:
            sync_result: 同期結果
            
        Returns:
            レポート文字列
        """
        report_lines = ["# Notion-Obsidian同期レポート\n"]
        
        # サマリー
        summary = sync_result.get_summary()
        report_lines.append("## サマリー")
        report_lines.append(f"- 開始時刻: {summary['start_time']}")
        report_lines.append(f"- 終了時刻: {summary['end_time']}")
        report_lines.append(f"- 処理時間: {summary['duration_seconds']:.2f}秒")
        report_lines.append(f"- 対象ページ数: {summary['total_pages']}")
        report_lines.append(f"- 成功: {summary['successful_pages']}")
        report_lines.append(f"- 失敗: {summary['failed_pages']}")
        report_lines.append(f"- スキップ: {summary['skipped_pages']}")
        report_lines.append(f"- 成功率: {summary['success_rate']:.1f}%")
        report_lines.append("")
        
        # エラー詳細
        if sync_result.errors:
            report_lines.append("## エラー")
            for i, error in enumerate(sync_result.errors, 1):
                report_lines.append(f"{i}. {error}")
            report_lines.append("")
        
        # 警告詳細
        if sync_result.warnings:
            report_lines.append("## 警告")
            for i, warning in enumerate(sync_result.warnings, 1):
                report_lines.append(f"{i}. {warning}")
            report_lines.append("")
        
        # 変換統計
        if sync_result.conversion_results:
            conversion_summary = self.data_processor.get_conversion_summary(sync_result.conversion_results)
            report_lines.append("## 変換統計")
            report_lines.append(f"- 総ファイルサイズ: {conversion_summary['total_size_mb']:.2f}MB")
            report_lines.append(f"- 総単語数: {conversion_summary['total_words']}")
            report_lines.append(f"- 平均ファイルサイズ: {conversion_summary['average_file_size']:.0f}バイト")
            report_lines.append(f"- 警告があるファイル: {conversion_summary['files_with_warnings']}")
            report_lines.append(f"- サポートされていないブロックがあるファイル: {conversion_summary['files_with_unsupported']}")
            
            if conversion_summary['most_common_unsupported']:
                report_lines.append("\n### よく見つかるサポートされていないブロック")
                for block_type, count in conversion_summary['most_common_unsupported']:
                    report_lines.append(f"- {block_type}: {count}回")
            
            report_lines.append("")
        
        # 推奨アクション
        report_lines.append("## 推奨アクション")
        if summary['success_rate'] < 50:
            report_lines.append("- 成功率が低いです。設定やネットワーク接続を確認してください")
        if summary['error_count'] > 0:
            report_lines.append("- エラーが発生しています。ログを確認して問題を解決してください")
        if summary['warning_count'] > 10:
            report_lines.append("- 多数の警告があります。設定の見直しを検討してください")
        if not report_lines[-1].startswith("-"):
            report_lines.append("- 同期は正常に完了しました")
        
        return "\n".join(report_lines)
    
    def setup_logging(self) -> None:
        """
        ログ設定をセットアップ
        """
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, self.config.logging.level))
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # ファイルハンドラー（設定されている場合）
        if self.config.logging.file:
            file_handler = logging.FileHandler(self.config.logging.file, encoding='utf-8')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
    
    def handle_sync_interruption(self, sync_result: SyncResult) -> Dict[str, Any]:
        """
        同期中断時の処理
        
        Args:
            sync_result: 中断時点での同期結果
            
        Returns:
            中断処理結果の辞書
        """
        try:
            self.logger.warning("同期が中断されました")
            
            # 現在の状態を保存
            interruption_info = {
                "interruption_time": datetime.now().isoformat(),
                "processed_pages": sync_result.successful_pages + sync_result.failed_pages,
                "remaining_pages": sync_result.total_pages - (sync_result.successful_pages + sync_result.failed_pages),
                "partial_results": len(sync_result.conversion_results),
                "can_resume": sync_result.total_pages > 0
            }
            
            # 部分的な結果があれば保存を試行
            if sync_result.conversion_results:
                try:
                    write_results = self.file_manager.safe_batch_write(
                        sync_result.conversion_results,
                        overwrite=self.config.sync.overwrite_existing,
                        resolve_conflicts=True
                    )
                    interruption_info["partial_save_successful"] = write_results["successful_writes"]
                    interruption_info["partial_save_failed"] = write_results["failed_writes"]
                    
                    self.logger.info(f"中断時に{write_results['successful_writes']}ファイルを保存しました")
                    
                except Exception as e:
                    interruption_info["partial_save_error"] = str(e)
                    self.logger.error(f"中断時の部分保存エラー: {str(e)}")
            
            # 整合性チェック
            try:
                integrity_results = self.file_manager.batch_verify_integrity()
                corrupted_files = [
                    filename for filename, result in integrity_results.items()
                    if not result.get("is_valid", True)
                ]
                interruption_info["corrupted_files"] = corrupted_files
                
                if corrupted_files:
                    self.logger.warning(f"{len(corrupted_files)}個の破損ファイルを検出しました")
                
            except Exception as e:
                interruption_info["integrity_check_error"] = str(e)
            
            return interruption_info
            
        except Exception as e:
            self.logger.error(f"中断処理エラー: {str(e)}")
            return {
                "interruption_time": datetime.now().isoformat(),
                "error": str(e),
                "can_resume": False
            }
    
    def cleanup_failed_files(self) -> Dict[str, Any]:
        """
        失敗したファイルのクリーンアップ
        
        Returns:
            クリーンアップ結果の辞書
        """
        try:
            self.logger.info("失敗ファイルのクリーンアップ開始")
            
            # 整合性チェック
            integrity_results = self.file_manager.batch_verify_integrity()
            
            cleanup_result = {
                "checked_files": len(integrity_results),
                "corrupted_files": [],
                "deleted_files": [],
                "backup_files": [],
                "errors": []
            }
            
            for filename, result in integrity_results.items():
                if not result.get("exists", True):
                    continue
                    
                if not result.get("readable", True):
                    cleanup_result["corrupted_files"].append(filename)
                    
                    # バックアップを作成してから削除
                    try:
                        if self.file_manager.backup_file(filename, ".corrupted"):
                            cleanup_result["backup_files"].append(f"{filename}.corrupted")
                        
                        if self.file_manager.delete_file(filename):
                            cleanup_result["deleted_files"].append(filename)
                            self.logger.info(f"破損ファイルを削除: {filename}")
                        
                    except Exception as e:
                        error_msg = f"ファイル削除エラー ({filename}): {str(e)}"
                        cleanup_result["errors"].append(error_msg)
                        self.logger.error(error_msg)
                
                elif not result.get("is_valid", True):
                    # 警告があるが読み取り可能なファイル
                    warnings = result.get("warnings", [])
                    if any("長すぎます" in w or "大きすぎます" in w for w in warnings):
                        self.logger.warning(f"大きなファイルを検出: {filename}")
            
            # 古いバックアップファイルをクリーンアップ
            self.file_manager.cleanup_old_backups(max_backups=3)
            
            self.logger.info(f"クリーンアップ完了: {len(cleanup_result['deleted_files'])}ファイル削除")
            return cleanup_result
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {str(e)}")
            return {
                "error": str(e),
                "checked_files": 0,
                "corrupted_files": [],
                "deleted_files": [],
                "backup_files": [],
                "errors": [str(e)]
            }
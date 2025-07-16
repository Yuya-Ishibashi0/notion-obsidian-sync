"""
同期オーケストレーターのユニットテスト
"""

import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.sync_orchestrator import SyncOrchestrator, SyncResult
from models.config import AppConfig, NotionConfig, ObsidianConfig, SyncConfig, ConversionConfig
from models.notion import NotionPage, NotionPageContent
from models.markdown import MarkdownFile, MarkdownConversionResult


class TestSyncResult:
    """SyncResult のテスト"""
    
    def test_init(self):
        """初期化テスト"""
        result = SyncResult()
        assert result.total_pages == 0
        assert result.successful_pages == 0
        assert result.failed_pages == 0
        assert result.skipped_pages == 0
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.end_time is None
    
    def test_add_error_and_warning(self):
        """エラーと警告の追加テスト"""
        result = SyncResult()
        result.add_error("テストエラー")
        result.add_warning("テスト警告")
        
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert result.errors[0] == "テストエラー"
        assert result.warnings[0] == "テスト警告"
    
    def test_complete(self):
        """完了処理テスト"""
        result = SyncResult()
        assert result.end_time is None
        
        result.complete()
        assert result.end_time is not None
        assert result.duration > 0
    
    def test_success_rate(self):
        """成功率計算テスト"""
        result = SyncResult()
        
        # ページがない場合
        assert result.success_rate == 0.0
        
        # 成功率50%の場合
        result.total_pages = 10
        result.successful_pages = 5
        assert result.success_rate == 50.0
        
        # 成功率100%の場合
        result.successful_pages = 10
        assert result.success_rate == 100.0
    
    def test_get_summary(self):
        """サマリー取得テスト"""
        result = SyncResult()
        result.total_pages = 5
        result.successful_pages = 4
        result.failed_pages = 1
        result.add_error("テストエラー")
        result.complete()
        
        summary = result.get_summary()
        assert summary["total_pages"] == 5
        assert summary["successful_pages"] == 4
        assert summary["failed_pages"] == 1
        assert summary["success_rate"] == 80.0
        assert summary["error_count"] == 1
        assert summary["has_errors"] is True
        assert summary["duration_seconds"] > 0


class TestSyncOrchestrator:
    """SyncOrchestrator のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用設定を作成
        self.config = AppConfig(
            notion=NotionConfig(api_token="test_token", database_id="test_db"),
            obsidian=ObsidianConfig(vault_path=self.temp_dir),
            sync=SyncConfig(conversion=ConversionConfig())
        )
    
    def teardown_method(self):
        """テストクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('services.sync_orchestrator.NotionClient')
    @patch('services.sync_orchestrator.DataProcessor')
    @patch('services.sync_orchestrator.FileManager')
    def test_init(self, mock_file_manager, mock_data_processor, mock_notion_client):
        """初期化テスト"""
        orchestrator = SyncOrchestrator(self.config)
        
        # コンポーネントが正しく初期化されることを確認
        mock_notion_client.assert_called_once_with("test_token", "test_db")
        mock_data_processor.assert_called_once()
        mock_file_manager.assert_called_once_with(self.temp_dir, None)
    
    @patch('services.sync_orchestrator.NotionClient')
    @patch('services.sync_orchestrator.DataProcessor')
    @patch('services.sync_orchestrator.FileManager')
    def test_sync_single_page_success(self, mock_file_manager_class, mock_data_processor_class, mock_notion_client_class):
        """単一ページ同期成功テスト"""
        # モックを設定
        mock_notion_client = Mock()
        mock_data_processor = Mock()
        mock_file_manager = Mock()
        
        mock_notion_client_class.return_value = mock_notion_client
        mock_data_processor_class.return_value = mock_data_processor
        mock_file_manager_class.return_value = mock_file_manager
        
        # テストデータを準備
        test_page = NotionPage(
            id="test_page_id",
            created_time=datetime.now(),
            last_edited_time=datetime.now(),
            created_by={},
            last_edited_by={}
        )
        test_page_content = NotionPageContent(page=test_page, blocks=[])
        test_markdown_file = MarkdownFile(filename="test.md", content="# テスト")
        test_conversion_result = MarkdownConversionResult(markdown_file=test_markdown_file)
        
        mock_notion_client.get_page_content.return_value = test_page_content
        mock_data_processor.convert_page_to_markdown.return_value = test_conversion_result
        mock_file_manager.write_markdown_file.return_value = True
        
        # テスト実行
        orchestrator = SyncOrchestrator(self.config)
        result = orchestrator.sync_single_page("test_page_id")
        
        # 結果確認
        assert result is True
        mock_notion_client.get_page_content.assert_called_once_with("test_page_id")
        mock_data_processor.convert_page_to_markdown.assert_called_once()
        mock_file_manager.write_markdown_file.assert_called_once()
    
    @patch('services.sync_orchestrator.NotionClient')
    @patch('services.sync_orchestrator.DataProcessor')
    @patch('services.sync_orchestrator.FileManager')
    def test_sync_single_page_failure(self, mock_file_manager_class, mock_data_processor_class, mock_notion_client_class):
        """単一ページ同期失敗テスト"""
        # モックを設定
        mock_notion_client = Mock()
        mock_notion_client_class.return_value = mock_notion_client
        mock_data_processor_class.return_value = Mock()
        mock_file_manager_class.return_value = Mock()
        
        # エラーを発生させる
        mock_notion_client.get_page_content.side_effect = Exception("API エラー")
        
        # テスト実行
        orchestrator = SyncOrchestrator(self.config)
        result = orchestrator.sync_single_page("test_page_id")
        
        # 結果確認
        assert result is False
    
    @patch('services.sync_orchestrator.NotionClient')
    @patch('services.sync_orchestrator.DataProcessor')
    @patch('services.sync_orchestrator.FileManager')
    def test_test_sync_connection_success(self, mock_file_manager_class, mock_data_processor_class, mock_notion_client_class):
        """同期接続テスト成功"""
        # モックを設定
        mock_notion_client = Mock()
        mock_file_manager = Mock()
        
        mock_notion_client_class.return_value = mock_notion_client
        mock_data_processor_class.return_value = Mock()
        mock_file_manager_class.return_value = mock_file_manager
        
        # 成功レスポンスを設定
        mock_notion_client.test_connection.return_value = True
        mock_notion_client.get_database_info.return_value = Mock(title="テストDB")
        mock_file_manager.validate_vault_structure.return_value = []
        mock_file_manager.sync_path = Mock()
        mock_file_manager.sync_path.__truediv__ = Mock(return_value=Mock())
        
        # テスト実行
        orchestrator = SyncOrchestrator(self.config)
        result = orchestrator.test_sync_connection()
        
        # 結果確認
        assert result["overall_status"] is True
        assert result["notion_connection"] is True
        assert result["database_access"] is True
        assert result["obsidian_vault"] is True
        assert len(result["errors"]) == 0
    
    @patch('services.sync_orchestrator.NotionClient')
    @patch('services.sync_orchestrator.DataProcessor')
    @patch('services.sync_orchestrator.FileManager')
    def test_test_sync_connection_failure(self, mock_file_manager_class, mock_data_processor_class, mock_notion_client_class):
        """同期接続テスト失敗"""
        # モックを設定
        mock_notion_client = Mock()
        mock_notion_client_class.return_value = mock_notion_client
        mock_data_processor_class.return_value = Mock()
        mock_file_manager_class.return_value = Mock()
        
        # 失敗レスポンスを設定
        mock_notion_client.test_connection.return_value = False
        
        # テスト実行
        orchestrator = SyncOrchestrator(self.config)
        result = orchestrator.test_sync_connection()
        
        # 結果確認
        assert result["overall_status"] is False
        assert result["notion_connection"] is False
        assert len(result["errors"]) > 0
    
    @patch('services.sync_orchestrator.NotionClient')
    @patch('services.sync_orchestrator.DataProcessor')
    @patch('services.sync_orchestrator.FileManager')
    def test_get_sync_preview(self, mock_file_manager_class, mock_data_processor_class, mock_notion_client_class):
        """同期プレビューテスト"""
        # モックを設定
        mock_notion_client = Mock()
        mock_data_processor = Mock()
        mock_file_manager = Mock()
        
        mock_notion_client_class.return_value = mock_notion_client
        mock_data_processor_class.return_value = mock_data_processor
        mock_file_manager_class.return_value = mock_file_manager
        
        # テストデータを準備
        test_pages = [
            NotionPage(
                id=f"page_{i}",
                created_time=datetime.now(),
                last_edited_time=datetime.now(),
                created_by={},
                last_edited_by={}
            ) for i in range(3)
        ]
        
        mock_notion_client.get_database_pages.return_value = test_pages
        mock_data_processor._generate_filename.side_effect = lambda page, pattern: f"{page.id}.md"
        mock_file_manager.check_file_conflicts.return_value = {}
        
        # テスト実行
        orchestrator = SyncOrchestrator(self.config)
        result = orchestrator.get_sync_preview(max_pages=5)
        
        # 結果確認
        assert result["total_pages_in_database"] == 3
        assert len(result["preview_pages"]) == 3
        assert len(result["estimated_files"]) == 3
        assert len(result["potential_conflicts"]) == 0
    
    @patch('services.sync_orchestrator.NotionClient')
    @patch('services.sync_orchestrator.DataProcessor')
    @patch('services.sync_orchestrator.FileManager')
    def test_validate_sync_prerequisites_success(self, mock_file_manager_class, mock_data_processor_class, mock_notion_client_class):
        """同期前提条件検証成功テスト"""
        # モックを設定
        mock_notion_client = Mock()
        mock_file_manager = Mock()
        
        mock_notion_client_class.return_value = mock_notion_client
        mock_data_processor_class.return_value = Mock()
        mock_file_manager_class.return_value = mock_file_manager
        
        # 成功レスポンスを設定
        mock_notion_client.test_connection.return_value = True
        mock_file_manager.validate_vault_structure.return_value = []
        
        # テスト実行
        orchestrator = SyncOrchestrator(self.config)
        
        # get_sync_previewをモック
        with patch.object(orchestrator, 'get_sync_preview') as mock_preview:
            mock_preview.return_value = {"potential_conflicts": []}
            
            result = orchestrator.validate_sync_prerequisites()
        
        # 結果確認
        assert result["is_valid"] is True
        assert result["checks"]["config_valid"] is True
        assert result["checks"]["notion_accessible"] is True
        assert result["checks"]["vault_writable"] is True
        assert len(result["errors"]) == 0
    
    @patch('services.sync_orchestrator.NotionClient')
    @patch('services.sync_orchestrator.DataProcessor')
    @patch('services.sync_orchestrator.FileManager')
    def test_validate_sync_prerequisites_failure(self, mock_file_manager_class, mock_data_processor_class, mock_notion_client_class):
        """同期前提条件検証失敗テスト"""
        # モックを設定
        mock_notion_client = Mock()
        mock_file_manager = Mock()
        
        mock_notion_client_class.return_value = mock_notion_client
        mock_data_processor_class.return_value = Mock()
        mock_file_manager_class.return_value = mock_file_manager
        
        # 失敗レスポンスを設定
        mock_notion_client.test_connection.return_value = False
        mock_file_manager.validate_vault_structure.return_value = ["書き込み権限がありません"]
        
        # テスト実行
        orchestrator = SyncOrchestrator(self.config)
        
        with patch.object(orchestrator, 'get_sync_preview') as mock_preview:
            mock_preview.return_value = {"potential_conflicts": []}
            
            result = orchestrator.validate_sync_prerequisites()
        
        # 結果確認
        assert result["is_valid"] is False
        assert result["checks"]["notion_accessible"] is False
        assert result["checks"]["vault_writable"] is False
        assert len(result["errors"]) > 0
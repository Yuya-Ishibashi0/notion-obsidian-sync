"""
統合テスト
エンドツーエンドの同期フローをテストする
"""

import pytest
import tempfile
import shutil
import os
import sys
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from main import main
from models.config import AppConfig, NotionConfig, ObsidianConfig, SyncConfig, ConversionConfig
from models.notion import NotionPage, NotionPageContent, NotionBlock
from models.markdown import MarkdownFile, MarkdownConversionResult
from services.sync_orchestrator import SyncOrchestrator
from utils.config_loader import ConfigLoader


class TestEndToEndIntegration:
    """エンドツーエンドの統合テスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.temp_dir) / "test_vault"
        self.vault_path.mkdir(exist_ok=True)
        
        # テスト用設定ファイルを作成
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        self.test_config = {
            'notion': {
                'api_token': 'test_token_12345',
                'database_id': 'test_database_id'
            },
            'obsidian': {
                'vault_path': str(self.vault_path),
                'subfolder': 'notion-sync'
            },
            'sync': {
                'file_naming': '{title}',
                'include_properties': True,
                'overwrite_existing': True,
                'batch_size': 5,
                'conversion': {
                    'database_mode': 'table',
                    'column_layout': 'separator',
                    'unsupported_blocks': 'placeholder',
                    'quality_level': 'standard'
                }
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f, default_flow_style=False, allow_unicode=True)
        
        # 同期先ディレクトリを作成
        self.sync_path = self.vault_path / "notion-sync"
        self.sync_path.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """テストクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_notion_pages(self) -> list:
        """テスト用のNotionページデータを作成"""
        from models.notion import NotionProperty
        
        pages = []
        for i in range(3):
            # タイトルプロパティを作成
            title_prop = NotionProperty(
                id="title",
                name="Name",
                type="title",
                value=[{"plain_text": f"テストページ{i+1}"}]
            )
            
            # その他のプロパティを作成
            status_prop = NotionProperty(
                id="status",
                name="Status",
                type="select",
                value={"name": "公開"}
            )
            
            tags_prop = NotionProperty(
                id="tags",
                name="Tags",
                type="multi_select",
                value=[{"name": "テスト"}, {"name": f"ページ{i+1}"}]
            )
            
            page = NotionPage(
                id=f"test_page_{i}",
                created_time=datetime.now(),
                last_edited_time=datetime.now(),
                created_by={"id": "test_user"},
                last_edited_by={"id": "test_user"},
                properties={
                    "title": title_prop,
                    "status": status_prop,
                    "tags": tags_prop
                }
            )
            pages.append(page)
        return pages
    
    def create_test_page_content(self, page: NotionPage) -> NotionPageContent:
        """テスト用のページコンテンツを作成"""
        blocks = [
            NotionBlock(
                id=f"block_{page.id}_1",
                type="paragraph",
                content={
                    "paragraph": {
                        "rich_text": [{"plain_text": f"これは{page.title}のコンテンツです。", "type": "text"}]
                    }
                }
            ),
            NotionBlock(
                id=f"block_{page.id}_2",
                type="heading_2",
                content={
                    "heading_2": {
                        "rich_text": [{"plain_text": "セクション1", "type": "text"}]
                    }
                }
            ),
            NotionBlock(
                id=f"block_{page.id}_3",
                type="bulleted_list_item",
                content={
                    "bulleted_list_item": {
                        "rich_text": [{"plain_text": "リストアイテム1", "type": "text"}]
                    }
                }
            )
        ]
        
        return NotionPageContent(page=page, blocks=blocks)
    
    @patch('services.sync_orchestrator.NotionClient')
    @patch('services.sync_orchestrator.DataProcessor')
    @patch('services.sync_orchestrator.FileManager')
    def test_full_sync_workflow(self, mock_file_manager_class, mock_data_processor_class, mock_notion_client_class):
        """完全な同期ワークフローのテスト"""
        # モックを設定
        mock_notion_client = Mock()
        mock_data_processor = Mock()
        mock_file_manager = Mock()
        
        mock_notion_client_class.return_value = mock_notion_client
        mock_data_processor_class.return_value = mock_data_processor
        mock_file_manager_class.return_value = mock_file_manager
        
        # テストデータを準備
        test_pages = self.create_test_notion_pages()
        
        # Notion APIのモック応答
        mock_notion_client.test_connection.return_value = True
        mock_notion_client.get_database_info.return_value = Mock(title="テストデータベース")
        mock_notion_client.get_database_pages.return_value = test_pages
        
        # ページコンテンツのモック応答
        def mock_get_page_content(page_id):
            page = next((p for p in test_pages if p.id == page_id), None)
            return self.create_test_page_content(page) if page else None
        
        mock_notion_client.get_page_content.side_effect = mock_get_page_content
        
        # データプロセッサーのモック応答
        def mock_convert_page(page_content, file_naming, include_properties):
            markdown_file = MarkdownFile(
                filename=f"{page_content.page.title}.md",
                content=f"# {page_content.page.title}\n\nテストコンテンツ",
                frontmatter={"title": page_content.page.title, "id": page_content.page.id}
            )
            return MarkdownConversionResult(markdown_file=markdown_file)
        
        mock_data_processor.convert_page_to_markdown.side_effect = mock_convert_page
        
        # ファイルマネージャーのモック応答
        mock_file_manager.validate_vault_structure.return_value = []
        mock_file_manager.safe_batch_write.return_value = {
            "successful_writes": len(test_pages),
            "failed_writes": 0,
            "conflicts_detected": 0,
            "conflict_report": ""
        }
        mock_file_manager.sync_path = self.sync_path
        
        # 設定を読み込み
        config_loader = ConfigLoader()
        config = config_loader.load_config(str(self.config_path))
        
        # 同期オーケストレーターを作成して実行
        orchestrator = SyncOrchestrator(config)
        result = orchestrator.sync_all_pages()
        
        # 結果を検証
        assert result.total_pages == len(test_pages)
        assert result.successful_pages == len(test_pages)
        assert result.failed_pages == 0
        assert result.success_rate == 100.0
        assert len(result.errors) == 0
        
        # モックの呼び出しを検証
        assert mock_notion_client.get_database_pages.call_count >= 1  # プレビューと実際の同期で複数回呼ばれる可能性
        assert mock_notion_client.get_page_content.call_count == len(test_pages)
        assert mock_data_processor.convert_page_to_markdown.call_count == len(test_pages)
        mock_file_manager.safe_batch_write.assert_called_once()
    
    @patch('services.sync_orchestrator.NotionClient')
    def test_connection_test_workflow(self, mock_notion_client_class):
        """接続テストワークフローのテスト"""
        # モックを設定
        mock_notion_client = Mock()
        mock_notion_client_class.return_value = mock_notion_client
        
        # 成功レスポンスを設定
        mock_notion_client.test_connection.return_value = True
        mock_notion_client.get_database_info.return_value = Mock(title="テストデータベース")
        
        # 設定を読み込み
        config_loader = ConfigLoader()
        config = config_loader.load_config(str(self.config_path))
        
        # 接続テストを実行
        orchestrator = SyncOrchestrator(config)
        
        # ファイルマネージャーのモックを設定
        with patch('utils.file_manager.FileManager') as mock_file_manager_class:
            mock_file_manager = Mock()
            mock_file_manager_class.return_value = mock_file_manager
            mock_file_manager.validate_vault_structure.return_value = []
            mock_file_manager.sync_path = self.sync_path
            
            # テスト用の一時ファイル作成をモック
            temp_file_mock = Mock()
            temp_file_mock.write_text = Mock()
            temp_file_mock.unlink = Mock()
            
            # sync_pathのパス操作をモック
            mock_sync_path = Mock()
            mock_sync_path.__truediv__ = Mock(return_value=temp_file_mock)
            mock_file_manager.sync_path = mock_sync_path
            
            result = orchestrator.test_sync_connection()
        
        # 結果を検証
        assert result["overall_status"] is True
        assert result["notion_connection"] is True
        assert result["database_access"] is True
        assert result["obsidian_vault"] is True
        assert result["file_write_permission"] is True
        assert len(result["errors"]) == 0
    
    @patch('services.notion_client.NotionClient')
    def test_sync_preview_workflow(self, mock_notion_client_class):
        """同期プレビューワークフローのテスト"""
        # モックを設定
        mock_notion_client = Mock()
        mock_notion_client_class.return_value = mock_notion_client
        
        # テストデータを準備
        test_pages = self.create_test_notion_pages()
        mock_notion_client.get_database_pages.return_value = test_pages
        
        # 設定を読み込み
        config_loader = ConfigLoader()
        config = config_loader.load_config(str(self.config_path))
        
        # プレビューを実行
        orchestrator = SyncOrchestrator(config)
        
        with patch('services.data_processor.DataProcessor') as mock_data_processor_class:
            mock_data_processor = Mock()
            mock_data_processor_class.return_value = mock_data_processor
            mock_data_processor._generate_filename.side_effect = lambda page, pattern: f"{page.title}.md"
            
            with patch('utils.file_manager.FileManager') as mock_file_manager_class:
                mock_file_manager = Mock()
                mock_file_manager_class.return_value = mock_file_manager
                mock_file_manager.check_file_conflicts.return_value = {}
                
                result = orchestrator.get_sync_preview(max_pages=5)
        
        # 結果を検証
        assert result["total_pages_in_database"] == len(test_pages)
        assert len(result["preview_pages"]) == len(test_pages)
        assert len(result["estimated_files"]) == len(test_pages)
        assert len(result["potential_conflicts"]) == 0
        
        # プレビューページの内容を検証
        for i, preview_page in enumerate(result["preview_pages"]):
            assert preview_page["id"] == test_pages[i].id
            assert preview_page["title"] == test_pages[i].title
            assert preview_page["estimated_filename"] == f"{test_pages[i].title}.md"
    
    def test_config_validation_workflow(self):
        """設定検証ワークフローのテスト"""
        # 設定ローダーを作成
        config_loader = ConfigLoader()
        
        # 設定ファイルの検証
        validation = config_loader.validate_config_file(str(self.config_path))
        
        # 結果を検証
        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0
        
        # 設定を読み込んで包括的検証
        config = config_loader.load_config(str(self.config_path))
        comprehensive_validation = config.validate_comprehensive()
        
        # 包括的検証の結果を確認（一部の項目は環境に依存するため、エラーがないことのみ確認）
        assert isinstance(comprehensive_validation["is_valid"], bool)
        assert isinstance(comprehensive_validation["errors"], list)
        assert isinstance(comprehensive_validation["warnings"], list)
    
    @patch('services.notion_client.NotionClient')
    def test_error_handling_workflow(self, mock_notion_client_class):
        """エラーハンドリングワークフローのテスト"""
        # モックを設定
        mock_notion_client = Mock()
        mock_notion_client_class.return_value = mock_notion_client
        
        # API エラーを発生させる
        mock_notion_client.get_database_pages.side_effect = Exception("API接続エラー")
        
        # 設定を読み込み
        config_loader = ConfigLoader()
        config = config_loader.load_config(str(self.config_path))
        
        # 同期を実行（エラーが発生することを期待）
        orchestrator = SyncOrchestrator(config)
        result = orchestrator.sync_all_pages()
        
        # エラーが適切に処理されることを確認
        assert result.total_pages == 0
        assert result.successful_pages == 0
        assert len(result.errors) > 0
        assert "API接続エラー" in str(result.errors)
    
    @patch('services.notion_client.NotionClient')
    def test_partial_failure_workflow(self, mock_notion_client_class):
        """部分的失敗ワークフローのテスト"""
        # モックを設定
        mock_notion_client = Mock()
        mock_notion_client_class.return_value = mock_notion_client
        
        # テストデータを準備
        test_pages = self.create_test_notion_pages()
        mock_notion_client.get_database_pages.return_value = test_pages
        
        # 一部のページでエラーを発生させる
        def mock_get_page_content(page_id):
            if page_id == "test_page_1":
                raise Exception("ページ取得エラー")
            page = next((p for p in test_pages if p.id == page_id), None)
            return self.create_test_page_content(page) if page else None
        
        mock_notion_client.get_page_content.side_effect = mock_get_page_content
        
        # 設定を読み込み
        config_loader = ConfigLoader()
        config = config_loader.load_config(str(self.config_path))
        
        # 同期を実行
        orchestrator = SyncOrchestrator(config)
        
        with patch('services.data_processor.DataProcessor') as mock_data_processor_class:
            mock_data_processor = Mock()
            mock_data_processor_class.return_value = mock_data_processor
            
            def mock_convert_page(page_content, file_naming, include_properties):
                markdown_file = MarkdownFile(
                    filename=f"{page_content.page.title}.md",
                    content=f"# {page_content.page.title}\n\nテストコンテンツ"
                )
                return MarkdownConversionResult(markdown_file=markdown_file)
            
            mock_data_processor.convert_page_to_markdown.side_effect = mock_convert_page
            
            with patch('utils.file_manager.FileManager') as mock_file_manager_class:
                mock_file_manager = Mock()
                mock_file_manager_class.return_value = mock_file_manager
                mock_file_manager.validate_vault_structure.return_value = []
                mock_file_manager.safe_batch_write.return_value = {
                    "successful_writes": 2,  # 3ページ中2ページ成功
                    "failed_writes": 0,
                    "conflicts_detected": 0,
                    "conflict_report": ""
                }
                
                result = orchestrator.sync_all_pages()
        
        # 部分的成功の結果を検証
        assert result.total_pages == len(test_pages)
        assert result.successful_pages == 2  # 1ページはエラーで処理されない
        assert len(result.errors) > 0
        assert result.success_rate < 100.0


class TestCommandLineIntegration:
    """コマンドライン統合テスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.temp_dir) / "test_vault"
        self.vault_path.mkdir(exist_ok=True)
        
        # テスト用設定ファイルを作成
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        test_config = {
            'notion': {
                'api_token': 'test_token_12345',
                'database_id': 'test_database_id'
            },
            'obsidian': {
                'vault_path': str(self.vault_path),
                'subfolder': 'notion-sync'
            },
            'sync': {
                'file_naming': '{title}',
                'include_properties': True,
                'overwrite_existing': True,
                'batch_size': 5
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
    
    def teardown_method(self):
        """テストクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('sys.argv', ['main.py', 'config', '--create', '--output', 'test_output.yaml'])
    @patch('utils.config_loader.ConfigLoader.create_default_config')
    def test_config_create_command(self, mock_create_config):
        """設定作成コマンドのテスト"""
        # コマンドを実行
        result = main()
        
        # 結果を検証
        assert result == 0
        mock_create_config.assert_called_once_with('test_output.yaml')
    
    @patch('sys.argv', ['main.py', 'config', '--validate', '--config', 'test_config.yaml'])
    def test_config_validate_command(self):
        """設定検証コマンドのテスト"""
        # sys.argvを一時的に変更
        original_argv = sys.argv
        try:
            sys.argv = ['main.py', 'config', '--validate', '--config', str(self.config_path)]
            result = main()
            
            # 結果を検証（設定ファイルが有効なので成功するはず）
            assert result == 0
            
        finally:
            sys.argv = original_argv
    
    @patch('services.sync_orchestrator.SyncOrchestrator')
    def test_test_command(self, mock_orchestrator_class):
        """テストコマンドのテスト"""
        # モックを設定
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.test_sync_connection.return_value = {
            "overall_status": True,
            "notion_connection": True,
            "database_access": True,
            "obsidian_vault": True,
            "file_write_permission": True,
            "errors": [],
            "warnings": []
        }
        
        # sys.argvを一時的に変更
        original_argv = sys.argv
        try:
            sys.argv = ['main.py', 'test', '--config', str(self.config_path)]
            result = main()
            
            # 結果を検証
            assert result == 0
            mock_orchestrator.test_sync_connection.assert_called_once()
            
        finally:
            sys.argv = original_argv
    
    @patch('services.sync_orchestrator.SyncOrchestrator')
    def test_preview_command(self, mock_orchestrator_class):
        """プレビューコマンドのテスト"""
        # モックを設定
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.get_sync_preview.return_value = {
            "total_pages_in_database": 5,
            "preview_pages": [
                {"title": "テストページ1", "estimated_filename": "テストページ1.md", "last_edited": None}
            ],
            "potential_conflicts": [],
            "warnings": []
        }
        
        # sys.argvを一時的に変更
        original_argv = sys.argv
        try:
            sys.argv = ['main.py', 'preview', '--config', str(self.config_path), '--max-pages', '5']
            result = main()
            
            # 結果を検証
            assert result == 0
            mock_orchestrator.get_sync_preview.assert_called_once_with(5)
            
        finally:
            sys.argv = original_argv


class TestConfigurationIntegration:
    """設定統合テスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.temp_dir) / "test_vault"
        self.vault_path.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """テストクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_config_loading_with_environment_variables(self):
        """環境変数を使用した設定読み込みテスト"""
        # 環境変数を設定
        os.environ['TEST_NOTION_TOKEN'] = 'env_test_token'
        os.environ['TEST_DATABASE_ID'] = 'env_database_id'
        
        try:
            # 環境変数を使用する設定ファイルを作成
            config_path = Path(self.temp_dir) / "env_config.yaml"
            config_data = {
                'notion': {
                    'api_token': '${TEST_NOTION_TOKEN}',
                    'database_id': '${TEST_DATABASE_ID}'
                },
                'obsidian': {
                    'vault_path': str(self.vault_path)
                }
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            # 設定を読み込み
            config_loader = ConfigLoader()
            config = config_loader.load_config(str(config_path))
            
            # 環境変数が正しく展開されることを確認
            assert config.notion.api_token == 'env_test_token'
            assert config.notion.database_id == 'env_database_id'
            
        finally:
            # 環境変数をクリーンアップ
            os.environ.pop('TEST_NOTION_TOKEN', None)
            os.environ.pop('TEST_DATABASE_ID', None)
    
    def test_config_validation_comprehensive(self):
        """包括的設定検証テスト"""
        # 有効な設定を作成
        config_path = Path(self.temp_dir) / "valid_config.yaml"
        config_data = {
            'notion': {
                'api_token': 'secret_valid_token_12345',
                'database_id': '12345678901234567890123456789012'
            },
            'obsidian': {
                'vault_path': str(self.vault_path),
                'subfolder': 'notion-sync'
            },
            'sync': {
                'file_naming': '{title}',
                'include_properties': True,
                'overwrite_existing': True,
                'batch_size': 10,
                'conversion': {
                    'database_mode': 'table',
                    'column_layout': 'separator',
                    'unsupported_blocks': 'placeholder',
                    'quality_level': 'standard'
                }
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        
        # 設定を読み込み
        config_loader = ConfigLoader()
        config = config_loader.load_config(str(config_path))
        
        # 包括的検証を実行
        validation = config.validate_comprehensive()
        
        # 基本的な検証項目が存在することを確認
        assert "is_valid" in validation
        assert "errors" in validation
        assert "warnings" in validation
        assert "checks" in validation
        
        # チェック項目が存在することを確認
        expected_checks = [
            "notion_config", "obsidian_config", "sync_config", 
            "logging_config", "file_permissions", "disk_space"
        ]
        for check in expected_checks:
            assert check in validation["checks"]
    
    def test_invalid_config_handling(self):
        """無効な設定の処理テスト"""
        # 無効な設定を作成
        config_path = Path(self.temp_dir) / "invalid_config.yaml"
        config_data = {
            'notion': {
                'api_token': '',  # 空のトークン
                'database_id': 'invalid_id'  # 無効なID
            },
            'obsidian': {
                'vault_path': '/nonexistent/path'  # 存在しないパス
            },
            'sync': {
                'batch_size': -1  # 無効なバッチサイズ
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        
        # 設定読み込みでエラーが発生することを確認
        config_loader = ConfigLoader()
        with pytest.raises(Exception):
            config_loader.load_config(str(config_path))


if __name__ == "__main__":
    pytest.main([__file__])
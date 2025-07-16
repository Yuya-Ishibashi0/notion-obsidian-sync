"""
設定データモデルのユニットテスト
"""

import pytest
import tempfile
import os
from pathlib import Path
from models.config import (
    NotionConfig, ObsidianConfig, ConversionConfig, 
    SyncConfig, LoggingConfig, AppConfig
)


class TestNotionConfig:
    """NotionConfig のテスト"""
    
    def test_valid_config(self):
        """有効な設定でのテスト"""
        config = NotionConfig(
            api_token="secret_test_token",
            database_id="test_database_id"
        )
        assert config.api_token == "secret_test_token"
        assert config.database_id == "test_database_id"
    
    def test_empty_api_token(self):
        """空のAPIトークンでのテスト"""
        with pytest.raises(ValueError, match="Notion APIトークンが必要です"):
            NotionConfig(api_token="", database_id="test_id")
    
    def test_empty_database_id(self):
        """空のデータベースIDでのテスト"""
        with pytest.raises(ValueError, match="NotionデータベースIDが必要です"):
            NotionConfig(api_token="test_token", database_id="")


class TestObsidianConfig:
    """ObsidianConfig のテスト"""
    
    def test_valid_config_with_temp_dir(self):
        """一時ディレクトリを使用した有効な設定のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ObsidianConfig(vault_path=temp_dir)
            assert config.vault_path == temp_dir
            assert config.subfolder is None
    
    def test_valid_config_with_subfolder(self):
        """サブフォルダ付きの有効な設定のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = ObsidianConfig(vault_path=temp_dir, subfolder="notes")
            assert config.subfolder == "notes"
            expected_path = str(Path(temp_dir) / "notes")
            assert config.full_sync_path == expected_path
    
    def test_nonexistent_path(self):
        """存在しないパスでのテスト"""
        with pytest.raises(ValueError, match="Obsidianボルトパスが存在しません"):
            ObsidianConfig(vault_path="/nonexistent/path")
    
    def test_file_instead_of_directory(self):
        """ファイルパスを指定した場合のテスト"""
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(ValueError, match="Obsidianボルトパスはディレクトリである必要があります"):
                ObsidianConfig(vault_path=temp_file.name)
    
    def test_empty_vault_path(self):
        """空のボルトパスでのテスト"""
        with pytest.raises(ValueError, match="Obsidianボルトパスが必要です"):
            ObsidianConfig(vault_path="")


class TestConversionConfig:
    """ConversionConfig のテスト"""
    
    def test_default_config(self):
        """デフォルト設定のテスト"""
        config = ConversionConfig()
        assert config.database_mode == "table"
        assert config.column_layout == "separator"
        assert config.unsupported_blocks == "placeholder"
        assert config.quality_level == "standard"
    
    def test_valid_custom_config(self):
        """有効なカスタム設定のテスト"""
        config = ConversionConfig(
            database_mode="description",
            column_layout="merge",
            unsupported_blocks="skip",
            quality_level="lenient"
        )
        assert config.database_mode == "description"
        assert config.column_layout == "merge"
        assert config.unsupported_blocks == "skip"
        assert config.quality_level == "lenient"
    
    def test_invalid_database_mode(self):
        """無効なdatabase_modeでのテスト"""
        with pytest.raises(ValueError, match="無効なdatabase_mode"):
            ConversionConfig(database_mode="invalid")
    
    def test_invalid_column_layout(self):
        """無効なcolumn_layoutでのテスト"""
        with pytest.raises(ValueError, match="無効なcolumn_layout"):
            ConversionConfig(column_layout="invalid")
    
    def test_invalid_unsupported_blocks(self):
        """無効なunsupported_blocksでのテスト"""
        with pytest.raises(ValueError, match="無効なunsupported_blocks"):
            ConversionConfig(unsupported_blocks="invalid")
    
    def test_invalid_quality_level(self):
        """無効なquality_levelでのテスト"""
        with pytest.raises(ValueError, match="無効なquality_level"):
            ConversionConfig(quality_level="invalid")


class TestSyncConfig:
    """SyncConfig のテスト"""
    
    def test_default_config(self):
        """デフォルト設定のテスト"""
        config = SyncConfig()
        assert config.file_naming == "{title}"
        assert config.include_properties is True
        assert config.overwrite_existing is True
        assert config.batch_size == 10
        assert isinstance(config.conversion, ConversionConfig)
    
    def test_valid_custom_config(self):
        """有効なカスタム設定のテスト"""
        conversion = ConversionConfig(database_mode="skip")
        config = SyncConfig(
            file_naming="{title}_{date}",
            include_properties=False,
            overwrite_existing=False,
            batch_size=5,
            conversion=conversion
        )
        assert config.file_naming == "{title}_{date}"
        assert config.include_properties is False
        assert config.overwrite_existing is False
        assert config.batch_size == 5
        assert config.conversion.database_mode == "skip"
    
    def test_invalid_batch_size_zero(self):
        """バッチサイズが0の場合のテスト"""
        with pytest.raises(ValueError, match="batch_sizeは正の整数である必要があります"):
            SyncConfig(batch_size=0)
    
    def test_invalid_batch_size_negative(self):
        """バッチサイズが負の場合のテスト"""
        with pytest.raises(ValueError, match="batch_sizeは正の整数である必要があります"):
            SyncConfig(batch_size=-1)
    
    def test_invalid_batch_size_too_large(self):
        """バッチサイズが大きすぎる場合のテスト"""
        with pytest.raises(ValueError, match="batch_sizeは100以下である必要があります"):
            SyncConfig(batch_size=101)


class TestLoggingConfig:
    """LoggingConfig のテスト"""
    
    def test_default_config(self):
        """デフォルト設定のテスト"""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.file is None
    
    def test_valid_custom_config(self):
        """有効なカスタム設定のテスト"""
        config = LoggingConfig(level="DEBUG", file="test.log")
        assert config.level == "DEBUG"
        assert config.file == "test.log"
    
    def test_invalid_log_level(self):
        """無効なログレベルでのテスト"""
        with pytest.raises(ValueError, match="無効なログレベル"):
            LoggingConfig(level="INVALID")


class TestAppConfig:
    """AppConfig のテスト"""
    
    def test_from_dict_minimal(self):
        """最小限の辞書からの設定作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dict = {
                'notion': {
                    'api_token': 'test_token',
                    'database_id': 'test_db_id'
                },
                'obsidian': {
                    'vault_path': temp_dir
                }
            }
            config = AppConfig.from_dict(config_dict)
            assert config.notion.api_token == 'test_token'
            assert config.obsidian.vault_path == temp_dir
            assert config.sync.batch_size == 10  # デフォルト値
            assert config.logging.level == "INFO"  # デフォルト値
    
    def test_from_dict_full(self):
        """完全な辞書からの設定作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dict = {
                'notion': {
                    'api_token': 'test_token',
                    'database_id': 'test_db_id'
                },
                'obsidian': {
                    'vault_path': temp_dir,
                    'subfolder': 'notes'
                },
                'sync': {
                    'file_naming': '{title}_{id}',
                    'include_properties': False,
                    'batch_size': 5,
                    'conversion': {
                        'database_mode': 'description',
                        'quality_level': 'lenient'
                    }
                },
                'logging': {
                    'level': 'DEBUG',
                    'file': 'debug.log'
                }
            }
            config = AppConfig.from_dict(config_dict)
            assert config.notion.api_token == 'test_token'
            assert config.obsidian.subfolder == 'notes'
            assert config.sync.file_naming == '{title}_{id}'
            assert config.sync.include_properties is False
            assert config.sync.batch_size == 5
            assert config.sync.conversion.database_mode == 'description'
            assert config.sync.conversion.quality_level == 'lenient'
            assert config.logging.level == 'DEBUG'
            assert config.logging.file == 'debug.log'
    
    def test_validate_success(self):
        """検証成功のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AppConfig(
                notion=NotionConfig(api_token="test", database_id="test"),
                obsidian=ObsidianConfig(vault_path=temp_dir)
            )
            # 例外が発生しないことを確認
            config.validate()
    
    def test_validate_invalid_sync_path_parent(self):
        """同期先の親ディレクトリが存在しない場合のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = os.path.join(temp_dir, "nonexistent", "subfolder")
            config = AppConfig(
                notion=NotionConfig(api_token="test", database_id="test"),
                obsidian=ObsidianConfig(vault_path=temp_dir, subfolder="nonexistent/subfolder")
            )
            with pytest.raises(ValueError, match="同期先の親ディレクトリが存在しません"):
                config.validate()
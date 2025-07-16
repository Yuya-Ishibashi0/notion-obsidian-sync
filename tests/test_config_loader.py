"""
設定ローダーのユニットテスト
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from utils.config_loader import ConfigLoader, ConfigLoadError
from models.config import AppConfig


class TestConfigLoader:
    """ConfigLoader のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.config_loader = ConfigLoader()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """テストクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_valid_config(self):
        """有効な設定ファイルの読み込みテスト"""
        config_content = """
notion:
  api_token: "test_token"
  database_id: "test_db_id"

obsidian:
  vault_path: "/test/vault"
  subfolder: "notes"

sync:
  file_naming: "{title}"
  include_properties: true
  overwrite_existing: true
  batch_size: 5
  conversion:
    database_mode: "table"
    column_layout: "separator"
    unsupported_blocks: "placeholder"
    quality_level: "standard"

logging:
  level: "DEBUG"
  file: "test.log"
"""
        
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        # ボルトディレクトリを作成（検証のため）
        vault_path = "/test/vault"
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            config = self.config_loader.load_config(config_path)
            
            assert isinstance(config, AppConfig)
            assert config.notion.api_token == "test_token"
            assert config.notion.database_id == "test_db_id"
            assert config.obsidian.vault_path == "/test/vault"
            assert config.obsidian.subfolder == "notes"
            assert config.sync.batch_size == 5
            assert config.logging.level == "DEBUG"
    
    def test_load_config_with_env_vars(self):
        """環境変数を含む設定ファイルの読み込みテスト"""
        config_content = """
notion:
  api_token: "${NOTION_API_TOKEN}"
  database_id: "${NOTION_DATABASE_ID}"

obsidian:
  vault_path: "${OBSIDIAN_VAULT_PATH}"
"""
        
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        # 環境変数を設定
        with patch.dict(os.environ, {
            'NOTION_API_TOKEN': 'env_token',
            'NOTION_DATABASE_ID': 'env_db_id',
            'OBSIDIAN_VAULT_PATH': '/env/vault'
        }):
            with patch('os.path.exists') as mock_exists:
                mock_exists.return_value = True
                
                config = self.config_loader.load_config(config_path)
                
                assert config.notion.api_token == "env_token"
                assert config.notion.database_id == "env_db_id"
                assert config.obsidian.vault_path == "/env/vault"
    
    def test_load_config_missing_env_var(self):
        """未設定の環境変数を含む設定ファイルのテスト"""
        config_content = """
notion:
  api_token: "${MISSING_TOKEN}"
  database_id: "test_db_id"

obsidian:
  vault_path: "/test/vault"
"""
        
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            # 未設定の環境変数があっても読み込みは成功するが、値は展開されない
            config = self.config_loader.load_config(config_path)
            assert config.notion.api_token == "${MISSING_TOKEN}"
    
    def test_load_invalid_yaml(self):
        """無効なYAMLファイルのテスト"""
        config_content = """
notion:
  api_token: "test_token"
  database_id: "test_db_id"
obsidian:
  vault_path: "/test/vault"
    invalid_indentation: true
"""
        
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        with pytest.raises(ConfigLoadError, match="YAML解析エラー"):
            self.config_loader.load_config(config_path)
    
    def test_load_missing_required_section(self):
        """必須セクションが欠けている設定ファイルのテスト"""
        config_content = """
notion:
  api_token: "test_token"
  database_id: "test_db_id"
# obsidian セクションが欠けている
"""
        
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        with pytest.raises(ConfigLoadError, match="必須セクションが見つかりません: obsidian"):
            self.config_loader.load_config(config_path)
    
    def test_load_missing_required_field(self):
        """必須フィールドが欠けている設定ファイルのテスト"""
        config_content = """
notion:
  # api_token が欠けている
  database_id: "test_db_id"

obsidian:
  vault_path: "/test/vault"
"""
        
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        with pytest.raises(ConfigLoadError, match="Notion設定の必須フィールドが見つかりません: api_token"):
            self.config_loader.load_config(config_path)
    
    def test_find_config_file(self):
        """設定ファイル検索のテスト"""
        # テスト用の設定ファイルを作成
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w') as f:
            f.write("test: true")
        
        # カレントディレクトリを変更
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            found_path = self.config_loader._find_config_file()
            assert found_path == "config.yaml"
        finally:
            os.chdir(original_cwd)
    
    def test_find_config_file_not_found(self):
        """設定ファイルが見つからない場合のテスト"""
        # 空のディレクトリで検索
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            found_path = self.config_loader._find_config_file()
            assert found_path is None
        finally:
            os.chdir(original_cwd)
    
    def test_create_default_config(self):
        """デフォルト設定ファイル作成のテスト"""
        output_path = os.path.join(self.temp_dir, "default_config.yaml")
        
        self.config_loader.create_default_config(output_path)
        
        assert os.path.exists(output_path)
        
        # 作成されたファイルが読み込み可能かテスト
        with open(output_path, 'r', encoding='utf-8') as f:
            import yaml
            config_dict = yaml.safe_load(f)
            assert 'notion' in config_dict
            assert 'obsidian' in config_dict
            assert 'sync' in config_dict
            assert 'logging' in config_dict
    
    def test_validate_config_file_valid(self):
        """有効な設定ファイルの検証テスト"""
        config_content = """
notion:
  api_token: "test_token"
  database_id: "test_db_id"

obsidian:
  vault_path: "/test/vault"
"""
        
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        result = self.config_loader.validate_config_file(config_path)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_config_file_invalid(self):
        """無効な設定ファイルの検証テスト"""
        config_content = """
notion:
  # api_token が欠けている
  database_id: "test_db_id"

obsidian:
  vault_path: "/test/vault"
"""
        
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        result = self.config_loader.validate_config_file(config_path)
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
    
    def test_validate_config_file_missing_env_vars(self):
        """未設定環境変数を含む設定ファイルの検証テスト"""
        config_content = """
notion:
  api_token: "${MISSING_TOKEN}"
  database_id: "test_db_id"

obsidian:
  vault_path: "/test/vault"
"""
        
        config_path = os.path.join(self.temp_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        result = self.config_loader.validate_config_file(config_path)
        
        assert "MISSING_TOKEN" in result["missing_env_vars"]
        assert len(result["warnings"]) > 0
    
    def test_expand_env_vars_in_string(self):
        """文字列内環境変数展開のテスト"""
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            result = self.config_loader._expand_env_vars_in_string("prefix_${TEST_VAR}_suffix")
            assert result == "prefix_test_value_suffix"
        
        # 未設定の環境変数
        result = self.config_loader._expand_env_vars_in_string("prefix_${MISSING_VAR}_suffix")
        assert result == "prefix_${MISSING_VAR}_suffix"
    
    def test_check_environment_variables(self):
        """環境変数チェックのテスト"""
        config_dict = {
            "notion": {
                "api_token": "${NOTION_TOKEN}",
                "database_id": "${DB_ID}"
            },
            "obsidian": {
                "vault_path": "/fixed/path"
            }
        }
        
        missing_vars = self.config_loader._check_environment_variables(config_dict)
        
        assert "NOTION_TOKEN" in missing_vars
        assert "DB_ID" in missing_vars
        assert len(missing_vars) == 2
    
    def test_get_config_template(self):
        """設定テンプレート取得のテスト"""
        template = self.config_loader.get_config_template()
        
        assert isinstance(template, str)
        assert "notion:" in template
        assert "obsidian:" in template
        assert "${NOTION_API_TOKEN}" in template
    
    def test_export_config_to_env(self):
        """設定の環境変数ファイルエクスポートのテスト"""
        # テスト用の設定を作成
        from models.config import NotionConfig, ObsidianConfig
        
        config = AppConfig(
            notion=NotionConfig(api_token="test_token", database_id="test_db"),
            obsidian=ObsidianConfig(vault_path="/test/vault", subfolder="notes")
        )
        
        output_path = os.path.join(self.temp_dir, ".env")
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            self.config_loader.export_config_to_env(config, output_path)
        
        assert os.path.exists(output_path)
        
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "NOTION_API_TOKEN=test_token" in content
            assert "NOTION_DATABASE_ID=test_db" in content
            assert "OBSIDIAN_VAULT_PATH=/test/vault" in content
            assert "OBSIDIAN_SUBFOLDER=notes" in content
"""
設定ファイル読み込み機能
YAML設定ファイルと環境変数を処理するユーティリティ
"""

import os
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from dotenv import load_dotenv

from models.config import AppConfig


class ConfigLoadError(Exception):
    """設定読み込み関連のエラー"""
    pass


class ConfigLoader:
    """設定ファイル読み込みクラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 環境変数を読み込み
        load_dotenv()
    
    def load_config(self, config_path: Optional[str] = None) -> AppConfig:
        """
        設定ファイルを読み込み
        
        Args:
            config_path: 設定ファイルのパス（Noneの場合はデフォルトパスを検索）
            
        Returns:
            AppConfigオブジェクト
        """
        try:
            # 設定ファイルパスを決定
            if config_path is None:
                config_path = self._find_config_file()
            
            if not config_path:
                raise ConfigLoadError("設定ファイルが見つかりません")
            
            self.logger.info(f"設定ファイルを読み込み: {config_path}")
            
            # YAMLファイルを読み込み
            config_dict = self._load_yaml_file(config_path)
            
            # 環境変数を展開
            config_dict = self._expand_environment_variables(config_dict)
            
            # 設定を検証
            self._validate_config_dict(config_dict)
            
            # AppConfigオブジェクトを作成
            app_config = AppConfig.from_dict(config_dict)
            
            # 追加検証
            app_config.validate()
            
            self.logger.info("設定ファイルの読み込みが完了しました")
            return app_config
            
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {str(e)}")
            raise ConfigLoadError(f"設定の読み込みに失敗しました: {str(e)}")
    
    def _find_config_file(self) -> Optional[str]:
        """
        設定ファイルを検索
        
        Returns:
            見つかった設定ファイルのパス
        """
        # 検索パスのリスト
        search_paths = [
            "config.yaml",
            "config.yml",
            ".config/notion-obsidian-sync.yaml",
            ".config/notion-obsidian-sync.yml",
            os.path.expanduser("~/.config/notion-obsidian-sync/config.yaml"),
            os.path.expanduser("~/.notion-obsidian-sync.yaml"),
            "/etc/notion-obsidian-sync/config.yaml"
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                self.logger.debug(f"設定ファイルを発見: {path}")
                return path
        
        return None
    
    def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """
        YAMLファイルを読み込み
        
        Args:
            file_path: YAMLファイルのパス
            
        Returns:
            読み込まれた設定辞書
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
            
            if not isinstance(config_dict, dict):
                raise ConfigLoadError("設定ファイルの形式が正しくありません（辞書である必要があります）")
            
            return config_dict
            
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"YAML解析エラー: {str(e)}")
        except FileNotFoundError:
            raise ConfigLoadError(f"設定ファイルが見つかりません: {file_path}")
        except PermissionError:
            raise ConfigLoadError(f"設定ファイルの読み取り権限がありません: {file_path}")
        except Exception as e:
            raise ConfigLoadError(f"設定ファイル読み込みエラー: {str(e)}")
    
    def _expand_environment_variables(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        設定内の環境変数を展開
        
        Args:
            config_dict: 設定辞書
            
        Returns:
            環境変数が展開された設定辞書
        """
        def expand_value(value):
            if isinstance(value, str):
                return self._expand_env_vars_in_string(value)
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(item) for item in value]
            else:
                return value
        
        return expand_value(config_dict)
    
    def _expand_env_vars_in_string(self, text: str) -> str:
        """
        文字列内の環境変数を展開
        
        Args:
            text: 展開対象の文字列
            
        Returns:
            環境変数が展開された文字列
        """
        # ${VAR_NAME} 形式の環境変数を展開
        def replace_env_var(match):
            var_name = match.group(1)
            env_value = os.getenv(var_name)
            
            if env_value is None:
                self.logger.warning(f"環境変数が設定されていません: {var_name}")
                return match.group(0)  # 元の文字列を返す
            
            return env_value
        
        # ${VAR_NAME} パターンを検索して置換
        pattern = r'\$\{([^}]+)\}'
        expanded_text = re.sub(pattern, replace_env_var, text)
        
        return expanded_text
    
    def _validate_config_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        設定辞書の基本検証
        
        Args:
            config_dict: 検証する設定辞書
        """
        required_sections = ['notion', 'obsidian']
        
        for section in required_sections:
            if section not in config_dict:
                raise ConfigLoadError(f"必須セクションが見つかりません: {section}")
        
        # Notion設定の検証
        notion_config = config_dict['notion']
        if not isinstance(notion_config, dict):
            raise ConfigLoadError("notion設定は辞書である必要があります")
        
        required_notion_fields = ['api_token', 'database_id']
        for field in required_notion_fields:
            if field not in notion_config or not notion_config[field]:
                raise ConfigLoadError(f"Notion設定の必須フィールドが見つかりません: {field}")
        
        # Obsidian設定の検証
        obsidian_config = config_dict['obsidian']
        if not isinstance(obsidian_config, dict):
            raise ConfigLoadError("obsidian設定は辞書である必要があります")
        
        if 'vault_path' not in obsidian_config or not obsidian_config['vault_path']:
            raise ConfigLoadError("Obsidian設定のvault_pathが必要です")
    
    def create_default_config(self, output_path: str = "config.yaml") -> None:
        """
        デフォルト設定ファイルを作成
        
        Args:
            output_path: 出力先パス
        """
        default_config = {
            'notion': {
                'api_token': '${NOTION_API_TOKEN}',
                'database_id': 'your-database-id-here'
            },
            'obsidian': {
                'vault_path': '/path/to/your/obsidian/vault',
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
                'level': 'INFO',
                'file': 'sync.log'
            }
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            self.logger.info(f"デフォルト設定ファイルを作成しました: {output_path}")
            
        except Exception as e:
            raise ConfigLoadError(f"デフォルト設定ファイルの作成に失敗しました: {str(e)}")
    
    def validate_config_file(self, config_path: str) -> Dict[str, Any]:
        """
        設定ファイルを検証（読み込まずに）
        
        Args:
            config_path: 設定ファイルのパス
            
        Returns:
            検証結果の辞書
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "missing_env_vars": []
        }
        
        try:
            # ファイルの存在確認
            if not os.path.exists(config_path):
                validation_result["errors"].append(f"設定ファイルが存在しません: {config_path}")
                validation_result["is_valid"] = False
                return validation_result
            
            # YAML構文チェック
            try:
                config_dict = self._load_yaml_file(config_path)
            except ConfigLoadError as e:
                validation_result["errors"].append(str(e))
                validation_result["is_valid"] = False
                return validation_result
            
            # 基本構造チェック
            try:
                self._validate_config_dict(config_dict)
            except ConfigLoadError as e:
                validation_result["errors"].append(str(e))
                validation_result["is_valid"] = False
            
            # 環境変数チェック
            missing_vars = self._check_environment_variables(config_dict)
            if missing_vars:
                validation_result["missing_env_vars"] = missing_vars
                validation_result["warnings"].append(f"未設定の環境変数: {', '.join(missing_vars)}")
            
            # パス存在チェック
            obsidian_path = config_dict.get('obsidian', {}).get('vault_path')
            if obsidian_path and not obsidian_path.startswith('${'):
                if not os.path.exists(obsidian_path):
                    validation_result["warnings"].append(f"Obsidianボルトパスが存在しません: {obsidian_path}")
            
            return validation_result
            
        except Exception as e:
            validation_result["errors"].append(f"検証中にエラーが発生しました: {str(e)}")
            validation_result["is_valid"] = False
            return validation_result
    
    def _check_environment_variables(self, config_dict: Dict[str, Any]) -> List[str]:
        """
        設定で使用されている環境変数をチェック
        
        Args:
            config_dict: 設定辞書
            
        Returns:
            未設定の環境変数のリスト
        """
        missing_vars = []
        
        def check_value(value):
            if isinstance(value, str):
                # ${VAR_NAME} パターンを検索
                pattern = r'\$\{([^}]+)\}'
                matches = re.findall(pattern, value)
                for var_name in matches:
                    if os.getenv(var_name) is None:
                        missing_vars.append(var_name)
            elif isinstance(value, dict):
                for v in value.values():
                    check_value(v)
            elif isinstance(value, list):
                for item in value:
                    check_value(item)
        
        check_value(config_dict)
        return list(set(missing_vars))  # 重複を除去
    
    def get_config_template(self) -> str:
        """
        設定ファイルのテンプレートを取得
        
        Returns:
            設定テンプレート文字列
        """
        template = """# Notion-Obsidian同期設定ファイル
# このファイルをコピーして、あなたの設定に合わせてカスタマイズしてください

notion:
  # あなたのNotion統合APIトークン
  # こちらから取得: https://www.notion.so/my-integrations
  api_token: ${NOTION_API_TOKEN}
  
  # 同期元のNotionデータベースのID
  # データベースURLから抽出: https://notion.so/your-workspace/DATABASE_ID?v=...
  database_id: "your-database-id-here"

obsidian:
  # Obsidianボルトディレクトリへのパス
  vault_path: "/path/to/your/obsidian/vault"
  
  # オプション: ボルト内の同期先サブフォルダ
  # 空にするとボルトルートに同期
  subfolder: "notion-sync"

sync:
  # 生成されるMarkdownファイルの命名パターン
  # 利用可能な変数: {title}, {id}, {date}
  file_naming: "{title}"
  
  # NotionページプロパティをYAMLフロントマターとして含めるかどうか
  include_properties: true
  
  # 同じ名前の既存ファイルを上書きするかどうか
  overwrite_existing: true
  
  # 各バッチで処理するページ数
  batch_size: 10
  
  # Notionの制限を処理するための変換設定
  conversion:
    # データベースブロックの処理方法: "table", "description", "skip"
    database_mode: "table"
    
    # カラムレイアウトの処理方法: "merge", "separator", "warning_only"
    column_layout: "separator"
    
    # サポートされていないブロックの処理方法: "skip", "placeholder", "warning"
    unsupported_blocks: "placeholder"
    
    # 変換品質レベル: "strict", "standard", "lenient"
    quality_level: "standard"

# ログ設定
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "sync.log"  # オプション: ファイルにログ出力

# 環境変数の例:
# NOTION_API_TOKEN=your_notion_api_token_here
"""
        return template
    
    def export_config_to_env(self, config: AppConfig, output_path: str = ".env") -> None:
        """
        設定を環境変数ファイルにエクスポート
        
        Args:
            config: AppConfigオブジェクト
            output_path: 出力先パス
        """
        try:
            env_lines = [
                "# Notion-Obsidian同期 環境変数設定",
                f"NOTION_API_TOKEN={config.notion.api_token}",
                f"NOTION_DATABASE_ID={config.notion.database_id}",
                f"OBSIDIAN_VAULT_PATH={config.obsidian.vault_path}",
                ""
            ]
            
            if config.obsidian.subfolder:
                env_lines.insert(-1, f"OBSIDIAN_SUBFOLDER={config.obsidian.subfolder}")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(env_lines))
            
            self.logger.info(f"環境変数ファイルを作成しました: {output_path}")
            
        except Exception as e:
            raise ConfigLoadError(f"環境変数ファイルの作成に失敗しました: {str(e)}")
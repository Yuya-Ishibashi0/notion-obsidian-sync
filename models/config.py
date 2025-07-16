"""
設定データモデル
Notion-Obsidian同期システムの設定を管理するためのデータクラス
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import os
from pathlib import Path


@dataclass
class NotionConfig:
    """Notion API設定"""
    api_token: str
    database_id: str
    
    def __post_init__(self):
        """設定値の検証"""
        if not self.api_token:
            raise ValueError("Notion APIトークンが必要です")
        if not self.database_id:
            raise ValueError("NotionデータベースIDが必要です")


@dataclass
class ObsidianConfig:
    """Obsidian設定"""
    vault_path: str
    subfolder: Optional[str] = None
    
    def __post_init__(self):
        """設定値の検証"""
        if not self.vault_path:
            raise ValueError("Obsidianボルトパスが必要です")
        
        # パスの存在確認
        vault_path = Path(self.vault_path)
        if not vault_path.exists():
            raise ValueError(f"Obsidianボルトパスが存在しません: {self.vault_path}")
        if not vault_path.is_dir():
            raise ValueError(f"Obsidianボルトパスはディレクトリである必要があります: {self.vault_path}")
    
    @property
    def full_sync_path(self) -> str:
        """同期先の完全パスを取得"""
        if self.subfolder:
            return str(Path(self.vault_path) / self.subfolder)
        return self.vault_path


@dataclass
class ConversionConfig:
    """変換設定"""
    database_mode: str = "table"  # "table", "description", "skip"
    column_layout: str = "separator"  # "merge", "separator", "warning_only"
    unsupported_blocks: str = "placeholder"  # "skip", "placeholder", "warning"
    quality_level: str = "standard"  # "strict", "standard", "lenient"
    
    # 詳細設定
    max_file_size_mb: float = 10.0  # 最大ファイルサイズ（MB）
    max_line_length: int = 1000  # 最大行長
    preserve_formatting: bool = True  # フォーマット保持
    convert_equations: bool = True  # 数式変換
    convert_tables: bool = True  # テーブル変換
    convert_images: bool = True  # 画像変換
    convert_videos: bool = False  # 動画変換（デフォルトはリンクのみ）
    convert_files: bool = True  # ファイル変換
    
    # ブロック別設定
    block_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """設定値の検証"""
        valid_database_modes = ["table", "description", "skip"]
        if self.database_mode not in valid_database_modes:
            raise ValueError(f"無効なdatabase_mode: {self.database_mode}. 有効な値: {valid_database_modes}")
        
        valid_column_layouts = ["merge", "separator", "warning_only"]
        if self.column_layout not in valid_column_layouts:
            raise ValueError(f"無効なcolumn_layout: {self.column_layout}. 有効な値: {valid_column_layouts}")
        
        valid_unsupported_blocks = ["skip", "placeholder", "warning"]
        if self.unsupported_blocks not in valid_unsupported_blocks:
            raise ValueError(f"無効なunsupported_blocks: {self.unsupported_blocks}. 有効な値: {valid_unsupported_blocks}")
        
        valid_quality_levels = ["strict", "standard", "lenient"]
        if self.quality_level not in valid_quality_levels:
            raise ValueError(f"無効なquality_level: {self.quality_level}. 有効な値: {valid_quality_levels}")
        
        # 数値範囲の検証
        if self.max_file_size_mb <= 0 or self.max_file_size_mb > 100:
            raise ValueError("max_file_size_mbは0より大きく100以下である必要があります")
        
        if self.max_line_length <= 0 or self.max_line_length > 10000:
            raise ValueError("max_line_lengthは0より大きく10000以下である必要があります")
        
        # デフォルトブロック設定を初期化
        if not self.block_settings:
            self.block_settings = self._get_default_block_settings()
    
    def _get_default_block_settings(self) -> Dict[str, Dict[str, Any]]:
        """デフォルトブロック設定を取得"""
        return {
            "callout": {
                "convert_icon": True,
                "use_quote_format": True,
                "preserve_color": False
            },
            "toggle": {
                "use_details_tag": True,
                "expand_by_default": False
            },
            "table": {
                "max_columns": 10,
                "max_rows": 100,
                "escape_pipes": True
            },
            "code": {
                "preserve_language": True,
                "add_line_numbers": False
            },
            "equation": {
                "use_latex": True,
                "inline_format": "${}$",
                "block_format": "$$\n{}\n$$"
            },
            "image": {
                "download_images": False,
                "max_width": None,
                "alt_text_from_caption": True
            },
            "video": {
                "embed_videos": False,
                "show_thumbnail": False
            },
            "bookmark": {
                "show_preview": False,
                "use_title_as_text": True
            }
        }
    
    def get_block_setting(self, block_type: str, setting_key: str, default=None):
        """特定ブロックタイプの設定値を取得"""
        return self.block_settings.get(block_type, {}).get(setting_key, default)
    
    def set_block_setting(self, block_type: str, setting_key: str, value: Any):
        """特定ブロックタイプの設定値を設定"""
        if block_type not in self.block_settings:
            self.block_settings[block_type] = {}
        self.block_settings[block_type][setting_key] = value
    
    def get_supported_block_types(self) -> List[str]:
        """サポートされているブロックタイプのリストを取得"""
        return [
            "paragraph", "heading_1", "heading_2", "heading_3",
            "bulleted_list_item", "numbered_list_item", "to_do",
            "toggle", "code", "quote", "callout", "divider",
            "image", "video", "file", "bookmark", "equation",
            "table", "table_row", "column_list", "column"
        ]
    
    def get_unsupported_block_types(self) -> List[str]:
        """サポートされていないブロックタイプのリストを取得"""
        return [
            "child_database", "link_to_page", "table_of_contents",
            "breadcrumb", "child_page", "embed", "link_preview",
            "synced_block", "template", "pdf"
        ]
    
    def should_convert_block(self, block_type: str) -> bool:
        """指定されたブロックタイプを変換すべきかどうか"""
        if block_type in self.get_supported_block_types():
            return True
        
        if block_type in self.get_unsupported_block_types():
            return self.unsupported_blocks != "skip"
        
        # 未知のブロックタイプ
        return self.quality_level != "strict"
    
    def get_conversion_strategy(self, block_type: str) -> str:
        """ブロックタイプの変換戦略を取得"""
        if block_type in self.get_supported_block_types():
            return "convert"
        
        if block_type in self.get_unsupported_block_types():
            if self.unsupported_blocks == "skip":
                return "skip"
            elif self.unsupported_blocks == "placeholder":
                return "placeholder"
            else:  # warning
                return "warning"
        
        # 未知のブロックタイプ
        if self.quality_level == "strict":
            return "error"
        elif self.quality_level == "standard":
            return "placeholder"
        else:  # lenient
            return "skip"
    
    def validate_file_constraints(self, file_size_bytes: int, line_count: int, max_line_length: int) -> List[str]:
        """ファイル制約の検証"""
        warnings = []
        
        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            warnings.append(f"ファイルサイズが制限を超えています: {file_size_mb:.1f}MB > {self.max_file_size_mb}MB")
        
        if max_line_length > self.max_line_length:
            warnings.append(f"行長が制限を超えています: {max_line_length} > {self.max_line_length}")
        
        if self.quality_level == "strict":
            if line_count > 1000:
                warnings.append(f"行数が多すぎます: {line_count}行")
        
        return warnings
    
    def get_quality_settings(self) -> Dict[str, Any]:
        """品質レベルに応じた設定を取得"""
        if self.quality_level == "strict":
            return {
                "allow_large_files": False,
                "allow_long_lines": False,
                "require_all_blocks_supported": True,
                "validate_markdown_syntax": True,
                "preserve_all_formatting": True
            }
        elif self.quality_level == "standard":
            return {
                "allow_large_files": True,
                "allow_long_lines": True,
                "require_all_blocks_supported": False,
                "validate_markdown_syntax": False,
                "preserve_all_formatting": True
            }
        else:  # lenient
            return {
                "allow_large_files": True,
                "allow_long_lines": True,
                "require_all_blocks_supported": False,
                "validate_markdown_syntax": False,
                "preserve_all_formatting": False
            }


@dataclass
class SyncConfig:
    """同期設定"""
    file_naming: str = "{title}"
    include_properties: bool = True
    overwrite_existing: bool = True
    batch_size: int = 10
    conversion: ConversionConfig = field(default_factory=ConversionConfig)
    
    def __post_init__(self):
        """設定値の検証"""
        if self.batch_size <= 0:
            raise ValueError("batch_sizeは正の整数である必要があります")
        if self.batch_size > 100:
            raise ValueError("batch_sizeは100以下である必要があります（APIレート制限のため）")


@dataclass
class LoggingConfig:
    """ログ設定"""
    level: str = "INFO"
    file: Optional[str] = None
    
    def __post_init__(self):
        """設定値の検証"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if self.level not in valid_levels:
            raise ValueError(f"無効なログレベル: {self.level}. 有効な値: {valid_levels}")


@dataclass
class AppConfig:
    """アプリケーション全体の設定"""
    notion: NotionConfig
    obsidian: ObsidianConfig
    sync: SyncConfig = field(default_factory=SyncConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AppConfig':
        """辞書から設定オブジェクトを作成"""
        notion_config = NotionConfig(**config_dict['notion'])
        obsidian_config = ObsidianConfig(**config_dict['obsidian'])
        
        sync_data = config_dict.get('sync', {})
        conversion_data = sync_data.pop('conversion', {})
        conversion_config = ConversionConfig(**conversion_data)
        sync_config = SyncConfig(conversion=conversion_config, **sync_data)
        
        logging_config = LoggingConfig(**config_dict.get('logging', {}))
        
        return cls(
            notion=notion_config,
            obsidian=obsidian_config,
            sync=sync_config,
            logging=logging_config
        )
    
    def validate(self) -> None:
        """全体的な設定の検証"""
        # 各コンポーネントの__post_init__で個別検証は実行済み
        # ここでは相互依存関係の検証を行う
        
        # 同期先ディレクトリの作成可能性チェック
        sync_path = Path(self.obsidian.full_sync_path)
        if not sync_path.parent.exists():
            raise ValueError(f"同期先の親ディレクトリが存在しません: {sync_path.parent}")
        
        # ログファイルの書き込み可能性チェック
        if self.logging.file:
            log_path = Path(self.logging.file)
            if log_path.parent.exists() and not os.access(log_path.parent, os.W_OK):
                raise ValueError(f"ログファイルの親ディレクトリに書き込み権限がありません: {log_path.parent}")
    
    def validate_comprehensive(self) -> Dict[str, Any]:
        """包括的な設定検証"""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "info": [],
            "checks": {
                "notion_config": False,
                "obsidian_config": False,
                "sync_config": False,
                "logging_config": False,
                "file_permissions": False,
                "disk_space": False,
                "network_connectivity": False
            }
        }
        
        try:
            # 基本検証
            self.validate()
            
            # Notion設定の詳細検証
            notion_validation = self._validate_notion_config()
            validation_result["checks"]["notion_config"] = notion_validation["is_valid"]
            validation_result["errors"].extend(notion_validation["errors"])
            validation_result["warnings"].extend(notion_validation["warnings"])
            
            # Obsidian設定の詳細検証
            obsidian_validation = self._validate_obsidian_config()
            validation_result["checks"]["obsidian_config"] = obsidian_validation["is_valid"]
            validation_result["errors"].extend(obsidian_validation["errors"])
            validation_result["warnings"].extend(obsidian_validation["warnings"])
            
            # 同期設定の詳細検証
            sync_validation = self._validate_sync_config()
            validation_result["checks"]["sync_config"] = sync_validation["is_valid"]
            validation_result["errors"].extend(sync_validation["errors"])
            validation_result["warnings"].extend(sync_validation["warnings"])
            
            # ログ設定の詳細検証
            logging_validation = self._validate_logging_config()
            validation_result["checks"]["logging_config"] = logging_validation["is_valid"]
            validation_result["errors"].extend(logging_validation["errors"])
            validation_result["warnings"].extend(logging_validation["warnings"])
            
            # ファイル権限チェック
            permission_validation = self._validate_file_permissions()
            validation_result["checks"]["file_permissions"] = permission_validation["is_valid"]
            validation_result["errors"].extend(permission_validation["errors"])
            validation_result["warnings"].extend(permission_validation["warnings"])
            
            # ディスク容量チェック
            disk_validation = self._validate_disk_space()
            validation_result["checks"]["disk_space"] = disk_validation["is_valid"]
            validation_result["warnings"].extend(disk_validation["warnings"])
            validation_result["info"].extend(disk_validation["info"])
            
            # 総合判定
            validation_result["is_valid"] = len(validation_result["errors"]) == 0
            
            return validation_result
            
        except Exception as e:
            validation_result["errors"].append(f"検証中にエラーが発生しました: {str(e)}")
            validation_result["is_valid"] = False
            return validation_result
    
    def _validate_notion_config(self) -> Dict[str, Any]:
        """Notion設定の詳細検証"""
        result = {"is_valid": True, "errors": [], "warnings": []}
        
        # APIトークンの形式チェック
        if not self.notion.api_token.startswith("secret_"):
            result["warnings"].append("Notion APIトークンが正しい形式ではない可能性があります")
        
        # データベースIDの形式チェック
        if len(self.notion.database_id.replace("-", "")) != 32:
            result["warnings"].append("NotionデータベースIDが正しい形式ではない可能性があります")
        
        return result
    
    def _validate_obsidian_config(self) -> Dict[str, Any]:
        """Obsidian設定の詳細検証"""
        result = {"is_valid": True, "errors": [], "warnings": []}
        
        vault_path = Path(self.obsidian.vault_path)
        
        # ボルトディレクトリの存在確認
        if not vault_path.exists():
            result["errors"].append(f"Obsidianボルトディレクトリが存在しません: {vault_path}")
            result["is_valid"] = False
            return result
        
        # .obsidianディレクトリの確認
        obsidian_dir = vault_path / ".obsidian"
        if not obsidian_dir.exists():
            result["warnings"].append("Obsidian設定ディレクトリ(.obsidian)が見つかりません")
        
        # 同期先ディレクトリの確認
        sync_path = Path(self.obsidian.full_sync_path)
        if not sync_path.exists():
            try:
                sync_path.mkdir(parents=True, exist_ok=True)
                result["warnings"].append(f"同期先ディレクトリを作成しました: {sync_path}")
            except Exception as e:
                result["errors"].append(f"同期先ディレクトリの作成に失敗しました: {str(e)}")
                result["is_valid"] = False
        
        return result
    
    def _validate_sync_config(self) -> Dict[str, Any]:
        """同期設定の詳細検証"""
        result = {"is_valid": True, "errors": [], "warnings": []}
        
        # ファイル命名パターンの検証
        try:
            test_vars = {"title": "テスト", "id": "test123", "date": "2023-01-01"}
            test_filename = self.sync.file_naming.format(**test_vars)
            
            # 危険な文字のチェック
            dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
            if any(char in test_filename for char in dangerous_chars):
                result["warnings"].append("ファイル命名パターンに危険な文字が含まれる可能性があります")
                
        except KeyError as e:
            result["errors"].append(f"ファイル命名パターンに無効な変数があります: {str(e)}")
            result["is_valid"] = False
        except Exception as e:
            result["errors"].append(f"ファイル命名パターンの検証エラー: {str(e)}")
            result["is_valid"] = False
        
        # バッチサイズの妥当性チェック
        if self.sync.batch_size > 50:
            result["warnings"].append("バッチサイズが大きすぎる可能性があります（APIレート制限に注意）")
        
        # 変換設定の検証
        conversion_validation = self._validate_conversion_config()
        result["errors"].extend(conversion_validation["errors"])
        result["warnings"].extend(conversion_validation["warnings"])
        if not conversion_validation["is_valid"]:
            result["is_valid"] = False
        
        return result
    
    def _validate_conversion_config(self) -> Dict[str, Any]:
        """変換設定の詳細検証"""
        result = {"is_valid": True, "errors": [], "warnings": []}
        
        # 品質レベルと他の設定の整合性チェック
        if self.sync.conversion.quality_level == "strict":
            if self.sync.conversion.unsupported_blocks != "warning":
                result["warnings"].append("厳密モードではunsupported_blocksを'warning'に設定することを推奨します")
        
        # ファイルサイズ制限の妥当性
        if self.sync.conversion.max_file_size_mb < 1:
            result["warnings"].append("最大ファイルサイズが小さすぎる可能性があります")
        elif self.sync.conversion.max_file_size_mb > 50:
            result["warnings"].append("最大ファイルサイズが大きすぎる可能性があります")
        
        return result
    
    def _validate_logging_config(self) -> Dict[str, Any]:
        """ログ設定の詳細検証"""
        result = {"is_valid": True, "errors": [], "warnings": []}
        
        # ログファイルの書き込み権限チェック
        if self.logging.file:
            log_path = Path(self.logging.file)
            
            # 親ディレクトリの存在確認
            if not log_path.parent.exists():
                try:
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    result["warnings"].append(f"ログディレクトリを作成しました: {log_path.parent}")
                except Exception as e:
                    result["errors"].append(f"ログディレクトリの作成に失敗しました: {str(e)}")
                    result["is_valid"] = False
            
            # 書き込み権限チェック
            elif not os.access(log_path.parent, os.W_OK):
                result["errors"].append(f"ログディレクトリに書き込み権限がありません: {log_path.parent}")
                result["is_valid"] = False
        
        return result
    
    def _validate_file_permissions(self) -> Dict[str, Any]:
        """ファイル権限の検証"""
        result = {"is_valid": True, "errors": [], "warnings": []}
        
        # Obsidianボルトの読み書き権限
        vault_path = Path(self.obsidian.vault_path)
        if vault_path.exists():
            if not os.access(vault_path, os.R_OK):
                result["errors"].append(f"Obsidianボルトに読み取り権限がありません: {vault_path}")
                result["is_valid"] = False
            
            if not os.access(vault_path, os.W_OK):
                result["errors"].append(f"Obsidianボルトに書き込み権限がありません: {vault_path}")
                result["is_valid"] = False
        
        # 同期先ディレクトリの権限
        sync_path = Path(self.obsidian.full_sync_path)
        if sync_path.exists():
            if not os.access(sync_path, os.W_OK):
                result["errors"].append(f"同期先ディレクトリに書き込み権限がありません: {sync_path}")
                result["is_valid"] = False
        
        return result
    
    def _validate_disk_space(self) -> Dict[str, Any]:
        """ディスク容量の検証"""
        result = {"is_valid": True, "errors": [], "warnings": [], "info": []}
        
        try:
            import shutil
            
            # Obsidianボルトのディスク使用量
            vault_path = Path(self.obsidian.vault_path)
            if vault_path.exists():
                total, used, free = shutil.disk_usage(vault_path)
                
                free_gb = free / (1024**3)
                total_gb = total / (1024**3)
                
                result["info"].append(f"利用可能ディスク容量: {free_gb:.1f}GB / {total_gb:.1f}GB")
                
                # 警告レベルのチェック
                if free_gb < 1:
                    result["warnings"].append("ディスク容量が不足しています（1GB未満）")
                elif free_gb < 5:
                    result["warnings"].append("ディスク容量が少なくなっています（5GB未満）")
                
        except Exception as e:
            result["warnings"].append(f"ディスク容量の確認に失敗しました: {str(e)}")
        
        return result
    
    def get_validation_summary(self) -> str:
        """検証結果のサマリーを取得"""
        validation = self.validate_comprehensive()
        
        lines = ["# 設定検証レポート\n"]
        
        # 総合結果
        status = "✅ 正常" if validation["is_valid"] else "❌ エラーあり"
        lines.append(f"## 総合結果: {status}\n")
        
        # チェック項目
        lines.append("## チェック項目")
        for check_name, is_passed in validation["checks"].items():
            status_icon = "✅" if is_passed else "❌"
            check_name_jp = {
                "notion_config": "Notion設定",
                "obsidian_config": "Obsidian設定", 
                "sync_config": "同期設定",
                "logging_config": "ログ設定",
                "file_permissions": "ファイル権限",
                "disk_space": "ディスク容量",
                "network_connectivity": "ネットワーク接続"
            }.get(check_name, check_name)
            lines.append(f"- {status_icon} {check_name_jp}")
        lines.append("")
        
        # エラー
        if validation["errors"]:
            lines.append("## ❌ エラー")
            for i, error in enumerate(validation["errors"], 1):
                lines.append(f"{i}. {error}")
            lines.append("")
        
        # 警告
        if validation["warnings"]:
            lines.append("## ⚠️ 警告")
            for i, warning in enumerate(validation["warnings"], 1):
                lines.append(f"{i}. {warning}")
            lines.append("")
        
        # 情報
        if validation["info"]:
            lines.append("## ℹ️ 情報")
            for i, info in enumerate(validation["info"], 1):
                lines.append(f"{i}. {info}")
            lines.append("")
        
        # 推奨アクション
        lines.append("## 推奨アクション")
        if validation["errors"]:
            lines.append("- エラーを修正してから同期を実行してください")
        if len(validation["warnings"]) > 3:
            lines.append("- 多数の警告があります。設定を見直すことを推奨します")
        if not validation["errors"] and not validation["warnings"]:
            lines.append("- 設定に問題はありません。同期を実行できます")
        
        return "\n".join(lines)
"""
データ変換プロセッサー（更新版）
NotionデータをMarkdown形式に変換するためのプロセッサー
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.notion import (
    NotionPage, NotionPageContent, NotionBlock, NotionProperty, 
    NotionRichText, NotionBlockType
)
from models.markdown import MarkdownFile, MarkdownConversionResult
from models.config import ConversionConfig
from services.advanced_block_converter import AdvancedBlockConverter


class DataProcessor:
    """データ変換プロセッサー"""
    
    def __init__(self, conversion_config: ConversionConfig):
        """
        初期化
        
        Args:
            conversion_config: 変換設定
        """
        self.config = conversion_config
        self.logger = logging.getLogger(__name__)
        self.block_converter = AdvancedBlockConverter(conversion_config)
    
    def extract_properties(self, page: NotionPage) -> Dict[str, Any]:
        """
        Notionページからプロパティを抽出
        
        Args:
            page: NotionPageオブジェクト
            
        Returns:
            プロパティの辞書
        """
        properties = {}
        
        try:
            for prop_name, prop in page.properties.items():
                extracted_value = self._extract_single_property(prop)
                if extracted_value is not None:
                    properties[prop_name] = extracted_value
            
            self.logger.debug(f"プロパティ抽出完了: {len(properties)}個")
            return properties
            
        except Exception as e:
            self.logger.error(f"プロパティ抽出エラー: {str(e)}")
            return {}
    
    def _extract_single_property(self, prop: NotionProperty) -> Any:
        """
        単一プロパティの値を抽出
        
        Args:
            prop: NotionPropertyオブジェクト
            
        Returns:
            抽出された値
        """
        try:
            if prop.type == "title":
                return self._extract_title_property(prop.value)
            elif prop.type == "rich_text":
                return self._extract_rich_text_property(prop.value)
            elif prop.type == "select":
                return self._extract_select_property(prop.value)
            elif prop.type == "multi_select":
                return self._extract_multi_select_property(prop.value)
            elif prop.type == "date":
                return self._extract_date_property(prop.value)
            elif prop.type == "people":
                return self._extract_people_property(prop.value)
            elif prop.type == "files":
                return self._extract_files_property(prop.value)
            elif prop.type == "checkbox":
                return self._extract_checkbox_property(prop.value)
            elif prop.type == "url":
                return self._extract_url_property(prop.value)
            elif prop.type == "email":
                return self._extract_email_property(prop.value)
            elif prop.type == "phone_number":
                return self._extract_phone_property(prop.value)
            elif prop.type == "number":
                return self._extract_number_property(prop.value)
            elif prop.type == "formula":
                return self._extract_formula_property(prop.value)
            elif prop.type == "relation":
                return self._extract_relation_property(prop.value)
            elif prop.type == "rollup":
                return self._extract_rollup_property(prop.value)
            elif prop.type in ["created_time", "last_edited_time"]:
                return self._extract_timestamp_property(prop.value)
            elif prop.type in ["created_by", "last_edited_by"]:
                return self._extract_user_property(prop.value)
            elif prop.type == "status":
                return self._extract_status_property(prop.value)
            else:
                self.logger.warning(f"未対応のプロパティタイプ: {prop.type}")
                return str(prop.value) if prop.value is not None else None
                
        except Exception as e:
            self.logger.error(f"プロパティ抽出エラー ({prop.type}): {str(e)}")
            return None
    
    def _extract_title_property(self, value: List[Dict[str, Any]]) -> str:
        """タイトルプロパティの抽出"""
        if not value:
            return ""
        return "".join([item.get("plain_text", "") for item in value])
    
    def _extract_rich_text_property(self, value: List[Dict[str, Any]]) -> str:
        """リッチテキストプロパティの抽出"""
        if not value:
            return ""
        return "".join([item.get("plain_text", "") for item in value])
    
    def _extract_select_property(self, value: Optional[Dict[str, Any]]) -> Optional[str]:
        """選択プロパティの抽出"""
        if not value:
            return None
        return value.get("name")
    
    def _extract_multi_select_property(self, value: List[Dict[str, Any]]) -> List[str]:
        """複数選択プロパティの抽出"""
        if not value:
            return []
        return [item.get("name", "") for item in value if item.get("name")]
    
    def _extract_date_property(self, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        """日付プロパティの抽出"""
        if not value:
            return None
        
        result = {}
        if value.get("start"):
            result["start"] = value["start"]
        if value.get("end"):
            result["end"] = value["end"]
        if value.get("time_zone"):
            result["time_zone"] = value["time_zone"]
        
        return result if result else None
    
    def _extract_people_property(self, value: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """人物プロパティの抽出"""
        if not value:
            return []
        
        people = []
        for person in value:
            person_info = {"id": person.get("id", "")}
            if person.get("name"):
                person_info["name"] = person["name"]
            if person.get("avatar_url"):
                person_info["avatar_url"] = person["avatar_url"]
            people.append(person_info)
        
        return people
    
    def _extract_files_property(self, value: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """ファイルプロパティの抽出"""
        if not value:
            return []
        
        files = []
        for file_info in value:
            file_data = {"name": file_info.get("name", "")}
            
            if file_info.get("type") == "external":
                file_data["url"] = file_info.get("external", {}).get("url", "")
                file_data["type"] = "external"
            elif file_info.get("type") == "file":
                file_data["url"] = file_info.get("file", {}).get("url", "")
                file_data["type"] = "file"
                file_data["expiry_time"] = file_info.get("file", {}).get("expiry_time", "")
            
            files.append(file_data)
        
        return files
    
    def _extract_checkbox_property(self, value: bool) -> bool:
        """チェックボックスプロパティの抽出"""
        return bool(value)
    
    def _extract_url_property(self, value: Optional[str]) -> Optional[str]:
        """URLプロパティの抽出"""
        return value if value else None
    
    def _extract_email_property(self, value: Optional[str]) -> Optional[str]:
        """メールプロパティの抽出"""
        return value if value else None
    
    def _extract_phone_property(self, value: Optional[str]) -> Optional[str]:
        """電話番号プロパティの抽出"""
        return value if value else None
    
    def _extract_number_property(self, value: Optional[float]) -> Optional[float]:
        """数値プロパティの抽出"""
        return value if value is not None else None
    
    def _extract_formula_property(self, value: Dict[str, Any]) -> Any:
        """数式プロパティの抽出"""
        if not value:
            return None
        
        formula_type = value.get("type")
        if formula_type == "string":
            return value.get("string")
        elif formula_type == "number":
            return value.get("number")
        elif formula_type == "boolean":
            return value.get("boolean")
        elif formula_type == "date":
            return self._extract_date_property(value.get("date"))
        else:
            return str(value)
    
    def _extract_relation_property(self, value: List[Dict[str, Any]]) -> List[str]:
        """関連プロパティの抽出"""
        if not value:
            return []
        return [item.get("id", "") for item in value if item.get("id")]
    
    def _extract_rollup_property(self, value: Dict[str, Any]) -> Any:
        """ロールアッププロパティの抽出"""
        if not value:
            return None
        
        rollup_type = value.get("type")
        if rollup_type == "number":
            return value.get("number")
        elif rollup_type == "date":
            return self._extract_date_property(value.get("date"))
        elif rollup_type == "array":
            return value.get("array", [])
        else:
            return str(value)
    
    def _extract_timestamp_property(self, value: Optional[str]) -> Optional[str]:
        """タイムスタンププロパティの抽出"""
        return value if value else None
    
    def _extract_user_property(self, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        """ユーザープロパティの抽出"""
        if not value:
            return None
        
        user_info = {"id": value.get("id", "")}
        if value.get("name"):
            user_info["name"] = value["name"]
        if value.get("avatar_url"):
            user_info["avatar_url"] = value["avatar_url"]
        
        return user_info
    
    def _extract_status_property(self, value: Optional[Dict[str, Any]]) -> Optional[str]:
        """ステータスプロパティの抽出"""
        if not value:
            return None
        return value.get("name")
    
    def create_frontmatter_dict(self, page: NotionPage, 
                               include_properties: bool = True) -> Dict[str, Any]:
        """
        YAMLフロントマター用の辞書を作成
        
        Args:
            page: NotionPageオブジェクト
            include_properties: プロパティを含めるかどうか
            
        Returns:
            フロントマター辞書
        """
        frontmatter = {
            "notion_id": page.id,
            "created_time": page.created_time.isoformat() if page.created_time else None,
            "last_edited_time": page.last_edited_time.isoformat() if page.last_edited_time else None,
            "archived": page.archived
        }
        
        # URLがある場合は追加
        if page.url:
            frontmatter["notion_url"] = page.url
        
        # プロパティを含める場合
        if include_properties:
            properties = self.extract_properties(page)
            
            # タイトルプロパティは特別扱い（通常はファイル名になるため）
            for prop_name, prop_value in properties.items():
                if prop_name.lower() not in ["title", "タイトル", "名前"]:
                    frontmatter[prop_name] = prop_value
        
        # 空の値を除去
        frontmatter = {k: v for k, v in frontmatter.items() if v is not None}
        
        return frontmatter
    
    def validate_properties(self, properties: Dict[str, Any]) -> List[str]:
        """
        プロパティの検証
        
        Args:
            properties: プロパティ辞書
            
        Returns:
            警告メッセージのリスト
        """
        warnings = []
        
        for prop_name, prop_value in properties.items():
            # 長すぎるプロパティ名
            if len(prop_name) > 100:
                warnings.append(f"プロパティ名が長すぎます: {prop_name[:50]}...")
            
            # 複雑すぎるプロパティ値
            if isinstance(prop_value, (list, dict)):
                if isinstance(prop_value, list) and len(prop_value) > 50:
                    warnings.append(f"プロパティ '{prop_name}' の配列が大きすぎます: {len(prop_value)}要素")
                elif isinstance(prop_value, dict) and len(prop_value) > 20:
                    warnings.append(f"プロパティ '{prop_name}' のオブジェクトが複雑すぎます: {len(prop_value)}フィールド")
            
            # 文字列の長さチェック
            if isinstance(prop_value, str) and len(prop_value) > 1000:
                warnings.append(f"プロパティ '{prop_name}' の値が長すぎます: {len(prop_value)}文字")
        
        return warnings
    
    def convert_page_to_markdown(self, page_content: NotionPageContent, 
                                file_naming_pattern: str = "{title}",
                                include_properties: bool = True) -> MarkdownConversionResult:
        """
        NotionページをMarkdownファイルに変換
        
        Args:
            page_content: NotionPageContentオブジェクト
            file_naming_pattern: ファイル名のパターン
            include_properties: プロパティをフロントマターに含めるかどうか
            
        Returns:
            MarkdownConversionResultオブジェクト
        """
        try:
            # ファイル名を生成
            filename = self._generate_filename(page_content.page, file_naming_pattern)
            
            # フロントマターを作成
            frontmatter = self.create_frontmatter_dict(
                page_content.page, 
                include_properties=include_properties
            )
            
            # ページタイトル
            title_line = f"# {page_content.page.title}\n\n"
            
            # ブロックコンテンツを変換（高度なブロック変換機能を使用）
            blocks_content = self.block_converter.convert_blocks_to_markdown(page_content.blocks)
            
            # 完全なMarkdownコンテンツを作成
            markdown_content = title_line + blocks_content
            
            # Markdownファイルオブジェクトを作成
            markdown_file = MarkdownFile(
                filename=filename,
                frontmatter=frontmatter,
                content=markdown_content
            )
            
            # 変換結果を作成
            result = MarkdownConversionResult(markdown_file=markdown_file)
            
            # サポートされていないブロックがあれば記録
            unsupported_blocks = [block for block in page_content.blocks if not block.is_supported()]
            for unsupported_block in unsupported_blocks:
                result.add_unsupported_block(unsupported_block.type)
            
            # プロパティの検証警告
            property_warnings = self.validate_properties(frontmatter)
            for warning in property_warnings:
                result.add_warning(warning)
            
            self.logger.info(f"ページ変換完了: {page_content.page.title} -> {filename}")
            return result
            
        except Exception as e:
            self.logger.error(f"ページ変換エラー: {str(e)}")
            # エラーが発生した場合でも基本的なファイルを作成
            fallback_filename = f"error_{page_content.page.id}.md"
            fallback_content = f"# エラー\n\nページの変換中にエラーが発生しました: {str(e)}"
            
            markdown_file = MarkdownFile(
                filename=fallback_filename,
                content=fallback_content
            )
            
            result = MarkdownConversionResult(markdown_file=markdown_file)
            result.add_warning(f"ページ変換エラー: {str(e)}")
            return result
    
    def _generate_filename(self, page: NotionPage, pattern: str) -> str:
        """
        ファイル名を生成
        
        Args:
            page: NotionPageオブジェクト
            pattern: ファイル名パターン
            
        Returns:
            生成されたファイル名
        """
        try:
            # 利用可能な変数
            variables = {
                "title": page.title,
                "id": page.id,
                "date": page.created_time.strftime("%Y-%m-%d") if page.created_time else "unknown"
            }
            
            # パターンを適用
            filename = pattern.format(**variables)
            
            # ファイル名をサニタイズ
            safe_filename = MarkdownFile.sanitize_filename(filename)
            
            # 拡張子を追加
            if not safe_filename.endswith('.md'):
                safe_filename += '.md'
            
            return safe_filename
            
        except Exception as e:
            self.logger.warning(f"ファイル名生成エラー: {str(e)}")
            # フォールバック: ページIDを使用
            return f"{page.id}.md"
    
    def get_conversion_summary(self, results: List[MarkdownConversionResult]) -> Dict[str, Any]:
        """
        変換結果のサマリーを取得
        
        Args:
            results: MarkdownConversionResultオブジェクトのリスト
            
        Returns:
            サマリー辞書
        """
        total_files = len(results)
        successful_files = len([r for r in results if not r.has_issues()])
        files_with_warnings = len([r for r in results if r.warnings])
        files_with_unsupported = len([r for r in results if r.unsupported_blocks])
        
        total_size = sum([r.markdown_file.get_file_size() for r in results])
        total_words = sum([r.markdown_file.get_word_count() for r in results])
        
        # よく見つかるサポートされていないブロックタイプを集計
        unsupported_block_counts = {}
        for result in results:
            for block_type in result.unsupported_blocks:
                unsupported_block_counts[block_type] = unsupported_block_counts.get(block_type, 0) + 1
        
        most_common_unsupported = sorted(unsupported_block_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_files": total_files,
            "successful_files": successful_files,
            "files_with_warnings": files_with_warnings,
            "files_with_unsupported": files_with_unsupported,
            "success_rate": (successful_files / total_files * 100) if total_files > 0 else 0,
            "total_size_mb": total_size / (1024 * 1024),
            "total_words": total_words,
            "average_file_size": total_size / total_files if total_files > 0 else 0,
            "average_words_per_file": total_words / total_files if total_files > 0 else 0,
            "most_common_unsupported": most_common_unsupported,
            "conversion_config": {
                "database_mode": self.config.database_mode,
                "column_layout": self.config.column_layout,
                "unsupported_blocks": self.config.unsupported_blocks,
                "quality_level": self.config.quality_level
            }
        }
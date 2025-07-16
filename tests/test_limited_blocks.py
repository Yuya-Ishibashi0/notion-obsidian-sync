"""
制限のあるブロックタイプの代替表現テスト
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from services.advanced_block_converter import AdvancedBlockConverter
from models.config import ConversionConfig
from models.notion import NotionBlock


class TestLimitedBlocksConversion:
    """制限のあるブロックタイプの代替表現テスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.config = ConversionConfig()
        self.converter = AdvancedBlockConverter(self.config)
    
    def test_convert_database_block(self):
        """データベースブロックの代替表現テスト"""
        database_block = NotionBlock(
            id="test_database",
            type="child_database",
            content={
                "child_database": {
                    "title": "プロジェクト管理"
                }
            }
        )
        
        # テーブルモード
        table_config = ConversionConfig(database_mode="table")
        table_converter = AdvancedBlockConverter(table_config)
        result = table_converter._convert_database_block(database_block)
        assert "📊 プロジェクト管理" in result
        assert "| 項目 | 値 |" in result
        
        # 説明モード
        desc_config = ConversionConfig(database_mode="description")
        desc_converter = AdvancedBlockConverter(desc_config)
        result = desc_converter._convert_database_block(database_block)
        assert "📊 **データベース: プロジェクト管理**" in result
        
        # スキップモード
        skip_config = ConversionConfig(database_mode="skip")
        skip_converter = AdvancedBlockConverter(skip_config)
        result = skip_converter._convert_database_block(database_block)
        assert result is None
    
    def test_convert_column_layout_blocks(self):
        """カラムレイアウトブロックの代替表現テスト"""
        column_list_block = NotionBlock(
            id="test_column_list",
            type="column_list",
            content={}
        )
        
        column_block = NotionBlock(
            id="test_column",
            type="column",
            content={}
        )
        
        # セパレーターモード
        sep_config = ConversionConfig(column_layout="separator")
        sep_converter = AdvancedBlockConverter(sep_config)
        
        list_result = sep_converter._convert_column_list_block(column_list_block)
        assert "📋 カラムレイアウト開始" in list_result
        assert "---" in list_result
        
        col_result = sep_converter._convert_column_block(column_block)
        assert "📄 カラム" in col_result
        
        # マージモード
        merge_config = ConversionConfig(column_layout="merge")
        merge_converter = AdvancedBlockConverter(merge_config)
        
        list_result = merge_converter._convert_column_list_block(column_list_block)
        assert list_result == ""
        
        col_result = merge_converter._convert_column_block(column_block)
        assert col_result == ""
        
        # 警告のみモード
        warn_config = ConversionConfig(column_layout="warning_only")
        warn_converter = AdvancedBlockConverter(warn_config)
        
        list_result = warn_converter._convert_column_list_block(column_list_block)
        assert "カラムレイアウトが検出されました" in list_result
    
    def test_convert_synced_block(self):
        """同期ブロックの代替表現テスト"""
        # オリジナル同期ブロック
        original_synced_block = NotionBlock(
            id="test_synced_original",
            type="synced_block",
            content={
                "synced_block": {}
            }
        )
        
        result = self.converter._convert_synced_block(original_synced_block)
        assert "🔄 **同期ブロック（オリジナル）**" in result
        assert "他の場所で参照される可能性があります" in result
        
        # 参照同期ブロック
        referenced_synced_block = NotionBlock(
            id="test_synced_ref",
            type="synced_block",
            content={
                "synced_block": {
                    "synced_from": {
                        "block_id": "abc123"
                    }
                }
            }
        )
        
        result = self.converter._convert_synced_block(referenced_synced_block)
        assert "🔄 **同期ブロック**" in result
        assert "他の場所から同期されています" in result
        assert "abc123" in result
    
    def test_convert_template_block(self):
        """テンプレートブロックの代替表現テスト"""
        template_block = NotionBlock(
            id="test_template",
            type="template",
            content={
                "template": {
                    "rich_text": [{"plain_text": "会議議事録テンプレート", "annotations": {}}]
                }
            }
        )
        
        result = self.converter._convert_template_block(template_block)
        assert "📋 **テンプレート: 会議議事録テンプレート**" in result
        assert "動的にコンテンツが生成されます" in result
    
    def test_convert_link_to_page_block(self):
        """ページリンクブロックの代替表現テスト"""
        link_block = NotionBlock(
            id="test_link",
            type="link_to_page",
            content={
                "link_to_page": {
                    "type": "page_id",
                    "page_id": "abc123-def456-ghi789"
                }
            }
        )
        
        result = self.converter._convert_link_to_page_block(link_block)
        assert "🔗 **[ページリンク]" in result
        assert "https://notion.so/abc123def456ghi789" in result
    
    def test_convert_table_of_contents_block(self):
        """目次ブロックの代替表現テスト"""
        toc_block = NotionBlock(
            id="test_toc",
            type="table_of_contents",
            content={
                "table_of_contents": {
                    "color": "default"
                }
            }
        )
        
        result = self.converter._convert_table_of_contents_block(toc_block)
        assert "📑 **目次**" in result
        assert "この位置にページの目次が表示されます" in result
    
    def test_convert_breadcrumb_block(self):
        """パンくずリストブロックの代替表現テスト"""
        breadcrumb_block = NotionBlock(
            id="test_breadcrumb",
            type="breadcrumb",
            content={}
        )
        
        result = self.converter._convert_breadcrumb_block(breadcrumb_block)
        assert "🍞 **パンくずリスト**" in result
        assert "ホーム > ... > 現在のページ" in result
    
    def test_enhanced_callout_with_colors(self):
        """色付きコールアウトブロックの拡張テスト"""
        colored_callout = NotionBlock(
            id="test_colored_callout",
            type="callout",
            content={
                "callout": {
                    "rich_text": [{"plain_text": "重要な警告", "annotations": {}}],
                    "icon": {"type": "emoji", "emoji": "⚠️"},
                    "color": "red"
                }
            }
        )
        
        # 色保持設定あり
        color_config = ConversionConfig()
        color_config.set_block_setting("callout", "preserve_color", True)
        color_converter = AdvancedBlockConverter(color_config)
        
        result = color_converter._convert_enhanced_callout_block(colored_callout)
        assert "❤️ ⚠️" in result
        assert "重要な警告" in result
        assert "(red)" in result
    
    def test_enhanced_toggle_with_children(self):
        """子要素付きトグルブロックの拡張テスト"""
        toggle_block = NotionBlock(
            id="test_toggle_with_children",
            type="toggle",
            content={
                "toggle": {
                    "rich_text": [{"plain_text": "詳細情報", "annotations": {}}]
                }
            }
        )
        
        # 子ブロックを模擬
        child_block = NotionBlock(
            id="child_block",
            type="paragraph",
            content={
                "paragraph": {
                    "rich_text": [{"plain_text": "これは詳細な説明です。", "annotations": {}}]
                }
            }
        )
        toggle_block.children = [child_block]
        
        result = self.converter._convert_enhanced_toggle_block(toggle_block)
        assert "<details>" in result
        assert "<summary>詳細情報</summary>" in result
        assert "</details>" in result
    
    def test_integration_with_limited_blocks(self):
        """制限のあるブロックタイプの統合テスト"""
        blocks = [
            NotionBlock(
                id="db_block",
                type="child_database",
                content={"child_database": {"title": "タスク管理"}}
            ),
            NotionBlock(
                id="col_list_block",
                type="column_list",
                content={}
            ),
            NotionBlock(
                id="template_block",
                type="template",
                content={
                    "template": {
                        "rich_text": [{"plain_text": "日報テンプレート", "annotations": {}}]
                    }
                }
            )
        ]
        
        # テーブルモード、セパレーターモードで変換
        config = ConversionConfig(database_mode="table", column_layout="separator")
        converter = AdvancedBlockConverter(config)
        
        result = converter.convert_blocks_to_markdown(blocks)
        
        assert "📊 タスク管理" in result
        assert "📋 カラムレイアウト開始" in result
        assert "📋 **テンプレート: 日報テンプレート**" in result


if __name__ == "__main__":
    pytest.main([__file__])
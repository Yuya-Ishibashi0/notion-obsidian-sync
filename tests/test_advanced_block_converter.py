"""
高度なブロック変換機能のユニットテスト
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from services.advanced_block_converter import AdvancedBlockConverter
from models.config import ConversionConfig
from models.notion import NotionBlock


class TestAdvancedBlockConverter:
    """AdvancedBlockConverter のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.config = ConversionConfig()
        self.converter = AdvancedBlockConverter(self.config)
    
    def test_convert_paragraph_block(self):
        """段落ブロックの変換テスト"""
        block = NotionBlock(
            id="test_block_1",
            type="paragraph",
            content={
                "paragraph": {
                    "rich_text": [
                        {
                            "plain_text": "これはテスト段落です。",
                            "annotations": {}
                        }
                    ]
                }
            }
        )
        
        result = self.converter._convert_paragraph_block(block)
        assert result == "これはテスト段落です。"
    
    def test_convert_heading_blocks(self):
        """見出しブロックの変換テスト"""
        # 見出し1
        h1_block = NotionBlock(
            id="test_h1",
            type="heading_1",
            content={
                "heading_1": {
                    "rich_text": [{"plain_text": "見出し1", "annotations": {}}]
                }
            }
        )
        result = self.converter._convert_heading_block(h1_block)
        assert result == "# 見出し1"
        
        # 見出し2
        h2_block = NotionBlock(
            id="test_h2",
            type="heading_2",
            content={
                "heading_2": {
                    "rich_text": [{"plain_text": "見出し2", "annotations": {}}]
                }
            }
        )
        result = self.converter._convert_heading_block(h2_block)
        assert result == "## 見出し2"
        
        # 見出し3
        h3_block = NotionBlock(
            id="test_h3",
            type="heading_3",
            content={
                "heading_3": {
                    "rich_text": [{"plain_text": "見出し3", "annotations": {}}]
                }
            }
        )
        result = self.converter._convert_heading_block(h3_block)
        assert result == "### 見出し3"
    
    def test_convert_list_blocks(self):
        """リストブロックの変換テスト"""
        # 箇条書きリスト
        bullet_block = NotionBlock(
            id="test_bullet",
            type="bulleted_list_item",
            content={
                "bulleted_list_item": {
                    "rich_text": [{"plain_text": "箇条書きアイテム", "annotations": {}}]
                }
            }
        )
        result = self.converter._convert_bulleted_list_block(bullet_block)
        assert result == "- 箇条書きアイテム"
        
        # 番号付きリスト
        numbered_block = NotionBlock(
            id="test_numbered",
            type="numbered_list_item",
            content={
                "numbered_list_item": {
                    "rich_text": [{"plain_text": "番号付きアイテム", "annotations": {}}]
                }
            }
        )
        result = self.converter._convert_numbered_list_block(numbered_block)
        assert result == "1. 番号付きアイテム"
    
    def test_convert_todo_block(self):
        """TODOブロックの変換テスト"""
        # 未完了のTODO
        todo_unchecked = NotionBlock(
            id="test_todo_unchecked",
            type="to_do",
            content={
                "to_do": {
                    "rich_text": [{"plain_text": "未完了タスク", "annotations": {}}],
                    "checked": False
                }
            }
        )
        result = self.converter._convert_todo_block(todo_unchecked)
        assert result == "- [ ] 未完了タスク"
        
        # 完了済みのTODO
        todo_checked = NotionBlock(
            id="test_todo_checked",
            type="to_do",
            content={
                "to_do": {
                    "rich_text": [{"plain_text": "完了タスク", "annotations": {}}],
                    "checked": True
                }
            }
        )
        result = self.converter._convert_todo_block(todo_checked)
        assert result == "- [x] 完了タスク"
    
    def test_convert_quote_block(self):
        """引用ブロックの変換テスト"""
        quote_block = NotionBlock(
            id="test_quote",
            type="quote",
            content={
                "quote": {
                    "rich_text": [{"plain_text": "これは引用文です。", "annotations": {}}]
                }
            }
        )
        result = self.converter._convert_quote_block(quote_block)
        assert result == "> これは引用文です。"
    
    def test_convert_code_block(self):
        """コードブロックの変換テスト"""
        code_block = NotionBlock(
            id="test_code",
            type="code",
            content={
                "code": {
                    "rich_text": [{"plain_text": "print('Hello, World!')", "annotations": {}}],
                    "language": "python"
                }
            }
        )
        result = self.converter._convert_code_block(code_block)
        assert result == "```python\nprint('Hello, World!')\n```"
    
    def test_convert_divider_block(self):
        """区切り線ブロックの変換テスト"""
        divider_block = NotionBlock(
            id="test_divider",
            type="divider",
            content={}
        )
        result = self.converter._convert_divider_block(divider_block)
        assert result == "---"
    
    def test_convert_callout_block(self):
        """コールアウトブロックの変換テスト"""
        callout_block = NotionBlock(
            id="test_callout",
            type="callout",
            content={
                "callout": {
                    "rich_text": [{"plain_text": "重要な情報", "annotations": {}}],
                    "icon": {"type": "emoji", "emoji": "💡"}
                }
            }
        )
        result = self.converter._convert_callout_block(callout_block)
        assert result == "> 💡 **重要な情報**"
    
    def test_convert_image_block(self):
        """画像ブロックの変換テスト"""
        image_block = NotionBlock(
            id="test_image",
            type="image",
            content={
                "image": {
                    "type": "external",
                    "external": {"url": "https://example.com/image.jpg"},
                    "caption": [{"plain_text": "テスト画像", "annotations": {}}]
                }
            }
        )
        result = self.converter._convert_image_block(image_block)
        assert result == "![テスト画像](https://example.com/image.jpg)"
    
    def test_convert_bookmark_block(self):
        """ブックマークブロックの変換テスト"""
        bookmark_block = NotionBlock(
            id="test_bookmark",
            type="bookmark",
            content={
                "bookmark": {
                    "url": "https://example.com",
                    "caption": [{"plain_text": "サンプルサイト", "annotations": {}}]
                }
            }
        )
        result = self.converter._convert_bookmark_block(bookmark_block)
        assert result == "[サンプルサイト](https://example.com)"
    
    def test_convert_equation_block(self):
        """数式ブロックの変換テスト"""
        equation_block = NotionBlock(
            id="test_equation",
            type="equation",
            content={
                "equation": {
                    "expression": "E = mc^2"
                }
            }
        )
        result = self.converter._convert_equation_block(equation_block)
        assert "E = mc^2" in result
    
    def test_extract_rich_text_with_formatting(self):
        """リッチテキストの装飾変換テスト"""
        rich_text_data = [
            {
                "plain_text": "太字テキスト",
                "annotations": {"bold": True}
            },
            {
                "plain_text": "斜体テキスト",
                "annotations": {"italic": True}
            },
            {
                "plain_text": "コードテキスト",
                "annotations": {"code": True}
            }
        ]
        
        result = self.converter._extract_rich_text_from_content(rich_text_data)
        assert "**太字テキスト**" in result
        assert "*斜体テキスト*" in result
        assert "`コードテキスト`" in result
    
    def test_handle_unsupported_block(self):
        """サポートされていないブロックの処理テスト"""
        unsupported_block = NotionBlock(
            id="test_unsupported",
            type="unsupported_type",
            content={}
        )
        
        # プレースホルダーモード
        placeholder_config = ConversionConfig(unsupported_blocks="placeholder")
        placeholder_converter = AdvancedBlockConverter(placeholder_config)
        result = placeholder_converter._handle_unsupported_block(unsupported_block)
        assert "サポートされていないブロック" in result
        
        # スキップモード
        skip_config = ConversionConfig(unsupported_blocks="skip")
        skip_converter = AdvancedBlockConverter(skip_config)
        result = skip_converter._handle_unsupported_block(unsupported_block)
        assert result is None
    
    def test_convert_table_blocks(self):
        """テーブルブロックの変換テスト"""
        # テーブル行ブロック
        table_row_block = NotionBlock(
            id="test_table_row",
            type="table_row",
            content={
                "table_row": {
                    "cells": [
                        [{"plain_text": "ヘッダー1", "annotations": {}}],
                        [{"plain_text": "ヘッダー2", "annotations": {}}],
                        [{"plain_text": "ヘッダー3", "annotations": {}}]
                    ]
                }
            }
        )
        
        result = self.converter._convert_table_row_block(table_row_block)
        assert result == "| ヘッダー1 | ヘッダー2 | ヘッダー3 |"
        
        # パイプ文字のエスケープテスト
        table_row_with_pipes = NotionBlock(
            id="test_table_row_pipes",
            type="table_row",
            content={
                "table_row": {
                    "cells": [
                        [{"plain_text": "データ|パイプ", "annotations": {}}],
                        [{"plain_text": "通常データ", "annotations": {}}]
                    ]
                }
            }
        )
        
        result = self.converter._convert_table_row_block(table_row_with_pipes)
        assert result == "| データ\\|パイプ | 通常データ |"
    
    def test_convert_file_block(self):
        """ファイルブロックの変換テスト"""
        file_block = NotionBlock(
            id="test_file",
            type="file",
            content={
                "file": {
                    "type": "external",
                    "external": {"url": "https://example.com/document.pdf"},
                    "name": "重要な文書.pdf",
                    "caption": [{"plain_text": "プロジェクト資料", "annotations": {}}]
                }
            }
        )
        
        result = self.converter._convert_file_block(file_block)
        assert result == "📎 [プロジェクト資料](https://example.com/document.pdf)"
    
    def test_convert_video_block(self):
        """動画ブロックの変換テスト"""
        video_block = NotionBlock(
            id="test_video",
            type="video",
            content={
                "video": {
                    "type": "external",
                    "external": {"url": "https://youtube.com/watch?v=abc123"},
                    "caption": [{"plain_text": "チュートリアル動画", "annotations": {}}]
                }
            }
        )
        
        result = self.converter._convert_video_block(video_block)
        assert result == "🎥 [チュートリアル動画](https://youtube.com/watch?v=abc123)"
    
    def test_convert_blocks_to_markdown_integration(self):
        """ブロックリスト全体の変換統合テスト"""
        blocks = [
            NotionBlock(
                id="block1",
                type="heading_1",
                content={
                    "heading_1": {
                        "rich_text": [{"plain_text": "メインタイトル", "annotations": {}}]
                    }
                }
            ),
            NotionBlock(
                id="block2",
                type="paragraph",
                content={
                    "paragraph": {
                        "rich_text": [{"plain_text": "これは段落です。", "annotations": {}}]
                    }
                }
            ),
            NotionBlock(
                id="block3",
                type="bulleted_list_item",
                content={
                    "bulleted_list_item": {
                        "rich_text": [{"plain_text": "リストアイテム", "annotations": {}}]
                    }
                }
            )
        ]
        
        result = self.converter.convert_blocks_to_markdown(blocks)
        
        assert "# メインタイトル" in result
        assert "これは段落です。" in result
        assert "- リストアイテム" in result


    # 制限のあるブロックタイプの代替表現テスト
    
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
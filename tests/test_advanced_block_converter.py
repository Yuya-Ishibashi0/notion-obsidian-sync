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


if __name__ == "__main__":
    pytest.main([__file__])
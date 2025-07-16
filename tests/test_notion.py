"""
Notionデータモデルのユニットテスト
"""

import pytest
from datetime import datetime
from models.notion import (
    NotionRichText, NotionProperty, NotionBlock, NotionPage, 
    NotionPageContent, NotionDatabase, NotionBlockType, NotionPropertyType
)


class TestNotionRichText:
    """NotionRichText のテスト"""
    
    def test_basic_rich_text(self):
        """基本的なリッチテキストのテスト"""
        rich_text = NotionRichText(
            type="text",
            plain_text="Hello World"
        )
        assert rich_text.type == "text"
        assert rich_text.plain_text == "Hello World"
        assert rich_text.href is None
        assert not rich_text.is_bold
        assert not rich_text.is_italic
    
    def test_rich_text_with_annotations(self):
        """アノテーション付きリッチテキストのテスト"""
        rich_text = NotionRichText(
            type="text",
            plain_text="Bold Text",
            annotations={
                "bold": True,
                "italic": False,
                "strikethrough": True,
                "underline": False,
                "code": True,
                "color": "red"
            }
        )
        assert rich_text.is_bold
        assert not rich_text.is_italic
        assert rich_text.is_strikethrough
        assert not rich_text.is_underline
        assert rich_text.is_code
        assert rich_text.color == "red"
    
    def test_rich_text_with_href(self):
        """リンク付きリッチテキストのテスト"""
        rich_text = NotionRichText(
            type="text",
            plain_text="Link Text",
            href="https://example.com"
        )
        assert rich_text.href == "https://example.com"
    
    def test_invalid_plain_text(self):
        """無効なplain_textでのテスト"""
        with pytest.raises(ValueError, match="plain_textは文字列である必要があります"):
            NotionRichText(type="text", plain_text=123)


class TestNotionProperty:
    """NotionProperty のテスト"""
    
    def test_basic_property(self):
        """基本的なプロパティのテスト"""
        prop = NotionProperty(
            id="prop_id",
            name="タイトル",
            type="title",
            value=[{"plain_text": "テストページ"}]
        )
        assert prop.id == "prop_id"
        assert prop.name == "タイトル"
        assert prop.type == "title"
        assert prop.get_plain_text_value() == "テストページ"
    
    def test_select_property(self):
        """選択プロパティのテスト"""
        prop = NotionProperty(
            id="select_id",
            name="ステータス",
            type="select",
            value={"name": "進行中"}
        )
        assert prop.get_plain_text_value() == "進行中"
    
    def test_multi_select_property(self):
        """複数選択プロパティのテスト"""
        prop = NotionProperty(
            id="multi_select_id",
            name="タグ",
            type="multi_select",
            value=[{"name": "重要"}, {"name": "緊急"}]
        )
        assert prop.get_plain_text_value() == "重要, 緊急"
    
    def test_checkbox_property(self):
        """チェックボックスプロパティのテスト"""
        prop_checked = NotionProperty(
            id="checkbox_id",
            name="完了",
            type="checkbox",
            value=True
        )
        assert prop_checked.get_plain_text_value() == "✓"
        
        prop_unchecked = NotionProperty(
            id="checkbox_id",
            name="完了",
            type="checkbox",
            value=False
        )
        assert prop_unchecked.get_plain_text_value() == "✗"
    
    def test_date_property(self):
        """日付プロパティのテスト"""
        prop_single = NotionProperty(
            id="date_id",
            name="作成日",
            type="date",
            value={"start": "2023-01-01"}
        )
        assert prop_single.get_plain_text_value() == "2023-01-01"
        
        prop_range = NotionProperty(
            id="date_id",
            name="期間",
            type="date",
            value={"start": "2023-01-01", "end": "2023-01-31"}
        )
        assert prop_range.get_plain_text_value() == "2023-01-01 - 2023-01-31"
    
    def test_number_property(self):
        """数値プロパティのテスト"""
        prop = NotionProperty(
            id="number_id",
            name="価格",
            type="number",
            value=1000
        )
        assert prop.get_plain_text_value() == "1000"
    
    def test_empty_property_validation(self):
        """空のプロパティでの検証テスト"""
        with pytest.raises(ValueError, match="プロパティIDが必要です"):
            NotionProperty(id="", name="test", type="text", value="test")
        
        with pytest.raises(ValueError, match="プロパティ名が必要です"):
            NotionProperty(id="test", name="", type="text", value="test")
        
        with pytest.raises(ValueError, match="プロパティタイプが必要です"):
            NotionProperty(id="test", name="test", type="", value="test")


class TestNotionBlock:
    """NotionBlock のテスト"""
    
    def test_basic_block(self):
        """基本的なブロックのテスト"""
        block = NotionBlock(
            id="block_id",
            type="paragraph"
        )
        assert block.id == "block_id"
        assert block.type == "paragraph"
        assert block.block_type == NotionBlockType.PARAGRAPH
        assert block.is_supported()
    
    def test_paragraph_block_with_content(self):
        """コンテンツ付き段落ブロックのテスト"""
        block = NotionBlock(
            id="para_id",
            type="paragraph",
            content={
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "plain_text": "Hello World",
                            "annotations": {}
                        }
                    ]
                }
            }
        )
        text_content = block.get_text_content()
        assert len(text_content) == 1
        assert text_content[0].plain_text == "Hello World"
        assert block.get_plain_text() == "Hello World"
    
    def test_heading_block(self):
        """見出しブロックのテスト"""
        block = NotionBlock(
            id="heading_id",
            type="heading_1",
            content={
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "plain_text": "見出し1",
                            "annotations": {"bold": True}
                        }
                    ]
                }
            }
        )
        assert block.block_type == NotionBlockType.HEADING_1
        assert block.get_plain_text() == "見出し1"
    
    def test_unsupported_block(self):
        """サポートされていないブロックのテスト"""
        block = NotionBlock(
            id="unsupported_id",
            type="unknown_type"
        )
        assert block.block_type == NotionBlockType.UNSUPPORTED
        assert not block.is_supported()
    
    def test_block_with_children(self):
        """子ブロック付きブロックのテスト"""
        child_block = NotionBlock(id="child_id", type="paragraph")
        parent_block = NotionBlock(
            id="parent_id",
            type="toggle",
            has_children=True,
            children=[child_block]
        )
        assert parent_block.has_children
        assert len(parent_block.children) == 1
        assert parent_block.children[0].id == "child_id"
    
    def test_empty_block_validation(self):
        """空のブロックでの検証テスト"""
        with pytest.raises(ValueError, match="ブロックIDが必要です"):
            NotionBlock(id="", type="paragraph")
        
        with pytest.raises(ValueError, match="ブロックタイプが必要です"):
            NotionBlock(id="test", type="")


class TestNotionPage:
    """NotionPage のテスト"""
    
    def test_basic_page(self):
        """基本的なページのテスト"""
        now = datetime.now()
        page = NotionPage(
            id="page_id",
            created_time=now,
            last_edited_time=now,
            created_by={"id": "user_id"},
            last_edited_by={"id": "user_id"}
        )
        assert page.id == "page_id"
        assert page.created_time == now
        assert page.title == "無題"  # デフォルトタイトル
    
    def test_page_with_title_property(self):
        """タイトルプロパティ付きページのテスト"""
        now = datetime.now()
        title_prop = NotionProperty(
            id="title_id",
            name="タイトル",
            type="title",
            value=[{"plain_text": "テストページ"}]
        )
        page = NotionPage(
            id="page_id",
            created_time=now,
            last_edited_time=now,
            created_by={"id": "user_id"},
            last_edited_by={"id": "user_id"},
            properties={"title": title_prop}
        )
        assert page.title == "テストページ"
    
    def test_page_with_multiple_properties(self):
        """複数プロパティ付きページのテスト"""
        now = datetime.now()
        title_prop = NotionProperty(
            id="title_id", name="タイトル", type="title",
            value=[{"plain_text": "テストページ"}]
        )
        status_prop = NotionProperty(
            id="status_id", name="ステータス", type="select",
            value={"name": "進行中"}
        )
        page = NotionPage(
            id="page_id",
            created_time=now,
            last_edited_time=now,
            created_by={"id": "user_id"},
            last_edited_by={"id": "user_id"},
            properties={"title": title_prop, "status": status_prop}
        )
        
        assert page.get_property_by_name("ステータス") == status_prop
        assert page.get_property_value("ステータス") == {"name": "進行中"}
    
    def test_frontmatter_generation(self):
        """フロントマター生成のテスト"""
        now = datetime.now()
        title_prop = NotionProperty(
            id="title_id", name="タイトル", type="title",
            value=[{"plain_text": "テストページ"}]
        )
        page = NotionPage(
            id="page_id",
            created_time=now,
            last_edited_time=now,
            created_by={"id": "user_id"},
            last_edited_by={"id": "user_id"},
            properties={"title": title_prop},
            url="https://notion.so/page_id"
        )
        
        frontmatter = page.get_frontmatter_dict()
        assert frontmatter["notion_id"] == "page_id"
        assert frontmatter["notion_url"] == "https://notion.so/page_id"
        assert frontmatter["archived"] is False
        assert "created_time" in frontmatter
        assert "last_edited_time" in frontmatter
    
    def test_invalid_page_validation(self):
        """無効なページでの検証テスト"""
        now = datetime.now()
        
        with pytest.raises(ValueError, match="ページIDが必要です"):
            NotionPage(
                id="", created_time=now, last_edited_time=now,
                created_by={}, last_edited_by={}
            )
        
        with pytest.raises(ValueError, match="created_timeはdatetimeオブジェクトである必要があります"):
            NotionPage(
                id="test", created_time="invalid", last_edited_time=now,
                created_by={}, last_edited_by={}
            )


class TestNotionPageContent:
    """NotionPageContent のテスト"""
    
    def test_basic_page_content(self):
        """基本的なページコンテンツのテスト"""
        now = datetime.now()
        page = NotionPage(
            id="page_id", created_time=now, last_edited_time=now,
            created_by={}, last_edited_by={}
        )
        block = NotionBlock(id="block_id", type="paragraph")
        
        content = NotionPageContent(page=page, blocks=[block])
        assert content.page == page
        assert len(content.blocks) == 1
        assert content.blocks[0] == block
    
    def test_text_blocks_filtering(self):
        """テキストブロックのフィルタリングテスト"""
        now = datetime.now()
        page = NotionPage(
            id="page_id", created_time=now, last_edited_time=now,
            created_by={}, last_edited_by={}
        )
        
        para_block = NotionBlock(id="para_id", type="paragraph")
        heading_block = NotionBlock(id="heading_id", type="heading_1")
        image_block = NotionBlock(id="image_id", type="image")
        unsupported_block = NotionBlock(id="unsupported_id", type="unknown")
        
        content = NotionPageContent(
            page=page,
            blocks=[para_block, heading_block, image_block, unsupported_block]
        )
        
        text_blocks = content.get_all_text_blocks()
        assert len(text_blocks) == 2
        assert para_block in text_blocks
        assert heading_block in text_blocks
        assert image_block not in text_blocks
        
        unsupported_blocks = content.get_unsupported_blocks()
        assert len(unsupported_blocks) == 1
        assert unsupported_block in unsupported_blocks
        
        assert content.has_unsupported_content()
    
    def test_invalid_page_content_validation(self):
        """無効なページコンテンツでの検証テスト"""
        with pytest.raises(ValueError, match="pageはNotionPageオブジェクトである必要があります"):
            NotionPageContent(page="invalid", blocks=[])
        
        now = datetime.now()
        page = NotionPage(
            id="page_id", created_time=now, last_edited_time=now,
            created_by={}, last_edited_by={}
        )
        
        with pytest.raises(ValueError, match="blocksはリストである必要があります"):
            NotionPageContent(page=page, blocks="invalid")


class TestNotionDatabase:
    """NotionDatabase のテスト"""
    
    def test_basic_database(self):
        """基本的なデータベースのテスト"""
        db = NotionDatabase(
            id="db_id",
            title="テストDB",
            description=[],
            properties={"タイトル": {"type": "title"}},
            parent={"type": "workspace"},
            url="https://notion.so/db_id"
        )
        assert db.id == "db_id"
        assert db.title == "テストDB"
        assert "タイトル" in db.get_property_names()
        assert db.get_property_type("タイトル") == "title"
    
    def test_database_with_multiple_properties(self):
        """複数プロパティ付きデータベースのテスト"""
        properties = {
            "タイトル": {"type": "title"},
            "ステータス": {"type": "select"},
            "作成日": {"type": "created_time"}
        }
        db = NotionDatabase(
            id="db_id", title="テストDB", description=[],
            properties=properties, parent={}, url=""
        )
        
        prop_names = db.get_property_names()
        assert len(prop_names) == 3
        assert "タイトル" in prop_names
        assert "ステータス" in prop_names
        assert "作成日" in prop_names
        
        assert db.get_property_type("ステータス") == "select"
        assert db.get_property_type("存在しない") is None
    
    def test_invalid_database_validation(self):
        """無効なデータベースでの検証テスト"""
        with pytest.raises(ValueError, match="データベースIDが必要です"):
            NotionDatabase(
                id="", title="test", description=[], properties={},
                parent={}, url=""
            )
        
        with pytest.raises(ValueError, match="データベースタイトルが必要です"):
            NotionDatabase(
                id="test", title="", description=[], properties={},
                parent={}, url=""
            )
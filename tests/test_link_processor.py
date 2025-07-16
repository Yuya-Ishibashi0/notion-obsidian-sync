"""
リンク処理システムのユニットテスト
"""

import pytest
from unittest.mock import Mock, patch

from services.link_processor import (
    NotionLinkProcessor, LinkReference, PageReference
)
from models.config import ConversionConfig


class TestNotionLinkProcessor:
    """NotionLinkProcessor のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.config = ConversionConfig()
        self.processor = NotionLinkProcessor(self.config)
    
    def test_initialization(self):
        """初期化テスト"""
        assert self.processor.config == self.config
        assert len(self.processor.page_registry) == 0
        assert len(self.processor.broken_links) == 0
        assert len(self.processor.processed_links) == 0
    
    def test_register_page(self):
        """ページ登録テスト"""
        page_id = "abc123def456"
        title = "テストページ"
        url = "https://notion.so/test/abc123def456"
        
        self.processor.register_page(page_id, title, url)
        
        assert page_id in self.processor.page_registry
        page_ref = self.processor.page_registry[page_id]
        assert page_ref.page_id == page_id
        assert page_ref.title == title
        assert page_ref.url == url
        assert page_ref.is_accessible == True
    
    def test_is_notion_url(self):
        """Notion URL判定テスト"""
        # Notion URL
        assert self.processor._is_notion_url("https://www.notion.so/test/abc123") == True
        assert self.processor._is_notion_url("https://notion.so/abc123") == True
        
        # 外部URL
        assert self.processor._is_notion_url("https://google.com") == False
        assert self.processor._is_notion_url("https://github.com") == False
    
    def test_normalize_page_id(self):
        """ページID正規化テスト"""
        # ハイフン付きID
        assert self.processor._normalize_page_id("abc123-def456-ghi789") == "abc123def456ghi789"
        
        # ハイフンなしID
        assert self.processor._normalize_page_id("abc123def456ghi789") == "abc123def456ghi789"
    
    def test_process_external_link(self):
        """外部リンク処理テスト"""
        external_url = "https://google.com"
        link_ref = self.processor.process_link(external_url)
        
        assert link_ref.original_url == external_url
        assert link_ref.link_type == "external"
        assert link_ref.is_valid == True
        assert link_ref.target_id is None
    
    def test_process_notion_page_link_valid(self):
        """有効なNotionページリンク処理テスト"""
        page_id = "abc123def456"
        page_title = "テストページ"
        page_url = "https://www.notion.so/test/abc123-def456"
        
        # ページを登録
        self.processor.register_page(page_id, page_title, "https://notion.so/test/abc123def456")
        
        # リンクを処理
        link_ref = self.processor.process_link(page_url)
        
        assert link_ref.original_url == page_url
        assert link_ref.link_type == "page"
        assert link_ref.target_id == page_id
        assert link_ref.target_title == page_title
        assert link_ref.is_valid == True
    
    def test_process_notion_page_link_broken(self):
        """壊れたNotionページリンク処理テスト"""
        page_url = "https://www.notion.so/test/unknown123-def456"
        
        # 未登録のページリンクを処理
        link_ref = self.processor.process_link(page_url)
        
        assert link_ref.original_url == page_url
        assert link_ref.link_type == "page"
        assert link_ref.target_id == "unknown123def456"
        assert link_ref.is_valid == False
        assert "見つかりません" in link_ref.error_message
        assert page_url in self.processor.broken_links
    
    def test_process_notion_database_link(self):
        """Notionデータベースリンク処理テスト"""
        db_id = "database123"
        db_title = "テストデータベース"
        db_url = "https://www.notion.so/database123?v=view456"
        
        # データベースを登録
        self.processor.register_page(db_id, db_title, "https://notion.so/database123")
        
        # リンクを処理
        link_ref = self.processor.process_link(db_url)
        
        assert link_ref.original_url == db_url
        assert link_ref.link_type == "database"
        assert link_ref.target_id == db_id
        assert link_ref.target_title == db_title
        assert link_ref.is_valid == True
    
    def test_process_notion_block_link(self):
        """Notionブロックリンク処理テスト"""
        page_id = "page123"
        block_id = "block456"
        page_title = "テストページ"
        block_url = f"https://www.notion.so/{page_id}#{block_id}"
        
        # ページを登録
        self.processor.register_page(page_id, page_title, f"https://notion.so/{page_id}")
        
        # リンクを処理
        link_ref = self.processor.process_link(block_url)
        
        assert link_ref.original_url == block_url
        assert link_ref.link_type == "block"
        assert link_ref.target_id == f"{page_id}#{block_id}"
        assert "ブロック" in link_ref.target_title
        assert link_ref.is_valid == True
    
    def test_convert_external_link_to_markdown(self):
        """外部リンクのMarkdown変換テスト"""
        link_ref = LinkReference(
            original_url="https://google.com",
            link_type="external",
            is_valid=True
        )
        
        result = self.processor.convert_link_to_markdown(link_ref, "Google")
        assert result == "[Google](https://google.com)"
    
    def test_convert_internal_link_obsidian_mode(self):
        """内部リンクのObsidian形式変換テスト"""
        # Obsidianモードに設定
        self.config.set_block_setting("link", "internal_link_mode", "obsidian")
        
        link_ref = LinkReference(
            original_url="https://notion.so/test/abc123",
            link_type="page",
            target_title="テストページ",
            is_valid=True
        )
        
        # 同じタイトルの場合
        result = self.processor.convert_link_to_markdown(link_ref, "テストページ")
        assert result == "[[テストページ]]"
        
        # 異なる表示テキストの場合
        result = self.processor.convert_link_to_markdown(link_ref, "リンクテキスト")
        assert result == "[[テストページ|リンクテキスト]]"
    
    def test_convert_internal_link_markdown_mode(self):
        """内部リンクのMarkdown形式変換テスト"""
        # Markdownモードに設定
        self.config.set_block_setting("link", "internal_link_mode", "markdown")
        
        link_ref = LinkReference(
            original_url="https://notion.so/test/abc123",
            link_type="page",
            target_title="テストページ",
            is_valid=True
        )
        
        result = self.processor.convert_link_to_markdown(link_ref, "リンクテキスト")
        assert result == "[リンクテキスト](テストページ.md)"
    
    def test_convert_broken_link_placeholder_mode(self):
        """壊れたリンクのプレースホルダー変換テスト"""
        # プレースホルダーモードに設定
        self.config.set_block_setting("link", "broken_link_mode", "placeholder")
        
        link_ref = LinkReference(
            original_url="https://notion.so/broken",
            link_type="page",
            is_valid=False,
            error_message="ページが見つかりません"
        )
        
        result = self.processor.convert_link_to_markdown(link_ref, "壊れたリンク")
        assert result == "~~壊れたリンク~~ (リンク切れ)"
    
    def test_convert_broken_link_comment_mode(self):
        """壊れたリンクのコメント変換テスト"""
        # コメントモードに設定
        self.config.set_block_setting("link", "broken_link_mode", "comment")
        
        link_ref = LinkReference(
            original_url="https://notion.so/broken",
            link_type="page",
            is_valid=False,
            error_message="ページが見つかりません"
        )
        
        result = self.processor.convert_link_to_markdown(link_ref, "壊れたリンク")
        assert result == "壊れたリンク <!-- リンク切れ: ページが見つかりません -->"
    
    def test_process_rich_text_links(self):
        """リッチテキストリンク処理テスト"""
        rich_text_data = [
            {
                "plain_text": "通常テキスト",
                "annotations": {}
            },
            {
                "plain_text": "リンクテキスト",
                "annotations": {},
                "href": "https://google.com"
            },
            {
                "plain_text": "壊れたリンク",
                "annotations": {},
                "href": "https://notion.so/broken123"
            }
        ]
        
        processed_data = self.processor.process_rich_text_links(rich_text_data)
        
        assert len(processed_data) == 3
        
        # 通常テキスト
        assert processed_data[0]["plain_text"] == "通常テキスト"
        assert "_link_status" not in processed_data[0]
        
        # 有効なリンク
        assert processed_data[1]["plain_text"] == "リンクテキスト"
        assert processed_data[1]["_link_status"] == "valid"
        assert processed_data[1]["_link_type"] == "external"
        
        # 壊れたリンク
        assert processed_data[2]["plain_text"] == "壊れたリンク"
        assert processed_data[2]["_link_status"] == "broken"
        assert processed_data[2]["_link_error"] is not None
    
    def test_sanitize_filename(self):
        """ファイル名サニタイズテスト"""
        # 無効な文字を含むファイル名
        assert self.processor._sanitize_filename("test<>file") == "testfile"
        assert self.processor._sanitize_filename("test/file\\name") == "testfilename"
        assert self.processor._sanitize_filename("test:file|name") == "testfilename"
        
        # 連続するスペース
        assert self.processor._sanitize_filename("test   file   name") == "test file name"
        
        # 前後の空白
        assert self.processor._sanitize_filename("  test file  ") == "test file"
        
        # 空のファイル名
        assert self.processor._sanitize_filename("") == "untitled"
        assert self.processor._sanitize_filename("   ") == "untitled"
    
    def test_get_link_report(self):
        """リンクレポート取得テスト"""
        # いくつかのリンクを処理
        self.processor.process_link("https://google.com")
        self.processor.process_link("https://notion.so/valid123")
        self.processor.register_page("valid123", "有効ページ", "https://notion.so/valid123")
        # 同じURLは再処理されない（キャッシュされる）ので、異なるURLを使用
        self.processor.process_link("https://notion.so/valid123-different")
        self.processor.process_link("https://notion.so/broken456")
        
        report = self.processor.get_link_report()
        
        assert report["total_links_processed"] == 4
        assert report["valid_links"] == 1  # google.comのみ有効（valid123は登録前に処理されたため無効）
        assert report["broken_links"] == 3  # valid123, valid123-different, broken456が無効
        assert "external" in report["link_types"]
        assert "page" in report["link_types"]
        assert len(report["broken_link_urls"]) == 3
        assert report["registered_pages"] == 1
    
    def test_generate_broken_links_report_empty(self):
        """空の壊れたリンクレポート生成テスト"""
        report = self.processor.generate_broken_links_report()
        
        assert "壊れたリンクは見つかりませんでした" in report
        assert "✅" in report
    
    def test_generate_broken_links_report_with_broken_links(self):
        """壊れたリンクありのレポート生成テスト"""
        # 壊れたリンクを処理
        self.processor.process_link("https://notion.so/broken123")
        self.processor.process_link("https://notion.so/broken456")
        
        report = self.processor.generate_broken_links_report()
        
        assert "2個の壊れたリンクが見つかりました" in report
        assert "⚠️" in report
        assert "broken123" in report
        assert "broken456" in report
        assert "対処方法" in report
        assert "設定による対処" in report
    
    def test_link_caching(self):
        """リンクキャッシュテスト"""
        url = "https://google.com"
        
        # 最初の処理
        link_ref1 = self.processor.process_link(url)
        
        # 2回目の処理（キャッシュから取得）
        link_ref2 = self.processor.process_link(url)
        
        # 同じオブジェクトが返されることを確認
        assert link_ref1 is link_ref2
        assert len(self.processor.processed_links) == 1


class TestLinkReference:
    """LinkReference のテスト"""
    
    def test_link_reference_creation(self):
        """LinkReference作成テスト"""
        link_ref = LinkReference(
            original_url="https://example.com",
            link_type="external",
            target_id="test123",
            target_title="テストタイトル",
            is_valid=True,
            error_message=None
        )
        
        assert link_ref.original_url == "https://example.com"
        assert link_ref.link_type == "external"
        assert link_ref.target_id == "test123"
        assert link_ref.target_title == "テストタイトル"
        assert link_ref.is_valid == True
        assert link_ref.error_message is None


class TestPageReference:
    """PageReference のテスト"""
    
    def test_page_reference_creation(self):
        """PageReference作成テスト"""
        page_ref = PageReference(
            page_id="abc123",
            title="テストページ",
            url="https://notion.so/abc123",
            is_accessible=True
        )
        
        assert page_ref.page_id == "abc123"
        assert page_ref.title == "テストページ"
        assert page_ref.url == "https://notion.so/abc123"
        assert page_ref.is_accessible == True


if __name__ == "__main__":
    pytest.main([__file__])
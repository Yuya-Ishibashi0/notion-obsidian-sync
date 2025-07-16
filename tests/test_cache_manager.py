"""
キャッシュ管理システムのユニットテスト
"""

import pytest
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path

from services.cache_manager import CacheManager, ChangeDetector, PageCacheEntry
from models.config import ConversionConfig


class TestPageCacheEntry:
    """PageCacheEntry のテスト"""
    
    def test_cache_entry_creation(self):
        """キャッシュエントリ作成テスト"""
        entry = PageCacheEntry(
            page_id="test123",
            title="テストページ",
            last_edited_time="2024-01-01T00:00:00Z",
            content_hash="abc123",
            file_path="test.md",
            cached_at="2024-01-01T01:00:00Z",
            properties_hash="def456",
            block_count=5
        )
        
        assert entry.page_id == "test123"
        assert entry.title == "テストページ"
        assert entry.block_count == 5
    
    def test_to_dict_and_from_dict(self):
        """辞書変換テスト"""
        entry = PageCacheEntry(
            page_id="test123",
            title="テストページ",
            last_edited_time="2024-01-01T00:00:00Z",
            content_hash="abc123",
            file_path="test.md",
            cached_at="2024-01-01T01:00:00Z"
        )
        
        # 辞書に変換
        entry_dict = entry.to_dict()
        assert isinstance(entry_dict, dict)
        assert entry_dict["page_id"] == "test123"
        
        # 辞書から復元
        restored_entry = PageCacheEntry.from_dict(entry_dict)
        assert restored_entry.page_id == entry.page_id
        assert restored_entry.title == entry.title


class TestCacheManager:
    """CacheManager のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ConversionConfig()
        self.cache_manager = CacheManager(self.config, self.temp_dir)
    
    def teardown_method(self):
        """テストクリーンアップ"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """初期化テスト"""
        assert self.cache_manager.config == self.config
        assert self.cache_manager.cache_dir == Path(self.temp_dir)
        assert isinstance(self.cache_manager.cache, dict)
    
    def test_update_and_get_page_cache(self):
        """ページキャッシュ更新・取得テスト"""
        page_id = "test123"
        title = "テストページ"
        last_edited_time = "2024-01-01T00:00:00Z"
        content = "テストコンテンツ"
        file_path = "test.md"
        
        # キャッシュ更新
        self.cache_manager.update_page_cache(
            page_id, title, last_edited_time, content, file_path
        )
        
        # キャッシュ取得
        cached_entry = self.cache_manager.get_page_cache(page_id)
        assert cached_entry is not None
        assert cached_entry.page_id == page_id
        assert cached_entry.title == title
        assert cached_entry.last_edited_time == last_edited_time
        assert cached_entry.file_path == file_path
    
    def test_is_page_changed(self):
        """ページ変更検出テスト"""
        page_id = "test123"
        title = "テストページ"
        last_edited_time = "2024-01-01T00:00:00Z"
        content = "テストコンテンツ"
        file_path = "test.md"
        
        # 初回は変更されているとみなす（キャッシュなし）
        assert self.cache_manager.is_page_changed(page_id, last_edited_time, content) == True
        
        # キャッシュ更新
        self.cache_manager.update_page_cache(
            page_id, title, last_edited_time, content, file_path
        )
        
        # 同じ内容なら変更されていない
        assert self.cache_manager.is_page_changed(page_id, last_edited_time, content) == False
        
        # 最終編集時刻が変わったら変更されている
        new_last_edited_time = "2024-01-02T00:00:00Z"
        assert self.cache_manager.is_page_changed(page_id, new_last_edited_time, content) == True
        
        # コンテンツが変わったら変更されている
        new_content = "新しいコンテンツ"
        assert self.cache_manager.is_page_changed(page_id, last_edited_time, new_content) == True
    
    def test_get_changed_pages(self):
        """変更ページ取得テスト"""
        # テストデータ
        pages_data = [
            {"id": "page1", "last_edited_time": "2024-01-01T00:00:00Z"},
            {"id": "page2", "last_edited_time": "2024-01-02T00:00:00Z"},
            {"id": "page3", "last_edited_time": "2024-01-03T00:00:00Z"}
        ]
        
        # 初回は全て変更されているとみなす
        changed_pages = self.cache_manager.get_changed_pages(pages_data)
        assert len(changed_pages) == 3
        
        # page1をキャッシュに追加
        self.cache_manager.update_page_cache(
            "page1", "ページ1", "2024-01-01T00:00:00Z", "コンテンツ1", "page1.md"
        )
        
        # page1は変更されていない
        changed_pages = self.cache_manager.get_changed_pages(pages_data)
        assert len(changed_pages) == 2
        assert not any(page["id"] == "page1" for page in changed_pages)
    
    def test_remove_page_cache(self):
        """ページキャッシュ削除テスト"""
        page_id = "test123"
        
        # キャッシュ追加
        self.cache_manager.update_page_cache(
            page_id, "テストページ", "2024-01-01T00:00:00Z", "コンテンツ", "test.md"
        )
        assert self.cache_manager.get_page_cache(page_id) is not None
        
        # キャッシュ削除
        self.cache_manager.remove_page_cache(page_id)
        assert self.cache_manager.get_page_cache(page_id) is None
    
    def test_clear_cache(self):
        """キャッシュクリアテスト"""
        # キャッシュ追加
        self.cache_manager.update_page_cache(
            "test123", "テストページ", "2024-01-01T00:00:00Z", "コンテンツ", "test.md"
        )
        assert len(self.cache_manager.cache) == 1
        
        # キャッシュクリア
        self.cache_manager.clear_cache()
        assert len(self.cache_manager.cache) == 0
    
    def test_save_and_load_cache(self):
        """キャッシュ保存・読み込みテスト"""
        # キャッシュ追加
        page_id = "test123"
        title = "テストページ"
        self.cache_manager.update_page_cache(
            page_id, title, "2024-01-01T00:00:00Z", "コンテンツ", "test.md"
        )
        
        # キャッシュ保存
        self.cache_manager.save_cache()
        assert self.cache_manager.cache_file.exists()
        
        # 新しいキャッシュマネージャーで読み込み
        new_cache_manager = CacheManager(self.config, self.temp_dir)
        cached_entry = new_cache_manager.get_page_cache(page_id)
        assert cached_entry is not None
        assert cached_entry.title == title
    
    def test_cleanup_old_cache(self):
        """古いキャッシュクリーンアップテスト"""
        # 古いエントリを追加
        old_time = (datetime.now() - timedelta(days=35)).isoformat()
        self.cache_manager.cache["old_page"] = PageCacheEntry(
            page_id="old_page",
            title="古いページ",
            last_edited_time="2024-01-01T00:00:00Z",
            content_hash="abc123",
            file_path="old.md",
            cached_at=old_time
        )
        
        # 新しいエントリを追加
        self.cache_manager.update_page_cache(
            "new_page", "新しいページ", "2024-01-01T00:00:00Z", "コンテンツ", "new.md"
        )
        
        assert len(self.cache_manager.cache) == 2
        
        # 古いキャッシュをクリーンアップ
        self.cache_manager.cleanup_old_cache(max_age_days=30)
        
        # 古いエントリが削除されている
        assert len(self.cache_manager.cache) == 1
        assert "old_page" not in self.cache_manager.cache
        assert "new_page" in self.cache_manager.cache
    
    def test_get_cache_stats(self):
        """キャッシュ統計取得テスト"""
        # 空のキャッシュ
        stats = self.cache_manager.get_cache_stats()
        assert stats["total_entries"] == 0
        
        # キャッシュ追加
        self.cache_manager.update_page_cache(
            "test123", "テストページ", "2024-01-01T00:00:00Z", "コンテンツ", "test.md"
        )
        
        stats = self.cache_manager.get_cache_stats()
        assert stats["total_entries"] == 1
        assert "cache_size_mb" in stats
        assert "oldest_entry" in stats
        assert "newest_entry" in stats
    
    def test_export_cache_report(self):
        """キャッシュレポート出力テスト"""
        # キャッシュ追加
        self.cache_manager.update_page_cache(
            "test123", "テストページ", "2024-01-01T00:00:00Z", "コンテンツ", "test.md"
        )
        
        report = self.cache_manager.export_cache_report()
        assert "# キャッシュレポート" in report
        assert "テストページ" in report
        assert "統計情報" in report


class TestChangeDetector:
    """ChangeDetector のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ConversionConfig()
        self.cache_manager = CacheManager(self.config, self.temp_dir)
        self.change_detector = ChangeDetector(self.cache_manager)
    
    def teardown_method(self):
        """テストクリーンアップ"""
        shutil.rmtree(self.temp_dir)
    
    def test_detect_changes_new_pages(self):
        """新規ページ検出テスト"""
        current_pages = [
            {"id": "page1", "last_edited_time": "2024-01-01T00:00:00Z"},
            {"id": "page2", "last_edited_time": "2024-01-02T00:00:00Z"}
        ]
        
        changes = self.change_detector.detect_changes(current_pages)
        
        assert len(changes["new"]) == 2
        assert "page1" in changes["new"]
        assert "page2" in changes["new"]
        assert len(changes["modified"]) == 0
        assert len(changes["deleted"]) == 0
    
    def test_detect_changes_modified_pages(self):
        """変更ページ検出テスト"""
        # キャッシュに追加
        self.cache_manager.update_page_cache(
            "page1", "ページ1", "2024-01-01T00:00:00Z", "コンテンツ1", "page1.md"
        )
        
        current_pages = [
            {"id": "page1", "last_edited_time": "2024-01-02T00:00:00Z"},  # 変更された
            {"id": "page2", "last_edited_time": "2024-01-01T00:00:00Z"}   # 新規
        ]
        
        changes = self.change_detector.detect_changes(current_pages)
        
        assert len(changes["new"]) == 1
        assert "page2" in changes["new"]
        assert len(changes["modified"]) == 1
        assert "page1" in changes["modified"]
    
    def test_detect_changes_deleted_pages(self):
        """削除ページ検出テスト"""
        # キャッシュに追加
        self.cache_manager.update_page_cache(
            "page1", "ページ1", "2024-01-01T00:00:00Z", "コンテンツ1", "page1.md"
        )
        self.cache_manager.update_page_cache(
            "page2", "ページ2", "2024-01-01T00:00:00Z", "コンテンツ2", "page2.md"
        )
        
        # page2が削除された
        current_pages = [
            {"id": "page1", "last_edited_time": "2024-01-01T00:00:00Z"}
        ]
        
        changes = self.change_detector.detect_changes(current_pages)
        
        assert len(changes["deleted"]) == 1
        assert "page2" in changes["deleted"]
        assert len(changes["unchanged"]) == 1
        assert "page1" in changes["unchanged"]
    
    def test_should_sync_page(self):
        """ページ同期判定テスト"""
        page_id = "test123"
        last_edited_time = "2024-01-01T00:00:00Z"
        
        # 強制同期フラグがTrueの場合は常に同期
        assert self.change_detector.should_sync_page(page_id, last_edited_time, force_sync=True) == True
        
        # キャッシュがない場合は同期
        assert self.change_detector.should_sync_page(page_id, last_edited_time) == True
        
        # キャッシュ追加
        self.cache_manager.update_page_cache(
            page_id, "テストページ", last_edited_time, "コンテンツ", "test.md"
        )
        
        # 変更がない場合は同期しない
        assert self.change_detector.should_sync_page(page_id, last_edited_time) == False
        
        # 変更がある場合は同期
        new_last_edited_time = "2024-01-02T00:00:00Z"
        assert self.change_detector.should_sync_page(page_id, new_last_edited_time) == True
    
    def test_get_sync_priority(self):
        """同期優先度テスト"""
        # キャッシュに追加（未変更ページ）
        self.cache_manager.update_page_cache(
            "page1", "ページ1", "2024-01-01T00:00:00Z", "コンテンツ1", "page1.md"
        )
        
        pages = [
            {"id": "page1", "last_edited_time": "2024-01-01T00:00:00Z"},  # 未変更
            {"id": "page2", "last_edited_time": "2024-01-02T00:00:00Z"},  # 新規
            {"id": "page3", "last_edited_time": "2024-01-03T00:00:00Z"}   # 新規
        ]
        
        prioritized_pages = self.change_detector.get_sync_priority(pages)
        
        # 新規ページが最初に来る
        assert prioritized_pages[0]["id"] in ["page2", "page3"]
        assert prioritized_pages[1]["id"] in ["page2", "page3"]
        # 未変更ページが最後に来る
        assert prioritized_pages[2]["id"] == "page1"


if __name__ == "__main__":
    pytest.main([__file__])
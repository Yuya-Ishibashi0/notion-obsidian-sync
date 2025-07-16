"""
キャッシュ管理システム
ページメタデータキャッシュと変更検出機能を提供
"""

import json
import logging
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from pathlib import Path

from models.config import ConversionConfig


@dataclass
class PageCacheEntry:
    """ページキャッシュエントリ"""
    page_id: str
    title: str
    last_edited_time: str
    content_hash: str
    file_path: str
    cached_at: str
    properties_hash: Optional[str] = None
    block_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PageCacheEntry':
        """辞書から作成"""
        return cls(**data)


class CacheManager:
    """キャッシュ管理システム"""
    
    def __init__(self, config: ConversionConfig, cache_dir: str = ".cache"):
        """
        初期化
        
        Args:
            config: 変換設定
            cache_dir: キャッシュディレクトリ
        """
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "page_cache.json"
        self.logger = logging.getLogger(__name__)
        
        # キャッシュディレクトリを作成
        self.cache_dir.mkdir(exist_ok=True)
        
        # キャッシュデータ
        self.cache: Dict[str, PageCacheEntry] = {}
        self.load_cache()
    
    def load_cache(self):
        """キャッシュファイルを読み込み"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                for page_id, entry_data in cache_data.items():
                    self.cache[page_id] = PageCacheEntry.from_dict(entry_data)
                
                self.logger.info(f"キャッシュを読み込みました: {len(self.cache)}エントリ")
            else:
                self.logger.info("キャッシュファイルが見つかりません。新規作成します。")
                
        except Exception as e:
            self.logger.error(f"キャッシュ読み込みエラー: {str(e)}")
            self.cache = {}
    
    def save_cache(self):
        """キャッシュファイルに保存"""
        try:
            cache_data = {
                page_id: entry.to_dict() 
                for page_id, entry in self.cache.items()
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"キャッシュを保存しました: {len(self.cache)}エントリ")
            
        except Exception as e:
            self.logger.error(f"キャッシュ保存エラー: {str(e)}")
    
    def get_page_cache(self, page_id: str) -> Optional[PageCacheEntry]:
        """
        ページキャッシュを取得
        
        Args:
            page_id: ページID
            
        Returns:
            キャッシュエントリ（存在しない場合はNone）
        """
        return self.cache.get(page_id)
    
    def update_page_cache(self, page_id: str, title: str, last_edited_time: str,
                         content: str, file_path: str, properties: Dict[str, Any] = None,
                         block_count: int = 0):
        """
        ページキャッシュを更新
        
        Args:
            page_id: ページID
            title: ページタイトル
            last_edited_time: 最終編集時刻
            content: ページコンテンツ
            file_path: ファイルパス
            properties: ページプロパティ
            block_count: ブロック数
        """
        content_hash = self._calculate_content_hash(content)
        properties_hash = self._calculate_properties_hash(properties) if properties else None
        
        cache_entry = PageCacheEntry(
            page_id=page_id,
            title=title,
            last_edited_time=last_edited_time,
            content_hash=content_hash,
            file_path=file_path,
            cached_at=datetime.now().isoformat(),
            properties_hash=properties_hash,
            block_count=block_count
        )
        
        self.cache[page_id] = cache_entry
        self.logger.debug(f"ページキャッシュを更新: {title} ({page_id})")
    
    def is_page_changed(self, page_id: str, last_edited_time: str, 
                       content: str = None, properties: Dict[str, Any] = None) -> bool:
        """
        ページが変更されているかチェック
        
        Args:
            page_id: ページID
            last_edited_time: 最終編集時刻
            content: ページコンテンツ（オプション）
            properties: ページプロパティ（オプション）
            
        Returns:
            変更されている場合True
        """
        cached_entry = self.get_page_cache(page_id)
        
        if not cached_entry:
            # キャッシュにない場合は変更されているとみなす
            return True
        
        # 最終編集時刻をチェック
        if cached_entry.last_edited_time != last_edited_time:
            return True
        
        # コンテンツハッシュをチェック（提供されている場合）
        if content is not None:
            content_hash = self._calculate_content_hash(content)
            if cached_entry.content_hash != content_hash:
                return True
        
        # プロパティハッシュをチェック（提供されている場合）
        if properties is not None:
            properties_hash = self._calculate_properties_hash(properties)
            if cached_entry.properties_hash != properties_hash:
                return True
        
        return False
    
    def get_changed_pages(self, pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        変更されたページのリストを取得
        
        Args:
            pages_data: ページデータのリスト
            
        Returns:
            変更されたページのリスト
        """
        changed_pages = []
        
        for page_data in pages_data:
            page_id = page_data.get('id')
            last_edited_time = page_data.get('last_edited_time')
            
            if self.is_page_changed(page_id, last_edited_time):
                changed_pages.append(page_data)
        
        self.logger.info(f"変更検出: {len(changed_pages)}/{len(pages_data)}ページが変更されています")
        return changed_pages
    
    def remove_page_cache(self, page_id: str):
        """
        ページキャッシュを削除
        
        Args:
            page_id: ページID
        """
        if page_id in self.cache:
            del self.cache[page_id]
            self.logger.debug(f"ページキャッシュを削除: {page_id}")
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self.cache.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.logger.info("キャッシュをクリアしました")
    
    def cleanup_old_cache(self, max_age_days: int = 30):
        """
        古いキャッシュエントリを削除
        
        Args:
            max_age_days: 最大保持日数
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        old_entries = []
        
        for page_id, entry in self.cache.items():
            try:
                cached_at = datetime.fromisoformat(entry.cached_at)
                if cached_at < cutoff_date:
                    old_entries.append(page_id)
            except ValueError:
                # 日付パースエラーの場合は古いエントリとして扱う
                old_entries.append(page_id)
        
        for page_id in old_entries:
            del self.cache[page_id]
        
        if old_entries:
            self.logger.info(f"古いキャッシュエントリを削除: {len(old_entries)}件")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        キャッシュ統計を取得
        
        Returns:
            キャッシュ統計情報
        """
        if not self.cache:
            return {
                "total_entries": 0,
                "cache_size_mb": 0,
                "oldest_entry": None,
                "newest_entry": None
            }
        
        # キャッシュファイルサイズ
        cache_size = 0
        if self.cache_file.exists():
            cache_size = self.cache_file.stat().st_size / (1024 * 1024)  # MB
        
        # 最古・最新エントリ
        cached_times = []
        for entry in self.cache.values():
            try:
                cached_times.append(datetime.fromisoformat(entry.cached_at))
            except ValueError:
                continue
        
        oldest_entry = min(cached_times).isoformat() if cached_times else None
        newest_entry = max(cached_times).isoformat() if cached_times else None
        
        return {
            "total_entries": len(self.cache),
            "cache_size_mb": round(cache_size, 2),
            "oldest_entry": oldest_entry,
            "newest_entry": newest_entry,
            "cache_file_path": str(self.cache_file)
        }
    
    def _calculate_content_hash(self, content: str) -> str:
        """
        コンテンツのハッシュを計算
        
        Args:
            content: コンテンツ文字列
            
        Returns:
            SHA256ハッシュ
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _calculate_properties_hash(self, properties: Dict[str, Any]) -> str:
        """
        プロパティのハッシュを計算
        
        Args:
            properties: プロパティ辞書
            
        Returns:
            SHA256ハッシュ
        """
        # プロパティを正規化してハッシュ化
        normalized_props = json.dumps(properties, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized_props.encode('utf-8')).hexdigest()
    
    def export_cache_report(self) -> str:
        """
        キャッシュレポートをMarkdown形式で出力
        
        Returns:
            Markdownレポート
        """
        stats = self.get_cache_stats()
        
        report_lines = [
            "# キャッシュレポート",
            "",
            f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 統計情報",
            "",
            f"- **総エントリ数**: {stats['total_entries']}",
            f"- **キャッシュサイズ**: {stats['cache_size_mb']} MB",
            f"- **最古エントリ**: {stats['oldest_entry'] or 'なし'}",
            f"- **最新エントリ**: {stats['newest_entry'] or 'なし'}",
            f"- **キャッシュファイル**: `{stats['cache_file_path']}`",
            "",
            "## ページ別詳細",
            ""
        ]
        
        if self.cache:
            # ページ別の詳細情報
            sorted_entries = sorted(
                self.cache.values(), 
                key=lambda x: x.cached_at, 
                reverse=True
            )
            
            for entry in sorted_entries[:20]:  # 最新20件のみ表示
                report_lines.extend([
                    f"### {entry.title}",
                    f"- **ページID**: `{entry.page_id}`",
                    f"- **最終編集**: {entry.last_edited_time}",
                    f"- **キャッシュ日時**: {entry.cached_at}",
                    f"- **ブロック数**: {entry.block_count}",
                    f"- **ファイルパス**: `{entry.file_path}`",
                    ""
                ])
            
            if len(self.cache) > 20:
                report_lines.append(f"*（他 {len(self.cache) - 20} エントリ）*")
        else:
            report_lines.append("キャッシュエントリはありません。")
        
        return "\n".join(report_lines)


class ChangeDetector:
    """変更検出システム"""
    
    def __init__(self, cache_manager: CacheManager):
        """
        初期化
        
        Args:
            cache_manager: キャッシュマネージャー
        """
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
    
    def detect_changes(self, current_pages: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        変更を検出
        
        Args:
            current_pages: 現在のページリスト
            
        Returns:
            変更検出結果
        """
        current_page_ids = {page['id'] for page in current_pages}
        cached_page_ids = set(self.cache_manager.cache.keys())
        
        # 新規ページ
        new_pages = current_page_ids - cached_page_ids
        
        # 削除されたページ
        deleted_pages = cached_page_ids - current_page_ids
        
        # 変更されたページ
        modified_pages = []
        for page in current_pages:
            page_id = page['id']
            if page_id in cached_page_ids:
                if self.cache_manager.is_page_changed(page_id, page.get('last_edited_time', '')):
                    modified_pages.append(page_id)
        
        result = {
            "new": list(new_pages),
            "modified": modified_pages,
            "deleted": list(deleted_pages),
            "unchanged": list(current_page_ids - set(new_pages) - set(modified_pages))
        }
        
        self.logger.info(f"変更検出結果: 新規={len(result['new'])}, "
                        f"変更={len(result['modified'])}, "
                        f"削除={len(result['deleted'])}, "
                        f"未変更={len(result['unchanged'])}")
        
        return result
    
    def should_sync_page(self, page_id: str, last_edited_time: str, 
                        force_sync: bool = False) -> bool:
        """
        ページを同期すべきかどうか判定
        
        Args:
            page_id: ページID
            last_edited_time: 最終編集時刻
            force_sync: 強制同期フラグ
            
        Returns:
            同期すべき場合True
        """
        if force_sync:
            return True
        
        return self.cache_manager.is_page_changed(page_id, last_edited_time)
    
    def get_sync_priority(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        同期優先度順にページをソート
        
        Args:
            pages: ページリスト
            
        Returns:
            優先度順にソートされたページリスト
        """
        def priority_key(page):
            page_id = page['id']
            cached_entry = self.cache_manager.get_page_cache(page_id)
            
            # 新規ページは最優先
            if not cached_entry:
                return (0, page.get('last_edited_time', ''))
            
            # 変更されたページは次の優先度
            if self.cache_manager.is_page_changed(page_id, page.get('last_edited_time', '')):
                return (1, page.get('last_edited_time', ''))
            
            # 未変更ページは最低優先度
            return (2, page.get('last_edited_time', ''))
        
        return sorted(pages, key=priority_key)
"""
Notionリンクと参照の処理システム
内部リンク、ページ参照、データベース参照の変換を担当
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass

from models.config import ConversionConfig


@dataclass
class LinkReference:
    """リンク参照情報"""
    original_url: str
    link_type: str  # "page", "database", "external", "internal"
    target_id: Optional[str] = None
    target_title: Optional[str] = None
    is_valid: bool = True
    error_message: Optional[str] = None


@dataclass
class PageReference:
    """ページ参照情報"""
    page_id: str
    title: str
    url: str
    is_accessible: bool = True


class NotionLinkProcessor:
    """Notionリンク処理システム"""
    
    # Notion URLパターン
    NOTION_URL_PATTERNS = {
        'database': re.compile(r'https://(?:www\.)?notion\.so/([a-zA-Z0-9\-]+)\?v=([a-zA-Z0-9\-]+)'),
        'block': re.compile(r'https://(?:www\.)?notion\.so/([a-zA-Z0-9\-]+)#([a-zA-Z0-9\-]+)'),
        'page': re.compile(r'https://(?:www\.)?notion\.so/([a-zA-Z0-9\-]+)/([a-zA-Z0-9\-]+)'),
        'page_short': re.compile(r'https://(?:www\.)?notion\.so/([a-zA-Z0-9\-]+)$')
    }
    
    def __init__(self, config: ConversionConfig):
        """
        初期化
        
        Args:
            config: 変換設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.page_registry: Dict[str, PageReference] = {}
        self.broken_links: Set[str] = set()
        self.processed_links: Dict[str, LinkReference] = {}
    
    def register_page(self, page_id: str, title: str, url: str, is_accessible: bool = True):
        """
        ページをレジストリに登録
        
        Args:
            page_id: ページID
            title: ページタイトル
            url: ページURL
            is_accessible: アクセス可能かどうか
        """
        self.page_registry[page_id] = PageReference(
            page_id=page_id,
            title=title,
            url=url,
            is_accessible=is_accessible
        )
        self.logger.debug(f"ページ登録: {title} ({page_id})")
    
    def process_link(self, url: str, context: str = "") -> LinkReference:
        """
        リンクを処理して参照情報を生成
        
        Args:
            url: 処理するURL
            context: コンテキスト情報
            
        Returns:
            リンク参照情報
        """
        # キャッシュから確認
        if url in self.processed_links:
            return self.processed_links[url]
        
        link_ref = self._analyze_link(url, context)
        self.processed_links[url] = link_ref
        
        return link_ref
    
    def _analyze_link(self, url: str, context: str = "") -> LinkReference:
        """
        リンクを分析して種類を判定
        
        Args:
            url: 分析するURL
            context: コンテキスト情報
            
        Returns:
            リンク参照情報
        """
        try:
            # 外部リンクかどうかを確認
            if not self._is_notion_url(url):
                return LinkReference(
                    original_url=url,
                    link_type="external",
                    is_valid=True
                )
            
            # Notion内部リンクの処理
            return self._process_notion_link(url, context)
            
        except Exception as e:
            self.logger.error(f"リンク分析エラー ({url}): {str(e)}")
            return LinkReference(
                original_url=url,
                link_type="unknown",
                is_valid=False,
                error_message=f"リンク分析エラー: {str(e)}"
            )
    
    def _is_notion_url(self, url: str) -> bool:
        """
        NotionのURLかどうかを判定
        
        Args:
            url: 判定するURL
            
        Returns:
            NotionのURLかどうか
        """
        return "notion.so" in url.lower()
    
    def _process_notion_link(self, url: str, context: str = "") -> LinkReference:
        """
        Notion内部リンクを処理
        
        Args:
            url: NotionのURL
            context: コンテキスト情報
            
        Returns:
            リンク参照情報
        """
        # データベースリンクの処理（最初にチェック）
        database_match = self.NOTION_URL_PATTERNS['database'].match(url)
        if database_match:
            database_id = self._normalize_page_id(database_match.group(1))
            return self._create_database_link_reference(url, database_id, context)
        
        # ブロックリンクの処理
        block_match = self.NOTION_URL_PATTERNS['block'].match(url)
        if block_match:
            page_id = self._normalize_page_id(block_match.group(1))
            block_id = self._normalize_page_id(block_match.group(2))
            return self._create_block_link_reference(url, page_id, block_id, context)
        
        # ページリンクの処理
        page_match = self.NOTION_URL_PATTERNS['page'].match(url)
        if page_match:
            page_id = self._normalize_page_id(page_match.group(2))
            return self._create_page_link_reference(url, page_id, context)
        
        # 短縮ページリンクの処理
        page_short_match = self.NOTION_URL_PATTERNS['page_short'].match(url)
        if page_short_match:
            page_id = self._normalize_page_id(page_short_match.group(1))
            return self._create_page_link_reference(url, page_id, context)
        
        # 認識できないNotionリンク
        return LinkReference(
            original_url=url,
            link_type="internal",
            is_valid=False,
            error_message="認識できないNotionリンク形式"
        )
    
    def _normalize_page_id(self, page_id: str) -> str:
        """
        ページIDを正規化（ハイフンを除去）
        
        Args:
            page_id: 正規化するページID
            
        Returns:
            正規化されたページID
        """
        return page_id.replace('-', '')
    
    def _create_page_link_reference(self, url: str, page_id: str, context: str) -> LinkReference:
        """
        ページリンク参照を作成
        
        Args:
            url: 元のURL
            page_id: ページID
            context: コンテキスト
            
        Returns:
            リンク参照情報
        """
        if page_id in self.page_registry:
            page_ref = self.page_registry[page_id]
            return LinkReference(
                original_url=url,
                link_type="page",
                target_id=page_id,
                target_title=page_ref.title,
                is_valid=page_ref.is_accessible
            )
        else:
            # 未知のページ
            self.broken_links.add(url)
            return LinkReference(
                original_url=url,
                link_type="page",
                target_id=page_id,
                is_valid=False,
                error_message="参照先ページが見つかりません"
            )
    
    def _create_database_link_reference(self, url: str, database_id: str, context: str) -> LinkReference:
        """
        データベースリンク参照を作成
        
        Args:
            url: 元のURL
            database_id: データベースID
            context: コンテキスト
            
        Returns:
            リンク参照情報
        """
        if database_id in self.page_registry:
            db_ref = self.page_registry[database_id]
            return LinkReference(
                original_url=url,
                link_type="database",
                target_id=database_id,
                target_title=db_ref.title,
                is_valid=db_ref.is_accessible
            )
        else:
            # 未知のデータベース
            self.broken_links.add(url)
            return LinkReference(
                original_url=url,
                link_type="database",
                target_id=database_id,
                is_valid=False,
                error_message="参照先データベースが見つかりません"
            )
    
    def _create_block_link_reference(self, url: str, page_id: str, block_id: str, context: str) -> LinkReference:
        """
        ブロックリンク参照を作成
        
        Args:
            url: 元のURL
            page_id: ページID
            block_id: ブロックID
            context: コンテキスト
            
        Returns:
            リンク参照情報
        """
        if page_id in self.page_registry:
            page_ref = self.page_registry[page_id]
            return LinkReference(
                original_url=url,
                link_type="block",
                target_id=f"{page_id}#{block_id}",
                target_title=f"{page_ref.title} (ブロック)",
                is_valid=page_ref.is_accessible
            )
        else:
            # 未知のページ
            self.broken_links.add(url)
            return LinkReference(
                original_url=url,
                link_type="block",
                target_id=f"{page_id}#{block_id}",
                is_valid=False,
                error_message="参照先ページが見つかりません"
            )
    
    def convert_link_to_markdown(self, link_ref: LinkReference, display_text: str = "") -> str:
        """
        リンク参照をMarkdown形式に変換
        
        Args:
            link_ref: リンク参照情報
            display_text: 表示テキスト
            
        Returns:
            Markdown形式のリンク
        """
        if not display_text:
            display_text = self._generate_display_text(link_ref)
        
        if link_ref.link_type == "external":
            return f"[{display_text}]({link_ref.original_url})"
        
        elif link_ref.link_type in ["page", "database", "block"]:
            if link_ref.is_valid:
                return self._convert_internal_link(link_ref, display_text)
            else:
                return self._convert_broken_link(link_ref, display_text)
        
        else:
            # 未知のリンクタイプ
            return f"[{display_text}]({link_ref.original_url})"
    
    def _generate_display_text(self, link_ref: LinkReference) -> str:
        """
        リンクの表示テキストを生成
        
        Args:
            link_ref: リンク参照情報
            
        Returns:
            表示テキスト
        """
        if link_ref.target_title:
            return link_ref.target_title
        elif link_ref.link_type == "page":
            return "ページリンク"
        elif link_ref.link_type == "database":
            return "データベースリンク"
        elif link_ref.link_type == "block":
            return "ブロックリンク"
        elif link_ref.link_type == "external":
            return link_ref.original_url
        else:
            return "リンク"
    
    def _convert_internal_link(self, link_ref: LinkReference, display_text: str) -> str:
        """
        有効な内部リンクを変換
        
        Args:
            link_ref: リンク参照情報
            display_text: 表示テキスト
            
        Returns:
            Markdown形式のリンク
        """
        link_conversion_mode = self.config.get_block_setting("link", "internal_link_mode", "obsidian")
        
        if link_conversion_mode == "obsidian":
            # Obsidian形式のWikiリンク
            if link_ref.target_title:
                if display_text != link_ref.target_title:
                    return f"[[{link_ref.target_title}|{display_text}]]"
                else:
                    return f"[[{link_ref.target_title}]]"
            else:
                return f"[[{display_text}]]"
        
        elif link_conversion_mode == "markdown":
            # 標準Markdown形式
            if link_ref.target_title:
                # ローカルファイルリンクとして表現
                filename = self._sanitize_filename(link_ref.target_title)
                return f"[{display_text}]({filename}.md)"
            else:
                return f"[{display_text}](#{link_ref.target_id})"
        
        elif link_conversion_mode == "notion_url":
            # 元のNotionURLを保持
            return f"[{display_text}]({link_ref.original_url})"
        
        else:
            # デフォルト: Obsidian形式
            return f"[[{display_text}]]"
    
    def _convert_broken_link(self, link_ref: LinkReference, display_text: str) -> str:
        """
        壊れたリンクを変換
        
        Args:
            link_ref: リンク参照情報
            display_text: 表示テキスト
            
        Returns:
            代替テキスト
        """
        broken_link_mode = self.config.get_block_setting("link", "broken_link_mode", "placeholder")
        
        if broken_link_mode == "placeholder":
            return f"~~{display_text}~~ (リンク切れ)"
        
        elif broken_link_mode == "comment":
            return f"{display_text} <!-- リンク切れ: {link_ref.error_message} -->"
        
        elif broken_link_mode == "text_only":
            return display_text
        
        elif broken_link_mode == "original_url":
            return f"[{display_text}]({link_ref.original_url})"
        
        else:
            # デフォルト: プレースホルダー
            return f"~~{display_text}~~ (リンク切れ)"
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        ファイル名をサニタイズ
        
        Args:
            filename: サニタイズするファイル名
            
        Returns:
            サニタイズされたファイル名
        """
        # 無効な文字を除去
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
        # 連続するスペースを単一のスペースに
        sanitized = re.sub(r'\s+', ' ', sanitized)
        # 前後の空白を除去
        sanitized = sanitized.strip()
        # 空の場合はデフォルト名
        if not sanitized:
            sanitized = "untitled"
        
        return sanitized
    
    def process_rich_text_links(self, rich_text_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        リッチテキスト内のリンクを処理
        
        Args:
            rich_text_data: リッチテキストデータ
            
        Returns:
            処理されたリッチテキストデータ
        """
        processed_data = []
        
        for text_item in rich_text_data:
            processed_item = text_item.copy()
            
            # hrefがある場合はリンクを処理
            if text_item.get("href"):
                link_ref = self.process_link(text_item["href"], "rich_text")
                
                # リンクが壊れている場合は注釈を追加
                if not link_ref.is_valid:
                    processed_item["_link_status"] = "broken"
                    processed_item["_link_error"] = link_ref.error_message
                else:
                    processed_item["_link_status"] = "valid"
                    processed_item["_link_type"] = link_ref.link_type
                    processed_item["_target_title"] = link_ref.target_title
            
            processed_data.append(processed_item)
        
        return processed_data
    
    def get_link_report(self) -> Dict[str, Any]:
        """
        リンク処理レポートを取得
        
        Returns:
            リンク処理レポート
        """
        total_links = len(self.processed_links)
        valid_links = len([link for link in self.processed_links.values() if link.is_valid])
        broken_links = len([link for link in self.processed_links.values() if not link.is_valid])
        
        link_types = {}
        for link in self.processed_links.values():
            link_types[link.link_type] = link_types.get(link.link_type, 0) + 1
        
        return {
            "total_links_processed": total_links,
            "valid_links": valid_links,
            "broken_links": broken_links,
            "success_rate": (valid_links / total_links * 100) if total_links > 0 else 100,
            "link_types": link_types,
            "broken_link_urls": list(self.broken_links),
            "registered_pages": len(self.page_registry)
        }
    
    def generate_broken_links_report(self) -> str:
        """
        壊れたリンクのレポートを生成
        
        Returns:
            Markdown形式のレポート
        """
        if not self.broken_links:
            return "# リンクレポート\n\n✅ 壊れたリンクは見つかりませんでした。"
        
        report_lines = [
            "# 壊れたリンクレポート",
            "",
            f"⚠️ {len(self.broken_links)}個の壊れたリンクが見つかりました:",
            ""
        ]
        
        for i, broken_url in enumerate(sorted(self.broken_links), 1):
            link_ref = self.processed_links.get(broken_url)
            if link_ref:
                report_lines.extend([
                    f"## {i}. {link_ref.link_type}リンク",
                    f"- **URL**: {broken_url}",
                    f"- **エラー**: {link_ref.error_message}",
                    f"- **対象ID**: {link_ref.target_id or '不明'}",
                    ""
                ])
            else:
                report_lines.extend([
                    f"## {i}. 不明なリンク",
                    f"- **URL**: {broken_url}",
                    ""
                ])
        
        report_lines.extend([
            "## 対処方法",
            "",
            "1. **ページリンク**: 参照先ページがアクセス可能か確認",
            "2. **データベースリンク**: データベースの共有設定を確認",
            "3. **ブロックリンク**: 参照先ページとブロックの存在を確認",
            "",
            "## 設定による対処",
            "",
            "設定ファイルで壊れたリンクの処理方法を変更できます:",
            "- `broken_link_mode`: placeholder/comment/text_only/original_url",
            ""
        ])
        
        return "\n".join(report_lines)
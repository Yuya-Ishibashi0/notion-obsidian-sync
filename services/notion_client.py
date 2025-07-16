"""
Notion APIクライアント
Notion APIとの通信を管理するクライアントクラス
"""

import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from notion_client import Client
from notion_client.errors import APIResponseError, RequestTimeoutError

from models.notion import (
    NotionPage, NotionPageContent, NotionBlock, NotionProperty, 
    NotionDatabase, NotionRichText
)


class NotionAPIError(Exception):
    """Notion API関連のエラー"""
    pass


class NotionRateLimitError(NotionAPIError):
    """レート制限エラー"""
    pass


class NotionClient:
    """Notion APIクライアント"""
    
    def __init__(self, api_token: str, database_id: str):
        """
        初期化
        
        Args:
            api_token: Notion APIトークン
            database_id: 対象のデータベースID
        """
        if not api_token:
            raise ValueError("Notion APIトークンが必要です")
        if not database_id:
            raise ValueError("NotionデータベースIDが必要です")
        
        self.api_token = api_token
        self.database_id = database_id
        self.client = Client(auth=api_token)
        self.logger = logging.getLogger(__name__)
        
        # レート制限管理
        self.last_request_time = 0
        self.min_request_interval = 0.34  # 約3リクエスト/秒
        self.max_retries = 3
        self.base_retry_delay = 1.0
    
    def _wait_for_rate_limit(self) -> None:
        """レート制限を考慮した待機"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            self.logger.debug(f"レート制限のため{sleep_time:.2f}秒待機")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _handle_api_error(self, error: Exception, operation: str) -> None:
        """APIエラーのハンドリング"""
        if isinstance(error, APIResponseError):
            if error.status == 429:  # Too Many Requests
                raise NotionRateLimitError(f"レート制限に達しました: {operation}")
            elif error.status == 401:
                raise NotionAPIError(f"認証エラー: APIトークンを確認してください")
            elif error.status == 404:
                raise NotionAPIError(f"リソースが見つかりません: {operation}")
            else:
                raise NotionAPIError(f"API エラー ({error.status}): {error.body}")
        elif isinstance(error, RequestTimeoutError):
            raise NotionAPIError(f"リクエストタイムアウト: {operation}")
        else:
            raise NotionAPIError(f"予期しないエラー: {operation} - {str(error)}")
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """指数バックオフでリトライ"""
        for attempt in range(self.max_retries):
            try:
                self._wait_for_rate_limit()
                return func(*args, **kwargs)
            except NotionRateLimitError:
                if attempt == self.max_retries - 1:
                    raise
                delay = self.base_retry_delay * (2 ** attempt)
                self.logger.warning(f"レート制限のため{delay}秒待機してリトライ (試行 {attempt + 1}/{self.max_retries})")
                time.sleep(delay)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                self.logger.warning(f"リトライ {attempt + 1}/{self.max_retries}: {str(e)}")
                time.sleep(self.base_retry_delay)
    
    def test_connection(self) -> bool:
        """
        接続テスト
        
        Returns:
            接続が成功した場合True
        """
        try:
            self._retry_with_backoff(self.client.databases.retrieve, self.database_id)
            self.logger.info("Notion API接続テスト成功")
            return True
        except Exception as e:
            self.logger.error(f"Notion API接続テスト失敗: {str(e)}")
            return False
    
    def get_database_info(self) -> NotionDatabase:
        """
        データベース情報を取得
        
        Returns:
            NotionDatabaseオブジェクト
        """
        try:
            response = self._retry_with_backoff(
                self.client.databases.retrieve, 
                self.database_id
            )
            
            # タイトルの抽出
            title = ""
            if response.get("title"):
                title = "".join([
                    item.get("plain_text", "") 
                    for item in response["title"]
                ])
            
            # 説明の抽出
            description = []
            if response.get("description"):
                for item in response["description"]:
                    description.append(NotionRichText(
                        type=item.get("type", "text"),
                        plain_text=item.get("plain_text", ""),
                        href=item.get("href"),
                        annotations=item.get("annotations", {})
                    ))
            
            return NotionDatabase(
                id=response["id"],
                title=title,
                description=description,
                properties=response.get("properties", {}),
                parent=response.get("parent", {}),
                url=response.get("url", ""),
                archived=response.get("archived", False),
                is_inline=response.get("is_inline", False),
                public_url=response.get("public_url"),
                created_time=self._parse_datetime(response.get("created_time")),
                last_edited_time=self._parse_datetime(response.get("last_edited_time")),
                created_by=response.get("created_by"),
                last_edited_by=response.get("last_edited_by"),
                cover=response.get("cover"),
                icon=response.get("icon")
            )
            
        except Exception as e:
            self._handle_api_error(e, "データベース情報取得")
    
    def get_database_pages(self, 
                          page_size: int = 100, 
                          filter_dict: Optional[Dict[str, Any]] = None,
                          sorts: Optional[List[Dict[str, Any]]] = None,
                          archived: bool = False) -> List[NotionPage]:
        """
        データベースからページを取得
        
        Args:
            page_size: 1回のリクエストで取得するページ数
            filter_dict: フィルター条件
            sorts: ソート条件
            archived: アーカイブされたページも含めるかどうか
            
        Returns:
            NotionPageオブジェクトのリスト
        """
        pages = []
        has_more = True
        next_cursor = None
        
        try:
            while has_more:
                query_params = {
                    "database_id": self.database_id,
                    "page_size": min(page_size, 100)  # APIの制限
                }
                
                if next_cursor:
                    query_params["start_cursor"] = next_cursor
                
                # フィルター条件を追加
                if filter_dict:
                    query_params["filter"] = filter_dict
                # Note: archivedはページレベルのプロパティのため、
                # データベースクエリではフィルターできません。
                # 取得後にPythonコードでフィルタリングします。
                
                # ソート条件を追加
                if sorts:
                    query_params["sorts"] = sorts
                else:
                    # デフォルトで最終編集日時の降順
                    query_params["sorts"] = [
                        {
                            "timestamp": "last_edited_time",
                            "direction": "descending"
                        }
                    ]
                
                response = self._retry_with_backoff(
                    self.client.databases.query,
                    **query_params
                )
                
                # ページを変換
                for page_data in response.get("results", []):
                    page = self._convert_to_notion_page(page_data)
                    # archivedフィルタリング（取得後にPythonで処理）
                    if not archived and page.archived:
                        continue
                    pages.append(page)
                
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
                
                self.logger.debug(f"取得済みページ数: {len(pages)}")
            
            self.logger.info(f"データベースから{len(pages)}ページを取得しました")
            return pages
            
        except Exception as e:
            self._handle_api_error(e, "データベースページ取得")
    
    def get_pages_by_title(self, title_pattern: str) -> List[NotionPage]:
        """
        タイトルでページを検索
        
        Args:
            title_pattern: 検索するタイトルパターン
            
        Returns:
            マッチしたNotionPageオブジェクトのリスト
        """
        try:
            # タイトルプロパティでフィルター
            filter_dict = {
                "property": "title",  # 実際のタイトルプロパティ名に応じて調整が必要
                "rich_text": {
                    "contains": title_pattern
                }
            }
            
            return self.get_database_pages(filter_dict=filter_dict)
            
        except Exception as e:
            self._handle_api_error(e, f"タイトル検索: {title_pattern}")
    
    def get_pages_modified_after(self, after_date: datetime) -> List[NotionPage]:
        """
        指定日時以降に更新されたページを取得
        
        Args:
            after_date: この日時以降に更新されたページを取得
            
        Returns:
            条件に合致するNotionPageオブジェクトのリスト
        """
        try:
            filter_dict = {
                "timestamp": "last_edited_time",
                "last_edited_time": {
                    "after": after_date.isoformat()
                }
            }
            
            return self.get_database_pages(filter_dict=filter_dict)
            
        except Exception as e:
            self._handle_api_error(e, f"更新日時フィルター: {after_date}")
    
    def get_page_count(self) -> int:
        """
        データベース内のページ数を取得
        
        Returns:
            ページ数
        """
        try:
            # 最小限のデータで1ページだけ取得してカウント情報を得る
            response = self._retry_with_backoff(
                self.client.databases.query,
                database_id=self.database_id,
                page_size=1
            )
            
            # 正確なカウントを得るために全ページを取得
            # （Notion APIは総数を直接提供しないため）
            pages = self.get_database_pages()
            return len(pages)
            
        except Exception as e:
            self._handle_api_error(e, "ページ数取得")
    
    def get_pages_in_batches(self, batch_size: int = 10) -> List[List[NotionPage]]:
        """
        ページをバッチ単位で取得
        
        Args:
            batch_size: バッチサイズ
            
        Returns:
            バッチごとに分割されたNotionPageオブジェクトのリスト
        """
        try:
            all_pages = self.get_database_pages()
            batches = []
            
            for i in range(0, len(all_pages), batch_size):
                batch = all_pages[i:i + batch_size]
                batches.append(batch)
            
            self.logger.info(f"{len(all_pages)}ページを{len(batches)}バッチに分割しました")
            return batches
            
        except Exception as e:
            self._handle_api_error(e, f"バッチ取得 (サイズ: {batch_size})")
    
    def get_page_content(self, page_id: str, include_children: bool = True) -> NotionPageContent:
        """
        ページの詳細コンテンツを取得
        
        Args:
            page_id: ページID
            include_children: 子ブロックも含めるかどうか
            
        Returns:
            NotionPageContentオブジェクト
        """
        try:
            # ページ情報を取得
            page_response = self._retry_with_backoff(
                self.client.pages.retrieve,
                page_id
            )
            page = self._convert_to_notion_page(page_response)
            
            # ブロック情報を取得
            blocks = self._get_page_blocks(page_id, include_children=include_children)
            
            return NotionPageContent(page=page, blocks=blocks)
            
        except Exception as e:
            self._handle_api_error(e, f"ページコンテンツ取得 (ID: {page_id})")
    
    def get_multiple_page_contents(self, page_ids: List[str], 
                                  include_children: bool = True) -> List[NotionPageContent]:
        """
        複数ページのコンテンツを一括取得
        
        Args:
            page_ids: ページIDのリスト
            include_children: 子ブロックも含めるかどうか
            
        Returns:
            NotionPageContentオブジェクトのリスト
        """
        contents = []
        
        for i, page_id in enumerate(page_ids):
            try:
                content = self.get_page_content(page_id, include_children)
                contents.append(content)
                self.logger.debug(f"ページコンテンツ取得完了: {i+1}/{len(page_ids)}")
            except Exception as e:
                self.logger.error(f"ページコンテンツ取得失敗 (ID: {page_id}): {str(e)}")
                # エラーが発生しても他のページの処理を継続
                continue
        
        self.logger.info(f"{len(contents)}/{len(page_ids)}ページのコンテンツを取得しました")
        return contents
    
    def get_page_properties_only(self, page_id: str) -> NotionPage:
        """
        ページのプロパティのみを取得（ブロックは取得しない）
        
        Args:
            page_id: ページID
            
        Returns:
            NotionPageオブジェクト
        """
        try:
            page_response = self._retry_with_backoff(
                self.client.pages.retrieve,
                page_id
            )
            return self._convert_to_notion_page(page_response)
            
        except Exception as e:
            self._handle_api_error(e, f"ページプロパティ取得 (ID: {page_id})")
    
    def _get_page_blocks(self, page_id: str, include_children: bool = True) -> List[NotionBlock]:
        """ページのブロックを再帰的に取得"""
        blocks = []
        has_more = True
        next_cursor = None
        
        while has_more:
            query_params = {"block_id": page_id, "page_size": 100}
            if next_cursor:
                query_params["start_cursor"] = next_cursor
            
            response = self._retry_with_backoff(
                self.client.blocks.children.list,
                **query_params
            )
            
            for block_data in response.get("results", []):
                block = self._convert_to_notion_block(block_data)
                
                # 子ブロックがある場合は再帰的に取得
                if block.has_children and include_children:
                    block.children = self._get_page_blocks(block.id, include_children)
                
                blocks.append(block)
            
            has_more = response.get("has_more", False)
            next_cursor = response.get("next_cursor")
        
        return blocks
    
    def _convert_to_notion_page(self, page_data: Dict[str, Any]) -> NotionPage:
        """APIレスポンスをNotionPageオブジェクトに変換"""
        properties = {}
        
        for prop_name, prop_data in page_data.get("properties", {}).items():
            prop = NotionProperty(
                id=prop_data.get("id", ""),
                name=prop_name,
                type=prop_data.get("type", ""),
                value=self._extract_property_value(prop_data)
            )
            properties[prop_name] = prop
        
        return NotionPage(
            id=page_data["id"],
            created_time=self._parse_datetime(page_data.get("created_time")),
            last_edited_time=self._parse_datetime(page_data.get("last_edited_time")),
            created_by=page_data.get("created_by", {}),
            last_edited_by=page_data.get("last_edited_by", {}),
            cover=page_data.get("cover"),
            icon=page_data.get("icon"),
            parent=page_data.get("parent"),
            archived=page_data.get("archived", False),
            properties=properties,
            url=page_data.get("url"),
            public_url=page_data.get("public_url")
        )
    
    def _convert_to_notion_block(self, block_data: Dict[str, Any]) -> NotionBlock:
        """APIレスポンスをNotionBlockオブジェクトに変換"""
        return NotionBlock(
            id=block_data["id"],
            type=block_data.get("type", ""),
            has_children=block_data.get("has_children", False),
            archived=block_data.get("archived", False),
            created_time=self._parse_datetime(block_data.get("created_time")),
            last_edited_time=self._parse_datetime(block_data.get("last_edited_time")),
            created_by=block_data.get("created_by"),
            last_edited_by=block_data.get("last_edited_by"),
            parent=block_data.get("parent"),
            content=block_data
        )
    
    def _extract_property_value(self, prop_data: Dict[str, Any]) -> Any:
        """プロパティ値を抽出"""
        prop_type = prop_data.get("type")
        
        if prop_type in ["title", "rich_text"]:
            return prop_data.get(prop_type, [])
        elif prop_type in ["select", "status"]:
            return prop_data.get(prop_type)
        elif prop_type == "multi_select":
            return prop_data.get("multi_select", [])
        elif prop_type == "date":
            return prop_data.get("date")
        elif prop_type == "checkbox":
            return prop_data.get("checkbox", False)
        elif prop_type == "number":
            return prop_data.get("number")
        elif prop_type in ["url", "email", "phone_number"]:
            return prop_data.get(prop_type)
        elif prop_type == "people":
            return prop_data.get("people", [])
        elif prop_type == "files":
            return prop_data.get("files", [])
        elif prop_type == "relation":
            return prop_data.get("relation", [])
        elif prop_type in ["created_time", "last_edited_time"]:
            return prop_data.get(prop_type)
        elif prop_type in ["created_by", "last_edited_by"]:
            return prop_data.get(prop_type)
        elif prop_type == "formula":
            return prop_data.get("formula", {})
        elif prop_type == "rollup":
            return prop_data.get("rollup", {})
        else:
            return prop_data.get(prop_type)
    
    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """ISO形式の日時文字列をdatetimeオブジェクトに変換"""
        if not datetime_str:
            return None
        
        try:
            # ISO形式の日時をパース
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            self.logger.warning(f"日時のパースに失敗: {datetime_str}")
            return None
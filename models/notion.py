"""
Notionデータモデル
Notion APIから取得したデータを表現するためのデータクラス
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum


class NotionBlockType(Enum):
    """Notionブロックタイプの列挙"""
    PARAGRAPH = "paragraph"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    BULLETED_LIST_ITEM = "bulleted_list_item"
    NUMBERED_LIST_ITEM = "numbered_list_item"
    TO_DO = "to_do"
    TOGGLE = "toggle"
    CODE = "code"
    QUOTE = "quote"
    CALLOUT = "callout"
    DIVIDER = "divider"
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    PDF = "pdf"
    BOOKMARK = "bookmark"
    EQUATION = "equation"
    TABLE = "table"
    TABLE_ROW = "table_row"
    COLUMN_LIST = "column_list"
    COLUMN = "column"
    EMBED = "embed"
    LINK_PREVIEW = "link_preview"
    SYNCED_BLOCK = "synced_block"
    TEMPLATE = "template"
    LINK_TO_PAGE = "link_to_page"
    TABLE_OF_CONTENTS = "table_of_contents"
    BREADCRUMB = "breadcrumb"
    CHILD_PAGE = "child_page"
    CHILD_DATABASE = "child_database"
    UNSUPPORTED = "unsupported"


class NotionPropertyType(Enum):
    """Notionプロパティタイプの列挙"""
    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    PEOPLE = "people"
    FILES = "files"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    FORMULA = "formula"
    RELATION = "relation"
    ROLLUP = "rollup"
    CREATED_TIME = "created_time"
    CREATED_BY = "created_by"
    LAST_EDITED_TIME = "last_edited_time"
    LAST_EDITED_BY = "last_edited_by"
    STATUS = "status"


@dataclass
class NotionRichText:
    """Notionリッチテキストオブジェクト"""
    type: str
    plain_text: str
    href: Optional[str] = None
    annotations: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """データ検証"""
        if not isinstance(self.plain_text, str):
            raise ValueError("plain_textは文字列である必要があります")
    
    @property
    def is_bold(self) -> bool:
        """太字かどうか"""
        return self.annotations.get("bold", False)
    
    @property
    def is_italic(self) -> bool:
        """斜体かどうか"""
        return self.annotations.get("italic", False)
    
    @property
    def is_strikethrough(self) -> bool:
        """取り消し線かどうか"""
        return self.annotations.get("strikethrough", False)
    
    @property
    def is_underline(self) -> bool:
        """下線かどうか"""
        return self.annotations.get("underline", False)
    
    @property
    def is_code(self) -> bool:
        """コードかどうか"""
        return self.annotations.get("code", False)
    
    @property
    def color(self) -> str:
        """テキストの色"""
        return self.annotations.get("color", "default")


@dataclass
class NotionProperty:
    """Notionプロパティ"""
    id: str
    name: str
    type: str
    value: Any
    
    def __post_init__(self):
        """データ検証"""
        if not self.id:
            raise ValueError("プロパティIDが必要です")
        if not self.name:
            raise ValueError("プロパティ名が必要です")
        if not self.type:
            raise ValueError("プロパティタイプが必要です")
    
    def get_plain_text_value(self) -> str:
        """プレーンテキスト値を取得"""
        if self.type == "title" and isinstance(self.value, list):
            return "".join([item.get("plain_text", "") for item in self.value])
        elif self.type == "rich_text" and isinstance(self.value, list):
            return "".join([item.get("plain_text", "") for item in self.value])
        elif self.type == "select" and self.value:
            return self.value.get("name", "")
        elif self.type == "multi_select" and isinstance(self.value, list):
            return ", ".join([item.get("name", "") for item in self.value])
        elif self.type == "date" and self.value:
            start = self.value.get("start", "")
            end = self.value.get("end", "")
            return f"{start} - {end}" if end else start
        elif self.type == "checkbox":
            return "✓" if self.value else "✗"
        elif self.type in ["url", "email", "phone_number"] and self.value:
            return str(self.value)
        elif self.type == "number" and self.value is not None:
            return str(self.value)
        else:
            return str(self.value) if self.value is not None else ""


@dataclass
class NotionBlock:
    """Notionブロック"""
    id: str
    type: str
    has_children: bool = False
    archived: bool = False
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None
    created_by: Optional[Dict[str, Any]] = None
    last_edited_by: Optional[Dict[str, Any]] = None
    parent: Optional[Dict[str, Any]] = None
    content: Dict[str, Any] = field(default_factory=dict)
    children: List['NotionBlock'] = field(default_factory=list)
    
    def __post_init__(self):
        """データ検証"""
        if not self.id:
            raise ValueError("ブロックIDが必要です")
        if not self.type:
            raise ValueError("ブロックタイプが必要です")
    
    @property
    def block_type(self) -> NotionBlockType:
        """ブロックタイプの列挙値を取得"""
        try:
            return NotionBlockType(self.type)
        except ValueError:
            return NotionBlockType.UNSUPPORTED
    
    def get_text_content(self) -> List[NotionRichText]:
        """ブロックのテキストコンテンツを取得"""
        if self.type in ["paragraph", "heading_1", "heading_2", "heading_3", 
                        "bulleted_list_item", "numbered_list_item", "to_do", "quote"]:
            rich_text_data = self.content.get(self.type, {}).get("rich_text", [])
            return [NotionRichText(**item) for item in rich_text_data]
        elif self.type == "callout":
            rich_text_data = self.content.get("callout", {}).get("rich_text", [])
            return [NotionRichText(**item) for item in rich_text_data]
        elif self.type == "toggle":
            rich_text_data = self.content.get("toggle", {}).get("rich_text", [])
            return [NotionRichText(**item) for item in rich_text_data]
        return []
    
    def get_plain_text(self) -> str:
        """プレーンテキストを取得"""
        rich_texts = self.get_text_content()
        return "".join([rt.plain_text for rt in rich_texts])
    
    def is_supported(self) -> bool:
        """サポートされているブロックタイプかどうか"""
        return self.block_type != NotionBlockType.UNSUPPORTED


@dataclass
class NotionPage:
    """Notionページ"""
    id: str
    created_time: datetime
    last_edited_time: datetime
    created_by: Dict[str, Any]
    last_edited_by: Dict[str, Any]
    cover: Optional[Dict[str, Any]] = None
    icon: Optional[Dict[str, Any]] = None
    parent: Optional[Dict[str, Any]] = None
    archived: bool = False
    properties: Dict[str, NotionProperty] = field(default_factory=dict)
    url: Optional[str] = None
    public_url: Optional[str] = None
    
    def __post_init__(self):
        """データ検証"""
        if not self.id:
            raise ValueError("ページIDが必要です")
        if not isinstance(self.created_time, datetime):
            raise ValueError("created_timeはdatetimeオブジェクトである必要があります")
        if not isinstance(self.last_edited_time, datetime):
            raise ValueError("last_edited_timeはdatetimeオブジェクトである必要があります")
    
    @property
    def title(self) -> str:
        """ページタイトルを取得"""
        for prop in self.properties.values():
            if prop.type == "title":
                return prop.get_plain_text_value()
        return "無題"
    
    def get_property_by_name(self, name: str) -> Optional[NotionProperty]:
        """名前でプロパティを取得"""
        for prop in self.properties.values():
            if prop.name == name:
                return prop
        return None
    
    def get_property_value(self, name: str) -> Any:
        """プロパティ値を取得"""
        prop = self.get_property_by_name(name)
        return prop.value if prop else None
    
    def get_frontmatter_dict(self) -> Dict[str, Any]:
        """YAMLフロントマター用の辞書を生成"""
        frontmatter = {
            "notion_id": self.id,
            "created_time": self.created_time.isoformat(),
            "last_edited_time": self.last_edited_time.isoformat(),
            "archived": self.archived
        }
        
        if self.url:
            frontmatter["notion_url"] = self.url
        
        # プロパティを追加
        for prop in self.properties.values():
            if prop.type != "title":  # タイトルは別途処理
                frontmatter[prop.name] = prop.get_plain_text_value()
        
        return frontmatter


@dataclass
class NotionPageContent:
    """Notionページの完全なコンテンツ"""
    page: NotionPage
    blocks: List[NotionBlock] = field(default_factory=list)
    
    def __post_init__(self):
        """データ検証"""
        if not isinstance(self.page, NotionPage):
            raise ValueError("pageはNotionPageオブジェクトである必要があります")
        if not isinstance(self.blocks, list):
            raise ValueError("blocksはリストである必要があります")
    
    def get_all_text_blocks(self) -> List[NotionBlock]:
        """すべてのテキストブロックを取得"""
        text_types = [
            NotionBlockType.PARAGRAPH, NotionBlockType.HEADING_1, 
            NotionBlockType.HEADING_2, NotionBlockType.HEADING_3,
            NotionBlockType.BULLETED_LIST_ITEM, NotionBlockType.NUMBERED_LIST_ITEM,
            NotionBlockType.TO_DO, NotionBlockType.QUOTE, NotionBlockType.CALLOUT
        ]
        return [block for block in self.blocks if block.block_type in text_types]
    
    def get_unsupported_blocks(self) -> List[NotionBlock]:
        """サポートされていないブロックを取得"""
        return [block for block in self.blocks if not block.is_supported()]
    
    def has_unsupported_content(self) -> bool:
        """サポートされていないコンテンツが含まれているかどうか"""
        return len(self.get_unsupported_blocks()) > 0


@dataclass
class NotionDatabase:
    """Notionデータベース"""
    id: str
    title: str
    description: List[NotionRichText]
    properties: Dict[str, Dict[str, Any]]
    parent: Dict[str, Any]
    url: str
    archived: bool = False
    is_inline: bool = False
    public_url: Optional[str] = None
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None
    created_by: Optional[Dict[str, Any]] = None
    last_edited_by: Optional[Dict[str, Any]] = None
    cover: Optional[Dict[str, Any]] = None
    icon: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """データ検証"""
        if not self.id:
            raise ValueError("データベースIDが必要です")
        if not self.title:
            raise ValueError("データベースタイトルが必要です")
    
    def get_property_names(self) -> List[str]:
        """プロパティ名のリストを取得"""
        return list(self.properties.keys())
    
    def get_property_type(self, name: str) -> Optional[str]:
        """プロパティのタイプを取得"""
        prop = self.properties.get(name)
        return prop.get("type") if prop else None
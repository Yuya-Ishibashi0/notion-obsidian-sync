"""
Markdownファイルモデル
NotionからObsidianへの変換結果を表現するためのデータクラス
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import yaml
import re
from pathlib import Path


@dataclass
class MarkdownFile:
    """Markdownファイルを表現するクラス"""
    filename: str
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    content: str = ""
    
    def __post_init__(self):
        """データ検証"""
        if not self.filename:
            raise ValueError("ファイル名が必要です")
        
        # ファイル名の安全性チェック
        if not self._is_safe_filename(self.filename):
            raise ValueError(f"安全でないファイル名です: {self.filename}")
    
    @staticmethod
    def _is_safe_filename(filename: str) -> bool:
        """ファイル名が安全かどうかチェック"""
        # 危険な文字をチェック
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        if any(char in filename for char in dangerous_chars):
            return False
        
        # 予約語をチェック（Windows）
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            return False
        
        # 空文字や空白のみの場合
        if not filename.strip():
            return False
        
        return True
    
    @staticmethod
    def sanitize_filename(title: str, max_length: int = 100) -> str:
        """タイトルから安全なファイル名を生成"""
        if not title:
            return "無題"
        
        # 危険な文字を置換
        safe_title = title
        replacements = {
            '<': '＜', '>': '＞', ':': '：', '"': '"', '|': '｜',
            '?': '？', '*': '＊', '\\': '￥', '/': '／'
        }
        for dangerous, safe in replacements.items():
            safe_title = safe_title.replace(dangerous, safe)
        
        # 改行文字を削除
        safe_title = safe_title.replace('\n', ' ').replace('\r', ' ')
        
        # 連続する空白を単一の空白に
        safe_title = re.sub(r'\s+', ' ', safe_title).strip()
        
        # 長さ制限
        if len(safe_title) > max_length:
            safe_title = safe_title[:max_length].rstrip()
        
        # 末尾のピリオドを削除（Windowsの制限）
        safe_title = safe_title.rstrip('.')
        
        # 空になった場合のフォールバック
        if not safe_title:
            safe_title = "無題"
        
        return safe_title
    
    def add_frontmatter_field(self, key: str, value: Any) -> None:
        """フロントマターにフィールドを追加"""
        if not key:
            raise ValueError("フロントマターのキーが必要です")
        self.frontmatter[key] = value
    
    def remove_frontmatter_field(self, key: str) -> None:
        """フロントマターからフィールドを削除"""
        self.frontmatter.pop(key, None)
    
    def get_frontmatter_field(self, key: str, default: Any = None) -> Any:
        """フロントマターからフィールドを取得"""
        return self.frontmatter.get(key, default)
    
    def has_frontmatter(self) -> bool:
        """フロントマターが存在するかどうか"""
        return bool(self.frontmatter)
    
    def generate_yaml_frontmatter(self) -> str:
        """YAMLフロントマターを生成"""
        if not self.frontmatter:
            return ""
        
        try:
            yaml_content = yaml.dump(
                self.frontmatter,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
            return f"---\n{yaml_content}---\n"
        except yaml.YAMLError as e:
            raise ValueError(f"YAMLフロントマターの生成に失敗しました: {e}")
    
    def to_string(self) -> str:
        """完全なMarkdownファイルの内容を文字列として生成"""
        result = ""
        
        # フロントマターを追加
        if self.has_frontmatter():
            result += self.generate_yaml_frontmatter()
            if self.content:  # コンテンツがある場合は改行を追加
                result += "\n"
        
        # コンテンツを追加
        result += self.content
        
        return result
    
    def get_file_size(self) -> int:
        """ファイルサイズ（バイト数）を取得"""
        return len(self.to_string().encode('utf-8'))
    
    def validate_content(self) -> List[str]:
        """コンテンツの検証を行い、警告のリストを返す"""
        warnings = []
        
        # ファイルサイズチェック
        size_mb = self.get_file_size() / (1024 * 1024)
        if size_mb > 10:  # 10MB以上
            warnings.append(f"ファイルサイズが大きいです: {size_mb:.1f}MB")
        
        # 長い行のチェック
        lines = self.content.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 1000:  # 1000文字以上の行
                warnings.append(f"行{i}が非常に長いです: {len(line)}文字")
        
        # フロントマターの検証
        if self.has_frontmatter():
            try:
                self.generate_yaml_frontmatter()
            except ValueError as e:
                warnings.append(f"フロントマターエラー: {e}")
        
        return warnings
    
    @classmethod
    def from_string(cls, filename: str, content: str) -> 'MarkdownFile':
        """文字列からMarkdownFileオブジェクトを作成"""
        frontmatter = {}
        markdown_content = content
        
        # フロントマターの抽出
        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    markdown_content = parts[2]
                except yaml.YAMLError:
                    # YAMLパースエラーの場合はフロントマターなしとして扱う
                    pass
        
        return cls(
            filename=filename,
            frontmatter=frontmatter,
            content=markdown_content
        )
    
    def clone(self) -> 'MarkdownFile':
        """MarkdownFileオブジェクトのコピーを作成"""
        return MarkdownFile(
            filename=self.filename,
            frontmatter=self.frontmatter.copy(),
            content=self.content
        )
    
    def merge_frontmatter(self, other_frontmatter: Dict[str, Any]) -> None:
        """他のフロントマターとマージ"""
        self.frontmatter.update(other_frontmatter)
    
    def append_content(self, additional_content: str) -> None:
        """コンテンツを追加"""
        if self.content and not self.content.endswith('\n'):
            self.content += '\n'
        self.content += additional_content
    
    def prepend_content(self, additional_content: str) -> None:
        """コンテンツの先頭に追加"""
        if additional_content and not additional_content.endswith('\n'):
            additional_content += '\n'
        self.content = additional_content + self.content
    
    def replace_content(self, new_content: str) -> None:
        """コンテンツを置換"""
        self.content = new_content
    
    def get_word_count(self) -> int:
        """単語数を取得（日本語文字も考慮）"""
        # 英数字の単語をカウント
        english_words = len(re.findall(r'\b\w+\b', self.content))
        
        # 日本語文字をカウント（ひらがな、カタカナ、漢字）
        japanese_chars = len(re.findall(r'[ひらがなカタカナ漢字]', self.content))
        
        return english_words + japanese_chars
    
    def get_line_count(self) -> int:
        """行数を取得"""
        return len(self.content.split('\n'))
    
    def has_images(self) -> bool:
        """画像が含まれているかどうか"""
        image_pattern = r'!\[.*?\]\(.*?\)'
        return bool(re.search(image_pattern, self.content))
    
    def has_links(self) -> bool:
        """リンクが含まれているかどうか"""
        link_pattern = r'\[.*?\]\(.*?\)'
        return bool(re.search(link_pattern, self.content))
    
    def get_headers(self) -> List[str]:
        """見出しのリストを取得"""
        header_pattern = r'^(#{1,6})\s+(.+)$'
        headers = []
        for line in self.content.split('\n'):
            match = re.match(header_pattern, line)
            if match:
                level = len(match.group(1))
                title = match.group(2)
                headers.append(f"{'  ' * (level - 1)}- {title}")
        return headers


@dataclass
class MarkdownConversionResult:
    """Markdown変換結果"""
    markdown_file: MarkdownFile
    warnings: List[str] = field(default_factory=list)
    conversion_notes: List[str] = field(default_factory=list)
    unsupported_blocks: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """データ検証"""
        if not isinstance(self.markdown_file, MarkdownFile):
            raise ValueError("markdown_fileはMarkdownFileオブジェクトである必要があります")
    
    def add_warning(self, warning: str) -> None:
        """警告を追加"""
        if warning and warning not in self.warnings:
            self.warnings.append(warning)
    
    def add_conversion_note(self, note: str) -> None:
        """変換ノートを追加"""
        if note and note not in self.conversion_notes:
            self.conversion_notes.append(note)
    
    def add_unsupported_block(self, block_type: str) -> None:
        """サポートされていないブロックを追加"""
        if block_type and block_type not in self.unsupported_blocks:
            self.unsupported_blocks.append(block_type)
    
    def has_issues(self) -> bool:
        """問題があるかどうか"""
        return bool(self.warnings or self.unsupported_blocks)
    
    def get_summary(self) -> Dict[str, Any]:
        """変換結果のサマリーを取得"""
        return {
            "filename": self.markdown_file.filename,
            "file_size": self.markdown_file.get_file_size(),
            "word_count": self.markdown_file.get_word_count(),
            "line_count": self.markdown_file.get_line_count(),
            "has_frontmatter": self.markdown_file.has_frontmatter(),
            "has_images": self.markdown_file.has_images(),
            "has_links": self.markdown_file.has_links(),
            "warning_count": len(self.warnings),
            "conversion_note_count": len(self.conversion_notes),
            "unsupported_block_count": len(self.unsupported_blocks),
            "has_issues": self.has_issues()
        }
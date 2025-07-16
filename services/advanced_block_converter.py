"""
高度なNotionブロック変換機能
画像、テーブル、コードブロックなどの高度なブロックタイプの変換を担当
"""

import logging
from typing import Dict, List, Any, Optional

from models.notion import NotionBlock
from models.config import ConversionConfig


class AdvancedBlockConverter:
    """高度なブロック変換機能"""
    
    def __init__(self, conversion_config: ConversionConfig):
        """
        初期化
        
        Args:
            conversion_config: 変換設定
        """
        self.config = conversion_config
        self.logger = logging.getLogger(__name__)
    
    def convert_blocks_to_markdown(self, blocks: List[NotionBlock]) -> str:
        """
        NotionブロックリストをMarkdownに変換
        
        Args:
            blocks: NotionBlockオブジェクトのリスト
            
        Returns:
            変換されたMarkdown文字列
        """
        markdown_lines = []
        
        for block in blocks:
            try:
                converted_block = self._convert_single_block(block)
                if converted_block:
                    markdown_lines.append(converted_block)
            except Exception as e:
                self.logger.warning(f"ブロック変換エラー ({block.type}): {str(e)}")
                # エラーが発生した場合はプレースホルダーを挿入
                if self.config.unsupported_blocks == "placeholder":
                    markdown_lines.append(f"<!-- エラー: {block.type}ブロックの変換に失敗しました -->")
        
        return "\n".join(markdown_lines)
    
    def _convert_single_block(self, block: NotionBlock) -> Optional[str]:
        """
        単一のNotionブロックをMarkdownに変換
        
        Args:
            block: NotionBlockオブジェクト
            
        Returns:
            変換されたMarkdown文字列（変換不可の場合はNone）
        """
        block_type = block.type
        
        # 基本的なテキストブロック
        if block_type == "paragraph":
            return self._convert_paragraph_block(block)
        elif block_type in ["heading_1", "heading_2", "heading_3"]:
            return self._convert_heading_block(block)
        elif block_type == "bulleted_list_item":
            return self._convert_bulleted_list_block(block)
        elif block_type == "numbered_list_item":
            return self._convert_numbered_list_block(block)
        elif block_type == "to_do":
            return self._convert_todo_block(block)
        elif block_type == "quote":
            return self._convert_quote_block(block)
        elif block_type == "callout":
            return self._convert_callout_block(block)
        elif block_type == "divider":
            return self._convert_divider_block(block)
        
        # 高度なブロック
        elif block_type == "code":
            return self._convert_code_block(block)
        elif block_type == "image":
            return self._convert_image_block(block)
        elif block_type == "table":
            return self._convert_table_block(block)
        elif block_type == "table_row":
            return self._convert_table_row_block(block)
        elif block_type == "toggle":
            return self._convert_toggle_block(block)
        elif block_type == "equation":
            return self._convert_equation_block(block)
        elif block_type == "bookmark":
            return self._convert_bookmark_block(block)
        elif block_type == "file":
            return self._convert_file_block(block)
        elif block_type == "video":
            return self._convert_video_block(block)
        
        # サポートされていないブロック
        else:
            return self._handle_unsupported_block(block)
    
    def _convert_paragraph_block(self, block: NotionBlock) -> str:
        """段落ブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "paragraph")
        return text_content if text_content.strip() else ""
    
    def _convert_heading_block(self, block: NotionBlock) -> str:
        """見出しブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, block.type)
        if not text_content.strip():
            return ""
        
        level_map = {"heading_1": "#", "heading_2": "##", "heading_3": "###"}
        prefix = level_map.get(block.type, "#")
        return f"{prefix} {text_content}"
    
    def _convert_bulleted_list_block(self, block: NotionBlock) -> str:
        """箇条書きリストブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "bulleted_list_item")
        return f"- {text_content}" if text_content.strip() else ""
    
    def _convert_numbered_list_block(self, block: NotionBlock) -> str:
        """番号付きリストブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "numbered_list_item")
        return f"1. {text_content}" if text_content.strip() else ""
    
    def _convert_todo_block(self, block: NotionBlock) -> str:
        """TODOブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "to_do")
        todo_data = block.content.get("to_do", {})
        checked = todo_data.get("checked", False)
        checkbox = "[x]" if checked else "[ ]"
        return f"- {checkbox} {text_content}" if text_content.strip() else f"- {checkbox}"
    
    def _convert_quote_block(self, block: NotionBlock) -> str:
        """引用ブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "quote")
        return f"> {text_content}" if text_content.strip() else ""
    
    def _convert_callout_block(self, block: NotionBlock) -> str:
        """コールアウトブロックの変換"""
        callout_data = block.content.get("callout", {})
        text_content = self._extract_rich_text_from_content(callout_data.get("rich_text", []))
        icon = callout_data.get("icon", {})
        
        # アイコンの処理
        icon_text = self._get_callout_icon(icon)
        
        # 設定に応じて変換方法を変更
        if self.config.get_block_setting("callout", "use_quote_format", True):
            return f"> {icon_text} **{text_content}**" if text_content.strip() else f"> {icon_text}"
        else:
            return f"{icon_text} {text_content}" if text_content.strip() else icon_text
    
    def _convert_divider_block(self, block: NotionBlock) -> str:
        """区切り線ブロックの変換"""
        return "---"
    
    def _convert_code_block(self, block: NotionBlock) -> str:
        """コードブロックの変換"""
        code_data = block.content.get("code", {})
        text_content = self._extract_rich_text_from_content(code_data.get("rich_text", []))
        language = code_data.get("language", "")
        
        # 言語の正規化
        language_map = {
            "plain text": "",
            "javascript": "javascript",
            "typescript": "typescript",
            "python": "python",
            "java": "java",
            "c": "c",
            "c++": "cpp",
            "c#": "csharp",
            "go": "go",
            "rust": "rust",
            "php": "php",
            "ruby": "ruby",
            "swift": "swift",
            "kotlin": "kotlin",
            "scala": "scala",
            "shell": "bash",
            "bash": "bash",
            "powershell": "powershell",
            "sql": "sql",
            "html": "html",
            "css": "css",
            "json": "json",
            "xml": "xml",
            "yaml": "yaml",
            "markdown": "markdown"
        }
        
        normalized_language = language_map.get(language.lower(), language)
        return f"```{normalized_language}\n{text_content}\n```"
    
    def _convert_image_block(self, block: NotionBlock) -> str:
        """画像ブロックの変換"""
        image_data = block.content.get("image", {})
        
        # 画像URLの取得
        image_url = ""
        if image_data.get("type") == "external":
            image_url = image_data.get("external", {}).get("url", "")
        elif image_data.get("type") == "file":
            image_url = image_data.get("file", {}).get("url", "")
        
        # キャプションの取得
        caption_content = ""
        if image_data.get("caption"):
            caption_content = self._extract_rich_text_from_content(image_data["caption"])
        
        # 設定に応じて処理方法を変更
        if self.config.convert_images and image_url:
            alt_text = caption_content if caption_content else "画像"
            return f"![{alt_text}]({image_url})"
        else:
            # 画像をダウンロードしない場合はリンクとして表示
            if caption_content:
                return f"[画像: {caption_content}]({image_url})" if image_url else f"画像: {caption_content}"
            else:
                return f"[画像]({image_url})" if image_url else "画像"
    
    def _convert_table_block(self, block: NotionBlock) -> str:
        """テーブルブロックの変換"""
        # テーブルブロック自体は子ブロック（table_row）を持つコンテナ
        # 子ブロックがある場合、最初の行の後にヘッダー区切り線を追加する必要がある
        if hasattr(block, 'children') and block.children:
            table_content = []
            for i, child_block in enumerate(block.children):
                if child_block.type == "table_row":
                    row_content = self._convert_table_row_block(child_block)
                    if row_content:
                        table_content.append(row_content)
                        # 最初の行（ヘッダー）の後に区切り線を追加
                        if i == 0:
                            table_row_data = child_block.content.get("table_row", {})
                            cells = table_row_data.get("cells", [])
                            if cells:
                                separator = "| " + " | ".join(["---"] * len(cells)) + " |"
                                table_content.append(separator)
            return "\n".join(table_content)
        return ""
    
    def _convert_table_row_block(self, block: NotionBlock) -> str:
        """テーブル行ブロックの変換"""
        table_row_data = block.content.get("table_row", {})
        cells = table_row_data.get("cells", [])
        
        if not cells:
            return ""
        
        # 各セルの内容を抽出
        cell_contents = []
        for cell in cells:
            cell_text = self._extract_rich_text_from_content(cell)
            # パイプ文字をエスケープ
            cell_text = cell_text.replace("|", "\\|") if self.config.get_block_setting("table", "escape_pipes", True) else cell_text
            cell_contents.append(cell_text)
        
        # Markdownテーブル行として出力
        return "| " + " | ".join(cell_contents) + " |"
    
    def _convert_toggle_block(self, block: NotionBlock) -> str:
        """トグルブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "toggle")
        
        # 設定に応じて変換方法を変更
        if self.config.get_block_setting("toggle", "use_details_tag", True):
            expand_by_default = self.config.get_block_setting("toggle", "expand_by_default", False)
            open_attr = " open" if expand_by_default else ""
            return f"<details{open_attr}>\n<summary>{text_content}</summary>\n\n<!-- 子コンテンツはここに表示されます -->\n\n</details>"
        else:
            return f"**{text_content}**"
    
    def _convert_equation_block(self, block: NotionBlock) -> str:
        """数式ブロックの変換"""
        equation_data = block.content.get("equation", {})
        expression = equation_data.get("expression", "")
        
        if not expression:
            return ""
        
        # 設定に応じてLaTeX形式で出力
        if self.config.convert_equations:
            block_format = self.config.get_block_setting("equation", "block_format", "$$\n{}\n$$")
            return block_format.format(expression)
        else:
            return f"数式: {expression}"
    
    def _convert_bookmark_block(self, block: NotionBlock) -> str:
        """ブックマークブロックの変換"""
        bookmark_data = block.content.get("bookmark", {})
        url = bookmark_data.get("url", "")
        caption_content = ""
        
        if bookmark_data.get("caption"):
            caption_content = self._extract_rich_text_from_content(bookmark_data["caption"])
        
        # 設定に応じて表示方法を変更
        if self.config.get_block_setting("bookmark", "use_title_as_text", True):
            link_text = caption_content if caption_content else url
            return f"[{link_text}]({url})" if url else caption_content
        else:
            if caption_content:
                return f"🔖 [{caption_content}]({url})" if url else f"🔖 {caption_content}"
            else:
                return f"🔖 {url}" if url else "🔖 ブックマーク"
    
    def _convert_file_block(self, block: NotionBlock) -> str:
        """ファイルブロックの変換"""
        file_data = block.content.get("file", {})
        
        # ファイルURLの取得
        file_url = ""
        file_name = ""
        
        if file_data.get("type") == "external":
            file_url = file_data.get("external", {}).get("url", "")
        elif file_data.get("type") == "file":
            file_url = file_data.get("file", {}).get("url", "")
        
        # ファイル名の取得
        if file_data.get("name"):
            file_name = file_data["name"]
        else:
            file_name = file_url.split("/")[-1] if file_url else "ファイル"
        
        # キャプションの取得
        caption_content = ""
        if file_data.get("caption"):
            caption_content = self._extract_rich_text_from_content(file_data["caption"])
        
        display_name = caption_content if caption_content else file_name
        
        if file_url:
            return f"📎 [{display_name}]({file_url})"
        else:
            return f"📎 {display_name}"
    
    def _convert_video_block(self, block: NotionBlock) -> str:
        """動画ブロックの変換"""
        video_data = block.content.get("video", {})
        
        # 動画URLの取得
        video_url = ""
        if video_data.get("type") == "external":
            video_url = video_data.get("external", {}).get("url", "")
        elif video_data.get("type") == "file":
            video_url = video_data.get("file", {}).get("url", "")
        
        # キャプションの取得
        caption_content = ""
        if video_data.get("caption"):
            caption_content = self._extract_rich_text_from_content(video_data["caption"])
        
        # 設定に応じて埋め込みまたはリンクとして表示
        if self.config.get_block_setting("video", "embed_videos", False):
            # 埋め込み対応（YouTube、Vimeoなど）
            if "youtube.com" in video_url or "youtu.be" in video_url:
                return f"[![{caption_content if caption_content else '動画'}]({video_url})]({video_url})"
            else:
                return f"🎥 [{caption_content if caption_content else '動画'}]({video_url})" if video_url else f"🎥 {caption_content}"
        else:
            return f"🎥 [{caption_content if caption_content else '動画'}]({video_url})" if video_url else f"🎥 {caption_content}"
    
    def _handle_unsupported_block(self, block: NotionBlock) -> Optional[str]:
        """サポートされていないブロックの処理"""
        # 直接設定を確認
        if self.config.unsupported_blocks == "skip":
            return None
        elif self.config.unsupported_blocks == "placeholder":
            return f"<!-- サポートされていないブロック: {block.type} -->"
        elif self.config.unsupported_blocks == "warning":
            self.logger.warning(f"サポートされていないブロックタイプ: {block.type}")
            return f"<!-- 警告: {block.type}ブロックはサポートされていません -->"
        else:
            return f"<!-- サポートされていないブロック: {block.type} -->"
    
    def _extract_rich_text_from_block(self, block: NotionBlock, block_type: str) -> str:
        """ブロックからリッチテキストを抽出"""
        block_content = block.content.get(block_type, {})
        rich_text_data = block_content.get("rich_text", [])
        return self._extract_rich_text_from_content(rich_text_data)
    
    def _extract_rich_text_from_content(self, rich_text_data: List[Dict[str, Any]]) -> str:
        """リッチテキストデータからMarkdown形式のテキストを抽出"""
        if not rich_text_data:
            return ""
        
        result_parts = []
        
        for text_item in rich_text_data:
            plain_text = text_item.get("plain_text", "")
            annotations = text_item.get("annotations", {})
            href = text_item.get("href")
            
            # テキストの装飾を適用
            formatted_text = plain_text
            
            if annotations.get("bold"):
                formatted_text = f"**{formatted_text}**"
            if annotations.get("italic"):
                formatted_text = f"*{formatted_text}*"
            if annotations.get("strikethrough"):
                formatted_text = f"~~{formatted_text}~~"
            if annotations.get("underline"):
                # Markdownには下線がないため、HTMLタグを使用
                formatted_text = f"<u>{formatted_text}</u>"
            if annotations.get("code"):
                formatted_text = f"`{formatted_text}`"
            
            # リンクの処理
            if href:
                formatted_text = f"[{formatted_text}]({href})"
            
            result_parts.append(formatted_text)
        
        return "".join(result_parts)
    
    def _get_callout_icon(self, icon: Dict[str, Any]) -> str:
        """コールアウトアイコンを取得"""
        if not icon:
            return "💡"
        
        if icon.get("type") == "emoji":
            return icon.get("emoji", "💡")
        elif icon.get("type") == "external":
            return "🔗"
        elif icon.get("type") == "file":
            return "📎"
        else:
            return "💡"
    
    def _convert_single_block(self, block: NotionBlock) -> Optional[str]:
        """
        単一のNotionブロックをMarkdownに変換
        
        Args:
            block: NotionBlockオブジェクト
            
        Returns:
            変換されたMarkdown文字列（変換不可の場合はNone）
        """
        block_type = block.type
        
        # 基本的なテキストブロック
        if block_type == "paragraph":
            return self._convert_paragraph_block(block)
        elif block_type in ["heading_1", "heading_2", "heading_3"]:
            return self._convert_heading_block(block)
        elif block_type == "bulleted_list_item":
            return self._convert_bulleted_list_block(block)
        elif block_type == "numbered_list_item":
            return self._convert_numbered_list_block(block)
        elif block_type == "to_do":
            return self._convert_todo_block(block)
        elif block_type == "quote":
            return self._convert_quote_block(block)
        elif block_type == "callout":
            return self._convert_callout_block(block)
        elif block_type == "divider":
            return self._convert_divider_block(block)
        
        # 高度なブロック
        elif block_type == "code":
            return self._convert_code_block(block)
        elif block_type == "image":
            return self._convert_image_block(block)
        elif block_type == "table":
            return self._convert_table_block(block)
        elif block_type == "table_row":
            return self._convert_table_row_block(block)
        elif block_type == "toggle":
            return self._convert_toggle_block(block)
        elif block_type == "equation":
            return self._convert_equation_block(block)
        elif block_type == "bookmark":
            return self._convert_bookmark_block(block)
        elif block_type == "file":
            return self._convert_file_block(block)
        elif block_type == "video":
            return self._convert_video_block(block)
        
        # 制限のあるブロックタイプの代替表現
        elif block_type == "child_database":
            return self._convert_database_block(block)
        elif block_type == "column_list":
            return self._convert_column_list_block(block)
        elif block_type == "column":
            return self._convert_column_block(block)
        elif block_type == "synced_block":
            return self._convert_synced_block(block)
        elif block_type == "template":
            return self._convert_template_block(block)
        elif block_type == "link_to_page":
            return self._convert_link_to_page_block(block)
        elif block_type == "table_of_contents":
            return self._convert_table_of_contents_block(block)
        elif block_type == "breadcrumb":
            return self._convert_breadcrumb_block(block)
        
        # サポートされていないブロック
        else:
            return self._handle_unsupported_block(block)
    
    def _convert_paragraph_block(self, block: NotionBlock) -> str:
        """段落ブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "paragraph")
        return text_content if text_content.strip() else ""
    
    def _convert_heading_block(self, block: NotionBlock) -> str:
        """見出しブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, block.type)
        if not text_content.strip():
            return ""
        
        level_map = {"heading_1": "#", "heading_2": "##", "heading_3": "###"}
        prefix = level_map.get(block.type, "#")
        return f"{prefix} {text_content}"
    
    def _convert_bulleted_list_block(self, block: NotionBlock) -> str:
        """箇条書きリストブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "bulleted_list_item")
        return f"- {text_content}" if text_content.strip() else ""
    
    def _convert_numbered_list_block(self, block: NotionBlock) -> str:
        """番号付きリストブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "numbered_list_item")
        return f"1. {text_content}" if text_content.strip() else ""
    
    def _convert_todo_block(self, block: NotionBlock) -> str:
        """TODOブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "to_do")
        todo_data = block.content.get("to_do", {})
        checked = todo_data.get("checked", False)
        checkbox = "[x]" if checked else "[ ]"
        return f"- {checkbox} {text_content}" if text_content.strip() else f"- {checkbox}"
    
    def _convert_quote_block(self, block: NotionBlock) -> str:
        """引用ブロックの変換"""
        text_content = self._extract_rich_text_from_block(block, "quote")
        return f"> {text_content}" if text_content.strip() else ""
    
    def _convert_callout_block(self, block: NotionBlock) -> str:
        """コールアウトブロックの変換（拡張版を使用）"""
        return self._convert_enhanced_callout_block(block)
    
    def _convert_divider_block(self, block: NotionBlock) -> str:
        """区切り線ブロックの変換"""
        return "---"
    
    def _convert_code_block(self, block: NotionBlock) -> str:
        """コードブロックの変換"""
        code_data = block.content.get("code", {})
        text_content = self._extract_rich_text_from_content(code_data.get("rich_text", []))
        language = code_data.get("language", "")
        
        # 言語の正規化
        language_map = {
            "plain text": "",
            "javascript": "javascript",
            "typescript": "typescript",
            "python": "python",
            "java": "java",
            "c": "c",
            "c++": "cpp",
            "c#": "csharp",
            "go": "go",
            "rust": "rust",
            "php": "php",
            "ruby": "ruby",
            "swift": "swift",
            "kotlin": "kotlin",
            "scala": "scala",
            "shell": "bash",
            "bash": "bash",
            "powershell": "powershell",
            "sql": "sql",
            "html": "html",
            "css": "css",
            "json": "json",
            "xml": "xml",
            "yaml": "yaml",
            "markdown": "markdown"
        }
        
        normalized_language = language_map.get(language.lower(), language)
        
        return f"```{normalized_language}\n{text_content}\n```"
    
    def _convert_image_block(self, block: NotionBlock) -> str:
        """画像ブロックの変換"""
        image_data = block.content.get("image", {})
        
        # 画像URLの取得
        image_url = ""
        if image_data.get("type") == "external":
            image_url = image_data.get("external", {}).get("url", "")
        elif image_data.get("type") == "file":
            image_url = image_data.get("file", {}).get("url", "")
        
        # キャプションの取得
        caption_content = ""
        if image_data.get("caption"):
            caption_content = self._extract_rich_text_from_content(image_data["caption"])
        
        # 設定に応じて処理方法を変更
        if self.config.convert_images and image_url:
            alt_text = caption_content if caption_content else "画像"
            return f"![{alt_text}]({image_url})"
        else:
            # 画像をダウンロードしない場合はリンクとして表示
            if caption_content:
                return f"[画像: {caption_content}]({image_url})" if image_url else f"画像: {caption_content}"
            else:
                return f"[画像]({image_url})" if image_url else "画像"
    
    def _convert_table_block(self, block: NotionBlock) -> str:
        """テーブルブロックの変換"""
        # テーブルブロック自体は子ブロック（table_row）を持つコンテナ
        # 実際の変換は子ブロックで行われるため、ここでは空文字を返す
        return ""
    
    def _convert_table_row_block(self, block: NotionBlock) -> str:
        """テーブル行ブロックの変換"""
        table_row_data = block.content.get("table_row", {})
        cells = table_row_data.get("cells", [])
        
        if not cells:
            return ""
        
        # 各セルの内容を抽出
        cell_contents = []
        for cell in cells:
            cell_text = self._extract_rich_text_from_content(cell)
            # パイプ文字をエスケープ
            cell_text = cell_text.replace("|", "\\|") if self.config.get_block_setting("table", "escape_pipes", True) else cell_text
            cell_contents.append(cell_text)
        
        # Markdownテーブル行として出力
        return "| " + " | ".join(cell_contents) + " |"
    
    def _convert_toggle_block(self, block: NotionBlock) -> str:
        """トグルブロックの変換（拡張版を使用）"""
        return self._convert_enhanced_toggle_block(block)
    
    def _convert_equation_block(self, block: NotionBlock) -> str:
        """数式ブロックの変換"""
        equation_data = block.content.get("equation", {})
        expression = equation_data.get("expression", "")
        
        if not expression:
            return ""
        
        # 設定に応じてLaTeX形式で出力
        if self.config.convert_equations:
            block_format = self.config.get_block_setting("equation", "block_format", "$$\n{}\n$$")
            return block_format.format(expression)
        else:
            return f"数式: {expression}"
    
    def _convert_bookmark_block(self, block: NotionBlock) -> str:
        """ブックマークブロックの変換"""
        bookmark_data = block.content.get("bookmark", {})
        url = bookmark_data.get("url", "")
        caption_content = ""
        
        if bookmark_data.get("caption"):
            caption_content = self._extract_rich_text_from_content(bookmark_data["caption"])
        
        # 設定に応じて表示方法を変更
        if self.config.get_block_setting("bookmark", "use_title_as_text", True):
            link_text = caption_content if caption_content else url
            return f"[{link_text}]({url})" if url else caption_content
        else:
            if caption_content:
                return f"🔖 [{caption_content}]({url})" if url else f"🔖 {caption_content}"
            else:
                return f"🔖 {url}" if url else "🔖 ブックマーク"
    
    def _convert_file_block(self, block: NotionBlock) -> str:
        """ファイルブロックの変換"""
        file_data = block.content.get("file", {})
        
        # ファイルURLの取得
        file_url = ""
        file_name = ""
        
        if file_data.get("type") == "external":
            file_url = file_data.get("external", {}).get("url", "")
        elif file_data.get("type") == "file":
            file_url = file_data.get("file", {}).get("url", "")
        
        # ファイル名の取得
        if file_data.get("name"):
            file_name = file_data["name"]
        else:
            file_name = file_url.split("/")[-1] if file_url else "ファイル"
        
        # キャプションの取得
        caption_content = ""
        if file_data.get("caption"):
            caption_content = self._extract_rich_text_from_content(file_data["caption"])
        
        display_name = caption_content if caption_content else file_name
        
        if file_url:
            return f"📎 [{display_name}]({file_url})"
        else:
            return f"📎 {display_name}"
    
    def _convert_video_block(self, block: NotionBlock) -> str:
        """動画ブロックの変換"""
        video_data = block.content.get("video", {})
        
        # 動画URLの取得
        video_url = ""
        if video_data.get("type") == "external":
            video_url = video_data.get("external", {}).get("url", "")
        elif video_data.get("type") == "file":
            video_url = video_data.get("file", {}).get("url", "")
        
        # キャプションの取得
        caption_content = ""
        if video_data.get("caption"):
            caption_content = self._extract_rich_text_from_content(video_data["caption"])
        
        # 設定に応じて埋め込みまたはリンクとして表示
        if self.config.get_block_setting("video", "embed_videos", False):
            # 埋め込み対応（YouTube、Vimeoなど）
            if "youtube.com" in video_url or "youtu.be" in video_url:
                # YouTube埋め込み用のMarkdown（一部のMarkdownプロセッサーでサポート）
                return f"[![{caption_content if caption_content else '動画'}]({video_url})]({video_url})"
            else:
                return f"🎥 [{caption_content if caption_content else '動画'}]({video_url})" if video_url else f"🎥 {caption_content}"
        else:
            return f"🎥 [{caption_content if caption_content else '動画'}]({video_url})" if video_url else f"🎥 {caption_content}"
    
    def _handle_unsupported_block(self, block: NotionBlock) -> Optional[str]:
        """サポートされていないブロックの処理"""
        # 直接設定を確認
        if self.config.unsupported_blocks == "skip":
            return None
        elif self.config.unsupported_blocks == "placeholder":
            return f"<!-- サポートされていないブロック: {block.type} -->"
        elif self.config.unsupported_blocks == "warning":
            self.logger.warning(f"サポートされていないブロックタイプ: {block.type}")
            return f"<!-- 警告: {block.type}ブロックはサポートされていません -->"
        else:
            return f"<!-- サポートされていないブロック: {block.type} -->"
    
    def _extract_rich_text_from_block(self, block: NotionBlock, block_type: str) -> str:
        """ブロックからリッチテキストを抽出"""
        block_content = block.content.get(block_type, {})
        rich_text_data = block_content.get("rich_text", [])
        return self._extract_rich_text_from_content(rich_text_data)
    
    def _extract_rich_text_from_content(self, rich_text_data: List[Dict[str, Any]]) -> str:
        """リッチテキストデータからMarkdown形式のテキストを抽出"""
        if not rich_text_data:
            return ""
        
        result_parts = []
        
        for text_item in rich_text_data:
            plain_text = text_item.get("plain_text", "")
            annotations = text_item.get("annotations", {})
            href = text_item.get("href")
            
            # テキストの装飾を適用
            formatted_text = plain_text
            
            if annotations.get("bold"):
                formatted_text = f"**{formatted_text}**"
            if annotations.get("italic"):
                formatted_text = f"*{formatted_text}*"
            if annotations.get("strikethrough"):
                formatted_text = f"~~{formatted_text}~~"
            if annotations.get("underline"):
                # Markdownには下線がないため、HTMLタグを使用
                formatted_text = f"<u>{formatted_text}</u>"
            if annotations.get("code"):
                formatted_text = f"`{formatted_text}`"
            
            # リンクの処理
            if href:
                formatted_text = f"[{formatted_text}]({href})"
            
            result_parts.append(formatted_text)
        
        return "".join(result_parts)  
  
    # 制限のあるブロックタイプの代替表現メソッド
    
    def _convert_database_block(self, block: NotionBlock) -> str:
        """データベースブロックの代替表現変換"""
        database_data = block.content.get("child_database", {})
        title = database_data.get("title", "データベース")
        
        # 設定に応じて変換方法を変更
        if self.config.database_mode == "table":
            # Markdownテーブル形式で表現
            return f"## 📊 {title}\n\n| 項目 | 値 |\n|------|----|\n| タイプ | データベース |\n| タイトル | {title} |\n\n> **注意**: このデータベースの詳細内容は同期されません。Notionで直接確認してください。"
        elif self.config.database_mode == "description":
            # 説明テキスト形式で表現
            return f"📊 **データベース: {title}**\n\nこのセクションにはNotionデータベース「{title}」が埋め込まれています。データベースの内容を確認するには、Notionで直接アクセスしてください。"
        else:  # skip
            return None
    
    def _convert_column_list_block(self, block: NotionBlock) -> str:
        """カラムリストブロックの代替表現変換"""
        # 設定に応じて変換方法を変更
        if self.config.column_layout == "separator":
            # 水平線区切りで表現
            return "\n---\n**📋 カラムレイアウト開始**\n---\n"
        elif self.config.column_layout == "merge":
            # 単純に結合（区切りなし）
            return ""
        else:  # warning_only
            return "<!-- カラムレイアウトが検出されました。Markdownでは正確に再現できません。 -->"
    
    def _convert_column_block(self, block: NotionBlock) -> str:
        """カラムブロックの代替表現変換"""
        # 設定に応じて変換方法を変更
        if self.config.column_layout == "separator":
            # カラム区切りを表現
            return "\n**📄 カラム**\n"
        elif self.config.column_layout == "merge":
            # 区切りなしで結合
            return ""
        else:  # warning_only
            return "<!-- カラム区切り -->"
    
    def _convert_synced_block(self, block: NotionBlock) -> str:
        """同期ブロックの代替表現変換"""
        synced_data = block.content.get("synced_block", {})
        synced_from = synced_data.get("synced_from")
        
        if synced_from:
            # 他のブロックから同期されている場合
            return f"🔄 **同期ブロック**\n\n> このコンテンツは他の場所から同期されています。\n> 同期元: {synced_from.get('block_id', '不明')}"
        else:
            # オリジナルの同期ブロック
            return "🔄 **同期ブロック（オリジナル）**\n\n> このブロックは他の場所で参照される可能性があります。"
    
    def _convert_template_block(self, block: NotionBlock) -> str:
        """テンプレートブロックの代替表現変換"""
        template_data = block.content.get("template", {})
        title = self._extract_rich_text_from_content(template_data.get("rich_text", []))
        
        return f"📋 **テンプレート: {title if title else 'テンプレート'}**\n\n> このセクションはNotionテンプレートです。実際の使用時には動的にコンテンツが生成されます。"
    
    def _convert_link_to_page_block(self, block: NotionBlock) -> str:
        """ページリンクブロックの代替表現変換"""
        link_data = block.content.get("link_to_page", {})
        page_id = ""
        
        if link_data.get("type") == "page_id":
            page_id = link_data.get("page_id", "")
        elif link_data.get("type") == "database_id":
            page_id = link_data.get("database_id", "")
        
        if page_id:
            return f"🔗 **[ページリンク](https://notion.so/{page_id.replace('-', '')})**"
        else:
            return "🔗 **ページリンク** (リンク先不明)"
    
    def _convert_table_of_contents_block(self, block: NotionBlock) -> str:
        """目次ブロックの代替表現変換"""
        toc_data = block.content.get("table_of_contents", {})
        color = toc_data.get("color", "default")
        
        return f"📑 **目次**\n\n> この位置にページの目次が表示されます。\n> Markdownビューアーによっては自動的に目次が生成される場合があります。"
    
    def _convert_breadcrumb_block(self, block: NotionBlock) -> str:
        """パンくずリストブロックの代替表現変換"""
        return "🍞 **パンくずリスト**\n\n> ホーム > ... > 現在のページ\n> \n> 実際のパンくずリストはNotionで確認してください。"
    
    def _convert_enhanced_callout_block(self, block: NotionBlock) -> str:
        """拡張コールアウトブロックの変換（色とスタイル対応）"""
        callout_data = block.content.get("callout", {})
        text_content = self._extract_rich_text_from_content(callout_data.get("rich_text", []))
        icon = callout_data.get("icon", {})
        color = callout_data.get("color", "default")
        
        # アイコンの処理
        icon_text = self._get_callout_icon(icon)
        
        # 色に応じたスタイル設定
        color_styles = {
            "gray": "💭",
            "brown": "🤎", 
            "orange": "🧡",
            "yellow": "💛",
            "green": "💚",
            "blue": "💙",
            "purple": "💜",
            "pink": "💖",
            "red": "❤️"
        }
        
        color_icon = color_styles.get(color, "")
        if color_icon and color != "default":
            icon_text = f"{color_icon} {icon_text}"
        
        # 設定に応じた変換
        if self.config.get_block_setting("callout", "use_quote_format", True):
            if self.config.get_block_setting("callout", "preserve_color", False) and color != "default":
                return f"> {icon_text} **{text_content}** `({color})`"
            else:
                return f"> {icon_text} **{text_content}**"
        else:
            return f"{icon_text} {text_content}"
    
    def _get_callout_icon(self, icon: Dict[str, Any]) -> str:
        """コールアウトアイコンを取得"""
        if not icon:
            return "💡"
        
        if icon.get("type") == "emoji":
            return icon.get("emoji", "💡")
        elif icon.get("type") == "external":
            return "🔗"
        elif icon.get("type") == "file":
            return "📎"
        else:
            return "💡"
    
    def _convert_enhanced_toggle_block(self, block: NotionBlock) -> str:
        """拡張トグルブロックの変換（折りたたみ可能なMarkdown）"""
        text_content = self._extract_rich_text_from_block(block, "toggle")
        
        # 設定に応じて変換方法を変更
        if self.config.get_block_setting("toggle", "use_details_tag", True):
            expand_by_default = self.config.get_block_setting("toggle", "expand_by_default", False)
            open_attr = " open" if expand_by_default else ""
            
            # 子ブロックがある場合の処理を想定
            child_content = "<!-- 子コンテンツがここに表示されます -->"
            if hasattr(block, 'children') and block.children:
                child_markdown = self.convert_blocks_to_markdown(block.children)
                child_content = child_markdown if child_markdown.strip() else child_content
            
            return f"<details{open_attr}>\n<summary>{text_content}</summary>\n\n{child_content}\n\n</details>"
        else:
            # シンプルな太字表現
            return f"**▶ {text_content}**"
"""
Notion to Markdown変換制限の文書化と警告システム
"""

import logging
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass
from enum import Enum

from models.config import ConversionConfig


class BlockSupportLevel(Enum):
    """ブロックサポートレベル"""
    FULLY_SUPPORTED = "fully_supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    ALTERNATIVE_REPRESENTATION = "alternative_representation"
    NOT_SUPPORTED = "not_supported"


@dataclass
class BlockLimitation:
    """ブロック制限情報"""
    block_type: str
    support_level: BlockSupportLevel
    description: str
    alternative_description: Optional[str] = None
    markdown_example: Optional[str] = None
    notion_features_lost: List[str] = None
    
    def __post_init__(self):
        if self.notion_features_lost is None:
            self.notion_features_lost = []


class ConversionLimitationTracker:
    """変換制限追跡システム"""
    
    # サポートされていないブロックタイプの定義
    UNSUPPORTED_BLOCKS = {
        "ai_block": "AI生成ブロック",
        "audio": "音声ファイル",
        "embed": "外部埋め込み",
        "pdf": "PDFファイル",
        "unsupported": "未対応ブロック",
        "child_page": "子ページ",
        "link_preview": "リンクプレビュー"
    }
    
    # 制限のあるブロックタイプの定義
    LIMITED_BLOCKS = {
        "child_database": BlockLimitation(
            block_type="child_database",
            support_level=BlockSupportLevel.ALTERNATIVE_REPRESENTATION,
            description="データベースブロックは完全には再現できません",
            alternative_description="Markdownテーブルまたは説明テキストとして表現",
            markdown_example="## 📊 データベース名\n\n| 項目 | 値 |\n|------|----|\n| タイプ | データベース |",
            notion_features_lost=["データベース機能", "フィルタリング", "ソート", "ビュー切り替え"]
        ),
        "column_list": BlockLimitation(
            block_type="column_list",
            support_level=BlockSupportLevel.ALTERNATIVE_REPRESENTATION,
            description="カラムレイアウトはMarkdownでは正確に再現できません",
            alternative_description="水平線区切りまたは連続セクションとして表現",
            markdown_example="---\n**📋 カラムレイアウト開始**\n---",
            notion_features_lost=["カラム幅調整", "レスポンシブレイアウト"]
        ),
        "column": BlockLimitation(
            block_type="column",
            support_level=BlockSupportLevel.ALTERNATIVE_REPRESENTATION,
            description="個別カラムは区切り線で表現",
            alternative_description="セクション区切りとして表現",
            markdown_example="**📄 カラム**",
            notion_features_lost=["カラム幅", "並列表示"]
        ),
        "synced_block": BlockLimitation(
            block_type="synced_block",
            support_level=BlockSupportLevel.ALTERNATIVE_REPRESENTATION,
            description="同期ブロックは静的テキストとして表現",
            alternative_description="同期情報を含む説明テキスト",
            markdown_example="🔄 **同期ブロック**\n\n> このコンテンツは他の場所から同期されています。",
            notion_features_lost=["リアルタイム同期", "双方向更新"]
        ),
        "template": BlockLimitation(
            block_type="template",
            support_level=BlockSupportLevel.ALTERNATIVE_REPRESENTATION,
            description="テンプレートブロックは説明テキストとして表現",
            alternative_description="テンプレート情報を含む説明",
            markdown_example="📋 **テンプレート: テンプレート名**\n\n> 動的にコンテンツが生成されます。",
            notion_features_lost=["動的生成", "テンプレート機能"]
        ),
        "callout": BlockLimitation(
            block_type="callout",
            support_level=BlockSupportLevel.PARTIALLY_SUPPORTED,
            description="コールアウトは引用ブロックとして表現",
            alternative_description="引用ブロック + アイコン + 太字テキスト",
            markdown_example="> 💡 **重要な情報**",
            notion_features_lost=["背景色", "カスタムスタイル"]
        ),
        "toggle": BlockLimitation(
            block_type="toggle",
            support_level=BlockSupportLevel.PARTIALLY_SUPPORTED,
            description="トグルブロックはHTML detailsタグまたは太字として表現",
            alternative_description="折りたたみ可能なHTML要素",
            markdown_example="<details>\n<summary>タイトル</summary>\n\n内容\n\n</details>",
            notion_features_lost=["Notion固有のスタイル"]
        )
    }
    
    def __init__(self, config: ConversionConfig):
        """
        初期化
        
        Args:
            config: 変換設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.encountered_blocks: Set[str] = set()
        self.conversion_warnings: List[str] = []
        self.unsupported_block_counts: Dict[str, int] = {}
        self.limitation_reports: List[Dict[str, Any]] = []
    
    def track_block_conversion(self, block_type: str, success: bool = True, 
                             warning_message: Optional[str] = None):
        """
        ブロック変換を追跡
        
        Args:
            block_type: ブロックタイプ
            success: 変換成功フラグ
            warning_message: 警告メッセージ
        """
        self.encountered_blocks.add(block_type)
        
        if not success or warning_message:
            if block_type in self.UNSUPPORTED_BLOCKS:
                self.unsupported_block_counts[block_type] = \
                    self.unsupported_block_counts.get(block_type, 0) + 1
                
                if warning_message:
                    self.conversion_warnings.append(warning_message)
                else:
                    self.conversion_warnings.append(
                        f"サポートされていないブロック: {self.UNSUPPORTED_BLOCKS[block_type]} ({block_type})"
                    )
            
            elif block_type in self.LIMITED_BLOCKS:
                limitation = self.LIMITED_BLOCKS[block_type]
                self.limitation_reports.append({
                    "block_type": block_type,
                    "support_level": limitation.support_level.value,
                    "description": limitation.description,
                    "features_lost": limitation.notion_features_lost
                })
                
                if warning_message:
                    self.conversion_warnings.append(warning_message)
                else:
                    self.conversion_warnings.append(
                        f"制限あり: {limitation.description}"
                    )
    
    def get_unsupported_blocks_list(self) -> List[Dict[str, str]]:
        """
        サポートされていないブロックタイプのリストを取得
        
        Returns:
            サポートされていないブロックのリスト
        """
        return [
            {
                "block_type": block_type,
                "description": description,
                "reason": "Markdownでは表現できない機能"
            }
            for block_type, description in self.UNSUPPORTED_BLOCKS.items()
        ]
    
    def get_limited_blocks_list(self) -> List[Dict[str, Any]]:
        """
        制限のあるブロックタイプのリストを取得
        
        Returns:
            制限のあるブロックのリスト
        """
        return [
            {
                "block_type": limitation.block_type,
                "support_level": limitation.support_level.value,
                "description": limitation.description,
                "alternative_description": limitation.alternative_description,
                "markdown_example": limitation.markdown_example,
                "notion_features_lost": limitation.notion_features_lost
            }
            for limitation in self.LIMITED_BLOCKS.values()
        ]
    
    def generate_conversion_quality_report(self) -> Dict[str, Any]:
        """
        変換品質レポートを生成
        
        Returns:
            変換品質レポート
        """
        total_blocks = len(self.encountered_blocks)
        unsupported_count = len([b for b in self.encountered_blocks 
                               if b in self.UNSUPPORTED_BLOCKS])
        limited_count = len([b for b in self.encountered_blocks 
                           if b in self.LIMITED_BLOCKS])
        fully_supported_count = total_blocks - unsupported_count - limited_count
        
        quality_score = 0
        if total_blocks > 0:
            quality_score = (fully_supported_count * 100 + limited_count * 60) / (total_blocks * 100)
        
        return {
            "conversion_quality_score": round(quality_score * 100, 2),
            "total_blocks_encountered": total_blocks,
            "fully_supported_blocks": fully_supported_count,
            "limited_support_blocks": limited_count,
            "unsupported_blocks": unsupported_count,
            "encountered_block_types": list(self.encountered_blocks),
            "unsupported_block_counts": self.unsupported_block_counts,
            "conversion_warnings": self.conversion_warnings,
            "limitation_reports": self.limitation_reports,
            "quality_assessment": self._get_quality_assessment(quality_score)
        }
    
    def _get_quality_assessment(self, quality_score: float) -> str:
        """
        品質評価を取得
        
        Args:
            quality_score: 品質スコア (0.0-1.0)
            
        Returns:
            品質評価文字列
        """
        if quality_score >= 0.9:
            return "優秀 - ほぼ完全な変換"
        elif quality_score >= 0.7:
            return "良好 - 一部制限あり"
        elif quality_score >= 0.5:
            return "普通 - 多くの制限あり"
        else:
            return "要改善 - 大幅な制限あり"
    
    def log_conversion_warnings(self):
        """変換警告をログに記録"""
        if self.conversion_warnings:
            self.logger.warning(f"変換中に{len(self.conversion_warnings)}個の警告が発生しました:")
            for warning in self.conversion_warnings:
                self.logger.warning(f"  - {warning}")
    
    def get_markdown_documentation(self) -> str:
        """
        変換制限のMarkdown文書を生成
        
        Returns:
            Markdown形式の制限文書
        """
        doc_lines = [
            "# Notion to Markdown 変換制限について",
            "",
            "このドキュメントでは、NotionからMarkdownへの変換における制限事項について説明します。",
            "",
            "## サポート状況の分類",
            "",
            "- **完全サポート**: Markdownで完全に再現可能",
            "- **部分サポート**: 基本機能は再現可能だが、一部制限あり", 
            "- **代替表現**: 異なる形式で表現",
            "- **未サポート**: 変換不可",
            "",
            "## サポートされていないブロックタイプ",
            ""
        ]
        
        for block_info in self.get_unsupported_blocks_list():
            doc_lines.extend([
                f"### {block_info['block_type']}",
                f"- **説明**: {block_info['description']}",
                f"- **理由**: {block_info['reason']}",
                ""
            ])
        
        doc_lines.extend([
            "## 制限のあるブロックタイプ",
            ""
        ])
        
        for block_info in self.get_limited_blocks_list():
            doc_lines.extend([
                f"### {block_info['block_type']}",
                f"- **サポートレベル**: {block_info['support_level']}",
                f"- **説明**: {block_info['description']}",
                f"- **代替表現**: {block_info['alternative_description']}",
                ""
            ])
            
            if block_info['markdown_example']:
                doc_lines.extend([
                    "**Markdown例:**",
                    "```markdown",
                    block_info['markdown_example'],
                    "```",
                    ""
                ])
            
            if block_info['notion_features_lost']:
                doc_lines.extend([
                    "**失われるNotion機能:**",
                    *[f"- {feature}" for feature in block_info['notion_features_lost']],
                    ""
                ])
        
        doc_lines.extend([
            "## 変換品質の向上について",
            "",
            "変換品質を向上させるには:",
            "1. サポートされているブロックタイプを優先的に使用",
            "2. 複雑なレイアウトは避ける",
            "3. 代替表現で十分な場合は受け入れる",
            "",
            "## 設定による制限対応",
            "",
            "設定ファイルで以下の動作を制御できます:",
            "- `unsupported_blocks`: skip/placeholder/warning",
            "- `database_mode`: table/description/skip", 
            "- `column_layout`: separator/merge/warning_only",
            ""
        ])
        
        return "\n".join(doc_lines)


class ConversionWarningSystem:
    """変換警告システム"""
    
    def __init__(self, limitation_tracker: ConversionLimitationTracker):
        """
        初期化
        
        Args:
            limitation_tracker: 制限追跡システム
        """
        self.tracker = limitation_tracker
        self.logger = logging.getLogger(__name__)
    
    def warn_unsupported_block(self, block_type: str, context: str = ""):
        """
        サポートされていないブロックの警告
        
        Args:
            block_type: ブロックタイプ
            context: コンテキスト情報
        """
        message = f"サポートされていないブロック '{block_type}' が検出されました"
        if context:
            message += f" (コンテキスト: {context})"
        
        self.logger.warning(message)
        self.tracker.track_block_conversion(block_type, success=False, warning_message=message)
    
    def warn_limited_block(self, block_type: str, limitation_description: str, context: str = ""):
        """
        制限のあるブロックの警告
        
        Args:
            block_type: ブロックタイプ
            limitation_description: 制限の説明
            context: コンテキスト情報
        """
        message = f"制限あり: {block_type} - {limitation_description}"
        if context:
            message += f" (コンテキスト: {context})"
        
        self.logger.info(message)
        self.tracker.track_block_conversion(block_type, success=True, warning_message=message)
    
    def generate_user_friendly_warnings(self) -> List[str]:
        """
        ユーザー向けの分かりやすい警告メッセージを生成
        
        Returns:
            ユーザー向け警告メッセージのリスト
        """
        warnings = []
        
        if self.tracker.unsupported_block_counts:
            warnings.append("⚠️  一部のNotionブロックは変換できませんでした:")
            for block_type, count in self.tracker.unsupported_block_counts.items():
                block_name = self.tracker.UNSUPPORTED_BLOCKS.get(block_type, block_type)
                warnings.append(f"   • {block_name}: {count}個")
        
        if self.tracker.limitation_reports:
            warnings.append("ℹ️  一部のブロックは制限付きで変換されました:")
            for report in self.tracker.limitation_reports:
                warnings.append(f"   • {report['block_type']}: {report['description']}")
        
        return warnings
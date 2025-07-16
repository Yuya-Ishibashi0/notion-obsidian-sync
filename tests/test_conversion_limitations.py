"""
変換制限システムのユニットテスト
"""

import pytest
from unittest.mock import Mock, patch
import logging

from services.conversion_limitations import (
    ConversionLimitationTracker, ConversionWarningSystem, 
    BlockLimitation, BlockSupportLevel
)
from models.config import ConversionConfig


class TestConversionLimitationTracker:
    """ConversionLimitationTracker のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.config = ConversionConfig()
        self.tracker = ConversionLimitationTracker(self.config)
    
    def test_initialization(self):
        """初期化テスト"""
        assert self.tracker.config == self.config
        assert len(self.tracker.encountered_blocks) == 0
        assert len(self.tracker.conversion_warnings) == 0
        assert len(self.tracker.unsupported_block_counts) == 0
        assert len(self.tracker.limitation_reports) == 0
    
    def test_track_successful_block_conversion(self):
        """成功したブロック変換の追跡テスト"""
        self.tracker.track_block_conversion("paragraph", success=True)
        
        assert "paragraph" in self.tracker.encountered_blocks
        assert len(self.tracker.conversion_warnings) == 0
    
    def test_track_unsupported_block_conversion(self):
        """サポートされていないブロック変換の追跡テスト"""
        self.tracker.track_block_conversion("ai_block", success=False)
        
        assert "ai_block" in self.tracker.encountered_blocks
        assert self.tracker.unsupported_block_counts["ai_block"] == 1
        assert len(self.tracker.conversion_warnings) == 1
        assert "AI生成ブロック" in self.tracker.conversion_warnings[0]
    
    def test_track_limited_block_conversion(self):
        """制限のあるブロック変換の追跡テスト"""
        self.tracker.track_block_conversion("child_database", success=True, 
                                          warning_message="データベース機能は制限されます")
        
        assert "child_database" in self.tracker.encountered_blocks
        assert len(self.tracker.limitation_reports) == 1
        assert self.tracker.limitation_reports[0]["block_type"] == "child_database"
        assert len(self.tracker.conversion_warnings) == 1
    
    def test_get_unsupported_blocks_list(self):
        """サポートされていないブロックリストの取得テスト"""
        unsupported_list = self.tracker.get_unsupported_blocks_list()
        
        assert len(unsupported_list) > 0
        assert any(block["block_type"] == "ai_block" for block in unsupported_list)
        assert any(block["description"] == "AI生成ブロック" for block in unsupported_list)
    
    def test_get_limited_blocks_list(self):
        """制限のあるブロックリストの取得テスト"""
        limited_list = self.tracker.get_limited_blocks_list()
        
        assert len(limited_list) > 0
        database_block = next((block for block in limited_list 
                             if block["block_type"] == "child_database"), None)
        assert database_block is not None
        assert database_block["support_level"] == "alternative_representation"
        assert "データベース機能" in database_block["notion_features_lost"]
    
    def test_generate_conversion_quality_report(self):
        """変換品質レポート生成テスト"""
        # 様々なブロックタイプを追跡
        self.tracker.track_block_conversion("paragraph", success=True)
        self.tracker.track_block_conversion("heading_1", success=True)
        self.tracker.track_block_conversion("child_database", success=True, 
                                          warning_message="制限あり")
        self.tracker.track_block_conversion("ai_block", success=False)
        
        report = self.tracker.generate_conversion_quality_report()
        
        assert report["total_blocks_encountered"] == 4
        assert report["fully_supported_blocks"] == 2
        assert report["limited_support_blocks"] == 1
        assert report["unsupported_blocks"] == 1
        assert 0 < report["conversion_quality_score"] < 100
        assert "paragraph" in report["encountered_block_types"]
        assert len(report["conversion_warnings"]) == 2
    
    def test_quality_assessment(self):
        """品質評価テスト"""
        # 高品質スコア
        high_quality_assessment = self.tracker._get_quality_assessment(0.95)
        assert "優秀" in high_quality_assessment
        
        # 中品質スコア
        medium_quality_assessment = self.tracker._get_quality_assessment(0.75)
        assert "良好" in medium_quality_assessment
        
        # 低品質スコア
        low_quality_assessment = self.tracker._get_quality_assessment(0.3)
        assert "要改善" in low_quality_assessment
    
    def test_log_conversion_warnings(self):
        """変換警告のログ記録テスト"""
        # 警告を追加
        self.tracker.conversion_warnings = ["警告1", "警告2"]
        
        # ログ記録を実行（例外が発生しないことを確認）
        try:
            self.tracker.log_conversion_warnings()
            assert True  # 例外が発生しなければ成功
        except Exception as e:
            pytest.fail(f"ログ記録でエラーが発生: {e}")
    
    def test_get_markdown_documentation(self):
        """Markdown文書生成テスト"""
        doc = self.tracker.get_markdown_documentation()
        
        assert "# Notion to Markdown 変換制限について" in doc
        assert "## サポートされていないブロックタイプ" in doc
        assert "## 制限のあるブロックタイプ" in doc
        assert "ai_block" in doc
        assert "child_database" in doc
        assert "設定による制限対応" in doc


class TestConversionWarningSystem:
    """ConversionWarningSystem のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.config = ConversionConfig()
        self.tracker = ConversionLimitationTracker(self.config)
        self.warning_system = ConversionWarningSystem(self.tracker)
    
    def test_warn_unsupported_block(self):
        """サポートされていないブロックの警告テスト"""
        self.warning_system.warn_unsupported_block("ai_block", "テストコンテキスト")
        
        # 追跡システムに記録されたことを確認
        assert "ai_block" in self.tracker.encountered_blocks
        assert len(self.tracker.conversion_warnings) == 1
        assert "ai_block" in self.tracker.conversion_warnings[0]
    
    def test_warn_limited_block(self):
        """制限のあるブロックの警告テスト"""
        self.warning_system.warn_limited_block("callout", "背景色が失われます", "テストコンテキスト")
        
        # 追跡システムに記録されたことを確認
        assert "callout" in self.tracker.encountered_blocks
        assert len(self.tracker.conversion_warnings) == 1
        assert "背景色が失われます" in self.tracker.conversion_warnings[0]
    
    def test_generate_user_friendly_warnings(self):
        """ユーザー向け警告生成テスト"""
        # サポートされていないブロックを追加
        self.tracker.unsupported_block_counts = {"ai_block": 2, "audio": 1}
        
        # 制限のあるブロックを追加
        self.tracker.limitation_reports = [
            {
                "block_type": "callout",
                "description": "背景色が失われます"
            }
        ]
        
        warnings = self.warning_system.generate_user_friendly_warnings()
        
        assert len(warnings) > 0
        assert any("変換できませんでした" in warning for warning in warnings)
        assert any("制限付きで変換されました" in warning for warning in warnings)
        assert any("AI生成ブロック: 2個" in warning for warning in warnings)


class TestBlockLimitation:
    """BlockLimitation のテスト"""
    
    def test_block_limitation_creation(self):
        """BlockLimitation作成テスト"""
        limitation = BlockLimitation(
            block_type="test_block",
            support_level=BlockSupportLevel.PARTIALLY_SUPPORTED,
            description="テスト制限",
            alternative_description="代替表現",
            markdown_example="```markdown\nテスト\n```",
            notion_features_lost=["機能1", "機能2"]
        )
        
        assert limitation.block_type == "test_block"
        assert limitation.support_level == BlockSupportLevel.PARTIALLY_SUPPORTED
        assert limitation.description == "テスト制限"
        assert limitation.alternative_description == "代替表現"
        assert limitation.markdown_example == "```markdown\nテスト\n```"
        assert len(limitation.notion_features_lost) == 2
    
    def test_block_limitation_post_init(self):
        """BlockLimitation __post_init__ テスト"""
        limitation = BlockLimitation(
            block_type="test_block",
            support_level=BlockSupportLevel.FULLY_SUPPORTED,
            description="テスト"
        )
        
        # notion_features_lost が自動的に空リストに設定されることを確認
        assert limitation.notion_features_lost == []


class TestBlockSupportLevel:
    """BlockSupportLevel のテスト"""
    
    def test_support_level_values(self):
        """サポートレベルの値テスト"""
        assert BlockSupportLevel.FULLY_SUPPORTED.value == "fully_supported"
        assert BlockSupportLevel.PARTIALLY_SUPPORTED.value == "partially_supported"
        assert BlockSupportLevel.ALTERNATIVE_REPRESENTATION.value == "alternative_representation"
        assert BlockSupportLevel.NOT_SUPPORTED.value == "not_supported"


if __name__ == "__main__":
    pytest.main([__file__])
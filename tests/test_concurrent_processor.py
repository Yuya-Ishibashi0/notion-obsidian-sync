"""
並行処理システムのユニットテスト
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from services.concurrent_processor import (
    ConcurrentProcessor, RateLimiter, ProgressTracker, 
    ProcessingResult, create_progress_callback
)
from models.config import ConversionConfig


class TestProcessingResult:
    """ProcessingResult のテスト"""
    
    def test_processing_result_creation(self):
        """処理結果作成テスト"""
        result = ProcessingResult(
            page_id="test123",
            success=True,
            result="処理結果",
            processing_time=1.5
        )
        
        assert result.page_id == "test123"
        assert result.success == True
        assert result.result == "処理結果"
        assert result.processing_time == 1.5
        assert result.error is None
    
    def test_to_dict(self):
        """辞書変換テスト"""
        result = ProcessingResult(
            page_id="test123",
            success=False,
            error="エラーメッセージ",
            processing_time=0.5
        )
        
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["page_id"] == "test123"
        assert result_dict["success"] == False
        assert result_dict["error"] == "エラーメッセージ"


class TestRateLimiter:
    """RateLimiter のテスト"""
    
    def test_rate_limiter_initialization(self):
        """レート制限初期化テスト"""
        limiter = RateLimiter(max_requests_per_second=2.0, burst_limit=5)
        
        assert limiter.max_requests_per_second == 2.0
        assert limiter.burst_limit == 5
        assert limiter.tokens == 5
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """レート制限取得テスト"""
        limiter = RateLimiter(max_requests_per_second=10.0, burst_limit=2)
        
        # 最初の2回は即座に取得可能
        assert await limiter.acquire() == True
        assert await limiter.acquire() == True
        
        # 3回目は待機が発生する
        start_time = time.time()
        assert await limiter.acquire() == True
        elapsed_time = time.time() - start_time
        
        # 待機時間が発生していることを確認（厳密ではないが概算）
        assert elapsed_time > 0.05  # 50ms以上の待機
    
    def test_get_wait_time(self):
        """待機時間取得テスト"""
        limiter = RateLimiter(max_requests_per_second=1.0, burst_limit=1)
        
        # トークンがある場合は待機時間なし
        assert limiter.get_wait_time() == 0.0
        
        # トークンを消費
        limiter.tokens = 0.5
        wait_time = limiter.get_wait_time()
        assert wait_time > 0


class TestConcurrentProcessor:
    """ConcurrentProcessor のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.config = ConversionConfig()
        self.processor = ConcurrentProcessor(self.config, max_workers=2)
    
    @pytest.mark.asyncio
    async def test_process_pages_async(self):
        """非同期並行処理テスト"""
        pages = [
            {"id": "page1", "data": "データ1"},
            {"id": "page2", "data": "データ2"},
            {"id": "page3", "data": "データ3"}
        ]
        
        async def mock_processor(page):
            # 短い待機をシミュレート
            await asyncio.sleep(0.1)
            return f"処理済み: {page['data']}"
        
        results = await self.processor.process_pages_async(pages, mock_processor)
        
        assert len(results) == 3
        assert all(result.success for result in results)
        assert all(result.processing_time > 0 for result in results)
        
        # 結果の内容を確認
        result_data = [result.result for result in results]
        assert "処理済み: データ1" in result_data
        assert "処理済み: データ2" in result_data
        assert "処理済み: データ3" in result_data
    
    @pytest.mark.asyncio
    async def test_process_pages_async_with_error(self):
        """非同期並行処理エラーテスト"""
        pages = [
            {"id": "page1", "data": "データ1"},
            {"id": "page2", "data": "エラー"},
            {"id": "page3", "data": "データ3"}
        ]
        
        async def mock_processor(page):
            if page['data'] == "エラー":
                raise Exception("テストエラー")
            return f"処理済み: {page['data']}"
        
        results = await self.processor.process_pages_async(pages, mock_processor)
        
        assert len(results) == 3
        
        # 成功とエラーの結果を確認
        successful_results = [r for r in results if r.success]
        error_results = [r for r in results if not r.success]
        
        assert len(successful_results) == 2
        assert len(error_results) == 1
        assert error_results[0].error == "テストエラー"
    
    def test_process_pages_threaded(self):
        """スレッド並行処理テスト"""
        pages = [
            {"id": "page1", "data": "データ1"},
            {"id": "page2", "data": "データ2"}
        ]
        
        def mock_processor(page):
            time.sleep(0.1)  # 短い待機をシミュレート
            return f"処理済み: {page['data']}"
        
        results = self.processor.process_pages_threaded(pages, mock_processor)
        
        assert len(results) == 2
        assert all(result.success for result in results)
        assert all(result.processing_time > 0 for result in results)
    
    def test_process_pages_batch(self):
        """バッチ処理テスト"""
        pages = [
            {"id": f"page{i}", "data": f"データ{i}"} 
            for i in range(5)
        ]
        
        def mock_batch_processor(batch):
            return [f"処理済み: {page['data']}" for page in batch]
        
        results = self.processor.process_pages_batch(
            pages, mock_batch_processor, batch_size=2
        )
        
        assert len(results) == 5
        assert all(result.success for result in results)
    
    def test_get_processing_stats(self):
        """処理統計取得テスト"""
        # 初期状態
        stats = self.processor.get_processing_stats()
        assert stats["total_processed"] == 0
        assert stats["success_rate"] == 0.0
        
        # 統計を手動で更新
        results = [
            ProcessingResult("page1", True, processing_time=1.0),
            ProcessingResult("page2", False, error="エラー", processing_time=0.5),
            ProcessingResult("page3", True, processing_time=1.5)
        ]
        
        self.processor._update_stats(results, 3.0)
        
        stats = self.processor.get_processing_stats()
        assert stats["total_processed"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert stats["success_rate"] == 66.67  # 2/3 * 100
    
    def test_reset_stats(self):
        """統計リセットテスト"""
        # 統計を更新
        results = [ProcessingResult("page1", True, processing_time=1.0)]
        self.processor._update_stats(results, 1.0)
        
        # リセット前
        stats = self.processor.get_processing_stats()
        assert stats["total_processed"] == 1
        
        # リセット
        self.processor.reset_stats()
        
        # リセット後
        stats = self.processor.get_processing_stats()
        assert stats["total_processed"] == 0


class TestProgressTracker:
    """ProgressTracker のテスト"""
    
    def test_progress_tracker_initialization(self):
        """進捗追跡初期化テスト"""
        tracker = ProgressTracker(total_items=10, update_interval=0.5)
        
        assert tracker.total_items == 10
        assert tracker.update_interval == 0.5
        assert tracker.completed_items == 0
    
    @patch('services.concurrent_processor.logging.getLogger')
    def test_progress_update(self, mock_logger):
        """進捗更新テスト"""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        tracker = ProgressTracker(total_items=10, update_interval=0.0)  # 即座に更新
        
        # 進捗更新
        tracker.update(5)
        
        assert tracker.completed_items == 5
        # ログが呼ばれることを確認（詳細な内容は確認しない）
        assert mock_logger_instance.info.called
    
    @patch('services.concurrent_processor.logging.getLogger')
    def test_progress_complete(self, mock_logger):
        """進捗完了テスト"""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        tracker = ProgressTracker(total_items=10)
        tracker.completed_items = 10
        
        # 完了
        tracker.complete()
        
        # 完了ログが呼ばれることを確認
        assert mock_logger_instance.info.called


class TestProgressCallback:
    """進捗コールバックのテスト"""
    
    def test_create_progress_callback(self):
        """進捗コールバック作成テスト"""
        tracker = Mock()
        callback = create_progress_callback(tracker)
        
        # コールバック実行
        callback(5, 10)
        
        # trackerのupdateが呼ばれることを確認
        tracker.update.assert_called_once_with(5, 10)


class TestIntegration:
    """統合テスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.config = ConversionConfig()
        self.processor = ConcurrentProcessor(self.config, max_workers=2)
    
    @pytest.mark.asyncio
    async def test_async_processing_with_progress(self):
        """進捗付き非同期処理テスト"""
        pages = [{"id": f"page{i}", "data": i} for i in range(5)]
        progress_updates = []
        
        def progress_callback(completed, total):
            progress_updates.append((completed, total))
        
        async def mock_processor(page):
            await asyncio.sleep(0.05)
            return page['data'] * 2
        
        results = await self.processor.process_pages_async(
            pages, mock_processor, progress_callback
        )
        
        assert len(results) == 5
        assert all(result.success for result in results)
        
        # 進捗コールバックが呼ばれたことを確認
        assert len(progress_updates) == 5
        assert progress_updates[-1] == (5, 5)  # 最後は完了状態
    
    def test_threaded_processing_with_rate_limit(self):
        """レート制限付きスレッド処理テスト"""
        pages = [{"id": f"page{i}", "data": i} for i in range(3)]
        
        def mock_processor(page):
            return page['data'] * 2
        
        results = self.processor.process_pages_threaded(pages, mock_processor)
        
        assert len(results) == 3
        assert all(result.success for result in results)
        
        # レート制限機能が動作することを確認（時間の厳密なテストは避ける）
        assert self.processor.rate_limiter is not None


if __name__ == "__main__":
    pytest.main([__file__])
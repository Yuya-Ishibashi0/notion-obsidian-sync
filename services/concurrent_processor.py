"""
並行処理システム
複数ページの並行処理とレート制限を考慮した並行制御を提供
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Callable, Awaitable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta

from models.config import ConversionConfig


@dataclass
class ProcessingResult:
    """処理結果"""
    page_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "page_id": self.page_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "processing_time": self.processing_time
        }


class RateLimiter:
    """レート制限管理"""
    
    def __init__(self, max_requests_per_second: float = 3.0, burst_limit: int = 10):
        """
        初期化
        
        Args:
            max_requests_per_second: 1秒あたりの最大リクエスト数
            burst_limit: バーストリミット
        """
        self.max_requests_per_second = max_requests_per_second
        self.burst_limit = burst_limit
        self.tokens = burst_limit
        self.last_update = time.time()
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
    
    async def acquire(self) -> bool:
        """
        レート制限トークンを取得
        
        Returns:
            トークンを取得できた場合True
        """
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            
            # トークンを補充
            self.tokens = min(
                self.burst_limit,
                self.tokens + time_passed * self.max_requests_per_second
            )
            self.last_update = now
            
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            else:
                # 待機時間を計算
                wait_time = (1.0 - self.tokens) / self.max_requests_per_second
                self.logger.debug(f"レート制限により{wait_time:.2f}秒待機")
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
                return True
    
    def get_wait_time(self) -> float:
        """
        次のリクエストまでの待機時間を取得
        
        Returns:
            待機時間（秒）
        """
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.max_requests_per_second


class ConcurrentProcessor:
    """並行処理システム"""
    
    def __init__(self, config: ConversionConfig, max_workers: int = 5):
        """
        初期化
        
        Args:
            config: 変換設定
            max_workers: 最大ワーカー数
        """
        self.config = config
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        
        # レート制限設定
        rate_limit = getattr(config, 'notion_api_rate_limit', 3.0)
        burst_limit = getattr(config, 'notion_api_burst_limit', 10)
        self.rate_limiter = RateLimiter(rate_limit, burst_limit)
        
        # 統計情報
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0.0,
            "average_time": 0.0
        }
    
    async def process_pages_async(self, 
                                 pages: List[Dict[str, Any]], 
                                 processor_func: Callable[[Dict[str, Any]], Awaitable[Any]],
                                 progress_callback: Optional[Callable[[int, int], None]] = None) -> List[ProcessingResult]:
        """
        ページを非同期で並行処理
        
        Args:
            pages: 処理するページのリスト
            processor_func: 処理関数（非同期）
            progress_callback: 進捗コールバック関数
            
        Returns:
            処理結果のリスト
        """
        start_time = time.time()
        results = []
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_single_page(page: Dict[str, Any]) -> ProcessingResult:
            """単一ページの処理"""
            async with semaphore:
                # レート制限を適用
                await self.rate_limiter.acquire()
                
                page_id = page.get('id', 'unknown')
                page_start_time = time.time()
                
                try:
                    result = await processor_func(page)
                    processing_time = time.time() - page_start_time
                    
                    return ProcessingResult(
                        page_id=page_id,
                        success=True,
                        result=result,
                        processing_time=processing_time
                    )
                    
                except Exception as e:
                    processing_time = time.time() - page_start_time
                    error_msg = str(e)
                    self.logger.error(f"ページ処理エラー ({page_id}): {error_msg}")
                    
                    return ProcessingResult(
                        page_id=page_id,
                        success=False,
                        error=error_msg,
                        processing_time=processing_time
                    )
        
        # 全ページを並行処理
        tasks = [process_single_page(page) for page in pages]
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            # 進捗コールバック
            if progress_callback:
                progress_callback(completed, len(pages))
        
        # 統計情報を更新
        total_time = time.time() - start_time
        self._update_stats(results, total_time)
        
        self.logger.info(f"並行処理完了: {len(pages)}ページ, {total_time:.2f}秒")
        return results
    
    def process_pages_threaded(self, 
                              pages: List[Dict[str, Any]], 
                              processor_func: Callable[[Dict[str, Any]], Any],
                              progress_callback: Optional[Callable[[int, int], None]] = None) -> List[ProcessingResult]:
        """
        ページをスレッドプールで並行処理
        
        Args:
            pages: 処理するページのリスト
            processor_func: 処理関数（同期）
            progress_callback: 進捗コールバック関数
            
        Returns:
            処理結果のリスト
        """
        start_time = time.time()
        results = []
        
        def process_single_page(page: Dict[str, Any]) -> ProcessingResult:
            """単一ページの処理"""
            page_id = page.get('id', 'unknown')
            page_start_time = time.time()
            
            try:
                # 同期的なレート制限（簡易版）
                wait_time = self.rate_limiter.get_wait_time()
                if wait_time > 0:
                    time.sleep(wait_time)
                
                result = processor_func(page)
                processing_time = time.time() - page_start_time
                
                return ProcessingResult(
                    page_id=page_id,
                    success=True,
                    result=result,
                    processing_time=processing_time
                )
                
            except Exception as e:
                processing_time = time.time() - page_start_time
                error_msg = str(e)
                self.logger.error(f"ページ処理エラー ({page_id}): {error_msg}")
                
                return ProcessingResult(
                    page_id=page_id,
                    success=False,
                    error=error_msg,
                    processing_time=processing_time
                )
        
        # スレッドプールで並行処理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_page = {executor.submit(process_single_page, page): page for page in pages}
            completed = 0
            
            for future in as_completed(future_to_page):
                result = future.result()
                results.append(result)
                completed += 1
                
                # 進捗コールバック
                if progress_callback:
                    progress_callback(completed, len(pages))
        
        # 統計情報を更新
        total_time = time.time() - start_time
        self._update_stats(results, total_time)
        
        self.logger.info(f"スレッド並行処理完了: {len(pages)}ページ, {total_time:.2f}秒")
        return results
    
    def process_pages_batch(self, 
                           pages: List[Dict[str, Any]], 
                           processor_func: Callable[[List[Dict[str, Any]]], List[Any]],
                           batch_size: int = 10,
                           progress_callback: Optional[Callable[[int, int], None]] = None) -> List[ProcessingResult]:
        """
        ページをバッチ処理
        
        Args:
            pages: 処理するページのリスト
            processor_func: バッチ処理関数
            batch_size: バッチサイズ
            progress_callback: 進捗コールバック関数
            
        Returns:
            処理結果のリスト
        """
        start_time = time.time()
        results = []
        
        # ページをバッチに分割
        batches = [pages[i:i + batch_size] for i in range(0, len(pages), batch_size)]
        processed_count = 0
        
        for batch in batches:
            batch_start_time = time.time()
            
            try:
                # レート制限を適用
                wait_time = self.rate_limiter.get_wait_time()
                if wait_time > 0:
                    time.sleep(wait_time)
                
                batch_results = processor_func(batch)
                batch_processing_time = time.time() - batch_start_time
                
                # バッチ結果を個別結果に変換
                for i, page in enumerate(batch):
                    page_id = page.get('id', 'unknown')
                    result = batch_results[i] if i < len(batch_results) else None
                    
                    results.append(ProcessingResult(
                        page_id=page_id,
                        success=True,
                        result=result,
                        processing_time=batch_processing_time / len(batch)
                    ))
                
            except Exception as e:
                batch_processing_time = time.time() - batch_start_time
                error_msg = str(e)
                self.logger.error(f"バッチ処理エラー: {error_msg}")
                
                # バッチ内の全ページをエラーとして記録
                for page in batch:
                    page_id = page.get('id', 'unknown')
                    results.append(ProcessingResult(
                        page_id=page_id,
                        success=False,
                        error=error_msg,
                        processing_time=batch_processing_time / len(batch)
                    ))
            
            processed_count += len(batch)
            
            # 進捗コールバック
            if progress_callback:
                progress_callback(processed_count, len(pages))
        
        # 統計情報を更新
        total_time = time.time() - start_time
        self._update_stats(results, total_time)
        
        self.logger.info(f"バッチ処理完了: {len(pages)}ページ, {len(batches)}バッチ, {total_time:.2f}秒")
        return results
    
    def _update_stats(self, results: List[ProcessingResult], total_time: float):
        """統計情報を更新"""
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        self.stats.update({
            "total_processed": self.stats["total_processed"] + len(results),
            "successful": self.stats["successful"] + successful,
            "failed": self.stats["failed"] + failed,
            "total_time": self.stats["total_time"] + total_time,
        })
        
        if self.stats["total_processed"] > 0:
            self.stats["average_time"] = self.stats["total_time"] / self.stats["total_processed"]
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        処理統計を取得
        
        Returns:
            処理統計情報
        """
        success_rate = 0.0
        if self.stats["total_processed"] > 0:
            success_rate = (self.stats["successful"] / self.stats["total_processed"]) * 100
        
        return {
            **self.stats,
            "success_rate": round(success_rate, 2),
            "pages_per_second": round(self.stats["total_processed"] / max(self.stats["total_time"], 0.001), 2)
        }
    
    def reset_stats(self):
        """統計情報をリセット"""
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0.0,
            "average_time": 0.0
        }


class ProgressTracker:
    """進捗追跡システム"""
    
    def __init__(self, total_items: int, update_interval: float = 1.0):
        """
        初期化
        
        Args:
            total_items: 総アイテム数
            update_interval: 更新間隔（秒）
        """
        self.total_items = total_items
        self.update_interval = update_interval
        self.completed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.logger = logging.getLogger(__name__)
    
    def update(self, completed: int, total: Optional[int] = None):
        """
        進捗を更新
        
        Args:
            completed: 完了アイテム数
            total: 総アイテム数（更新する場合）
        """
        if total is not None:
            self.total_items = total
        
        self.completed_items = completed
        current_time = time.time()
        
        # 更新間隔をチェック
        if current_time - self.last_update_time >= self.update_interval:
            self._log_progress()
            self.last_update_time = current_time
    
    def _log_progress(self):
        """進捗をログ出力"""
        if self.total_items == 0:
            return
        
        progress_percent = (self.completed_items / self.total_items) * 100
        elapsed_time = time.time() - self.start_time
        
        if self.completed_items > 0:
            estimated_total_time = elapsed_time * (self.total_items / self.completed_items)
            remaining_time = estimated_total_time - elapsed_time
            items_per_second = self.completed_items / elapsed_time
            
            self.logger.info(
                f"進捗: {self.completed_items}/{self.total_items} "
                f"({progress_percent:.1f}%) - "
                f"残り時間: {remaining_time:.1f}秒 - "
                f"処理速度: {items_per_second:.2f}件/秒"
            )
        else:
            self.logger.info(f"進捗: {self.completed_items}/{self.total_items} ({progress_percent:.1f}%)")
    
    def complete(self):
        """処理完了"""
        total_time = time.time() - self.start_time
        items_per_second = self.completed_items / max(total_time, 0.001)
        
        self.logger.info(
            f"処理完了: {self.completed_items}件 - "
            f"総時間: {total_time:.2f}秒 - "
            f"平均速度: {items_per_second:.2f}件/秒"
        )


def create_progress_callback(tracker: ProgressTracker) -> Callable[[int, int], None]:
    """
    進捗追跡用のコールバック関数を作成
    
    Args:
        tracker: 進捗追跡システム
        
    Returns:
        コールバック関数
    """
    def callback(completed: int, total: int):
        tracker.update(completed, total)
    
    return callback
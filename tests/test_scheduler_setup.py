"""
スケジューラー設定のテスト
"""

import pytest
import tempfile
import platform
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# scriptsディレクトリをパスに追加
import sys
sys.path.append('scripts')

from setup_scheduler import SchedulerSetup


class TestSchedulerSetup:
    """SchedulerSetup のテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        # 一時的なスクリプトファイルを作成
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        self.temp_file.write('print("test script")')
        self.temp_file.close()
        
        self.scheduler = SchedulerSetup(self.temp_file.name, interval_minutes=15)
    
    def teardown_method(self):
        """テストクリーンアップ"""
        Path(self.temp_file.name).unlink(missing_ok=True)
    
    def test_initialization(self):
        """初期化テスト"""
        assert self.scheduler.script_path.exists()
        assert self.scheduler.interval_minutes == 15
        assert self.scheduler.system in ['linux', 'darwin', 'windows']
    
    def test_generate_cron_entry_minutes(self):
        """cronエントリ生成テスト（分単位）"""
        python_path = "/usr/bin/python3"
        entry = self.scheduler._generate_cron_entry(python_path)
        
        expected = f"*/15 * * * * {python_path} {self.scheduler.script_path}"
        assert entry == expected
    
    def test_generate_cron_entry_hours(self):
        """cronエントリ生成テスト（時間単位）"""
        scheduler = SchedulerSetup(self.temp_file.name, interval_minutes=120)
        python_path = "/usr/bin/python3"
        entry = scheduler._generate_cron_entry(python_path)
        
        expected = f"0 */2 * * * {python_path} {scheduler.script_path}"
        assert entry == expected
    
    @patch('subprocess.run')
    @patch('sys.executable', '/usr/bin/python3')
    def test_setup_cron_new_entry(self, mock_subprocess):
        """新規cronエントリ設定テスト"""
        # crontab -l が空を返す（既存エントリなし）
        mock_subprocess.side_effect = [
            Mock(returncode=1, stdout=""),  # crontab -l
            Mock(returncode=0)  # crontab -
        ]
        
        if platform.system().lower() in ['linux', 'darwin']:
            result = self.scheduler._setup_cron()
            assert result == True
            assert mock_subprocess.call_count == 2
    
    @patch('subprocess.run')
    @patch('sys.executable', '/usr/bin/python3')
    def test_setup_cron_existing_entry(self, mock_subprocess):
        """既存cronエントリ更新テスト"""
        existing_crontab = f"0 0 * * * /some/other/script\n*/30 * * * * /usr/bin/python3 {self.scheduler.script_path}\n"
        
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout=existing_crontab),  # crontab -l
            Mock(returncode=0)  # crontab -
        ]
        
        if platform.system().lower() in ['linux', 'darwin']:
            result = self.scheduler._setup_cron()
            assert result == True
    
    @patch('subprocess.run')
    def test_setup_windows_task(self, mock_subprocess):
        """Windowsタスク設定テスト"""
        mock_subprocess.return_value = Mock(returncode=0)
        
        if platform.system().lower() == 'windows':
            result = self.scheduler._setup_windows_task()
            assert result == True
            mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_remove_cron(self, mock_subprocess):
        """cronエントリ削除テスト"""
        existing_crontab = f"0 0 * * * /some/other/script\n*/15 * * * * /usr/bin/python3 {self.scheduler.script_path}\n"
        
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout=existing_crontab),  # crontab -l
            Mock(returncode=0)  # crontab -
        ]
        
        if platform.system().lower() in ['linux', 'darwin']:
            result = self.scheduler._remove_cron()
            assert result == True
    
    @patch('subprocess.run')
    def test_remove_windows_task(self, mock_subprocess):
        """Windowsタスク削除テスト"""
        mock_subprocess.return_value = Mock(returncode=0)
        
        if platform.system().lower() == 'windows':
            result = self.scheduler._remove_windows_task()
            assert result == True
    
    @patch('subprocess.run')
    def test_check_cron_status_exists(self, mock_subprocess):
        """cron状態チェックテスト（存在）"""
        existing_crontab = f"*/15 * * * * /usr/bin/python3 {self.scheduler.script_path}\n"
        mock_subprocess.return_value = Mock(returncode=0, stdout=existing_crontab)
        
        if platform.system().lower() in ['linux', 'darwin']:
            result = self.scheduler._check_cron_status()
            assert result == True
    
    @patch('subprocess.run')
    def test_check_cron_status_not_exists(self, mock_subprocess):
        """cron状態チェックテスト（存在しない）"""
        mock_subprocess.return_value = Mock(returncode=0, stdout="0 0 * * * /some/other/script\n")
        
        if platform.system().lower() in ['linux', 'darwin']:
            result = self.scheduler._check_cron_status()
            assert result == False
    
    @patch('subprocess.run')
    def test_check_windows_task_status_exists(self, mock_subprocess):
        """Windowsタスク状態チェックテスト（存在）"""
        mock_subprocess.return_value = Mock(returncode=0)
        
        if platform.system().lower() == 'windows':
            result = self.scheduler._check_windows_task_status()
            assert result == True
    
    @patch('subprocess.run')
    def test_check_windows_task_status_not_exists(self, mock_subprocess):
        """Windowsタスク状態チェックテスト（存在しない）"""
        mock_subprocess.return_value = Mock(returncode=1)
        
        if platform.system().lower() == 'windows':
            result = self.scheduler._check_windows_task_status()
            assert result == False
    
    @patch.object(SchedulerSetup, '_setup_cron')
    @patch.object(SchedulerSetup, '_setup_windows_task')
    def test_setup_scheduler_platform_detection(self, mock_windows, mock_cron):
        """プラットフォーム検出テスト"""
        mock_cron.return_value = True
        mock_windows.return_value = True
        
        # 現在のプラットフォームに応じて適切なメソッドが呼ばれることを確認
        result = self.scheduler.setup_scheduler()
        
        if platform.system().lower() in ['linux', 'darwin']:
            mock_cron.assert_called_once()
            mock_windows.assert_not_called()
        elif platform.system().lower() == 'windows':
            mock_windows.assert_called_once()
            mock_cron.assert_not_called()
        
        assert result == True
    
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        # 存在しないスクリプトパスでSchedulerSetupを作成
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_path = temp_file.name
        
        # ファイルが削除された後なので存在しない
        scheduler = SchedulerSetup(temp_path, interval_minutes=30)
        
        # スクリプトパスは設定されるが、実際の操作でエラーが発生する可能性がある
        assert scheduler.script_path == Path(temp_path).absolute()


if __name__ == "__main__":
    pytest.main([__file__])
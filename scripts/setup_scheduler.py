#!/usr/bin/env python3
"""
スケジュール実行設定スクリプト
Linux/macOS用cronジョブとWindows用タスクスケジューラーの設定
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional


class SchedulerSetup:
    """スケジューラー設定クラス"""
    
    def __init__(self, script_path: str, interval_minutes: int = 30):
        """
        初期化
        
        Args:
            script_path: 実行するスクリプトのパス
            interval_minutes: 実行間隔（分）
        """
        self.script_path = Path(script_path).absolute()
        self.interval_minutes = interval_minutes
        self.system = platform.system().lower()
        
    def setup_scheduler(self) -> bool:
        """
        プラットフォームに応じてスケジューラーを設定
        
        Returns:
            設定成功時True
        """
        try:
            if self.system in ['linux', 'darwin']:  # Linux/macOS
                return self._setup_cron()
            elif self.system == 'windows':
                return self._setup_windows_task()
            else:
                print(f"サポートされていないプラットフォーム: {self.system}")
                return False
        except Exception as e:
            print(f"スケジューラー設定エラー: {e}")
            return False
    
    def _setup_cron(self) -> bool:
        """cronジョブを設定"""
        print("cronジョブを設定しています...")
        
        # 現在のcrontabを取得
        try:
            current_crontab = subprocess.run(
                ['crontab', '-l'], 
                capture_output=True, 
                text=True, 
                check=False
            )
            existing_entries = current_crontab.stdout if current_crontab.returncode == 0 else ""
        except FileNotFoundError:
            print("crontabコマンドが見つかりません")
            return False
        
        # 新しいcronエントリを作成
        python_path = sys.executable
        cron_entry = self._generate_cron_entry(python_path)
        
        # 既存のエントリに同じスクリプトがないかチェック
        if str(self.script_path) in existing_entries:
            print("既存のcronエントリが見つかりました。更新します...")
            # 既存のエントリを削除
            lines = existing_entries.strip().split('\n')
            filtered_lines = [line for line in lines if str(self.script_path) not in line]
            existing_entries = '\n'.join(filtered_lines) + '\n' if filtered_lines else ""
        
        # 新しいcrontabを設定
        new_crontab = existing_entries + cron_entry + '\n'
        
        try:
            process = subprocess.run(
                ['crontab', '-'], 
                input=new_crontab, 
                text=True, 
                check=True
            )
            print(f"cronジョブが設定されました: {self.interval_minutes}分間隔")
            print(f"エントリ: {cron_entry}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"crontab設定エラー: {e}")
            return False
    
    def _generate_cron_entry(self, python_path: str) -> str:
        """cronエントリを生成"""
        if self.interval_minutes < 60:
            # 分単位の間隔
            return f"*/{self.interval_minutes} * * * * {python_path} {self.script_path}"
        else:
            # 時間単位の間隔
            hours = self.interval_minutes // 60
            return f"0 */{hours} * * * {python_path} {self.script_path}"
    
    def _setup_windows_task(self) -> bool:
        """Windowsタスクスケジューラーを設定"""
        print("Windowsタスクスケジューラーを設定しています...")
        
        task_name = "NotionObsidianSync"
        python_path = sys.executable
        
        # タスクスケジューラーコマンドを構築
        schtasks_cmd = [
            'schtasks', '/create',
            '/tn', task_name,
            '/tr', f'"{python_path}" "{self.script_path}"',
            '/sc', 'minute',
            '/mo', str(self.interval_minutes),
            '/f'  # 既存のタスクを上書き
        ]
        
        try:
            subprocess.run(schtasks_cmd, check=True, capture_output=True)
            print(f"Windowsタスクが設定されました: {task_name}")
            print(f"実行間隔: {self.interval_minutes}分")
            return True
        except subprocess.CalledProcessError as e:
            print(f"タスクスケジューラー設定エラー: {e}")
            return False
        except FileNotFoundError:
            print("schtasksコマンドが見つかりません")
            return False
    
    def remove_scheduler(self) -> bool:
        """スケジューラーエントリを削除"""
        try:
            if self.system in ['linux', 'darwin']:
                return self._remove_cron()
            elif self.system == 'windows':
                return self._remove_windows_task()
            else:
                print(f"サポートされていないプラットフォーム: {self.system}")
                return False
        except Exception as e:
            print(f"スケジューラー削除エラー: {e}")
            return False
    
    def _remove_cron(self) -> bool:
        """cronジョブを削除"""
        print("cronジョブを削除しています...")
        
        try:
            current_crontab = subprocess.run(
                ['crontab', '-l'], 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            if current_crontab.returncode != 0:
                print("既存のcrontabが見つかりません")
                return True
            
            existing_entries = current_crontab.stdout
            
            # 対象スクリプトのエントリを削除
            lines = existing_entries.strip().split('\n')
            filtered_lines = [line for line in lines if str(self.script_path) not in line]
            
            if len(filtered_lines) == len(lines):
                print("削除対象のcronエントリが見つかりません")
                return True
            
            new_crontab = '\n'.join(filtered_lines) + '\n' if filtered_lines else ""
            
            subprocess.run(
                ['crontab', '-'], 
                input=new_crontab, 
                text=True, 
                check=True
            )
            print("cronジョブが削除されました")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"crontab削除エラー: {e}")
            return False
    
    def _remove_windows_task(self) -> bool:
        """Windowsタスクを削除"""
        print("Windowsタスクを削除しています...")
        
        task_name = "NotionObsidianSync"
        
        try:
            subprocess.run(
                ['schtasks', '/delete', '/tn', task_name, '/f'], 
                check=True, 
                capture_output=True
            )
            print(f"Windowsタスクが削除されました: {task_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"タスク削除エラー: {e}")
            return False
    
    def check_scheduler_status(self) -> bool:
        """スケジューラーの状態をチェック"""
        try:
            if self.system in ['linux', 'darwin']:
                return self._check_cron_status()
            elif self.system == 'windows':
                return self._check_windows_task_status()
            else:
                return False
        except Exception as e:
            print(f"スケジューラー状態チェックエラー: {e}")
            return False
    
    def _check_cron_status(self) -> bool:
        """cronジョブの状態をチェック"""
        try:
            current_crontab = subprocess.run(
                ['crontab', '-l'], 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            if current_crontab.returncode != 0:
                return False
            
            return str(self.script_path) in current_crontab.stdout
        except Exception:
            return False
    
    def _check_windows_task_status(self) -> bool:
        """Windowsタスクの状態をチェック"""
        task_name = "NotionObsidianSync"
        
        try:
            result = subprocess.run(
                ['schtasks', '/query', '/tn', task_name], 
                capture_output=True, 
                text=True, 
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Notion-Obsidian同期スケジューラー設定')
    parser.add_argument('script_path', help='実行するスクリプトのパス')
    parser.add_argument('--interval', type=int, default=30, help='実行間隔（分）')
    parser.add_argument('--remove', action='store_true', help='スケジューラーエントリを削除')
    parser.add_argument('--status', action='store_true', help='スケジューラーの状態をチェック')
    
    args = parser.parse_args()
    
    if not Path(args.script_path).exists():
        print(f"エラー: スクリプトファイルが見つかりません: {args.script_path}")
        sys.exit(1)
    
    scheduler = SchedulerSetup(args.script_path, args.interval)
    
    if args.status:
        status = scheduler.check_scheduler_status()
        print(f"スケジューラー状態: {'有効' if status else '無効'}")
        sys.exit(0 if status else 1)
    
    if args.remove:
        success = scheduler.remove_scheduler()
        sys.exit(0 if success else 1)
    else:
        success = scheduler.setup_scheduler()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
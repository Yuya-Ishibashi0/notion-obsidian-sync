"""
ファイル管理システム
Obsidianボルトのファイル操作を管理するクラス
"""

import os
import logging
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import threading
from contextlib import contextmanager

from models.markdown import MarkdownFile, MarkdownConversionResult


class FileOperationError(Exception):
    """ファイル操作関連のエラー"""
    pass


class FileManager:
    """ファイル管理クラス"""
    
    def __init__(self, vault_path: str, subfolder: Optional[str] = None):
        """
        初期化
        
        Args:
            vault_path: Obsidianボルトのパス
            subfolder: サブフォルダ（オプション）
        """
        self.vault_path = Path(vault_path)
        self.subfolder = subfolder
        self.logger = logging.getLogger(__name__)
        
        # ファイルロック用の辞書
        self._file_locks = {}
        self._locks_lock = threading.Lock()
        
        # 同期先パスを設定
        if subfolder:
            self.sync_path = self.vault_path / subfolder
        else:
            self.sync_path = self.vault_path
        
        # 初期化時にパスの検証
        self._validate_paths()
    
    def _validate_paths(self) -> None:
        """パスの検証"""
        if not self.vault_path.exists():
            raise FileOperationError(f"Obsidianボルトパスが存在しません: {self.vault_path}")
        
        if not self.vault_path.is_dir():
            raise FileOperationError(f"Obsidianボルトパスはディレクトリである必要があります: {self.vault_path}")
        
        # 書き込み権限の確認
        if not os.access(self.vault_path, os.W_OK):
            raise FileOperationError(f"Obsidianボルトパスに書き込み権限がありません: {self.vault_path}")
    
    @contextmanager
    def _get_file_lock(self, filepath: str):
        """ファイルロックを取得"""
        with self._locks_lock:
            if filepath not in self._file_locks:
                self._file_locks[filepath] = threading.Lock()
            lock = self._file_locks[filepath]
        
        with lock:
            yield
    
    def ensure_directory_exists(self, path: Optional[Path] = None) -> None:
        """
        ディレクトリの存在を確認し、必要に応じて作成
        
        Args:
            path: 作成するディレクトリのパス（Noneの場合は同期パス）
        """
        target_path = path if path else self.sync_path
        
        try:
            target_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"ディレクトリを確認/作成しました: {target_path}")
        except Exception as e:
            raise FileOperationError(f"ディレクトリの作成に失敗しました: {target_path} - {str(e)}")
    
    def get_safe_filename(self, title: str, max_length: int = 100) -> str:
        """
        安全なファイル名を生成
        
        Args:
            title: 元のタイトル
            max_length: 最大長
            
        Returns:
            安全なファイル名
        """
        return MarkdownFile.sanitize_filename(title, max_length)
    
    def file_exists(self, filename: str) -> bool:
        """
        ファイルの存在確認
        
        Args:
            filename: ファイル名
            
        Returns:
            ファイルが存在する場合True
        """
        file_path = self.sync_path / filename
        return file_path.exists()
    
    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        ファイル情報を取得
        
        Args:
            filename: ファイル名
            
        Returns:
            ファイル情報の辞書（存在しない場合はNone）
        """
        file_path = self.sync_path / filename
        
        if not file_path.exists():
            return None
        
        try:
            stat = file_path.stat()
            return {
                "path": str(file_path),
                "size": stat.st_size,
                "created_time": stat.st_ctime,
                "modified_time": stat.st_mtime,
                "is_file": file_path.is_file(),
                "is_directory": file_path.is_dir()
            }
        except Exception as e:
            self.logger.error(f"ファイル情報取得エラー: {filename} - {str(e)}")
            return None
    
    def list_markdown_files(self) -> List[str]:
        """
        同期ディレクトリ内のMarkdownファイル一覧を取得
        
        Returns:
            Markdownファイル名のリスト
        """
        try:
            if not self.sync_path.exists():
                return []
            
            markdown_files = []
            for file_path in self.sync_path.glob("*.md"):
                if file_path.is_file():
                    markdown_files.append(file_path.name)
            
            return sorted(markdown_files)
            
        except Exception as e:
            self.logger.error(f"ファイル一覧取得エラー: {str(e)}")
            return []
    
    def read_markdown_file(self, filename: str) -> Optional[MarkdownFile]:
        """
        Markdownファイルを読み込み
        
        Args:
            filename: ファイル名
            
        Returns:
            MarkdownFileオブジェクト（存在しない場合はNone）
        """
        file_path = self.sync_path / filename
        
        if not file_path.exists():
            return None
        
        try:
            with self._get_file_lock(str(file_path)):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return MarkdownFile.from_string(filename, content)
                
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー: {filename} - {str(e)}")
            return None
    
    def write_markdown_file(self, markdown_file: MarkdownFile, 
                           overwrite: bool = True) -> bool:
        """
        Markdownファイルを書き込み
        
        Args:
            markdown_file: MarkdownFileオブジェクト
            overwrite: 既存ファイルを上書きするかどうか
            
        Returns:
            書き込み成功時True
        """
        try:
            # ディレクトリの存在確認
            self.ensure_directory_exists()
            
            file_path = self.sync_path / markdown_file.filename
            
            # 上書き確認
            if file_path.exists() and not overwrite:
                self.logger.warning(f"ファイルが既に存在します（上書きしません）: {markdown_file.filename}")
                return False
            
            # アトミックな書き込みを実行
            return self._atomic_write(file_path, markdown_file.to_string())
            
        except Exception as e:
            self.logger.error(f"ファイル書き込みエラー: {markdown_file.filename} - {str(e)}")
            return False
    
    def write_multiple_markdown_files(self, 
                                    conversion_results: List[MarkdownConversionResult],
                                    overwrite: bool = True) -> Dict[str, bool]:
        """
        複数のMarkdownファイルを一括書き込み
        
        Args:
            conversion_results: MarkdownConversionResultオブジェクトのリスト
            overwrite: 既存ファイルを上書きするかどうか
            
        Returns:
            ファイル名と書き込み結果の辞書
        """
        results = {}
        
        for result in conversion_results:
            filename = result.markdown_file.filename
            success = self.write_markdown_file(result.markdown_file, overwrite)
            results[filename] = success
            
            if success:
                self.logger.debug(f"ファイル書き込み成功: {filename}")
            else:
                self.logger.error(f"ファイル書き込み失敗: {filename}")
        
        successful_count = sum(1 for success in results.values() if success)
        self.logger.info(f"ファイル書き込み完了: {successful_count}/{len(results)}ファイル")
        
        return results
    
    def _atomic_write(self, file_path: Path, content: str) -> bool:
        """
        アトミックなファイル書き込み
        
        Args:
            file_path: ファイルパス
            content: 書き込み内容
            
        Returns:
            書き込み成功時True
        """
        try:
            with self._get_file_lock(str(file_path)):
                # 一時ファイルに書き込み
                with tempfile.NamedTemporaryFile(
                    mode='w', 
                    encoding='utf-8', 
                    dir=file_path.parent,
                    prefix=f".{file_path.stem}_",
                    suffix=".tmp",
                    delete=False
                ) as temp_file:
                    temp_file.write(content)
                    temp_path = Path(temp_file.name)
                
                # アトミックに移動
                temp_path.replace(file_path)
                
                self.logger.debug(f"アトミック書き込み成功: {file_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"アトミック書き込みエラー: {file_path} - {str(e)}")
            # 一時ファイルのクリーンアップ
            try:
                if 'temp_path' in locals() and temp_path.exists():
                    temp_path.unlink()
            except:
                pass
            return False
    
    def delete_file(self, filename: str) -> bool:
        """
        ファイルを削除
        
        Args:
            filename: ファイル名
            
        Returns:
            削除成功時True
        """
        file_path = self.sync_path / filename
        
        if not file_path.exists():
            self.logger.warning(f"削除対象ファイルが存在しません: {filename}")
            return False
        
        try:
            with self._get_file_lock(str(file_path)):
                file_path.unlink()
                self.logger.debug(f"ファイル削除成功: {filename}")
                return True
                
        except Exception as e:
            self.logger.error(f"ファイル削除エラー: {filename} - {str(e)}")
            return False
    
    def backup_file(self, filename: str, backup_suffix: str = ".backup") -> bool:
        """
        ファイルをバックアップ
        
        Args:
            filename: ファイル名
            backup_suffix: バックアップファイルの接尾辞
            
        Returns:
            バックアップ成功時True
        """
        file_path = self.sync_path / filename
        
        if not file_path.exists():
            self.logger.warning(f"バックアップ対象ファイルが存在しません: {filename}")
            return False
        
        backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)
        
        try:
            shutil.copy2(file_path, backup_path)
            self.logger.debug(f"ファイルバックアップ成功: {filename} -> {backup_path.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルバックアップエラー: {filename} - {str(e)}")
            return False
    
    def cleanup_old_backups(self, max_backups: int = 5) -> None:
        """
        古いバックアップファイルをクリーンアップ
        
        Args:
            max_backups: 保持する最大バックアップ数
        """
        try:
            backup_files = list(self.sync_path.glob("*.backup"))
            
            if len(backup_files) <= max_backups:
                return
            
            # 更新日時でソート（古い順）
            backup_files.sort(key=lambda p: p.stat().st_mtime)
            
            # 古いファイルを削除
            files_to_delete = backup_files[:-max_backups]
            for backup_file in files_to_delete:
                try:
                    backup_file.unlink()
                    self.logger.debug(f"古いバックアップを削除: {backup_file.name}")
                except Exception as e:
                    self.logger.error(f"バックアップ削除エラー: {backup_file.name} - {str(e)}")
            
            self.logger.info(f"バックアップクリーンアップ完了: {len(files_to_delete)}ファイル削除")
            
        except Exception as e:
            self.logger.error(f"バックアップクリーンアップエラー: {str(e)}")
    
    def get_disk_usage(self) -> Dict[str, int]:
        """
        ディスク使用量を取得
        
        Returns:
            使用量情報の辞書
        """
        try:
            total_size = 0
            file_count = 0
            
            for file_path in self.sync_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            return {
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "file_count": file_count,
                "average_file_size": total_size / file_count if file_count > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"ディスク使用量取得エラー: {str(e)}")
            return {"total_size_bytes": 0, "total_size_mb": 0, "file_count": 0, "average_file_size": 0}
    
    def validate_vault_structure(self) -> List[str]:
        """
        ボルト構造の検証
        
        Returns:
            問題のリスト
        """
        issues = []
        
        try:
            # 基本パスの確認
            if not self.vault_path.exists():
                issues.append(f"ボルトパスが存在しません: {self.vault_path}")
                return issues
            
            if not self.vault_path.is_dir():
                issues.append(f"ボルトパスがディレクトリではありません: {self.vault_path}")
                return issues
            
            # 権限の確認
            if not os.access(self.vault_path, os.R_OK):
                issues.append(f"ボルトパスに読み取り権限がありません: {self.vault_path}")
            
            if not os.access(self.vault_path, os.W_OK):
                issues.append(f"ボルトパスに書き込み権限がありません: {self.vault_path}")
            
            # 同期パスの確認
            if not self.sync_path.exists():
                try:
                    self.ensure_directory_exists()
                except Exception as e:
                    issues.append(f"同期パスの作成に失敗しました: {self.sync_path} - {str(e)}")
            
            # Obsidianの設定ファイルの確認
            obsidian_config = self.vault_path / ".obsidian"
            if not obsidian_config.exists():
                issues.append("Obsidianの設定フォルダが見つかりません（.obsidian）")
            
            return issues
            
        except Exception as e:
            issues.append(f"ボルト構造検証エラー: {str(e)}")
            return issues
    
    def check_file_conflicts(self, markdown_files: List[MarkdownFile]) -> Dict[str, List[str]]:
        """
        ファイル名の競合をチェック
        
        Args:
            markdown_files: MarkdownFileオブジェクトのリスト
            
        Returns:
            競合情報の辞書
        """
        conflicts = {}
        filename_map = {}
        
        # ファイル名の重複をチェック
        for md_file in markdown_files:
            filename = md_file.filename.lower()  # 大文字小文字を無視
            
            if filename in filename_map:
                if filename not in conflicts:
                    conflicts[filename] = [filename_map[filename]]
                conflicts[filename].append(md_file.filename)
            else:
                filename_map[filename] = md_file.filename
        
        # 既存ファイルとの競合もチェック
        existing_files = self.list_markdown_files()
        for md_file in markdown_files:
            if md_file.filename in existing_files:
                conflict_key = f"existing_{md_file.filename}"
                conflicts[conflict_key] = [md_file.filename, "既存ファイル"]
        
        return conflicts
    
    def resolve_filename_conflicts(self, markdown_files: List[MarkdownFile]) -> List[MarkdownFile]:
        """
        ファイル名の競合を解決
        
        Args:
            markdown_files: MarkdownFileオブジェクトのリスト
            
        Returns:
            競合が解決されたMarkdownFileオブジェクトのリスト
        """
        resolved_files = []
        used_filenames = set()
        
        for md_file in markdown_files:
            original_filename = md_file.filename
            resolved_filename = self._get_unique_filename(original_filename, used_filenames)
            
            if resolved_filename != original_filename:
                self.logger.info(f"ファイル名競合を解決: {original_filename} -> {resolved_filename}")
                # 新しいファイル名でクローンを作成
                resolved_file = md_file.clone()
                resolved_file.filename = resolved_filename
                resolved_files.append(resolved_file)
            else:
                resolved_files.append(md_file)
            
            used_filenames.add(resolved_filename)
        
        return resolved_files
    
    def _get_unique_filename(self, filename: str, used_filenames: set) -> str:
        """
        ユニークなファイル名を生成
        
        Args:
            filename: 元のファイル名
            used_filenames: 使用済みファイル名のセット
            
        Returns:
            ユニークなファイル名
        """
        if filename not in used_filenames:
            return filename
        
        # ファイル名と拡張子を分離
        path = Path(filename)
        stem = path.stem
        suffix = path.suffix
        
        # 番号を付けてユニークにする
        counter = 1
        while True:
            new_filename = f"{stem}_{counter}{suffix}"
            if new_filename not in used_filenames:
                return new_filename
            counter += 1
    
    def create_conflict_resolution_report(self, conflicts: Dict[str, List[str]]) -> str:
        """
        競合解決レポートを作成
        
        Args:
            conflicts: 競合情報の辞書
            
        Returns:
            レポート文字列
        """
        if not conflicts:
            return "ファイル名の競合は検出されませんでした。"
        
        report_lines = ["# ファイル名競合レポート\n"]
        
        for conflict_key, conflict_files in conflicts.items():
            if conflict_key.startswith("existing_"):
                filename = conflict_key.replace("existing_", "")
                report_lines.append(f"## 既存ファイルとの競合: {filename}")
                report_lines.append("- 既存のファイルが上書きされます")
            else:
                report_lines.append(f"## 重複ファイル名: {conflict_key}")
                report_lines.append("- 競合するファイル:")
                for file in conflict_files:
                    report_lines.append(f"  - {file}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def safe_batch_write(self, conversion_results: List[MarkdownConversionResult],
                        overwrite: bool = True,
                        resolve_conflicts: bool = True) -> Dict[str, Any]:
        """
        安全なバッチ書き込み（競合チェック付き）
        
        Args:
            conversion_results: MarkdownConversionResultオブジェクトのリスト
            overwrite: 既存ファイルを上書きするかどうか
            resolve_conflicts: 競合を自動解決するかどうか
            
        Returns:
            書き込み結果の詳細辞書
        """
        markdown_files = [result.markdown_file for result in conversion_results]
        
        # 競合チェック
        conflicts = self.check_file_conflicts(markdown_files)
        
        # 競合解決
        if resolve_conflicts and conflicts:
            self.logger.info(f"{len(conflicts)}件のファイル名競合を検出、自動解決を実行")
            resolved_files = self.resolve_filename_conflicts(markdown_files)
            
            # 解決されたファイルで結果を更新
            for i, resolved_file in enumerate(resolved_files):
                conversion_results[i].markdown_file = resolved_file
        
        # バッチ書き込み実行
        write_results = self.write_multiple_markdown_files(conversion_results, overwrite)
        
        # 結果をまとめる
        return {
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": len(conflicts) if resolve_conflicts else 0,
            "write_results": write_results,
            "successful_writes": sum(1 for success in write_results.values() if success),
            "failed_writes": sum(1 for success in write_results.values() if not success),
            "conflict_report": self.create_conflict_resolution_report(conflicts) if conflicts else None
        }
    
    def verify_file_integrity(self, filename: str) -> Dict[str, Any]:
        """
        ファイルの整合性を検証
        
        Args:
            filename: ファイル名
            
        Returns:
            整合性チェック結果
        """
        file_path = self.sync_path / filename
        
        if not file_path.exists():
            return {"exists": False, "error": "ファイルが存在しません"}
        
        try:
            # ファイルサイズチェック
            file_size = file_path.stat().st_size
            
            # 読み取り可能性チェック
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Markdownファイルとしての妥当性チェック
            md_file = MarkdownFile.from_string(filename, content)
            warnings = md_file.validate_content()
            
            return {
                "exists": True,
                "readable": True,
                "size_bytes": file_size,
                "size_mb": file_size / (1024 * 1024),
                "line_count": len(content.split('\n')),
                "has_frontmatter": md_file.has_frontmatter(),
                "warnings": warnings,
                "is_valid": len(warnings) == 0
            }
            
        except UnicodeDecodeError:
            return {"exists": True, "readable": False, "error": "文字エンコーディングエラー"}
        except Exception as e:
            return {"exists": True, "readable": False, "error": str(e)}
    
    def batch_verify_integrity(self, filenames: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        複数ファイルの整合性を一括検証
        
        Args:
            filenames: 検証するファイル名のリスト（Noneの場合は全Markdownファイル）
            
        Returns:
            ファイル名と整合性チェック結果の辞書
        """
        if filenames is None:
            filenames = self.list_markdown_files()
        
        results = {}
        for filename in filenames:
            results[filename] = self.verify_file_integrity(filename)
        
        return results
    
    def create_integrity_report(self, integrity_results: Dict[str, Dict[str, Any]]) -> str:
        """
        整合性チェックレポートを作成
        
        Args:
            integrity_results: 整合性チェック結果
            
        Returns:
            レポート文字列
        """
        report_lines = ["# ファイル整合性レポート\n"]
        
        valid_files = []
        invalid_files = []
        unreadable_files = []
        
        for filename, result in integrity_results.items():
            if not result.get("exists", False):
                unreadable_files.append((filename, "ファイルが存在しません"))
            elif not result.get("readable", False):
                unreadable_files.append((filename, result.get("error", "読み取りエラー")))
            elif result.get("is_valid", False):
                valid_files.append(filename)
            else:
                invalid_files.append((filename, result.get("warnings", [])))
        
        # サマリー
        report_lines.append(f"## サマリー")
        report_lines.append(f"- 正常なファイル: {len(valid_files)}")
        report_lines.append(f"- 警告があるファイル: {len(invalid_files)}")
        report_lines.append(f"- 読み取り不可ファイル: {len(unreadable_files)}")
        report_lines.append("")
        
        # 詳細
        if invalid_files:
            report_lines.append("## 警告があるファイル")
            for filename, warnings in invalid_files:
                report_lines.append(f"### {filename}")
                for warning in warnings:
                    report_lines.append(f"- {warning}")
                report_lines.append("")
        
        if unreadable_files:
            report_lines.append("## 読み取り不可ファイル")
            for filename, error in unreadable_files:
                report_lines.append(f"- {filename}: {error}")
            report_lines.append("")
        
        return "\n".join(report_lines)
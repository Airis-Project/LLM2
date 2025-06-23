# src/utils/backup_utils.py
"""
バックアップユーティリティ
ファイル・プロジェクトのバックアップ・復元に関する共通機能を提供
"""

import os
import shutil
import zipfile
import tarfile
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Union, Callable, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import hashlib
import fnmatch

from ..core.logger import get_logger
from .file_utils import get_file_utils
from .encryption_utils import get_encryption_utils


class BackupType(Enum):
    """バックアップタイプ"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class CompressionType(Enum):
    """圧縮タイプ"""
    NONE = "none"
    ZIP = "zip"
    TAR_GZ = "tar.gz"
    TAR_BZ2 = "tar.bz2"


@dataclass
class BackupInfo:
    """バックアップ情報"""
    backup_id: str
    timestamp: datetime
    backup_type: BackupType
    source_path: str
    backup_path: str
    compression_type: CompressionType
    file_count: int
    total_size: int
    compressed_size: Optional[int] = None
    checksum: Optional[str] = None
    encrypted: bool = False
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BackupConfig:
    """バックアップ設定"""
    source_paths: List[str]
    backup_directory: str
    backup_type: BackupType = BackupType.FULL
    compression_type: CompressionType = CompressionType.ZIP
    max_backups: int = 10
    exclude_patterns: List[str] = None
    include_patterns: List[str] = None
    encrypt_backup: bool = False
    encryption_password: Optional[str] = None
    auto_cleanup: bool = True
    verify_backup: bool = True
    
    def __post_init__(self):
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                '*.tmp', '*.log', '*.cache', '__pycache__', '.git',
                'node_modules', '.DS_Store', 'Thumbs.db'
            ]
        if self.include_patterns is None:
            self.include_patterns = ['*']


class BackupProgress:
    """バックアップ進捗情報"""
    
    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.total_size = 0
        self.processed_size = 0
        self.current_file = ""
        self.start_time = time.time()
        self.is_cancelled = False
        self.callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable):
        """進捗コールバックを追加"""
        self.callbacks.append(callback)
    
    def update(self, file_path: str = None, file_size: int = 0):
        """進捗を更新"""
        if file_path:
            self.current_file = file_path
            self.processed_files += 1
        self.processed_size += file_size
        
        # コールバック実行
        for callback in self.callbacks:
            try:
                callback(self)
            except Exception:
                pass  # コールバックエラーは無視
    
    def get_progress_percent(self) -> float:
        """進捗率を取得"""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100
    
    def get_speed(self) -> float:
        """処理速度を取得（MB/s）"""
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return (self.processed_size / (1024 * 1024)) / elapsed
    
    def get_eta(self) -> float:
        """残り時間を予測（秒）"""
        if self.processed_size == 0:
            return 0.0
        speed = self.get_speed()
        if speed == 0:
            return 0.0
        remaining_size = self.total_size - self.processed_size
        return (remaining_size / (1024 * 1024)) / speed


class BackupUtils:
    """バックアップユーティリティクラス"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.file_utils = get_file_utils()
        self.encryption_utils = get_encryption_utils()
        
        # バックアップ履歴を保存するファイル
        self.backup_history_file = "backup_history.json"
        self._lock = threading.Lock()
    
    def _should_include_file(self, file_path: Path, config: BackupConfig) -> bool:
        """ファイルをバックアップに含めるかチェック"""
        try:
            file_str = str(file_path)
            
            # 除外パターンチェック
            for pattern in config.exclude_patterns:
                if fnmatch.fnmatch(file_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                    return False
            
            # 含有パターンチェック
            for pattern in config.include_patterns:
                if fnmatch.fnmatch(file_str, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"ファイル包含チェックエラー: {e}")
            return False
    
    def _get_backup_files(self, source_paths: List[str], config: BackupConfig) -> List[Path]:
        """バックアップ対象ファイルのリストを取得"""
        backup_files = []
        
        try:
            for source_path in source_paths:
                source = Path(source_path)
                
                if not source.exists():
                    self.logger.warning(f"ソースパスが存在しません: {source}")
                    continue
                
                if source.is_file():
                    if self._should_include_file(source, config):
                        backup_files.append(source)
                elif source.is_dir():
                    for file_path in source.rglob('*'):
                        if file_path.is_file() and self._should_include_file(file_path, config):
                            backup_files.append(file_path)
            
            return backup_files
            
        except Exception as e:
            self.logger.error(f"バックアップファイル取得エラー: {e}")
            return []
    
    def _calculate_total_size(self, files: List[Path]) -> int:
        """ファイルリストの合計サイズを計算"""
        total_size = 0
        try:
            for file_path in files:
                if file_path.exists():
                    total_size += file_path.stat().st_size
        except Exception as e:
            self.logger.error(f"サイズ計算エラー: {e}")
        return total_size
    
    def _create_backup_id(self) -> str:
        """バックアップIDを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{timestamp}"
    
    def _save_backup_history(self, backup_directory: str, backup_info: BackupInfo):
        """バックアップ履歴を保存"""
        try:
            history_file = Path(backup_directory) / self.backup_history_file
            
            # 既存の履歴を読み込み
            history = []
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # 新しいバックアップ情報を追加
            backup_dict = asdict(backup_info)
            backup_dict['timestamp'] = backup_info.timestamp.isoformat()
            backup_dict['backup_type'] = backup_info.backup_type.value
            backup_dict['compression_type'] = backup_info.compression_type.value
            
            history.append(backup_dict)
            
            # 履歴を保存
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"バックアップ履歴保存エラー: {e}")
    
    def _load_backup_history(self, backup_directory: str) -> List[BackupInfo]:
        """バックアップ履歴を読み込み"""
        try:
            history_file = Path(backup_directory) / self.backup_history_file
            
            if not history_file.exists():
                return []
            
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            history = []
            for item in history_data:
                backup_info = BackupInfo(
                    backup_id=item['backup_id'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    backup_type=BackupType(item['backup_type']),
                    source_path=item['source_path'],
                    backup_path=item['backup_path'],
                    compression_type=CompressionType(item['compression_type']),
                    file_count=item['file_count'],
                    total_size=item['total_size'],
                    compressed_size=item.get('compressed_size'),
                    checksum=item.get('checksum'),
                    encrypted=item.get('encrypted', False),
                    description=item.get('description'),
                    metadata=item.get('metadata')
                )
                history.append(backup_info)
            
            return history
            
        except Exception as e:
            self.logger.error(f"バックアップ履歴読み込みエラー: {e}")
            return []
    
    def _create_zip_backup(self, files: List[Path], source_paths: List[str],
                          backup_path: Path, progress: BackupProgress) -> int:
        """ZIPバックアップを作成"""
        try:
            compressed_size = 0
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    if progress.is_cancelled:
                        break
                    
                    # 相対パスを計算
                    relative_path = None
                    for source_path in source_paths:
                        source = Path(source_path)
                        try:
                            if source.is_file() and file_path == source:
                                relative_path = file_path.name
                                break
                            elif source.is_dir() and file_path.is_relative_to(source):
                                relative_path = file_path.relative_to(source)
                                break
                        except ValueError:
                            continue
                    
                    if relative_path is None:
                        relative_path = file_path.name
                    
                    # ファイルをZIPに追加
                    zipf.write(file_path, str(relative_path))
                    progress.update(str(file_path), file_path.stat().st_size)
            
            if backup_path.exists():
                compressed_size = backup_path.stat().st_size
            
            return compressed_size
            
        except Exception as e:
            self.logger.error(f"ZIPバックアップ作成エラー: {e}")
            raise
    
    def _create_tar_backup(self, files: List[Path], source_paths: List[str],
                          backup_path: Path, compression_type: CompressionType,
                          progress: BackupProgress) -> int:
        """TARバックアップを作成"""
        try:
            compressed_size = 0
            
            # 圧縮モードを決定
            if compression_type == CompressionType.TAR_GZ:
                mode = 'w:gz'
            elif compression_type == CompressionType.TAR_BZ2:
                mode = 'w:bz2'
            else:
                mode = 'w'
            
            with tarfile.open(backup_path, mode) as tarf:
                for file_path in files:
                    if progress.is_cancelled:
                        break
                    
                    # 相対パスを計算
                    relative_path = None
                    for source_path in source_paths:
                        source = Path(source_path)
                        try:
                            if source.is_file() and file_path == source:
                                relative_path = file_path.name
                                break
                            elif source.is_dir() and file_path.is_relative_to(source):
                                relative_path = file_path.relative_to(source)
                                break
                        except ValueError:
                            continue
                    
                    if relative_path is None:
                        relative_path = file_path.name
                    
                    # ファイルをTARに追加
                    tarf.add(file_path, str(relative_path))
                    progress.update(str(file_path), file_path.stat().st_size)
            
            if backup_path.exists():
                compressed_size = backup_path.stat().st_size
            
            return compressed_size
            
        except Exception as e:
            self.logger.error(f"TARバックアップ作成エラー: {e}")
            raise
    
    def _create_directory_backup(self, files: List[Path], source_paths: List[str],
                               backup_path: Path, progress: BackupProgress) -> int:
        """ディレクトリバックアップを作成"""
        try:
            backup_path.mkdir(parents=True, exist_ok=True)
            total_size = 0
            
            for file_path in files:
                if progress.is_cancelled:
                    break
                
                # 相対パスを計算
                relative_path = None
                for source_path in source_paths:
                    source = Path(source_path)
                    try:
                        if source.is_file() and file_path == source:
                            relative_path = file_path.name
                            break
                        elif source.is_dir() and file_path.is_relative_to(source):
                            relative_path = file_path.relative_to(source)
                            break
                    except ValueError:
                        continue
                
                if relative_path is None:
                    relative_path = file_path.name
                
                # ファイルをコピー
                dest_path = backup_path / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                
                file_size = file_path.stat().st_size
                total_size += file_size
                progress.update(str(file_path), file_size)
            
            return total_size
            
        except Exception as e:
            self.logger.error(f"ディレクトリバックアップ作成エラー: {e}")
            raise
    
    def create_backup(self, config: BackupConfig, progress: Optional[BackupProgress] = None) -> BackupInfo:
        """バックアップを作成"""
        try:
            if progress is None:
                progress = BackupProgress()
            
            # バックアップディレクトリを作成
            backup_dir = Path(config.backup_directory)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # バックアップ対象ファイルを取得
            backup_files = self._get_backup_files(config.source_paths, config)
            if not backup_files:
                raise ValueError("バックアップ対象ファイルが見つかりません")
            
            # 進捗情報を初期化
            progress.total_files = len(backup_files)
            progress.total_size = self._calculate_total_size(backup_files)
            
            # バックアップIDとパスを生成
            backup_id = self._create_backup_id()
            
            # 拡張子を決定
            if config.compression_type == CompressionType.ZIP:
                extension = ".zip"
            elif config.compression_type == CompressionType.TAR_GZ:
                extension = ".tar.gz"
            elif config.compression_type == CompressionType.TAR_BZ2:
                extension = ".tar.bz2"
            else:
                extension = ""
            
            backup_path = backup_dir / f"{backup_id}{extension}"
            
            # バックアップを作成
            compressed_size = None
            if config.compression_type == CompressionType.ZIP:
                compressed_size = self._create_zip_backup(backup_files, config.source_paths, backup_path, progress)
            elif config.compression_type in [CompressionType.TAR_GZ, CompressionType.TAR_BZ2]:
                compressed_size = self._create_tar_backup(backup_files, config.source_paths, backup_path, config.compression_type, progress)
            else:
                backup_path = backup_dir / backup_id
                compressed_size = self._create_directory_backup(backup_files, config.source_paths, backup_path, progress)
            
            # キャンセルされた場合はクリーンアップ
            if progress.is_cancelled:
                if backup_path.exists():
                    if backup_path.is_file():
                        backup_path.unlink()
                    else:
                        shutil.rmtree(backup_path)
                raise InterruptedError("バックアップがキャンセルされました")
            
            # チェックサムを計算
            checksum = None
            if config.verify_backup and backup_path.is_file():
                checksum = self.file_utils.calculate_file_hash(backup_path)
            
            # 暗号化
            if config.encrypt_backup and config.encryption_password:
                if backup_path.is_file():
                    encrypted_path = self.encryption_utils.encrypt_file(
                        backup_path, config.encryption_password
                    )
                    backup_path.unlink()  # 元ファイルを削除
                    backup_path = encrypted_path
                else:
                    self.logger.warning("ディレクトリバックアップの暗号化はサポートされていません")
            
            # バックアップ情報を作成
            backup_info = BackupInfo(
                backup_id=backup_id,
                timestamp=datetime.now(),
                backup_type=config.backup_type,
                source_path=';'.join(config.source_paths),
                backup_path=str(backup_path),
                compression_type=config.compression_type,
                file_count=len(backup_files),
                total_size=progress.total_size,
                compressed_size=compressed_size,
                checksum=checksum,
                encrypted=config.encrypt_backup,
                metadata={
                    'exclude_patterns': config.exclude_patterns,
                    'include_patterns': config.include_patterns
                }
            )
            
            # バックアップ履歴を保存
            self._save_backup_history(config.backup_directory, backup_info)
            
            # 古いバックアップをクリーンアップ
            if config.auto_cleanup:
                self.cleanup_old_backups(config.backup_directory, config.max_backups)
            
            self.logger.info(f"バックアップが完了しました: {backup_id}")
            return backup_info
            
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー: {e}")
            raise
    
    def restore_backup(self, backup_info: BackupInfo, restore_path: str,
                      password: Optional[str] = None,
                      progress: Optional[BackupProgress] = None) -> bool:
        """バックアップを復元"""
        try:
            if progress is None:
                progress = BackupProgress()
            
            backup_path = Path(backup_info.backup_path)
            restore_dir = Path(restore_path)
            
            if not backup_path.exists():
                raise FileNotFoundError(f"バックアップファイルが見つかりません: {backup_path}")
            
            # 復元ディレクトリを作成
            restore_dir.mkdir(parents=True, exist_ok=True)
            
            # 暗号化されている場合は復号化
            if backup_info.encrypted:
                if not password:
                    raise ValueError("暗号化されたバックアップにはパスワードが必要です")
                
                decrypted_path = self.encryption_utils.decrypt_file(backup_path, password)
                backup_path = decrypted_path
            
            # バックアップを展開
            if backup_info.compression_type == CompressionType.ZIP:
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(restore_dir)
            elif backup_info.compression_type in [CompressionType.TAR_GZ, CompressionType.TAR_BZ2]:
                with tarfile.open(backup_path, 'r') as tarf:
                    tarf.extractall(restore_dir)
            else:
                # ディレクトリバックアップの場合
                if backup_path.is_dir():
                    shutil.copytree(backup_path, restore_dir, dirs_exist_ok=True)
            
            # 暗号化で一時ファイルを作成した場合はクリーンアップ
            if backup_info.encrypted and backup_path != Path(backup_info.backup_path):
                backup_path.unlink()
            
            self.logger.info(f"バックアップを復元しました: {backup_info.backup_id} -> {restore_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"バックアップ復元エラー: {e}")
            return False
    
    def list_backups(self, backup_directory: str) -> List[BackupInfo]:
        """バックアップ一覧を取得"""
        try:
            return self._load_backup_history(backup_directory)
        except Exception as e:
            self.logger.error(f"バックアップ一覧取得エラー: {e}")
            return []
    
    def delete_backup(self, backup_directory: str, backup_id: str) -> bool:
        """指定されたバックアップを削除"""
        try:
            history = self._load_backup_history(backup_directory)
            
            # 削除対象のバックアップを検索
            backup_to_delete = None
            for backup_info in history:
                if backup_info.backup_id == backup_id:
                    backup_to_delete = backup_info
                    break
            
            if not backup_to_delete:
                self.logger.warning(f"バックアップが見つかりません: {backup_id}")
                return False
            
            # バックアップファイルを削除
            backup_path = Path(backup_to_delete.backup_path)
            if backup_path.exists():
                if backup_path.is_file():
                    backup_path.unlink()
                else:
                    shutil.rmtree(backup_path)
            
            # 履歴から削除
            history = [b for b in history if b.backup_id != backup_id]
            
            # 履歴を保存
            history_file = Path(backup_directory) / self.backup_history_file
            history_data = []
            for backup_info in history:
                backup_dict = asdict(backup_info)
                backup_dict['timestamp'] = backup_info.timestamp.isoformat()
                backup_dict['backup_type'] = backup_info.backup_type.value
                backup_dict['compression_type'] = backup_info.compression_type.value
                history_data.append(backup_dict)
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"バックアップを削除しました: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"バックアップ削除エラー: {e}")
            return False
    
    def cleanup_old_backups(self, backup_directory: str, max_backups: int) -> int:
        """古いバックアップをクリーンアップ"""
        try:
            history = self._load_backup_history(backup_directory)
            
            if len(history) <= max_backups:
                return 0
            
            # 日付でソート（古い順）
            history.sort(key=lambda x: x.timestamp)
            
            # 削除対象を決定
            backups_to_delete = history[:-max_backups]
            deleted_count = 0
            
            for backup_info in backups_to_delete:
                if self.delete_backup(backup_directory, backup_info.backup_id):
                    deleted_count += 1
            
            self.logger.info(f"{deleted_count}個の古いバックアップを削除しました")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"バックアップクリーンアップエラー: {e}")
            return 0
    
    def verify_backup(self, backup_info: BackupInfo, password: Optional[str] = None) -> bool:
        """バックアップの整合性を検証"""
        try:
            backup_path = Path(backup_info.backup_path)
            
            if not backup_path.exists():
                self.logger.error(f"バックアップファイルが見つかりません: {backup_path}")
                return False
            
            # 暗号化されている場合は復号化してチェック
            if backup_info.encrypted:
                if not password:
                    self.logger.error("暗号化されたバックアップの検証にはパスワードが必要です")
                    return False
                
                try:
                    # 一時的に復号化
                    decrypted_path = self.encryption_utils.decrypt_file(backup_path, password)
                    backup_path = decrypted_path
                except Exception as e:
                    self.logger.error(f"バックアップの復号化に失敗しました: {e}")
                    return False
            
            # チェックサム検証
            if backup_info.checksum and backup_path.is_file():
                current_checksum = self.file_utils.calculate_file_hash(backup_path)
                if current_checksum != backup_info.checksum:
                    self.logger.error("バックアップのチェックサムが一致しません")
                    return False
            
            # アーカイブの整合性チェック
            try:
                if backup_info.compression_type == CompressionType.ZIP:
                    with zipfile.ZipFile(backup_path, 'r') as zipf:
                        zipf.testzip()
                elif backup_info.compression_type in [CompressionType.TAR_GZ, CompressionType.TAR_BZ2]:
                    with tarfile.open(backup_path, 'r') as tarf:
                        tarf.getmembers()  # アーカイブの読み込みテスト
            except Exception as e:
                self.logger.error(f"アーカイブの整合性チェックに失敗しました: {e}")
                return False
            
            # 暗号化で一時ファイルを作成した場合はクリーンアップ
            if backup_info.encrypted and backup_path != Path(backup_info.backup_path):
                backup_path.unlink()
            
            self.logger.info(f"バックアップの検証が完了しました: {backup_info.backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"バックアップ検証エラー: {e}")
            return False
    
    def get_backup_statistics(self, backup_directory: str) -> Dict[str, Any]:
        """バックアップ統計情報を取得"""
        try:
            history = self._load_backup_history(backup_directory)
            
            if not history:
                return {
                    'total_backups': 0,
                    'total_size': 0,
                    'compressed_size': 0,
                    'compression_ratio': 0.0,
                    'oldest_backup': None,
                    'newest_backup': None,
                    'backup_types': {},
                    'compression_types': {}
                }
            
            total_size = sum(b.total_size for b in history)
            compressed_size = sum(b.compressed_size or b.total_size for b in history)
            compression_ratio = (1 - compressed_size / total_size) * 100 if total_size > 0 else 0
            
            # バックアップタイプ別統計
            backup_types = {}
            for backup_info in history:
                backup_type = backup_info.backup_type.value
                backup_types[backup_type] = backup_types.get(backup_type, 0) + 1
            
            # 圧縮タイプ別統計
            compression_types = {}
            for backup_info in history:
                compression_type = backup_info.compression_type.value
                compression_types[compression_type] = compression_types.get(compression_type, 0) + 1
            
            # 日付でソート
            sorted_history = sorted(history, key=lambda x: x.timestamp)
            
            return {
                'total_backups': len(history),
                'total_size': total_size,
                'compressed_size': compressed_size,
                'compression_ratio': compression_ratio,
                'oldest_backup': sorted_history[0].timestamp if sorted_history else None,
                'newest_backup': sorted_history[-1].timestamp if sorted_history else None,
                'backup_types': backup_types,
                'compression_types': compression_types,
                'average_size': total_size // len(history) if history else 0,
                'average_compressed_size': compressed_size // len(history) if history else 0
            }
            
        except Exception as e:
            self.logger.error(f"バックアップ統計取得エラー: {e}")
            return {}
    
    def schedule_backup(self, config: BackupConfig, interval_hours: int = 24) -> bool:
        """定期バックアップをスケジュール"""
        try:
            # 簡単な実装例（実際のスケジューリングシステムと連携する場合は適宜修正）
            import threading
            import time
            
            def backup_worker():
                while True:
                    try:
                        self.create_backup(config)
                        self.logger.info(f"定期バックアップが完了しました")
                    except Exception as e:
                        self.logger.error(f"定期バックアップエラー: {e}")
                    
                    # 指定された間隔で待機
                    time.sleep(interval_hours * 3600)
            
            # バックグラウンドスレッドで実行
            backup_thread = threading.Thread(target=backup_worker, daemon=True)
            backup_thread.start()
            
            self.logger.info(f"定期バックアップをスケジュールしました（{interval_hours}時間間隔）")
            return True
            
        except Exception as e:
            self.logger.error(f"バックアップスケジュールエラー: {e}")
            return False
    
    def create_incremental_backup(self, config: BackupConfig, 
                                 last_backup_time: datetime,
                                 progress: Optional[BackupProgress] = None) -> BackupInfo:
        """増分バックアップを作成"""
        try:
            # 最後のバックアップ以降に変更されたファイルのみを対象とする
            all_files = self._get_backup_files(config.source_paths, config)
            
            # 変更されたファイルをフィルタリング
            modified_files = []
            for file_path in all_files:
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime > last_backup_time:
                        modified_files.append(file_path)
                except Exception:
                    continue
            
            if not modified_files:
                self.logger.info("増分バックアップ対象のファイルがありません")
                return None
            
            # 一時的にファイルリストを置き換えて通常のバックアップを実行
            original_get_backup_files = self._get_backup_files
            self._get_backup_files = lambda paths, cfg: modified_files
            
            try:
                # バックアップタイプを増分に設定
                incremental_config = BackupConfig(
                    source_paths=config.source_paths,
                    backup_directory=config.backup_directory,
                    backup_type=BackupType.INCREMENTAL,
                    compression_type=config.compression_type,
                    max_backups=config.max_backups,
                    exclude_patterns=config.exclude_patterns,
                    include_patterns=config.include_patterns,
                    encrypt_backup=config.encrypt_backup,
                    encryption_password=config.encryption_password,
                    auto_cleanup=config.auto_cleanup,
                    verify_backup=config.verify_backup
                )
                
                backup_info = self.create_backup(incremental_config, progress)
                backup_info.description = f"増分バックアップ（{len(modified_files)}ファイル）"
                
                return backup_info
                
            finally:
                # 元のメソッドを復元
                self._get_backup_files = original_get_backup_files
                
        except Exception as e:
            self.logger.error(f"増分バックアップ作成エラー: {e}")
            raise
    
    def create_differential_backup(self, config: BackupConfig,
                                  base_backup_time: datetime,
                                  progress: Optional[BackupProgress] = None) -> BackupInfo:
        """差分バックアップを作成"""
        try:
            # ベースバックアップ以降に変更されたファイルを対象とする
            all_files = self._get_backup_files(config.source_paths, config)
            
            # 変更されたファイルをフィルタリング
            modified_files = []
            for file_path in all_files:
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime > base_backup_time:
                        modified_files.append(file_path)
                except Exception:
                    continue
            
            if not modified_files:
                self.logger.info("差分バックアップ対象のファイルがありません")
                return None
            
            # 一時的にファイルリストを置き換えて通常のバックアップを実行
            original_get_backup_files = self._get_backup_files
            self._get_backup_files = lambda paths, cfg: modified_files
            
            try:
                # バックアップタイプを差分に設定
                differential_config = BackupConfig(
                    source_paths=config.source_paths,
                    backup_directory=config.backup_directory,
                    backup_type=BackupType.DIFFERENTIAL,
                    compression_type=config.compression_type,
                    max_backups=config.max_backups,
                    exclude_patterns=config.exclude_patterns,
                    include_patterns=config.include_patterns,
                    encrypt_backup=config.encrypt_backup,
                    encryption_password=config.encryption_password,
                    auto_cleanup=config.auto_cleanup,
                    verify_backup=config.verify_backup
                )
                
                backup_info = self.create_backup(differential_config, progress)
                backup_info.description = f"差分バックアップ（{len(modified_files)}ファイル）"
                
                return backup_info
                
            finally:
                # 元のメソッドを復元
                self._get_backup_files = original_get_backup_files
                
        except Exception as e:
            self.logger.error(f"差分バックアップ作成エラー: {e}")
            raise
    
    def export_backup_config(self, config: BackupConfig, file_path: str) -> bool:
        """バックアップ設定をファイルにエクスポート"""
        try:
            config_dict = {
                'source_paths': config.source_paths,
                'backup_directory': config.backup_directory,
                'backup_type': config.backup_type.value,
                'compression_type': config.compression_type.value,
                'max_backups': config.max_backups,
                'exclude_patterns': config.exclude_patterns,
                'include_patterns': config.include_patterns,
                'encrypt_backup': config.encrypt_backup,
                'auto_cleanup': config.auto_cleanup,
                'verify_backup': config.verify_backup,
                'exported_at': datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"バックアップ設定をエクスポートしました: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"バックアップ設定エクスポートエラー: {e}")
            return False
    
    def import_backup_config(self, file_path: str) -> Optional[BackupConfig]:
        """ファイルからバックアップ設定をインポート"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            config = BackupConfig(
                source_paths=config_dict['source_paths'],
                backup_directory=config_dict['backup_directory'],
                backup_type=BackupType(config_dict.get('backup_type', 'full')),
                compression_type=CompressionType(config_dict.get('compression_type', 'zip')),
                max_backups=config_dict.get('max_backups', 10),
                exclude_patterns=config_dict.get('exclude_patterns'),
                include_patterns=config_dict.get('include_patterns'),
                encrypt_backup=config_dict.get('encrypt_backup', False),
                auto_cleanup=config_dict.get('auto_cleanup', True),
                verify_backup=config_dict.get('verify_backup', True)
            )
            
            self.logger.info(f"バックアップ設定をインポートしました: {file_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"バックアップ設定インポートエラー: {e}")
            return None
    
    def sync_backups(self, source_directory: str, target_directory: str,
                    delete_extra: bool = False) -> bool:
        """バックアップディレクトリ間の同期"""
        try:
            source_dir = Path(source_directory)
            target_dir = Path(target_directory)
            
            if not source_dir.exists():
                raise FileNotFoundError(f"ソースディレクトリが見つかりません: {source_directory}")
            
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # ソースのバックアップ履歴を読み込み
            source_history = self._load_backup_history(source_directory)
            target_history = self._load_backup_history(target_directory)
            
            # ターゲットに存在しないバックアップIDを特定
            target_backup_ids = {b.backup_id for b in target_history}
            
            synced_count = 0
            for backup_info in source_history:
                if backup_info.backup_id not in target_backup_ids:
                    # バックアップファイルをコピー
                    source_backup_path = Path(backup_info.backup_path)
                    if source_backup_path.exists():
                        target_backup_path = target_dir / source_backup_path.name
                        
                        if source_backup_path.is_file():
                            shutil.copy2(source_backup_path, target_backup_path)
                        else:
                            shutil.copytree(source_backup_path, target_backup_path, dirs_exist_ok=True)
                        
                        # バックアップ情報を更新
                        backup_info.backup_path = str(target_backup_path)
                        self._save_backup_history(target_directory, backup_info)
                        synced_count += 1
            
            # 余分なバックアップを削除
            if delete_extra:
                source_backup_ids = {b.backup_id for b in source_history}
                deleted_count = 0
                
                for backup_info in target_history:
                    if backup_info.backup_id not in source_backup_ids:
                        if self.delete_backup(target_directory, backup_info.backup_id):
                            deleted_count += 1
                
                self.logger.info(f"{deleted_count}個の余分なバックアップを削除しました")
            
            self.logger.info(f"バックアップ同期が完了しました: {synced_count}個のバックアップを同期")
            return True
            
        except Exception as e:
            self.logger.error(f"バックアップ同期エラー: {e}")
            return False


# グローバルインスタンス
_backup_utils: Optional[BackupUtils] = None


def get_backup_utils() -> BackupUtils:
    """グローバルバックアップユーティリティを取得"""
    global _backup_utils
    if _backup_utils is None:
        _backup_utils = BackupUtils()
    return _backup_utils


# 便利関数
def create_simple_backup(source_path: str, backup_directory: str,
                        compression: str = "zip", encrypt: bool = False,
                        password: Optional[str] = None) -> Optional[BackupInfo]:
    """簡単なバックアップ作成"""
    try:
        config = BackupConfig(
            source_paths=[source_path],
            backup_directory=backup_directory,
            compression_type=CompressionType(compression),
            encrypt_backup=encrypt,
            encryption_password=password
        )
        
        backup_utils = get_backup_utils()
        return backup_utils.create_backup(config)
        
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"簡単バックアップ作成エラー: {e}")
        return None


def restore_simple_backup(backup_id: str, backup_directory: str,
                         restore_path: str, password: Optional[str] = None) -> bool:
    """簡単なバックアップ復元"""
    try:
        backup_utils = get_backup_utils()
        backups = backup_utils.list_backups(backup_directory)
        
        # バックアップIDで検索
        backup_info = None
        for backup in backups:
            if backup.backup_id == backup_id:
                backup_info = backup
                break
        
        if not backup_info:
            return False
        
        return backup_utils.restore_backup(backup_info, restore_path, password)
        
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"簡単バックアップ復元エラー: {e}")
        return False

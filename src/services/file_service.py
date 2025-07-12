# src/services/file_service.py
"""
ファイル操作サービス
LLM Code Assistant のファイル管理機能を提供
"""

import os
import shutil
import json
import yaml
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple, Any
from datetime import datetime, timedelta
import logging
import asyncio
import aiofiles
from dataclasses import dataclass
from enum import Enum

from ..core.exceptions import (
    FileServiceError,
    FileNotFoundError,
    FilePermissionError,
    FileSizeError,
    FileTypeError
)
#from ..core.config_manager import ConfigManager
from src.core.logger import get_logger

def ConfigManager(*args, **kwargs):
    from ..core.config_manager import ConfigManager
    return ConfigManager(*args, **kwargs)


logger = get_logger(__name__)


class FileType(Enum):
    """サポートされるファイルタイプ"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    HTML = "html"
    CSS = "css"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    TEXT = "text"
    SQL = "sql"
    SHELL = "shell"
    BINARY = "binary"
    UNKNOWN = "unknown"


@dataclass
class FileInfo:
    """ファイル情報データクラス"""
    path: str
    name: str
    size: int
    modified: datetime
    created: datetime
    file_type: FileType
    encoding: str
    mime_type: str
    is_directory: bool
    permissions: str
    hash_md5: Optional[str] = None
    content_preview: Optional[str] = None


@dataclass
class BackupInfo:
    """バックアップ情報データクラス"""
    original_path: str
    backup_path: str
    timestamp: datetime
    size: int
    hash_md5: str


class FileService:
    """ファイル操作サービスクラス"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        ファイルサービスの初期化
        
        Args:
            config_manager: 設定管理インスタンス
        """
        self.config = config_manager
        self.logger = get_logger(self.__class__.__name__)
        
        # 設定値の取得
        file_config = self.config.get('file_management', {})
        self.auto_save_enabled = file_config.get('auto_save', {}).get('enabled', True)
        self.auto_save_interval = file_config.get('auto_save', {}).get('interval', 300)
        self.backup_enabled = file_config.get('backup', {}).get('enabled', True)
        self.backup_interval = file_config.get('backup', {}).get('interval', 1800)
        self.max_backups = file_config.get('backup', {}).get('max_backups', 20)
        self.backup_path = Path(file_config.get('backup', {}).get('path', 'backups/files/'))
        self.temp_path = Path(file_config.get('temp_files', {}).get('path', 'temp/'))
        self.max_file_size = self._parse_size(
            self.config.get('performance', {}).get('limits', {}).get('max_file_size', '100MB')
        )
        
        # サポートされるファイル拡張子
        self.supported_extensions = set(
            file_config.get('file_types', {}).get('supported_extensions', [
                '.py', '.js', '.ts', '.html', '.css', '.json', '.yaml', '.yml',
                '.md', '.txt', '.sql', '.sh', '.bat', '.ps1'
            ])
        )
        
        # ディレクトリの作成
        self._ensure_directories()
        
        # ファイル監視とバックアップのタスク
        self._auto_save_task = None
        self._backup_task = None
        self._start_background_tasks()
    
    def _parse_size(self, size_str: str) -> int:
        """サイズ文字列をバイト数に変換"""
        size_str = size_str.upper().strip()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def _ensure_directories(self):
        """必要なディレクトリを作成"""
        try:
            self.backup_path.mkdir(parents=True, exist_ok=True)
            self.temp_path.mkdir(parents=True, exist_ok=True)
            self.logger.info("必要なディレクトリを作成しました")
        except Exception as e:
            self.logger.error(f"ディレクトリ作成エラー: {e}")
            raise FileServiceError(f"ディレクトリ作成に失敗しました: {e}")
    
    def _start_background_tasks(self):
        """バックグラウンドタスクの開始"""
        if self.auto_save_enabled:
            self._auto_save_task = asyncio.create_task(self._auto_save_loop())
        if self.backup_enabled:
            self._backup_task = asyncio.create_task(self._backup_loop())
    
    async def _auto_save_loop(self):
        """自動保存ループ"""
        while True:
            try:
                await asyncio.sleep(self.auto_save_interval)
                await self._perform_auto_save()
            except Exception as e:
                self.logger.error(f"自動保存エラー: {e}")
    
    async def _backup_loop(self):
        """バックアップループ"""
        while True:
            try:
                await asyncio.sleep(self.backup_interval)
                await self._perform_backup()
            except Exception as e:
                self.logger.error(f"バックアップエラー: {e}")
    
    async def _perform_auto_save(self):
        """自動保存の実行"""
        # 実装は後で追加
        pass
    
    async def _perform_backup(self):
        """バックアップの実行"""
        # 実装は後で追加
        pass
    
    def get_file_type(self, file_path: Union[str, Path]) -> FileType:
        """ファイルタイプの判定"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        type_mapping = {
            '.py': FileType.PYTHON,
            '.js': FileType.JAVASCRIPT,
            '.ts': FileType.TYPESCRIPT,
            '.html': FileType.HTML,
            '.css': FileType.CSS,
            '.json': FileType.JSON,
            '.yaml': FileType.YAML,
            '.yml': FileType.YAML,
            '.md': FileType.MARKDOWN,
            '.txt': FileType.TEXT,
            '.sql': FileType.SQL,
            '.sh': FileType.SHELL,
            '.bat': FileType.SHELL,
            '.ps1': FileType.SHELL
        }
        
        return type_mapping.get(extension, FileType.UNKNOWN)
    
    def get_file_info(self, file_path: Union[str, Path]) -> FileInfo:
        """ファイル情報の取得"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
            
            stat = path.stat()
            file_type = self.get_file_type(path)
            mime_type, _ = mimetypes.guess_type(str(path))
            
            # ファイルハッシュの計算（小さなファイルのみ）
            hash_md5 = None
            if not path.is_dir() and stat.st_size < 10 * 1024 * 1024:  # 10MB未満
                hash_md5 = self._calculate_file_hash(path)
            
            # コンテンツプレビュー（テキストファイルのみ）
            content_preview = None
            if file_type in [FileType.PYTHON, FileType.JAVASCRIPT, FileType.TEXT, 
                           FileType.JSON, FileType.YAML, FileType.MARKDOWN]:
                content_preview = self._get_content_preview(path)
            
            return FileInfo(
                path=str(path.absolute()),
                name=path.name,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                created=datetime.fromtimestamp(stat.st_ctime),
                file_type=file_type,
                encoding='utf-8',  # デフォルト
                mime_type=mime_type or 'application/octet-stream',
                is_directory=path.is_dir(),
                permissions=oct(stat.st_mode)[-3:],
                hash_md5=hash_md5,
                content_preview=content_preview
            )
            
        except Exception as e:
            self.logger.error(f"ファイル情報取得エラー: {e}")
            raise FileServiceError(f"ファイル情報の取得に失敗しました: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """ファイルのMD5ハッシュを計算"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.warning(f"ハッシュ計算エラー: {e}")
            return None
    
    def _get_content_preview(self, file_path: Path, max_lines: int = 10) -> str:
        """ファイルのコンテンツプレビューを取得"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append("...")
                        break
                    lines.append(line.rstrip())
                return '\n'.join(lines)
        except Exception as e:
            self.logger.warning(f"プレビュー取得エラー: {e}")
            return None
    
    async def read_file(self, file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
        """ファイルの非同期読み取り"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
            
            if path.stat().st_size > self.max_file_size:
                raise FileSizeError(f"ファイルサイズが制限を超えています: {file_path}")
            
            async with aiofiles.open(path, 'r', encoding=encoding) as f:
                content = await f.read()
                
            self.logger.debug(f"ファイル読み取り完了: {file_path}")
            return content
            
        except Exception as e:
            self.logger.error(f"ファイル読み取りエラー: {e}")
            raise FileServiceError(f"ファイルの読み取りに失敗しました: {e}")
    
    async def write_file(self, file_path: Union[str, Path], content: str, 
                        encoding: str = 'utf-8', backup: bool = True) -> bool:
        """ファイルの非同期書き込み"""
        try:
            path = Path(file_path)
            
            # バックアップの作成
            if backup and path.exists():
                await self.create_backup(path)
            
            # ディレクトリの作成
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイルの書き込み
            async with aiofiles.open(path, 'w', encoding=encoding) as f:
                await f.write(content)
            
            self.logger.info(f"ファイル書き込み完了: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル書き込みエラー: {e}")
            raise FileServiceError(f"ファイルの書き込みに失敗しました: {e}")
    
    async def create_backup(self, file_path: Union[str, Path]) -> BackupInfo:
        """ファイルのバックアップを作成"""
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                raise FileNotFoundError(f"バックアップ対象ファイルが見つかりません: {file_path}")
            
            # バックアップファイル名の生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
            backup_file_path = self.backup_path / backup_name
            
            # バックアップの作成
            shutil.copy2(source_path, backup_file_path)
            
            # バックアップ情報の作成
            backup_info = BackupInfo(
                original_path=str(source_path.absolute()),
                backup_path=str(backup_file_path.absolute()),
                timestamp=datetime.now(),
                size=backup_file_path.stat().st_size,
                hash_md5=self._calculate_file_hash(backup_file_path)
            )
            
            self.logger.info(f"バックアップ作成完了: {backup_file_path}")
            
            # 古いバックアップの削除
            await self._cleanup_old_backups(source_path.stem)
            
            return backup_info
            
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー: {e}")
            raise FileServiceError(f"バックアップの作成に失敗しました: {e}")
    
    async def _cleanup_old_backups(self, file_stem: str):
        """古いバックアップファイルの削除"""
        try:
            backup_files = list(self.backup_path.glob(f"{file_stem}_*"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 制限を超えたバックアップを削除
            for backup_file in backup_files[self.max_backups:]:
                backup_file.unlink()
                self.logger.debug(f"古いバックアップを削除: {backup_file}")
                
        except Exception as e:
            self.logger.warning(f"バックアップクリーンアップエラー: {e}")
            
    def list_directory(self, directory_path: Union[str, Path], 
                      recursive: bool = False, 
                      include_hidden: bool = False,
                      file_types: Optional[List[FileType]] = None) -> List[FileInfo]:
        """ディレクトリ内のファイル一覧を取得"""
        try:
            path = Path(directory_path)
            if not path.exists():
                raise FileNotFoundError(f"ディレクトリが見つかりません: {directory_path}")
            
            if not path.is_dir():
                raise FileServiceError(f"指定されたパスはディレクトリではありません: {directory_path}")
            
            files = []
            
            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"
            
            for item_path in path.glob(pattern):
                # 隠しファイルのスキップ
                if not include_hidden and item_path.name.startswith('.'):
                    continue
                
                try:
                    file_info = self.get_file_info(item_path)
                    
                    # ファイルタイプフィルタ
                    if file_types and file_info.file_type not in file_types:
                        continue
                    
                    files.append(file_info)
                    
                except Exception as e:
                    self.logger.warning(f"ファイル情報取得スキップ: {item_path}, エラー: {e}")
                    continue
            
            # ソート（フォルダ優先、名前順）
            files.sort(key=lambda x: (not x.is_directory, x.name.lower()))
            
            self.logger.debug(f"ディレクトリ一覧取得完了: {len(files)}件")
            return files
            
        except Exception as e:
            self.logger.error(f"ディレクトリ一覧取得エラー: {e}")
            raise FileServiceError(f"ディレクトリ一覧の取得に失敗しました: {e}")
    
    async def create_directory(self, directory_path: Union[str, Path], 
                              parents: bool = True, exist_ok: bool = True) -> bool:
        """ディレクトリの作成"""
        try:
            path = Path(directory_path)
            path.mkdir(parents=parents, exist_ok=exist_ok)
            
            self.logger.info(f"ディレクトリ作成完了: {directory_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ディレクトリ作成エラー: {e}")
            raise FileServiceError(f"ディレクトリの作成に失敗しました: {e}")
    
    async def delete_file(self, file_path: Union[str, Path], backup: bool = True) -> bool:
        """ファイルの削除"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"削除対象ファイルが見つかりません: {file_path}")
            
            # バックアップの作成
            if backup and path.is_file():
                await self.create_backup(path)
            
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            
            self.logger.info(f"ファイル削除完了: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル削除エラー: {e}")
            raise FileServiceError(f"ファイルの削除に失敗しました: {e}")
    
    async def move_file(self, source_path: Union[str, Path], 
                       destination_path: Union[str, Path], backup: bool = True) -> bool:
        """ファイルの移動"""
        try:
            src = Path(source_path)
            dst = Path(destination_path)
            
            if not src.exists():
                raise FileNotFoundError(f"移動元ファイルが見つかりません: {source_path}")
            
            # バックアップの作成
            if backup and src.is_file():
                await self.create_backup(src)
            
            # 移動先ディレクトリの作成
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(src), str(dst))
            
            self.logger.info(f"ファイル移動完了: {source_path} -> {destination_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル移動エラー: {e}")
            raise FileServiceError(f"ファイルの移動に失敗しました: {e}")
    
    async def copy_file(self, source_path: Union[str, Path], 
                       destination_path: Union[str, Path]) -> bool:
        """ファイルのコピー"""
        try:
            src = Path(source_path)
            dst = Path(destination_path)
            
            if not src.exists():
                raise FileNotFoundError(f"コピー元ファイルが見つかりません: {source_path}")
            
            # コピー先ディレクトリの作成
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            
            self.logger.info(f"ファイルコピー完了: {source_path} -> {destination_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルコピーエラー: {e}")
            raise FileServiceError(f"ファイルのコピーに失敗しました: {e}")
    
    def search_files(self, directory_path: Union[str, Path], 
                    pattern: str = "*", 
                    content_search: Optional[str] = None,
                    file_types: Optional[List[FileType]] = None,
                    size_range: Optional[Tuple[int, int]] = None,
                    date_range: Optional[Tuple[datetime, datetime]] = None) -> List[FileInfo]:
        """ファイル検索"""
        try:
            path = Path(directory_path)
            if not path.exists() or not path.is_dir():
                raise FileServiceError(f"検索対象ディレクトリが無効です: {directory_path}")
            
            results = []
            
            # パターンマッチングによる検索
            for file_path in path.rglob(pattern):
                try:
                    file_info = self.get_file_info(file_path)
                    
                    # ファイルタイプフィルタ
                    if file_types and file_info.file_type not in file_types:
                        continue
                    
                    # サイズフィルタ
                    if size_range:
                        min_size, max_size = size_range
                        if not (min_size <= file_info.size <= max_size):
                            continue
                    
                    # 日付フィルタ
                    if date_range:
                        start_date, end_date = date_range
                        if not (start_date <= file_info.modified <= end_date):
                            continue
                    
                    # コンテンツ検索
                    if content_search and not file_info.is_directory:
                        if not self._search_in_file_content(file_path, content_search):
                            continue
                    
                    results.append(file_info)
                    
                except Exception as e:
                    self.logger.warning(f"ファイル検索スキップ: {file_path}, エラー: {e}")
                    continue
            
            self.logger.info(f"ファイル検索完了: {len(results)}件")
            return results
            
        except Exception as e:
            self.logger.error(f"ファイル検索エラー: {e}")
            raise FileServiceError(f"ファイル検索に失敗しました: {e}")
    
    def _search_in_file_content(self, file_path: Path, search_term: str) -> bool:
        """ファイル内容の検索"""
        try:
            # バイナリファイルのスキップ
            if self.get_file_type(file_path) == FileType.BINARY:
                return False
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return search_term.lower() in content.lower()
                
        except Exception:
            return False
    
    async def create_temp_file(self, content: str = "", 
                              suffix: str = ".tmp", 
                              prefix: str = "llm_temp_") -> Path:
        """一時ファイルの作成"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            temp_filename = f"{prefix}{timestamp}{suffix}"
            temp_file_path = self.temp_path / temp_filename
            
            if content:
                async with aiofiles.open(temp_file_path, 'w', encoding='utf-8') as f:
                    await f.write(content)
            else:
                temp_file_path.touch()
            
            self.logger.debug(f"一時ファイル作成: {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            self.logger.error(f"一時ファイル作成エラー: {e}")
            raise FileServiceError(f"一時ファイルの作成に失敗しました: {e}")
    
    async def cleanup_temp_files(self, max_age_hours: int = 24):
        """一時ファイルのクリーンアップ"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            deleted_count = 0
            
            for temp_file in self.temp_path.glob("*"):
                try:
                    if temp_file.is_file():
                        file_time = datetime.fromtimestamp(temp_file.stat().st_mtime)
                        if file_time < cutoff_time:
                            temp_file.unlink()
                            deleted_count += 1
                            
                except Exception as e:
                    self.logger.warning(f"一時ファイル削除エラー: {temp_file}, {e}")
            
            self.logger.info(f"一時ファイルクリーンアップ完了: {deleted_count}件削除")
            
        except Exception as e:
            self.logger.error(f"一時ファイルクリーンアップエラー: {e}")
    
    def get_file_encoding(self, file_path: Union[str, Path]) -> str:
        """ファイルエンコーディングの検出"""
        try:
            import chardet
            
            path = Path(file_path)
            if not path.exists() or path.is_dir():
                return 'utf-8'
            
            with open(path, 'rb') as f:
                raw_data = f.read(10000)  # 最初の10KBを読み取り
                
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            # 信頼度が低い場合はUTF-8を使用
            if confidence < 0.7:
                encoding = 'utf-8'
            
            self.logger.debug(f"エンコーディング検出: {file_path} -> {encoding} (信頼度: {confidence})")
            return encoding
            
        except ImportError:
            self.logger.warning("chardetライブラリが見つかりません。UTF-8を使用します。")
            return 'utf-8'
        except Exception as e:
            self.logger.warning(f"エンコーディング検出エラー: {e}")
            return 'utf-8'
    
    async def validate_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """ファイルの検証"""
        try:
            path = Path(file_path)
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'file_info': None
            }
            
            # 基本的な存在確認
            if not path.exists():
                validation_result['valid'] = False
                validation_result['errors'].append("ファイルが存在しません")
                return validation_result
            
            # ファイル情報の取得
            file_info = self.get_file_info(path)
            validation_result['file_info'] = file_info
            
            # サイズチェック
            if file_info.size > self.max_file_size:
                validation_result['valid'] = False
                validation_result['errors'].append(f"ファイルサイズが制限を超えています: {file_info.size} bytes")
            
            # 拡張子チェック
            if path.suffix.lower() not in self.supported_extensions:
                validation_result['warnings'].append(f"サポートされていない拡張子です: {path.suffix}")
            
            # 読み取り権限チェック
            if not os.access(path, os.R_OK):
                validation_result['valid'] = False
                validation_result['errors'].append("ファイルの読み取り権限がありません")
            
            # テキストファイルの場合、エンコーディングチェック
            if file_info.file_type in [FileType.PYTHON, FileType.JAVASCRIPT, FileType.TEXT]:
                try:
                    encoding = self.get_file_encoding(path)
                    with open(path, 'r', encoding=encoding) as f:
                        f.read(1000)  # 最初の1000文字を試し読み
                except Exception as e:
                    validation_result['warnings'].append(f"ファイル読み取りテストで警告: {e}")
            
            self.logger.debug(f"ファイル検証完了: {file_path}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"ファイル検証エラー: {e}")
            return {
                'valid': False,
                'errors': [f"検証中にエラーが発生しました: {e}"],
                'warnings': [],
                'file_info': None
            }
    
    def get_project_structure(self, project_path: Union[str, Path], 
                            max_depth: int = 5) -> Dict[str, Any]:
        """プロジェクト構造の取得"""
        try:
            path = Path(project_path)
            if not path.exists() or not path.is_dir():
                raise FileServiceError(f"プロジェクトディレクトリが無効です: {project_path}")
            
            def build_tree(current_path: Path, current_depth: int = 0) -> Dict[str, Any]:
                if current_depth > max_depth:
                    return {"type": "directory", "truncated": True}
                
                node = {
                    "name": current_path.name,
                    "path": str(current_path.relative_to(path)),
                    "type": "directory" if current_path.is_dir() else "file"
                }
                
                if current_path.is_dir():
                    node["children"] = []
                    try:
                        for child in sorted(current_path.iterdir()):
                            # 隠しファイル・ディレクトリのスキップ
                            if child.name.startswith('.'):
                                continue
                            
                            # 一般的な無視すべきディレクトリ
                            ignore_dirs = {'__pycache__', 'node_modules', '.git', '.vscode', 'venv', 'env'}
                            if child.is_dir() and child.name in ignore_dirs:
                                continue
                            
                            child_node = build_tree(child, current_depth + 1)
                            node["children"].append(child_node)
                            
                    except PermissionError:
                        node["error"] = "アクセス権限がありません"
                else:
                    # ファイルの場合、追加情報
                    try:
                        file_info = self.get_file_info(current_path)
                        node["size"] = file_info.size
                        node["file_type"] = file_info.file_type.value
                        node["modified"] = file_info.modified.isoformat()
                    except Exception:
                        pass
                
                return node
            
            structure = build_tree(path)
            structure["project_root"] = str(path.absolute())
            
            self.logger.info(f"プロジェクト構造取得完了: {project_path}")
            return structure
            
        except Exception as e:
            self.logger.error(f"プロジェクト構造取得エラー: {e}")
            raise FileServiceError(f"プロジェクト構造の取得に失敗しました: {e}")
    
    async def export_files(self, file_paths: List[Union[str, Path]], 
                          export_path: Union[str, Path], 
                          format_type: str = "zip") -> Path:
        """ファイルのエクスポート"""
        try:
            export_dir = Path(export_path)
            export_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format_type == "zip":
                import zipfile
                export_file = export_dir / f"export_{timestamp}.zip"
                
                with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in file_paths:
                        path = Path(file_path)
                        if path.exists():
                            if path.is_file():
                                zipf.write(path, path.name)
                            elif path.is_dir():
                                for file_in_dir in path.rglob('*'):
                                    if file_in_dir.is_file():
                                        arcname = file_in_dir.relative_to(path.parent)
                                        zipf.write(file_in_dir, arcname)
            
            elif format_type == "tar":
                import tarfile
                export_file = export_dir / f"export_{timestamp}.tar.gz"
                
                with tarfile.open(export_file, 'w:gz') as tarf:
                    for file_path in file_paths:
                        path = Path(file_path)
                        if path.exists():
                            tarf.add(path, arcname=path.name)
            
            else:
                raise FileServiceError(f"サポートされていないエクスポート形式: {format_type}")
            
            self.logger.info(f"ファイルエクスポート完了: {export_file}")
            return export_file
            
        except Exception as e:
            self.logger.error(f"ファイルエクスポートエラー: {e}")
            raise FileServiceError(f"ファイルのエクスポートに失敗しました: {e}")
    
    async def close(self):
        """サービスのクリーンアップ"""
        try:
            # バックグラウンドタスクの停止
            if self._auto_save_task:
                self._auto_save_task.cancel()
            if self._backup_task:
                self._backup_task.cancel()
            
            # 一時ファイルのクリーンアップ
            await self.cleanup_temp_files()
            
            self.logger.info("FileService クリーンアップ完了")
            
        except Exception as e:
            self.logger.error(f"FileService クリーンアップエラー: {e}")


# ファイルサービスのファクトリ関数
def create_file_service(config_manager: ConfigManager) -> FileService:
    """ファイルサービスのインスタンスを作成"""
    return FileService(config_manager)

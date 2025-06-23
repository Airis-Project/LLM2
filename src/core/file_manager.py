# src/core/file_manager.py
"""
ファイル管理モジュール
ファイルの読み書き、監視、バックアップなどを管理
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import hashlib
import json
import mimetypes
from dataclasses import dataclass

from .logger import get_logger

@dataclass
class FileInfo:
    """ファイル情報データクラス"""
    path: Path
    name: str
    size: int
    modified: datetime
    is_directory: bool
    mime_type: Optional[str] = None
    encoding: Optional[str] = None

class FileManager:
    """ファイル管理クラス"""
    
    def __init__(self, config=None):  # configの型チェックを緩和
        self.logger = get_logger(__name__)
        self.config = config
        
        # 設定からパスを取得（設定がない場合はデフォルト値を使用）
        if hasattr(config, 'workspace_directory'):
            self.workspace_directory = Path(config.workspace_directory)
        else:
            self.workspace_directory = Path('./workspace')
        
        if hasattr(config, 'backup_directory'):
            self.backup_directory = Path(config.backup_directory)
        else:
            self.backup_directory = Path('./backups')
        
        # ディレクトリを作成
        self.workspace_directory.mkdir(parents=True, exist_ok=True)
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("ファイル管理を初期化しました")
    
    def read_file(self, file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
        """ファイルを読み込み"""
        try:
            path = Path(file_path)
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            self.logger.debug(f"ファイルを読み込みました: {path}")
            return content
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー {file_path}: {e}")
            raise
    
    def write_file(self, file_path: Union[str, Path], content: str, encoding: str = 'utf-8'):
        """ファイルに書き込み"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            self.logger.debug(f"ファイルに書き込みました: {path}")
        except Exception as e:
            self.logger.error(f"ファイル書き込みエラー {file_path}: {e}")
            raise
    
    def get_file_info(self, file_path: Union[str, Path]) -> FileInfo:
        """ファイル情報を取得"""
        path = Path(file_path)
        stat = path.stat()
        
        mime_type, _ = mimetypes.guess_type(str(path))
        
        return FileInfo(
            path=path,
            name=path.name,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
            is_directory=path.is_dir(),
            mime_type=mime_type
        )
    
    def list_files(self, directory: Union[str, Path], 
                   pattern: str = "*", recursive: bool = False) -> List[FileInfo]:
        """ディレクトリ内のファイル一覧を取得"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return []
            
            if recursive:
                files = dir_path.rglob(pattern)
            else:
                files = dir_path.glob(pattern)
            
            file_infos = []
            for file_path in files:
                try:
                    file_infos.append(self.get_file_info(file_path))
                except Exception as e:
                    self.logger.warning(f"ファイル情報取得エラー {file_path}: {e}")
            
            return file_infos
        except Exception as e:
            self.logger.error(f"ファイル一覧取得エラー {directory}: {e}")
            return []
    
    def create_backup(self, file_path: Union[str, Path]) -> Path:
        """ファイルのバックアップを作成"""
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                raise FileNotFoundError(f"ファイルが存在しません: {source_path}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
            backup_path = self.backup_directory / backup_name
            
            shutil.copy2(source_path, backup_path)
            self.logger.info(f"バックアップを作成しました: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー {file_path}: {e}")
            raise

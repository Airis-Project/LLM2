# src/utils/file_utils.py
"""
ファイルユーティリティ
ファイル操作に関する共通機能を提供
"""

import os
import shutil
import hashlib
import mimetypes
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Iterator, Any
from dataclasses import dataclass
from datetime import datetime
import json
import yaml

from ..core.logger import get_logger


@dataclass
class FileInfo:
    """ファイル情報"""
    path: str
    name: str
    size: int
    modified_time: datetime
    created_time: datetime
    is_directory: bool
    extension: str = ""
    mime_type: str = ""
    hash_md5: str = ""
    hash_sha256: str = ""
    encoding: str = "utf-8"
    
    def __post_init__(self):
        if not self.extension and not self.is_directory:
            self.extension = Path(self.path).suffix.lower()
        if not self.mime_type:
            self.mime_type, _ = mimetypes.guess_type(self.path)
            if not self.mime_type:
                self.mime_type = "application/octet-stream"


class FileUtils:
    """ファイルユーティリティクラス"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # サポートされるテキストファイル拡張子
        self.text_extensions = {
            '.txt', '.py', '.js', '.html', '.htm', '.css', '.json', '.xml',
            '.yaml', '.yml', '.md', '.rst', '.ini', '.cfg', '.conf',
            '.log', '.sql', '.sh', '.bat', '.ps1', '.php', '.rb', '.go',
            '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.vb', '.pl',
            '.r', '.scala', '.swift', '.kt', '.dart', '.ts', '.jsx',
            '.tsx', '.vue', '.svelte', '.sass', '.scss', '.less'
        }
        
        # バイナリファイル拡張子
        self.binary_extensions = {
            '.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.db',
            '.sqlite', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.ppt', '.pptx', '.zip', '.rar', '.7z', '.tar', '.gz',
            '.bz2', '.xz', '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.tiff', '.svg', '.ico', '.mp3', '.mp4', '.avi', '.mov',
            '.wmv', '.flv', '.mkv', '.wav', '.ogg', '.flac'
        }
    
    def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """ファイル情報を取得"""
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            path_obj = Path(file_path)
            
            file_info = FileInfo(
                path=str(path_obj.absolute()),
                name=path_obj.name,
                size=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                created_time=datetime.fromtimestamp(stat.st_ctime),
                is_directory=os.path.isdir(file_path)
            )
            
            # ハッシュ値を計算（ファイルの場合のみ）
            if not file_info.is_directory and file_info.size > 0:
                try:
                    file_info.hash_md5 = self.calculate_file_hash(file_path, 'md5')
                    file_info.hash_sha256 = self.calculate_file_hash(file_path, 'sha256')
                except Exception as e:
                    self.logger.warning(f"ハッシュ計算エラー {file_path}: {e}")
            
            # エンコーディング検出（テキストファイルの場合）
            if self.is_text_file(file_path):
                file_info.encoding = self.detect_encoding(file_path)
            
            return file_info
            
        except Exception as e:
            self.logger.error(f"ファイル情報取得エラー {file_path}: {e}")
            return None
    
    def calculate_file_hash(self, file_path: str, algorithm: str = 'md5') -> str:
        """ファイルのハッシュ値を計算"""
        try:
            if algorithm.lower() == 'md5':
                hash_obj = hashlib.md5()
            elif algorithm.lower() == 'sha256':
                hash_obj = hashlib.sha256()
            elif algorithm.lower() == 'sha1':
                hash_obj = hashlib.sha1()
            else:
                raise ValueError(f"サポートされていないハッシュアルゴリズム: {algorithm}")
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"ハッシュ計算エラー {file_path}: {e}")
            raise
    
    def is_text_file(self, file_path: str) -> bool:
        """テキストファイルかどうかを判定"""
        try:
            extension = Path(file_path).suffix.lower()
            
            # 拡張子による判定
            if extension in self.text_extensions:
                return True
            if extension in self.binary_extensions:
                return False
            
            # ファイル内容による判定
            try:
                with open(file_path, 'rb') as f:
                    chunk = f.read(1024)
                    if b'\x00' in chunk:  # NULL文字があればバイナリ
                        return False
                    
                    # UTF-8として解読可能かチェック
                    chunk.decode('utf-8')
                    return True
                    
            except (UnicodeDecodeError, IOError):
                return False
                
        except Exception as e:
            self.logger.error(f"テキストファイル判定エラー {file_path}: {e}")
            return False
    
    def detect_encoding(self, file_path: str) -> str:
        """ファイルのエンコーディングを検出"""
        try:
            import chardet
            
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # 最初の10KBを読み取り
                
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            # 信頼度が低い場合はUTF-8を使用
            if confidence < 0.7:
                encoding = 'utf-8'
            
            return encoding
            
        except ImportError:
            # chardetがない場合はUTF-8を返す
            return 'utf-8'
        except Exception as e:
            self.logger.warning(f"エンコーディング検出エラー {file_path}: {e}")
            return 'utf-8'
    
    def read_file(self, file_path: str, encoding: str = None) -> Optional[str]:
        """ファイルを読み取り"""
        try:
            if not os.path.exists(file_path):
                return None
            
            if not self.is_text_file(file_path):
                self.logger.warning(f"テキストファイルではありません: {file_path}")
                return None
            
            if encoding is None:
                encoding = self.detect_encoding(file_path)
            
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
                
        except Exception as e:
            self.logger.error(f"ファイル読み取りエラー {file_path}: {e}")
            return None
    
    def write_file(self, file_path: str, content: str, encoding: str = 'utf-8',
                   create_dirs: bool = True, backup: bool = False) -> bool:
        """ファイルを書き込み"""
        try:
            # ディレクトリ作成
            if create_dirs:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # バックアップ作成
            if backup and os.path.exists(file_path):
                backup_path = f"{file_path}.backup"
                shutil.copy2(file_path, backup_path)
            
            # ファイル書き込み
            with open(file_path, 'w', encoding=encoding, newline='') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル書き込みエラー {file_path}: {e}")
            return False
    
    def copy_file(self, src_path: str, dst_path: str, 
                  create_dirs: bool = True) -> bool:
        """ファイルをコピー"""
        try:
            if not os.path.exists(src_path):
                self.logger.error(f"ソースファイルが存在しません: {src_path}")
                return False
            
            if create_dirs:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            
            shutil.copy2(src_path, dst_path)
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルコピーエラー {src_path} -> {dst_path}: {e}")
            return False
    
    def move_file(self, src_path: str, dst_path: str,
                  create_dirs: bool = True) -> bool:
        """ファイルを移動"""
        try:
            if not os.path.exists(src_path):
                self.logger.error(f"ソースファイルが存在しません: {src_path}")
                return False
            
            if create_dirs:
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            
            shutil.move(src_path, dst_path)
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル移動エラー {src_path} -> {dst_path}: {e}")
            return False
    
    def delete_file(self, file_path: str) -> bool:
        """ファイルを削除"""
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                return True
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                return True
            else:
                self.logger.warning(f"ファイルが存在しません: {file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"ファイル削除エラー {file_path}: {e}")
            return False
    
    def list_files(self, directory: str, recursive: bool = False,
                   include_dirs: bool = True, pattern: str = None) -> List[str]:
        """ディレクトリ内のファイル一覧を取得"""
        try:
            files = []
            
            if recursive:
                for root, dirs, filenames in os.walk(directory):
                    if include_dirs:
                        for dirname in dirs:
                            dir_path = os.path.join(root, dirname)
                            if pattern is None or self._match_pattern(dirname, pattern):
                                files.append(dir_path)
                    
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        if pattern is None or self._match_pattern(filename, pattern):
                            files.append(file_path)
            else:
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    if os.path.isfile(item_path) or (include_dirs and os.path.isdir(item_path)):
                        if pattern is None or self._match_pattern(item, pattern):
                            files.append(item_path)
            
            return sorted(files)
            
        except Exception as e:
            self.logger.error(f"ファイル一覧取得エラー {directory}: {e}")
            return []
    
    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """パターンマッチング"""
        try:
            import fnmatch
            return fnmatch.fnmatch(filename.lower(), pattern.lower())
        except Exception:
            return pattern.lower() in filename.lower()
    
    def find_files(self, directory: str, extensions: List[str] = None,
                   name_pattern: str = None, content_pattern: str = None,
                   recursive: bool = True) -> List[str]:
        """条件に一致するファイルを検索"""
        try:
            found_files = []
            
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    
                    # 拡張子フィルタ
                    if extensions:
                        file_ext = Path(filename).suffix.lower()
                        if file_ext not in [ext.lower() for ext in extensions]:
                            continue
                    
                    # ファイル名パターンフィルタ
                    if name_pattern and not self._match_pattern(filename, name_pattern):
                        continue
                    
                    # ファイル内容パターンフィルタ
                    if content_pattern and self.is_text_file(file_path):
                        content = self.read_file(file_path)
                        if content and content_pattern.lower() not in content.lower():
                            continue
                    
                    found_files.append(file_path)
                
                if not recursive:
                    break
            
            return found_files
            
        except Exception as e:
            self.logger.error(f"ファイル検索エラー {directory}: {e}")
            return []
    
    def get_directory_size(self, directory: str) -> int:
        """ディレクトリのサイズを取得（バイト）"""
        try:
            total_size = 0
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, IOError):
                        continue
            return total_size
            
        except Exception as e:
            self.logger.error(f"ディレクトリサイズ取得エラー {directory}: {e}")
            return 0
    
    def create_directory(self, directory: str, exist_ok: bool = True) -> bool:
        """ディレクトリを作成"""
        try:
            os.makedirs(directory, exist_ok=exist_ok)
            return True
            
        except Exception as e:
            self.logger.error(f"ディレクトリ作成エラー {directory}: {e}")
            return False
    
    def copy_directory(self, src_dir: str, dst_dir: str) -> bool:
        """ディレクトリをコピー"""
        try:
            if not os.path.exists(src_dir):
                self.logger.error(f"ソースディレクトリが存在しません: {src_dir}")
                return False
            
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
            return True
            
        except Exception as e:
            self.logger.error(f"ディレクトリコピーエラー {src_dir} -> {dst_dir}: {e}")
            return False
    
    def create_archive(self, source_path: str, archive_path: str,
                       archive_type: str = 'zip') -> bool:
        """アーカイブを作成"""
        try:
            if archive_type.lower() == 'zip':
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    if os.path.isfile(source_path):
                        zipf.write(source_path, os.path.basename(source_path))
                    else:
                        for root, dirs, files in os.walk(source_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, source_path)
                                zipf.write(file_path, arcname)
            
            elif archive_type.lower() in ['tar', 'tar.gz', 'tgz']:
                mode = 'w:gz' if archive_type.lower() in ['tar.gz', 'tgz'] else 'w'
                with tarfile.open(archive_path, mode) as tarf:
                    tarf.add(source_path, arcname=os.path.basename(source_path))
            
            else:
                raise ValueError(f"サポートされていないアーカイブタイプ: {archive_type}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"アーカイブ作成エラー {source_path} -> {archive_path}: {e}")
            return False
    
    def extract_archive(self, archive_path: str, extract_path: str) -> bool:
        """アーカイブを展開"""
        try:
            if not os.path.exists(archive_path):
                self.logger.error(f"アーカイブファイルが存在しません: {archive_path}")
                return False
            
            os.makedirs(extract_path, exist_ok=True)
            
            if archive_path.lower().endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    zipf.extractall(extract_path)
            
            elif archive_path.lower().endswith(('.tar', '.tar.gz', '.tgz', '.tar.bz2')):
                with tarfile.open(archive_path, 'r:*') as tarf:
                    tarf.extractall(extract_path)
            
            else:
                raise ValueError(f"サポートされていないアーカイブタイプ: {archive_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"アーカイブ展開エラー {archive_path} -> {extract_path}: {e}")
            return False
    
    def create_temp_file(self, suffix: str = '', prefix: str = 'tmp',
                        content: str = None) -> Optional[str]:
        """一時ファイルを作成"""
        try:
            fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            
            if content is not None:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                os.close(fd)
            
            return temp_path
            
        except Exception as e:
            self.logger.error(f"一時ファイル作成エラー: {e}")
            return None
    
    def create_temp_directory(self, suffix: str = '', prefix: str = 'tmp') -> Optional[str]:
        """一時ディレクトリを作成"""
        try:
            temp_dir = tempfile.mkdtemp(suffix=suffix, prefix=prefix)
            return temp_dir
            
        except Exception as e:
            self.logger.error(f"一時ディレクトリ作成エラー: {e}")
            return None
    
    def safe_filename(self, filename: str) -> str:
        """安全なファイル名に変換"""
        try:
            # 危険な文字を置換
            unsafe_chars = '<>:"/\\|?*'
            safe_name = filename
            
            for char in unsafe_chars:
                safe_name = safe_name.replace(char, '_')
            
            # 制御文字を削除
            safe_name = ''.join(char for char in safe_name if ord(char) >= 32)
            
            # 先頭・末尾の空白とピリオドを削除
            safe_name = safe_name.strip(' .')
            
            # 空の場合はデフォルト名
            if not safe_name:
                safe_name = 'untitled'
            
            # 長さ制限（255文字）
            if len(safe_name) > 255:
                name, ext = os.path.splitext(safe_name)
                safe_name = name[:255-len(ext)] + ext
            
            return safe_name
            
        except Exception as e:
            self.logger.error(f"安全ファイル名変換エラー {filename}: {e}")
            return 'untitled'
    
    def load_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        """JSONファイルを読み込み"""
        try:
            content = self.read_file(file_path)
            if content is None:
                return None
            
            return json.loads(content)
            
        except Exception as e:
            self.logger.error(f"JSON読み込みエラー {file_path}: {e}")
            return None
    
    def save_json(self, file_path: str, data: Dict[str, Any],
                  indent: int = 2, ensure_ascii: bool = False) -> bool:
        """JSONファイルを保存"""
        try:
            content = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
            return self.write_file(file_path, content)
            
        except Exception as e:
            self.logger.error(f"JSON保存エラー {file_path}: {e}")
            return False
    
    def load_yaml(self, file_path: str) -> Optional[Dict[str, Any]]:
        """YAMLファイルを読み込み"""
        try:
            content = self.read_file(file_path)
            if content is None:
                return None
            
            return yaml.safe_load(content)
            
        except Exception as e:
            self.logger.error(f"YAML読み込みエラー {file_path}: {e}")
            return None
    
    def save_yaml(self, file_path: str, data: Dict[str, Any]) -> bool:
        """YAMLファイルを保存"""
        try:
            content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
            return self.write_file(file_path, content)
            
        except Exception as e:
            self.logger.error(f"YAML保存エラー {file_path}: {e}")
            return False


# グローバルインスタンス
_file_utils: Optional[FileUtils] = None


def get_file_utils() -> FileUtils:
    """グローバルファイルユーティリティを取得"""
    global _file_utils
    if _file_utils is None:
        _file_utils = FileUtils()
    return _file_utils

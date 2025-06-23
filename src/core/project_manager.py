# src/core/project_manager.py
"""
プロジェクト管理モジュール
プロジェクトの作成、読み込み、保存、分析を行う
VectorDBとの連携でコード検索・参照機能を提供
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import mimetypes
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .logger import get_logger
from .config_manager import get_config
from ..utils.file_utils import FileUtils
from ..utils.text_utils import TextUtils
from ..utils.validation_utils import ValidationUtils

logger = get_logger(__name__)

@dataclass
class FileInfo:
    """ファイル情報のデータクラス"""
    path: str
    name: str
    extension: str
    size: int
    modified: str
    encoding: str = "utf-8"
    language: str = ""
    hash: str = ""
    content_preview: str = ""
    line_count: int = 0
    is_binary: bool = False

@dataclass
class ProjectInfo:
    """プロジェクト情報のデータクラス"""
    name: str
    path: str
    description: str = ""
    created: str = ""
    modified: str = ""
    version: str = "1.0.0"
    author: str = ""
    language: str = ""
    framework: str = ""
    dependencies: List[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []

@dataclass
class ProjectStats:
    """プロジェクト統計情報のデータクラス"""
    total_files: int = 0
    total_lines: int = 0
    total_size: int = 0
    file_types: Dict[str, int] = None
    languages: Dict[str, int] = None
    largest_files: List[Tuple[str, int]] = None
    
    def __post_init__(self):
        if self.file_types is None:
            self.file_types = {}
        if self.languages is None:
            self.languages = {}
        if self.largest_files is None:
            self.largest_files = []

class ProjectDatabase:
    """プロジェクトデータベース管理クラス"""
    
    def __init__(self, db_path: str):
        """
        初期化
        
        Args:
            db_path: データベースファイルパス
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """データベースを初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        path TEXT UNIQUE NOT NULL,
                        description TEXT,
                        created TEXT,
                        modified TEXT,
                        version TEXT,
                        author TEXT,
                        language TEXT,
                        framework TEXT,
                        dependencies TEXT,
                        tags TEXT,
                        metadata TEXT
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER,
                        path TEXT NOT NULL,
                        name TEXT NOT NULL,
                        extension TEXT,
                        size INTEGER,
                        modified TEXT,
                        encoding TEXT,
                        language TEXT,
                        hash TEXT,
                        content_preview TEXT,
                        line_count INTEGER,
                        is_binary BOOLEAN,
                        FOREIGN KEY (project_id) REFERENCES projects (id)
                    )
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_files_project_id ON files (project_id)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_files_extension ON files (extension)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_files_language ON files (language)
                ''')
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
    
    def save_project(self, project_info: ProjectInfo) -> bool:
        """
        プロジェクト情報を保存
        
        Args:
            project_info: プロジェクト情報
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO projects 
                        (name, path, description, created, modified, version, 
                         author, language, framework, dependencies, tags, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        project_info.name,
                        project_info.path,
                        project_info.description,
                        project_info.created,
                        project_info.modified,
                        project_info.version,
                        project_info.author,
                        project_info.language,
                        project_info.framework,
                        json.dumps(project_info.dependencies),
                        json.dumps(project_info.tags),
                        json.dumps(asdict(project_info))
                    ))
                    conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"プロジェクト保存エラー: {e}")
            return False
    
    def load_project(self, project_path: str) -> Optional[ProjectInfo]:
        """
        プロジェクト情報を読み込み
        
        Args:
            project_path: プロジェクトパス
            
        Returns:
            Optional[ProjectInfo]: プロジェクト情報
        """
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        'SELECT * FROM projects WHERE path = ?',
                        (project_path,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        return ProjectInfo(
                            name=row[1],
                            path=row[2],
                            description=row[3] or "",
                            created=row[4] or "",
                            modified=row[5] or "",
                            version=row[6] or "1.0.0",
                            author=row[7] or "",
                            language=row[8] or "",
                            framework=row[9] or "",
                            dependencies=json.loads(row[10] or "[]"),
                            tags=json.loads(row[11] or "[]")
                        )
            return None
            
        except Exception as e:
            logger.error(f"プロジェクト読み込みエラー: {e}")
            return None
    
    def save_files(self, project_path: str, files: List[FileInfo]) -> bool:
        """
        ファイル情報を保存
        
        Args:
            project_path: プロジェクトパス
            files: ファイル情報リスト
            
        Returns:
            bool: 保存成功フラグ
        """
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    # プロジェクトIDを取得
                    cursor = conn.execute(
                        'SELECT id FROM projects WHERE path = ?',
                        (project_path,)
                    )
                    project_row = cursor.fetchone()
                    if not project_row:
                        return False
                    
                    project_id = project_row[0]
                    
                    # 既存のファイル情報を削除
                    conn.execute(
                        'DELETE FROM files WHERE project_id = ?',
                        (project_id,)
                    )
                    
                    # 新しいファイル情報を挿入
                    for file_info in files:
                        conn.execute('''
                            INSERT INTO files 
                            (project_id, path, name, extension, size, modified, 
                             encoding, language, hash, content_preview, line_count, is_binary)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            project_id,
                            file_info.path,
                            file_info.name,
                            file_info.extension,
                            file_info.size,
                            file_info.modified,
                            file_info.encoding,
                            file_info.language,
                            file_info.hash,
                            file_info.content_preview,
                            file_info.line_count,
                            file_info.is_binary
                        ))
                    
                    conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"ファイル情報保存エラー: {e}")
            return False
    
    def get_projects(self) -> List[ProjectInfo]:
        """
        全プロジェクト情報を取得
        
        Returns:
            List[ProjectInfo]: プロジェクト情報リスト
        """
        projects = []
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('SELECT * FROM projects ORDER BY modified DESC')
                    for row in cursor.fetchall():
                        projects.append(ProjectInfo(
                            name=row[1],
                            path=row[2],
                            description=row[3] or "",
                            created=row[4] or "",
                            modified=row[5] or "",
                            version=row[6] or "1.0.0",
                            author=row[7] or "",
                            language=row[8] or "",
                            framework=row[9] or "",
                            dependencies=json.loads(row[10] or "[]"),
                            tags=json.loads(row[11] or "[]")
                        ))
        except Exception as e:
            logger.error(f"プロジェクト一覧取得エラー: {e}")
        
        return projects

class ProjectManager:
    """プロジェクト管理クラス"""
    
    # サポートするファイル拡張子
    SUPPORTED_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.txt': 'text',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bat': 'batch',
        '.ps1': 'powershell',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.r': 'r',
        '.m': 'matlab',
        '.pl': 'perl'
    }
    
    # 除外するディレクトリ
    EXCLUDE_DIRS = {
        '__pycache__', '.git', '.svn', '.hg', 'node_modules',
        '.vscode', '.idea', 'venv', 'env', '.env',
        'build', 'dist', 'target', 'bin', 'obj',
        '.pytest_cache', '.coverage', '.tox'
    }
    
    # 除外するファイル
    EXCLUDE_FILES = {
        '.gitignore', '.gitattributes', '.DS_Store', 'Thumbs.db',
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe',
        '.log', '.tmp', '.temp', '.cache'
    }
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初期化
        
        Args:
            db_path: データベースファイルパス
        """
        config = get_config()
        self.db_path = db_path or "./data/projects.db"
        
        # データベースディレクトリを作成
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.database = ProjectDatabase(self.db_path)
        self.current_project: Optional[ProjectInfo] = None
        self.current_files: List[FileInfo] = []
        
        # ユーティリティクラス
        self.file_utils = FileUtils()
        self.text_utils = TextUtils()
        self.validation_utils = ValidationUtils()
    
    def create_project(self, name: str, path: str, description: str = "",
                      author: str = "", language: str = "", 
                      framework: str = "") -> bool:
        """
        新しいプロジェクトを作成
        
        Args:
            name: プロジェクト名
            path: プロジェクトパス
            description: 説明
            author: 作成者
            language: 主要言語
            framework: フレームワーク
            
        Returns:
            bool: 作成成功フラグ
        """
        try:
            # パス検証
            if not self.validation_utils.is_valid_path(path):
                logger.error(f"無効なパス: {path}")
                return False
            
            project_path = Path(path).resolve()
            
            # プロジェクト情報を作成
            now = datetime.now().isoformat()
            project_info = ProjectInfo(
                name=name,
                path=str(project_path),
                description=description,
                created=now,
                modified=now,
                author=author,
                language=language,
                framework=framework
            )
            
            # データベースに保存
            if self.database.save_project(project_info):
                self.current_project = project_info
                logger.info(f"プロジェクトを作成しました: {name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"プロジェクト作成エラー: {e}")
            return False
    
    def load_project(self, path: str) -> bool:
        """
        プロジェクトを読み込み
        
        Args:
            path: プロジェクトパス
            
        Returns:
            bool: 読み込み成功フラグ
        """
        try:
            project_path = Path(path).resolve()
            
            if not project_path.exists():
                logger.error(f"プロジェクトパスが存在しません: {path}")
                return False
            
            # データベースからプロジェクト情報を読み込み
            project_info = self.database.load_project(str(project_path))
            
            if not project_info:
                # 新しいプロジェクトとして作成
                project_name = project_path.name
                if not self.create_project(project_name, str(project_path)):
                    return False
                project_info = self.current_project
            
            self.current_project = project_info
            
            # ファイルを分析
            self.analyze_project()
            
            logger.info(f"プロジェクトを読み込みました: {project_info.name}")
            return True
            
        except Exception as e:
            logger.error(f"プロジェクト読み込みエラー: {e}")
            return False
    
    def analyze_project(self) -> bool:
        """
        プロジェクトを分析してファイル情報を更新
        
        Returns:
            bool: 分析成功フラグ
        """
        if not self.current_project:
            logger.error("プロジェクトが読み込まれていません")
            return False
        
        try:
            project_path = Path(self.current_project.path)
            
            if not project_path.exists():
                logger.error(f"プロジェクトパスが存在しません: {project_path}")
                return False
            
            logger.info("プロジェクト分析を開始します...")
            
            # ファイル情報を収集
            files = []
            
            def analyze_file(file_path: Path) -> Optional[FileInfo]:
                """個別ファイルを分析"""
                try:
                    if not file_path.is_file():
                        return None
                    
                    # 除外ファイルチェック
                    if file_path.name in self.EXCLUDE_FILES:
                        return None
                    
                    # ファイル情報を取得
                    stat = file_path.stat()
                    extension = file_path.suffix.lower()
                    language = self.SUPPORTED_EXTENSIONS.get(extension, "")
                    
                    # バイナリファイル判定
                    is_binary = self._is_binary_file(file_path)
                    
                    # ファイルハッシュ計算
                    file_hash = self._calculate_file_hash(file_path)
                    
                    # コンテンツプレビューと行数
                    content_preview = ""
                    line_count = 0
                    encoding = "utf-8"
                    
                    if not is_binary and stat.st_size < 1024 * 1024:  # 1MB未満
                        try:
                            encoding = self.file_utils.detect_encoding(str(file_path))
                            content = self.file_utils.read_file(str(file_path), encoding)
                            if content:
                                lines = content.split('\n')
                                line_count = len(lines)
                                # 最初の5行をプレビューとして保存
                                content_preview = '\n'.join(lines[:5])
                        except Exception:
                            is_binary = True
                    
                    return FileInfo(
                        path=str(file_path.relative_to(project_path)),
                        name=file_path.name,
                        extension=extension,
                        size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        encoding=encoding,
                        language=language,
                        hash=file_hash,
                        content_preview=content_preview,
                        line_count=line_count,
                        is_binary=is_binary
                    )
                    
                except Exception as e:
                    logger.warning(f"ファイル分析エラー {file_path}: {e}")
                    return None
            
            # 並列でファイルを分析
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_file = {}
                
                for file_path in self._walk_project(project_path):
                    future = executor.submit(analyze_file, file_path)
                    future_to_file[future] = file_path
                
                for future in as_completed(future_to_file):
                    file_info = future.result()
                    if file_info:
                        files.append(file_info)
            
            self.current_files = files
            
            # データベースに保存
            self.database.save_files(self.current_project.path, files)
            
            # プロジェクト情報を更新
            self.current_project.modified = datetime.now().isoformat()
            
            # 主要言語を推定
            if not self.current_project.language:
                self.current_project.language = self._detect_primary_language(files)
            
            self.database.save_project(self.current_project)
            
            logger.info(f"プロジェクト分析完了: {len(files)}個のファイルを処理")
            return True
            
        except Exception as e:
            logger.error(f"プロジェクト分析エラー: {e}")
            return False
    
    def _walk_project(self, project_path: Path):
        """プロジェクト内のファイルを再帰的に取得"""
        for root, dirs, files in os.walk(project_path):
            # 除外ディレクトリをスキップ
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                yield file_path
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """バイナリファイル判定"""
        try:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and not mime_type.startswith('text/'):
                return True
            
            # 最初の1024バイトをチェック
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\x00' in chunk
                
        except Exception:
            return True
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """ファイルハッシュを計算"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _detect_primary_language(self, files: List[FileInfo]) -> str:
        """主要言語を推定"""
        language_count = {}
        
        for file_info in files:
            if file_info.language and not file_info.is_binary:
                language_count[file_info.language] = language_count.get(file_info.language, 0) + 1
        
        if language_count:
            return max(language_count, key=language_count.get)
        
        return ""
    
    def get_project_stats(self) -> Optional[ProjectStats]:
        """プロジェクト統計情報を取得"""
        if not self.current_files:
            return None
        
        stats = ProjectStats()
        stats.total_files = len(self.current_files)
        
        for file_info in self.current_files:
            stats.total_size += file_info.size
            stats.total_lines += file_info.line_count
            
            # ファイルタイプ統計
            ext = file_info.extension or "no_extension"
            stats.file_types[ext] = stats.file_types.get(ext, 0) + 1
            
            # 言語統計
            if file_info.language:
                stats.languages[file_info.language] = stats.languages.get(file_info.language, 0) + 1
        
        # 最大ファイル
        sorted_files = sorted(self.current_files, key=lambda f: f.size, reverse=True)
        stats.largest_files = [(f.path, f.size) for f in sorted_files[:10]]
        
        return stats
    
    def search_files(self, query: str, file_type: str = "", 
                    language: str = "") -> List[FileInfo]:
        """
        ファイルを検索
        
        Args:
            query: 検索クエリ
            file_type: ファイルタイプフィルター
            language: 言語フィルター
            
        Returns:
            List[FileInfo]: 検索結果
        """
        results = []
        
        for file_info in self.current_files:
            # フィルター適用
            if file_type and file_info.extension != file_type:
                continue
            
            if language and file_info.language != language:
                continue
            
            # 検索クエリマッチング
            if (query.lower() in file_info.name.lower() or
                query.lower() in file_info.path.lower() or
                query.lower() in file_info.content_preview.lower()):
                results.append(file_info)
        
        return results
    
    def get_recent_projects(self, limit: int = 10) -> List[ProjectInfo]:
        """最近のプロジェクトを取得"""
        projects = self.database.get_projects()
        return projects[:limit]
    
    def export_project_info(self, export_path: str) -> bool:
        """プロジェクト情報をエクスポート"""
        if not self.current_project:
            return False
        
        try:
            export_data = {
                'project': asdict(self.current_project),
                'files': [asdict(f) for f in self.current_files],
                'stats': asdict(self.get_project_stats()) if self.get_project_stats() else None,
                'exported_at': datetime.now().isoformat()
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"プロジェクト情報をエクスポートしました: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"プロジェクト情報エクスポートエラー: {e}")
            return False

# グローバルプロジェクトマネージャーインスタンス
project_manager = ProjectManager()

def get_project_manager() -> ProjectManager:
    """グローバルプロジェクトマネージャーを取得"""
    return project_manager

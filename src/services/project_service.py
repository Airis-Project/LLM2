# src/services/project_service.py
"""
プロジェクト管理サービス
LLM Code Assistant のプロジェクト管理機能を提供
"""

import os
import json
import yaml
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import subprocess
import tempfile
import shutil

from ..core.exceptions import (
    ProjectServiceError,
    ProjectNotFoundError,
    ProjectConfigError,
    ValidationError
)
#from ..core.config_manager import ConfigManager
from ..services.file_service import FileService, FileType, FileInfo
from src.core.logger import get_logger

def ConfigManager(*args, **kwargs):
    from src.core.config_manager import ConfigManager
    return ConfigManager(*args, **kwargs)


logger = get_logger(__name__)


class ProjectType(Enum):
    """プロジェクトタイプ"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    WEB = "web"
    DATA_SCIENCE = "data_science"
    MACHINE_LEARNING = "machine_learning"
    API = "api"
    CLI = "cli"
    LIBRARY = "library"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ProjectStatus(Enum):
    """プロジェクト状態"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    TEMPLATE = "template"
    CORRUPTED = "corrupted"


@dataclass
class ProjectMetadata:
    """プロジェクトメタデータ"""
    name: str
    path: str
    project_type: ProjectType
    status: ProjectStatus
    created_at: datetime
    modified_at: datetime
    last_opened: Optional[datetime] = None
    description: str = ""
    tags: List[str] = None
    version: str = "1.0.0"
    author: str = ""
    dependencies: List[str] = None
    file_count: int = 0
    total_size: int = 0
    main_language: str = ""
    frameworks: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []
        if self.frameworks is None:
            self.frameworks = []


@dataclass
class ProjectTemplate:
    """プロジェクトテンプレート"""
    name: str
    description: str
    project_type: ProjectType
    files: Dict[str, str]  # ファイルパス -> コンテンツ
    directories: List[str]
    dependencies: List[str]
    config: Dict[str, Any]


@dataclass
class ProjectAnalysis:
    """プロジェクト解析結果"""
    project_type: ProjectType
    main_language: str
    frameworks: List[str]
    dependencies: List[str]
    file_types: Dict[FileType, int]
    complexity_score: float
    maintainability_score: float
    test_coverage: float
    documentation_score: float
    issues: List[str]
    suggestions: List[str]


class ProjectService:
    """プロジェクト管理サービスクラス"""
    
    def __init__(self, config_manager: ConfigManager, file_service: FileService):
        """
        プロジェクトサービスの初期化
        
        Args:
            config_manager: 設定管理インスタンス
            file_service: ファイルサービスインスタンス
        """
        self.config = config_manager
        self.file_service = file_service
        self.logger = get_logger(self.__class__.__name__)
        
        # 設定値の取得
        project_config = self.config.get('project_management', {})
        self.max_recent_projects = project_config.get('recent_projects', {}).get('max_count', 10)
        self.auto_open_last = project_config.get('recent_projects', {}).get('auto_open_last', False)
        self.templates_enabled = project_config.get('templates', {}).get('enabled', True)
        self.templates_path = Path(project_config.get('templates', {}).get('path', 'data/templates/'))
        self.auto_detect_type = project_config.get('templates', {}).get('auto_detect_type', True)
        self.auto_analyze = project_config.get('analysis', {}).get('auto_analyze', True)
        self.max_analysis_depth = project_config.get('analysis', {}).get('max_depth', 5)
        
        # データディレクトリ
        self.projects_data_path = Path(self.config.get('paths', {}).get('user_data_dir', 'user_data/')) / 'projects'
        self.recent_projects_file = self.projects_data_path / 'recent_projects.json'
        
        # 初期化
        self._ensure_directories()
        self._load_recent_projects()
        self._current_project: Optional[ProjectMetadata] = None
    
    def _ensure_directories(self):
        """必要なディレクトリを作成"""
        try:
            self.projects_data_path.mkdir(parents=True, exist_ok=True)
            if self.templates_enabled:
                self.templates_path.mkdir(parents=True, exist_ok=True)
            self.logger.info("プロジェクト管理ディレクトリを初期化しました")
        except Exception as e:
            self.logger.error(f"ディレクトリ初期化エラー: {e}")
            raise ProjectServiceError(f"ディレクトリの初期化に失敗しました: {e}")
    
    def _load_recent_projects(self):
        """最近使用したプロジェクトの読み込み"""
        try:
            if self.recent_projects_file.exists():
                with open(self.recent_projects_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.recent_projects = [
                        ProjectMetadata(**project) for project in data.get('projects', [])
                    ]
            else:
                self.recent_projects = []
            
            self.logger.debug(f"最近のプロジェクト読み込み完了: {len(self.recent_projects)}件")
        except Exception as e:
            self.logger.warning(f"最近のプロジェクト読み込みエラー: {e}")
            self.recent_projects = []
    
    def _save_recent_projects(self):
        """最近使用したプロジェクトの保存"""
        try:
            data = {
                'projects': [asdict(project) for project in self.recent_projects],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.recent_projects_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.debug("最近のプロジェクト保存完了")
        except Exception as e:
            self.logger.error(f"最近のプロジェクト保存エラー: {e}")
    
    async def create_project(self, name: str, path: Union[str, Path], 
                           project_type: ProjectType = ProjectType.UNKNOWN,
                           template_name: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> ProjectMetadata:
        """新しいプロジェクトを作成"""
        try:
            project_path = Path(path) / name
            
            # プロジェクトディレクトリの存在確認
            if project_path.exists():
                raise ProjectServiceError(f"プロジェクトディレクトリが既に存在します: {project_path}")
            
            # プロジェクトディレクトリの作成
            await self.file_service.create_directory(project_path)
            
            # テンプレートの適用
            if template_name and self.templates_enabled:
                await self._apply_template(project_path, template_name)
            
            # プロジェクトメタデータの作成
            project_metadata = ProjectMetadata(
                name=name,
                path=str(project_path.absolute()),
                project_type=project_type,
                status=ProjectStatus.ACTIVE,
                created_at=datetime.now(),
                modified_at=datetime.now(),
                description=metadata.get('description', '') if metadata else '',
                author=metadata.get('author', '') if metadata else '',
                version=metadata.get('version', '1.0.0') if metadata else '1.0.0'
            )
            
            # プロジェクト設定ファイルの作成
            await self._create_project_config(project_path, project_metadata)
            
            # 自動解析
            if self.auto_analyze:
                analysis = await self.analyze_project(project_path)
                project_metadata.project_type = analysis.project_type
                project_metadata.main_language = analysis.main_language
                project_metadata.frameworks = analysis.frameworks
                project_metadata.dependencies = analysis.dependencies
            
            # 最近のプロジェクトに追加
            self._add_to_recent_projects(project_metadata)
            
            self.logger.info(f"プロジェクト作成完了: {name} at {project_path}")
            return project_metadata
            
        except Exception as e:
            self.logger.error(f"プロジェクト作成エラー: {e}")
            raise ProjectServiceError(f"プロジェクトの作成に失敗しました: {e}")
    
    async def _apply_template(self, project_path: Path, template_name: str):
        """テンプレートの適用"""
        try:
            template = await self.get_template(template_name)
            if not template:
                raise ProjectServiceError(f"テンプレートが見つかりません: {template_name}")
            
            # ディレクトリの作成
            for directory in template.directories:
                dir_path = project_path / directory
                await self.file_service.create_directory(dir_path)
            
            # ファイルの作成
            for file_path, content in template.files.items():
                full_path = project_path / file_path
                await self.file_service.write_file(full_path, content, backup=False)
            
            self.logger.info(f"テンプレート適用完了: {template_name}")
            
        except Exception as e:
            self.logger.error(f"テンプレート適用エラー: {e}")
            raise ProjectServiceError(f"テンプレートの適用に失敗しました: {e}")
    
    async def _create_project_config(self, project_path: Path, metadata: ProjectMetadata):
        """プロジェクト設定ファイルの作成"""
        try:
            config_data = {
                'project': asdict(metadata),
                'settings': {
                    'auto_save': True,
                    'auto_format': False,
                    'lint_on_save': True,
                    'git_integration': True
                },
                'build': {
                    'output_dir': 'dist',
                    'source_dir': 'src',
                    'test_dir': 'tests'
                },
                'dependencies': {
                    'runtime': [],
                    'development': [],
                    'testing': []
                }
            }
            
            config_file = project_path / '.llm-project.json'
            await self.file_service.write_file(
                config_file, 
                json.dumps(config_data, indent=2, ensure_ascii=False, default=str),
                backup=False
            )
            
            self.logger.debug(f"プロジェクト設定ファイル作成: {config_file}")
            
        except Exception as e:
            self.logger.error(f"プロジェクト設定ファイル作成エラー: {e}")
    
    async def open_project(self, project_path: Union[str, Path]) -> ProjectMetadata:
        """プロジェクトを開く"""
        try:
            path = Path(project_path)
            if not path.exists() or not path.is_dir():
                raise ProjectNotFoundError(f"プロジェクトディレクトリが見つかりません: {project_path}")
            
            # プロジェクト設定の読み込み
            project_metadata = await self._load_project_metadata(path)
            
            # 最終オープン時刻の更新
            project_metadata.last_opened = datetime.now()
            project_metadata.modified_at = datetime.now()
            
            # プロジェクト情報の更新
            await self._update_project_info(project_metadata)
            
            # 最近のプロジェクトに追加
            self._add_to_recent_projects(project_metadata)
            
            # 現在のプロジェクトとして設定
            self._current_project = project_metadata
            
            self.logger.info(f"プロジェクトオープン完了: {project_metadata.name}")
            return project_metadata
            
        except Exception as e:
            self.logger.error(f"プロジェクトオープンエラー: {e}")
            raise ProjectServiceError(f"プロジェクトのオープンに失敗しました: {e}")
    
    async def _load_project_metadata(self, project_path: Path) -> ProjectMetadata:
        """プロジェクトメタデータの読み込み"""
        try:
            config_file = project_path / '.llm-project.json'
            
            if config_file.exists():
                # 既存の設定ファイルから読み込み
                content = await self.file_service.read_file(config_file)
                config_data = json.loads(content)
                project_data = config_data.get('project', {})
                
                # datetime フィールドの変換
                for field in ['created_at', 'modified_at', 'last_opened']:
                    if field in project_data and project_data[field]:
                        if isinstance(project_data[field], str):
                            project_data[field] = datetime.fromisoformat(project_data[field])
                
                return ProjectMetadata(**project_data)
            else:
                # 新規プロジェクトとして解析
                return await self._analyze_existing_project(project_path)
                
        except Exception as e:
            self.logger.error(f"プロジェクトメタデータ読み込みエラー: {e}")
            raise ProjectConfigError(f"プロジェクト設定の読み込みに失敗しました: {e}")
    
    async def _analyze_existing_project(self, project_path: Path) -> ProjectMetadata:
        """既存プロジェクトの解析"""
        try:
            # 基本情報の取得
            stat = project_path.stat()
            
            # プロジェクト解析の実行
            analysis = await self.analyze_project(project_path)
            
            metadata = ProjectMetadata(
                name=project_path.name,
                path=str(project_path.absolute()),
                project_type=analysis.project_type,
                status=ProjectStatus.ACTIVE,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                main_language=analysis.main_language,
                frameworks=analysis.frameworks,
                dependencies=analysis.dependencies
            )
            
            # プロジェクト設定ファイルの作成
            await self._create_project_config(project_path, metadata)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"既存プロジェクト解析エラー: {e}")
            raise ProjectServiceError(f"既存プロジェクトの解析に失敗しました: {e}")
    
    async def _update_project_info(self, metadata: ProjectMetadata):
        """プロジェクト情報の更新"""
        try:
            project_path = Path(metadata.path)
            
            # ファイル数とサイズの計算
            file_count = 0
            total_size = 0
            
            for file_path in project_path.rglob('*'):
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        file_count += 1
                        total_size += stat.st_size
                    except Exception:
                        continue
            
            metadata.file_count = file_count
            metadata.total_size = total_size
            
            # プロジェクト設定ファイルの更新
            await self._create_project_config(project_path, metadata)
            
        except Exception as e:
            self.logger.warning(f"プロジェクト情報更新エラー: {e}")
    
    def _add_to_recent_projects(self, metadata: ProjectMetadata):
        """最近のプロジェクトに追加"""
        try:
            # 既存のエントリを削除
            self.recent_projects = [
                p for p in self.recent_projects 
                if p.path != metadata.path
            ]
            
            # 先頭に追加
            self.recent_projects.insert(0, metadata)
            
            # 制限数を超えた場合は削除
            if len(self.recent_projects) > self.max_recent_projects:
                self.recent_projects = self.recent_projects[:self.max_recent_projects]
            
            # 保存
            self._save_recent_projects()
            
        except Exception as e:
            self.logger.warning(f"最近のプロジェクト追加エラー: {e}")
    async def analyze_project(self, project_path: Union[str, Path]) -> ProjectAnalysis:
        """プロジェクトの詳細解析"""
        try:
            path = Path(project_path)
            if not path.exists() or not path.is_dir():
                raise ProjectNotFoundError(f"プロジェクトディレクトリが見つかりません: {project_path}")
            
            # ファイル一覧の取得
            files = self.file_service.list_directory(
                path, 
                recursive=True, 
                include_hidden=False
            )
            
            # ファイルタイプの集計
            file_types = {}
            total_files = 0
            code_files = 0
            
            for file_info in files:
                if not file_info.is_directory:
                    total_files += 1
                    file_type = file_info.file_type
                    file_types[file_type] = file_types.get(file_type, 0) + 1
                    
                    if file_type in [FileType.PYTHON, FileType.JAVASCRIPT, 
                                   FileType.TYPESCRIPT, FileType.HTML, FileType.CSS]:
                        code_files += 1
            
            # プロジェクトタイプの判定
            project_type = self._detect_project_type(path, file_types)
            
            # 主要言語の判定
            main_language = self._detect_main_language(file_types)
            
            # フレームワークの検出
            frameworks = await self._detect_frameworks(path, file_types)
            
            # 依存関係の検出
            dependencies = await self._detect_dependencies(path)
            
            # 複雑度スコアの計算
            complexity_score = self._calculate_complexity_score(files, file_types)
            
            # 保守性スコアの計算
            maintainability_score = self._calculate_maintainability_score(files, file_types)
            
            # テストカバレッジの計算
            test_coverage = await self._calculate_test_coverage(path, files)
            
            # ドキュメントスコアの計算
            documentation_score = self._calculate_documentation_score(files)
            
            # 問題と提案の生成
            issues, suggestions = self._generate_analysis_feedback(
                files, file_types, frameworks, dependencies
            )
            
            analysis = ProjectAnalysis(
                project_type=project_type,
                main_language=main_language,
                frameworks=frameworks,
                dependencies=dependencies,
                file_types=file_types,
                complexity_score=complexity_score,
                maintainability_score=maintainability_score,
                test_coverage=test_coverage,
                documentation_score=documentation_score,
                issues=issues,
                suggestions=suggestions
            )
            
            self.logger.info(f"プロジェクト解析完了: {project_path}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"プロジェクト解析エラー: {e}")
            raise ProjectServiceError(f"プロジェクトの解析に失敗しました: {e}")
    
    def _detect_project_type(self, project_path: Path, file_types: Dict[FileType, int]) -> ProjectType:
        """プロジェクトタイプの検出"""
        try:
            # 設定ファイルによる判定
            if (project_path / 'package.json').exists():
                return ProjectType.JAVASCRIPT
            elif (project_path / 'tsconfig.json').exists():
                return ProjectType.TYPESCRIPT
            elif (project_path / 'requirements.txt').exists() or (project_path / 'pyproject.toml').exists():
                return ProjectType.PYTHON
            elif (project_path / 'index.html').exists():
                return ProjectType.WEB
            
            # ファイル数による判定
            python_files = file_types.get(FileType.PYTHON, 0)
            js_files = file_types.get(FileType.JAVASCRIPT, 0)
            ts_files = file_types.get(FileType.TYPESCRIPT, 0)
            html_files = file_types.get(FileType.HTML, 0)
            
            if python_files > max(js_files, ts_files, html_files):
                # データサイエンス関連ファイルの確認
                if any((project_path / name).exists() for name in ['jupyter', 'notebooks', 'data']):
                    return ProjectType.DATA_SCIENCE
                return ProjectType.PYTHON
            elif ts_files > 0:
                return ProjectType.TYPESCRIPT
            elif js_files > 0:
                return ProjectType.JAVASCRIPT
            elif html_files > 0:
                return ProjectType.WEB
            
            return ProjectType.UNKNOWN
            
        except Exception as e:
            self.logger.warning(f"プロジェクトタイプ検出エラー: {e}")
            return ProjectType.UNKNOWN
    
    def _detect_main_language(self, file_types: Dict[FileType, int]) -> str:
        """主要言語の検出"""
        language_mapping = {
            FileType.PYTHON: "Python",
            FileType.JAVASCRIPT: "JavaScript",
            FileType.TYPESCRIPT: "TypeScript",
            FileType.HTML: "HTML",
            FileType.CSS: "CSS",
            FileType.SQL: "SQL"
        }
        
        code_types = {ft: count for ft, count in file_types.items() if ft in language_mapping}
        
        if code_types:
            main_type = max(code_types, key=code_types.get)
            return language_mapping[main_type]
        
        return "Unknown"
    
    async def _detect_frameworks(self, project_path: Path, file_types: Dict[FileType, int]) -> List[str]:
        """フレームワークの検出"""
        frameworks = []
        
        try:
            # Python フレームワーク
            if file_types.get(FileType.PYTHON, 0) > 0:
                frameworks.extend(await self._detect_python_frameworks(project_path))
            
            # JavaScript/TypeScript フレームワーク
            if file_types.get(FileType.JAVASCRIPT, 0) > 0 or file_types.get(FileType.TYPESCRIPT, 0) > 0:
                frameworks.extend(await self._detect_js_frameworks(project_path))
            
            # Web フレームワーク
            if file_types.get(FileType.HTML, 0) > 0:
                frameworks.extend(await self._detect_web_frameworks(project_path))
            
        except Exception as e:
            self.logger.warning(f"フレームワーク検出エラー: {e}")
        
        return list(set(frameworks))  # 重複除去
    
    async def _detect_python_frameworks(self, project_path: Path) -> List[str]:
        """Python フレームワークの検出"""
        frameworks = []
        
        # requirements.txt の確認
        requirements_file = project_path / 'requirements.txt'
        if requirements_file.exists():
            try:
                content = await self.file_service.read_file(requirements_file)
                requirements = content.lower()
                
                if 'django' in requirements:
                    frameworks.append('Django')
                if 'flask' in requirements:
                    frameworks.append('Flask')
                if 'fastapi' in requirements:
                    frameworks.append('FastAPI')
                if 'streamlit' in requirements:
                    frameworks.append('Streamlit')
                if 'pandas' in requirements:
                    frameworks.append('Pandas')
                if 'numpy' in requirements:
                    frameworks.append('NumPy')
                if 'tensorflow' in requirements or 'keras' in requirements:
                    frameworks.append('TensorFlow')
                if 'torch' in requirements or 'pytorch' in requirements:
                    frameworks.append('PyTorch')
                    
            except Exception as e:
                self.logger.warning(f"requirements.txt 読み取りエラー: {e}")
        
        # ディレクトリ構造による判定
        if (project_path / 'manage.py').exists():
            frameworks.append('Django')
        if (project_path / 'app.py').exists() or (project_path / 'wsgi.py').exists():
            frameworks.append('Flask')
        
        return frameworks
    
    async def _detect_js_frameworks(self, project_path: Path) -> List[str]:
        """JavaScript/TypeScript フレームワークの検出"""
        frameworks = []
        
        # package.json の確認
        package_json = project_path / 'package.json'
        if package_json.exists():
            try:
                content = await self.file_service.read_file(package_json)
                package_data = json.loads(content)
                
                dependencies = {
                    **package_data.get('dependencies', {}),
                    **package_data.get('devDependencies', {})
                }
                
                if 'react' in dependencies:
                    frameworks.append('React')
                if 'vue' in dependencies:
                    frameworks.append('Vue.js')
                if 'angular' in dependencies or '@angular/core' in dependencies:
                    frameworks.append('Angular')
                if 'express' in dependencies:
                    frameworks.append('Express.js')
                if 'next' in dependencies:
                    frameworks.append('Next.js')
                if 'nuxt' in dependencies:
                    frameworks.append('Nuxt.js')
                if 'svelte' in dependencies:
                    frameworks.append('Svelte')
                    
            except Exception as e:
                self.logger.warning(f"package.json 読み取りエラー: {e}")
        
        return frameworks
    
    async def _detect_web_frameworks(self, project_path: Path) -> List[str]:
        """Web フレームワークの検出"""
        frameworks = []
        
        # CSSフレームワークの検出
        css_files = list(project_path.rglob('*.css'))
        for css_file in css_files:
            try:
                content = await self.file_service.read_file(css_file)
                content_lower = content.lower()
                
                if 'bootstrap' in content_lower:
                    frameworks.append('Bootstrap')
                if 'tailwind' in content_lower:
                    frameworks.append('Tailwind CSS')
                if 'bulma' in content_lower:
                    frameworks.append('Bulma')
                    
            except Exception:
                continue
        
        return frameworks
    
    async def _detect_dependencies(self, project_path: Path) -> List[str]:
        """依存関係の検出"""
        dependencies = []
        
        try:
            # Python dependencies
            requirements_file = project_path / 'requirements.txt'
            if requirements_file.exists():
                content = await self.file_service.read_file(requirements_file)
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        dep = line.split('==')[0].split('>=')[0].split('<=')[0]
                        dependencies.append(dep)
            
            # JavaScript dependencies
            package_json = project_path / 'package.json'
            if package_json.exists():
                content = await self.file_service.read_file(package_json)
                package_data = json.loads(content)
                
                deps = package_data.get('dependencies', {})
                dev_deps = package_data.get('devDependencies', {})
                
                dependencies.extend(list(deps.keys()))
                dependencies.extend(list(dev_deps.keys()))
                
        except Exception as e:
            self.logger.warning(f"依存関係検出エラー: {e}")
        
        return list(set(dependencies))  # 重複除去
    
    def _calculate_complexity_score(self, files: List[FileInfo], file_types: Dict[FileType, int]) -> float:
        """複雑度スコアの計算"""
        try:
            total_files = sum(1 for f in files if not f.is_directory)
            if total_files == 0:
                return 0.0
            
            # ファイル数による基本スコア
            base_score = min(total_files / 100, 1.0)  # 100ファイルで1.0
            
            # ファイルタイプの多様性
            type_diversity = len(file_types) / 10  # 10種類で1.0
            
            # コードファイルの割合
            code_files = sum(count for ft, count in file_types.items() 
                           if ft in [FileType.PYTHON, FileType.JAVASCRIPT, FileType.TYPESCRIPT])
            code_ratio = code_files / total_files if total_files > 0 else 0
            
            # 最終スコア（0-1の範囲）
            complexity_score = (base_score * 0.5 + type_diversity * 0.3 + code_ratio * 0.2)
            return min(complexity_score, 1.0)
            
        except Exception as e:
            self.logger.warning(f"複雑度スコア計算エラー: {e}")
            return 0.0
    
    def _calculate_maintainability_score(self, files: List[FileInfo], file_types: Dict[FileType, int]) -> float:
        """保守性スコアの計算"""
        try:
            score = 1.0  # 基本スコア
            
            # ファイルサイズの評価
            large_files = sum(1 for f in files if not f.is_directory and f.size > 50000)  # 50KB以上
            total_files = sum(1 for f in files if not f.is_directory)
            
            if total_files > 0:
                large_file_ratio = large_files / total_files
                score -= large_file_ratio * 0.3  # 大きなファイルが多いと減点
            
            # 設定ファイルの存在
            config_bonus = 0
            config_files = ['.gitignore', 'README.md', 'requirements.txt', 'package.json']
            for config_file in config_files:
                if any(f.name == config_file for f in files):
                    config_bonus += 0.05
            
            score += config_bonus
            
            return max(min(score, 1.0), 0.0)
            
        except Exception as e:
            self.logger.warning(f"保守性スコア計算エラー: {e}")
            return 0.5
    
    async def _calculate_test_coverage(self, project_path: Path, files: List[FileInfo]) -> float:
        """テストカバレッジの計算"""
        try:
            # テストファイルの検出
            test_files = []
            code_files = []
            
            for file_info in files:
                if file_info.is_directory:
                    continue
                
                file_name = file_info.name.lower()
                
                # テストファイルの判定
                if ('test' in file_name or 'spec' in file_name) and file_info.file_type in [
                    FileType.PYTHON, FileType.JAVASCRIPT, FileType.TYPESCRIPT
                ]:
                    test_files.append(file_info)
                elif file_info.file_type in [FileType.PYTHON, FileType.JAVASCRIPT, FileType.TYPESCRIPT]:
                    code_files.append(file_info)
            
            if not code_files:
                return 0.0
            
            # 簡易的なカバレッジ計算（テストファイル数 / コードファイル数）
            coverage = min(len(test_files) / len(code_files), 1.0)
            
            return coverage
            
        except Exception as e:
            self.logger.warning(f"テストカバレッジ計算エラー: {e}")
            return 0.0
    
    def _calculate_documentation_score(self, files: List[FileInfo]) -> float:
        """ドキュメントスコアの計算"""
        try:
            doc_files = 0
            total_files = 0
            
            for file_info in files:
                if file_info.is_directory:
                    continue
                
                total_files += 1
                file_name = file_info.name.lower()
                
                # ドキュメントファイルの判定
                if (file_info.file_type == FileType.MARKDOWN or 
                    file_name in ['readme.md', 'readme.txt', 'changelog.md', 'license']):
                    doc_files += 1
            
            if total_files == 0:
                return 0.0
            
            # ドキュメントファイルの割合
            doc_ratio = doc_files / total_files
            
            # README.mdの存在ボーナス
            readme_bonus = 0.3 if any(f.name.lower() == 'readme.md' for f in files) else 0
            
            score = min(doc_ratio * 2 + readme_bonus, 1.0)  # 最大1.0
            
            return score
            
        except Exception as e:
            self.logger.warning(f"ドキュメントスコア計算エラー: {e}")
            return 0.0
    
    def _generate_analysis_feedback(self, files: List[FileInfo], file_types: Dict[FileType, int], 
                                  frameworks: List[str], dependencies: List[str]) -> Tuple[List[str], List[str]]:
        """解析結果に基づく問題と提案の生成"""
        issues = []
        suggestions = []
        
        try:
            total_files = sum(1 for f in files if not f.is_directory)
            
            # 問題の検出
            if total_files == 0:
                issues.append("プロジェクトにファイルが含まれていません")
            
            # 大きなファイルの警告
            large_files = [f for f in files if not f.is_directory and f.size > 100000]  # 100KB以上
            if large_files:
                issues.append(f"{len(large_files)}個の大きなファイルが見つかりました")
            
            # README.mdの不存在
            if not any(f.name.lower() == 'readme.md' for f in files):
                issues.append("README.mdファイルが見つかりません")
            
            # .gitignoreの不存在
            if not any(f.name == '.gitignore' for f in files):
                issues.append(".gitignoreファイルが見つかりません")
            
            # 提案の生成
            if not frameworks:
                suggestions.append("フレームワークの使用を検討してください")
            
            if file_types.get(FileType.PYTHON, 0) > 0 and 'requirements.txt' not in [f.name for f in files]:
                suggestions.append("requirements.txtファイルの作成を推奨します")
            
            if file_types.get(FileType.JAVASCRIPT, 0) > 0 and 'package.json' not in [f.name for f in files]:
                suggestions.append("package.jsonファイルの作成を推奨します")
            
            # テストファイルの不足
            test_files = [f for f in files if 'test' in f.name.lower() or 'spec' in f.name.lower()]
            if not test_files:
                suggestions.append("テストファイルの追加を推奨します")
            
            if total_files > 50:
                suggestions.append("プロジェクトが大きくなっています。モジュール化を検討してください")
                
        except Exception as e:
            self.logger.warning(f"フィードバック生成エラー: {e}")
        
        return issues, suggestions
    async def get_template(self, template_name: str) -> Optional[ProjectTemplate]:
        """テンプレートの取得"""
        try:
            if not self.templates_enabled:
                return None
            
            template_path = self.templates_path / f"{template_name}.json"
            if not template_path.exists():
                return None
            
            content = await self.file_service.read_file(template_path)
            template_data = json.loads(content)
            
            return ProjectTemplate(
                name=template_data['name'],
                description=template_data['description'],
                project_type=ProjectType(template_data['project_type']),
                files=template_data['files'],
                directories=template_data['directories'],
                dependencies=template_data['dependencies'],
                config=template_data.get('config', {})
            )
            
        except Exception as e:
            self.logger.error(f"テンプレート取得エラー: {e}")
            return None
    
    async def list_templates(self) -> List[ProjectTemplate]:
        """利用可能なテンプレート一覧の取得"""
        templates = []
        
        try:
            if not self.templates_enabled or not self.templates_path.exists():
                return templates
            
            for template_file in self.templates_path.glob("*.json"):
                template = await self.get_template(template_file.stem)
                if template:
                    templates.append(template)
            
            self.logger.debug(f"テンプレート一覧取得完了: {len(templates)}件")
            return templates
            
        except Exception as e:
            self.logger.error(f"テンプレート一覧取得エラー: {e}")
            return templates
    
    async def create_template(self, name: str, description: str, 
                            project_path: Union[str, Path],
                            project_type: ProjectType = ProjectType.UNKNOWN) -> bool:
        """既存プロジェクトからテンプレートを作成"""
        try:
            if not self.templates_enabled:
                raise ProjectServiceError("テンプレート機能が無効です")
            
            path = Path(project_path)
            if not path.exists() or not path.is_dir():
                raise ProjectNotFoundError(f"プロジェクトディレクトリが見つかりません: {project_path}")
            
            # プロジェクト解析
            analysis = await self.analyze_project(path)
            
            # テンプレートデータの構築
            template_data = {
                'name': name,
                'description': description,
                'project_type': project_type.value if project_type != ProjectType.UNKNOWN else analysis.project_type.value,
                'files': {},
                'directories': [],
                'dependencies': analysis.dependencies,
                'config': {
                    'frameworks': analysis.frameworks,
                    'main_language': analysis.main_language
                }
            }
            
            # ファイル構造の取得
            files = self.file_service.list_directory(path, recursive=True, include_hidden=False)
            
            for file_info in files:
                relative_path = Path(file_info.path).relative_to(path)
                
                if file_info.is_directory:
                    template_data['directories'].append(str(relative_path))
                else:
                    # 小さなテキストファイルのみテンプレートに含める
                    if (file_info.size < 10000 and  # 10KB未満
                        file_info.file_type in [FileType.TEXT, FileType.PYTHON, 
                                              FileType.JAVASCRIPT, FileType.HTML, 
                                              FileType.CSS, FileType.MARKDOWN]):
                        try:
                            content = await self.file_service.read_file(file_info.path)
                            template_data['files'][str(relative_path)] = content
                        except Exception:
                            # 読み取りエラーの場合は空ファイルとして追加
                            template_data['files'][str(relative_path)] = ""
            
            # テンプレートファイルの保存
            template_file = self.templates_path / f"{name}.json"
            await self.file_service.write_file(
                template_file,
                json.dumps(template_data, indent=2, ensure_ascii=False),
                backup=False
            )
            
            self.logger.info(f"テンプレート作成完了: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"テンプレート作成エラー: {e}")
            raise ProjectServiceError(f"テンプレートの作成に失敗しました: {e}")
    
    async def delete_template(self, template_name: str) -> bool:
        """テンプレートの削除"""
        try:
            if not self.templates_enabled:
                raise ProjectServiceError("テンプレート機能が無効です")
            
            template_file = self.templates_path / f"{template_name}.json"
            if not template_file.exists():
                raise ProjectNotFoundError(f"テンプレートが見つかりません: {template_name}")
            
            await self.file_service.delete_file(template_file, backup=True)
            
            self.logger.info(f"テンプレート削除完了: {template_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"テンプレート削除エラー: {e}")
            raise ProjectServiceError(f"テンプレートの削除に失敗しました: {e}")
    
    def search_projects(self, query: str = "", 
                       project_type: Optional[ProjectType] = None,
                       status: Optional[ProjectStatus] = None,
                       tags: Optional[List[str]] = None,
                       date_range: Optional[Tuple[datetime, datetime]] = None) -> List[ProjectMetadata]:
        """プロジェクトの検索"""
        try:
            results = []
            
            for project in self.recent_projects:
                # クエリによるフィルタリング
                if query:
                    query_lower = query.lower()
                    if not (query_lower in project.name.lower() or 
                           query_lower in project.description.lower()):
                        continue
                
                # プロジェクトタイプフィルタ
                if project_type and project.project_type != project_type:
                    continue
                
                # ステータスフィルタ
                if status and project.status != status:
                    continue
                
                # タグフィルタ
                if tags:
                    if not any(tag in project.tags for tag in tags):
                        continue
                
                # 日付範囲フィルタ
                if date_range:
                    start_date, end_date = date_range
                    if not (start_date <= project.modified_at <= end_date):
                        continue
                
                results.append(project)
            
            self.logger.debug(f"プロジェクト検索完了: {len(results)}件")
            return results
            
        except Exception as e:
            self.logger.error(f"プロジェクト検索エラー: {e}")
            return []
    
    def get_recent_projects(self, limit: Optional[int] = None) -> List[ProjectMetadata]:
        """最近のプロジェクト一覧の取得"""
        try:
            if limit:
                return self.recent_projects[:limit]
            return self.recent_projects.copy()
            
        except Exception as e:
            self.logger.error(f"最近のプロジェクト取得エラー: {e}")
            return []
    
    def get_current_project(self) -> Optional[ProjectMetadata]:
        """現在開いているプロジェクトの取得"""
        return self._current_project
    
    async def close_project(self) -> bool:
        """現在のプロジェクトを閉じる"""
        try:
            if self._current_project:
                # プロジェクト情報の更新
                await self._update_project_info(self._current_project)
                
                self.logger.info(f"プロジェクトクローズ: {self._current_project.name}")
                self._current_project = None
                
            return True
            
        except Exception as e:
            self.logger.error(f"プロジェクトクローズエラー: {e}")
            return False
    
    async def archive_project(self, project_path: Union[str, Path]) -> bool:
        """プロジェクトのアーカイブ"""
        try:
            path = Path(project_path)
            metadata = await self._load_project_metadata(path)
            
            # ステータスをアーカイブに変更
            metadata.status = ProjectStatus.ARCHIVED
            metadata.modified_at = datetime.now()
            
            # プロジェクト設定の更新
            await self._create_project_config(path, metadata)
            
            # 最近のプロジェクトからも更新
            for i, project in enumerate(self.recent_projects):
                if project.path == str(path.absolute()):
                    self.recent_projects[i] = metadata
                    break
            
            self._save_recent_projects()
            
            self.logger.info(f"プロジェクトアーカイブ完了: {metadata.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"プロジェクトアーカイブエラー: {e}")
            raise ProjectServiceError(f"プロジェクトのアーカイブに失敗しました: {e}")
    
    async def restore_project(self, project_path: Union[str, Path]) -> bool:
        """アーカイブプロジェクトの復元"""
        try:
            path = Path(project_path)
            metadata = await self._load_project_metadata(path)
            
            # ステータスをアクティブに変更
            metadata.status = ProjectStatus.ACTIVE
            metadata.modified_at = datetime.now()
            
            # プロジェクト設定の更新
            await self._create_project_config(path, metadata)
            
            # 最近のプロジェクトからも更新
            for i, project in enumerate(self.recent_projects):
                if project.path == str(path.absolute()):
                    self.recent_projects[i] = metadata
                    break
            
            self._save_recent_projects()
            
            self.logger.info(f"プロジェクト復元完了: {metadata.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"プロジェクト復元エラー: {e}")
            raise ProjectServiceError(f"プロジェクトの復元に失敗しました: {e}")
    
    async def export_project(self, project_path: Union[str, Path], 
                           export_path: Union[str, Path],
                           include_dependencies: bool = True,
                           include_cache: bool = False) -> Path:
        """プロジェクトのエクスポート"""
        try:
            path = Path(project_path)
            export_dir = Path(export_path)
            
            if not path.exists():
                raise ProjectNotFoundError(f"プロジェクトが見つかりません: {project_path}")
            
            # エクスポート対象ファイルの収集
            files_to_export = []
            
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(path)
                    
                    # 除外パターンのチェック
                    if self._should_exclude_from_export(relative_path, include_dependencies, include_cache):
                        continue
                    
                    files_to_export.append(file_path)
            
            # エクスポートの実行
            export_file = await self.file_service.export_files(
                files_to_export,
                export_dir,
                format_type="zip"
            )
            
            self.logger.info(f"プロジェクトエクスポート完了: {export_file}")
            return export_file
            
        except Exception as e:
            self.logger.error(f"プロジェクトエクスポートエラー: {e}")
            raise ProjectServiceError(f"プロジェクトのエクスポートに失敗しました: {e}")
    
    def _should_exclude_from_export(self, file_path: Path, 
                                  include_dependencies: bool, 
                                  include_cache: bool) -> bool:
        """エクスポート時の除外判定"""
        path_str = str(file_path).lower()
        
        # 常に除外するパターン
        always_exclude = ['.git', '.svn', '.hg', '__pycache__', '.pytest_cache']
        for pattern in always_exclude:
            if pattern in path_str:
                return True
        
        # 依存関係ディレクトリの除外
        if not include_dependencies:
            dependency_dirs = ['node_modules', 'venv', 'env', '.venv', 'site-packages']
            for pattern in dependency_dirs:
                if pattern in path_str:
                    return True
        
        # キャッシュファイルの除外
        if not include_cache:
            cache_patterns = ['.cache', 'cache', 'tmp', 'temp', '.tmp']
            for pattern in cache_patterns:
                if pattern in path_str:
                    return True
        
        return False
    
    async def import_project(self, archive_path: Union[str, Path], 
                           destination_path: Union[str, Path]) -> ProjectMetadata:
        """プロジェクトのインポート"""
        try:
            archive_file = Path(archive_path)
            dest_path = Path(destination_path)
            
            if not archive_file.exists():
                raise FileNotFoundError(f"アーカイブファイルが見つかりません: {archive_path}")
            
            # 一時ディレクトリでの展開
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # アーカイブの展開
                if archive_file.suffix.lower() == '.zip':
                    import zipfile
                    with zipfile.ZipFile(archive_file, 'r') as zipf:
                        zipf.extractall(temp_path)
                else:
                    raise ProjectServiceError(f"サポートされていないアーカイブ形式: {archive_file.suffix}")
                
                # 展開されたプロジェクトの検索
                project_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
                if not project_dirs:
                    raise ProjectServiceError("有効なプロジェクトディレクトリが見つかりません")
                
                source_project = project_dirs[0]  # 最初のディレクトリを使用
                
                # 目的地にコピー
                final_dest = dest_path / source_project.name
                await self.file_service.copy_file(source_project, final_dest)
                
                # プロジェクトを開く
                metadata = await self.open_project(final_dest)
                
                self.logger.info(f"プロジェクトインポート完了: {metadata.name}")
                return metadata
                
        except Exception as e:
            self.logger.error(f"プロジェクトインポートエラー: {e}")
            raise ProjectServiceError(f"プロジェクトのインポートに失敗しました: {e}")
    
    def get_project_statistics(self) -> Dict[str, Any]:
        """プロジェクト統計の取得"""
        try:
            stats = {
                'total_projects': len(self.recent_projects),
                'active_projects': 0,
                'archived_projects': 0,
                'project_types': {},
                'languages': {},
                'total_files': 0,
                'total_size': 0,
                'last_activity': None
            }
            
            for project in self.recent_projects:
                # ステータス統計
                if project.status == ProjectStatus.ACTIVE:
                    stats['active_projects'] += 1
                elif project.status == ProjectStatus.ARCHIVED:
                    stats['archived_projects'] += 1
                
                # プロジェクトタイプ統計
                project_type = project.project_type.value
                stats['project_types'][project_type] = stats['project_types'].get(project_type, 0) + 1
                
                # 言語統計
                if project.main_language:
                    stats['languages'][project.main_language] = stats['languages'].get(project.main_language, 0) + 1
                
                # ファイル・サイズ統計
                stats['total_files'] += project.file_count
                stats['total_size'] += project.total_size
                
                # 最終活動日時
                if project.last_opened:
                    if not stats['last_activity'] or project.last_opened > stats['last_activity']:
                        stats['last_activity'] = project.last_opened
            
            return stats
            
        except Exception as e:
            self.logger.error(f"プロジェクト統計取得エラー: {e}")
            return {}
    
    async def cleanup_projects(self, max_age_days: int = 30) -> int:
        """古いプロジェクト情報のクリーンアップ"""
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            cleaned_count = 0
            
            # 存在しないプロジェクトの削除
            valid_projects = []
            for project in self.recent_projects:
                project_path = Path(project.path)
                
                if project_path.exists():
                    # アーカイブされた古いプロジェクトの確認
                    if (project.status == ProjectStatus.ARCHIVED and 
                        project.modified_at < cutoff_date):
                        cleaned_count += 1
                        continue
                    
                    valid_projects.append(project)
                else:
                    cleaned_count += 1
            
            self.recent_projects = valid_projects
            self._save_recent_projects()
            
            self.logger.info(f"プロジェクトクリーンアップ完了: {cleaned_count}件削除")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"プロジェクトクリーンアップエラー: {e}")
            return 0
    
    async def close(self):
        """サービスのクリーンアップ"""
        try:
            # 現在のプロジェクトを閉じる
            await self.close_project()
            
            # 最近のプロジェクト情報を保存
            self._save_recent_projects()
            
            self.logger.info("ProjectService クリーンアップ完了")
            
        except Exception as e:
            self.logger.error(f"ProjectService クリーンアップエラー: {e}")


# プロジェクトサービスのファクトリ関数
def create_project_service(config_manager: ConfigManager, file_service: FileService) -> ProjectService:
    """プロジェクトサービスのインスタンスを作成"""
    return ProjectService(config_manager, file_service)

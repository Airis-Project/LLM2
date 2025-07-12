# src/core/template_engine.py
"""
テンプレートエンジンモジュール
コード生成用のテンプレート管理と処理を行う
Jinja2ベースのテンプレートシステムを提供
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import re
from jinja2 import Environment, FileSystemLoader, Template, TemplateError
from jinja2.exceptions import TemplateNotFound, TemplateSyntaxError

from .logger import get_logger
#from .config_manager import AppConfig, get_config
from ..utils.file_utils import FileUtils
from ..utils.text_utils import TextUtils
from ..utils.validation_utils import ValidationUtils

def get_config(*args, **kwargs):
    from .config_manager import get_config
    return get_config(*args, **kwargs)

def AppConfig(*args, **kwargs):
    from .config_manager import AppConfig
    return AppConfig(*args, **kwargs)

logger = get_logger(__name__)

@dataclass
class TemplateInfo:
    """テンプレート情報のデータクラス"""
    name: str
    path: str
    description: str = ""
    language: str = ""
    category: str = ""
    author: str = ""
    version: str = "1.0.0"
    created: str = ""
    modified: str = ""
    tags: List[str] = None
    variables: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.variables is None:
            self.variables = []

@dataclass
class TemplateContext:
    """テンプレートコンテキストのデータクラス"""
    variables: Dict[str, Any] = None
    functions: Dict[str, Any] = None
    filters: Dict[str, Any] = None
    globals: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = {}
        if self.functions is None:
            self.functions = {}
        if self.filters is None:
            self.filters = {}
        if self.globals is None:
            self.globals = {}

class TemplateManager:
    """テンプレート管理クラス"""
    
    def __init__(self, template_dirs: Optional[List[str]] = None):
        """
        初期化
        
        Args:
            template_dirs: テンプレートディレクトリリスト
        """
        config = get_config()
        
        # デフォルトテンプレートディレクトリ
        default_dirs = [
            "./data/templates",
            "./templates",
            str(Path(__file__).parent.parent.parent / "data" / "templates")
        ]
        
        self.template_dirs = template_dirs or default_dirs
        
        # 存在するディレクトリのみを使用
        self.template_dirs = [d for d in self.template_dirs if Path(d).exists()]
        
        # テンプレートディレクトリを作成
        for template_dir in self.template_dirs:
            Path(template_dir).mkdir(parents=True, exist_ok=True)
        
        # Jinja2環境を初期化
        self.env = Environment(
            loader=FileSystemLoader(self.template_dirs),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # ユーティリティクラス
        self.file_utils = FileUtils()
        self.text_utils = TextUtils()
        self.validation_utils = ValidationUtils()
        
        # テンプレート情報キャッシュ
        self.template_cache: Dict[str, TemplateInfo] = {}
        
        # カスタムフィルターとファンクションを登録
        self._register_custom_filters()
        self._register_custom_functions()
        
        # テンプレート情報を読み込み
        self._load_template_info()
    
    def _register_custom_filters(self):
        """カスタムフィルターを登録"""
        
        def snake_case(text: str) -> str:
            """スネークケースに変換"""
            return self.text_utils.to_snake_case(text)
        
        def camel_case(text: str) -> str:
            """キャメルケースに変換"""
            return self.text_utils.to_camel_case(text)
        
        def pascal_case(text: str) -> str:
            """パスカルケースに変換"""
            return self.text_utils.to_pascal_case(text)
        
        def kebab_case(text: str) -> str:
            """ケバブケースに変換"""
            return self.text_utils.to_kebab_case(text)
        
        def pluralize(text: str) -> str:
            """複数形に変換"""
            return self.text_utils.pluralize(text)
        
        def singularize(text: str) -> str:
            """単数形に変換"""
            return self.text_utils.singularize(text)
        
        def indent_code(text: str, spaces: int = 4) -> str:
            """コードをインデント"""
            lines = text.split('\n')
            indented_lines = [' ' * spaces + line if line.strip() else line for line in lines]
            return '\n'.join(indented_lines)
        
        def comment_block(text: str, style: str = "//") -> str:
            """コメントブロックを作成"""
            lines = text.split('\n')
            if style == "//":
                commented_lines = [f"// {line}" if line.strip() else "//" for line in lines]
            elif style == "#":
                commented_lines = [f"# {line}" if line.strip() else "#" for line in lines]
            elif style == "/*":
                commented_lines = ["/*"] + [f" * {line}" if line.strip() else " *" for line in lines] + [" */"]
            else:
                commented_lines = lines
            return '\n'.join(commented_lines)
        
        # フィルターを登録
        self.env.filters['snake_case'] = snake_case
        self.env.filters['camel_case'] = camel_case
        self.env.filters['pascal_case'] = pascal_case
        self.env.filters['kebab_case'] = kebab_case
        self.env.filters['pluralize'] = pluralize
        self.env.filters['singularize'] = singularize
        self.env.filters['indent'] = indent_code
        self.env.filters['comment'] = comment_block
    
    def _register_custom_functions(self):
        """カスタムファンクションを登録"""
        
        def now(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
            """現在時刻を取得"""
            return datetime.now().strftime(format_str)
        
        def uuid4() -> str:
            """UUID4を生成"""
            import uuid
            return str(uuid.uuid4())
        
        def range_list(start: int, end: int, step: int = 1) -> List[int]:
            """範囲リストを生成"""
            return list(range(start, end, step))
        
        def file_exists(path: str) -> bool:
            """ファイル存在チェック"""
            return Path(path).exists()
        
        def read_file(path: str, encoding: str = "utf-8") -> str:
            """ファイルを読み込み"""
            try:
                return self.file_utils.read_file(path, encoding) or ""
            except Exception:
                return ""
        
        def json_load(json_str: str) -> Any:
            """JSON文字列をパース"""
            try:
                return json.loads(json_str)
            except Exception:
                return {}
        
        def json_dump(obj: Any, indent: int = 2) -> str:
            """オブジェクトをJSON文字列に変換"""
            try:
                return json.dumps(obj, indent=indent, ensure_ascii=False)
            except Exception:
                return "{}"
        
        # グローバル関数として登録
        self.env.globals['now'] = now
        self.env.globals['uuid4'] = uuid4
        self.env.globals['range_list'] = range_list
        self.env.globals['file_exists'] = file_exists
        self.env.globals['read_file'] = read_file
        self.env.globals['json_load'] = json_load
        self.env.globals['json_dump'] = json_dump
    
    def _load_template_info(self, template_path: Path) -> Optional[Dict[str, Any]]:
        """テンプレート情報の読み込み"""
        try:
            # パスの正規化
            template_path = template_path.resolve()
            templates_dir = Path(self.config.templates_dir).resolve()
            
            # 相対パスの計算（セキュリティチェック）
            try:
                relative_path = template_path.relative_to(templates_dir)
            except ValueError:
                # templates_dir の外部にある場合は警告してスキップ
                logger.warning(f"テンプレートファイルが指定ディレクトリ外にあります: {template_path}")
                return None
            
            # テンプレート情報の作成
            template_info = {
                'name': template_path.stem.replace('.template', ''),
                'path': str(template_path),
                'relative_path': str(relative_path),
                'category': self._get_template_category(template_path),
                'description': self._extract_description(template_path),
                'variables': self._extract_variables(template_path),
                'size': template_path.stat().st_size,
                'modified': template_path.stat().st_mtime
            }
            
            return template_info
            
        except Exception as e:
            logger.error(f"テンプレート情報読み込みエラー {template_path}: {e}")
            return None
    
    def _load_single_template_info(self, template_file: Path):
        """単一テンプレート情報を読み込み"""
        try:
            # テンプレート名を生成
            template_name = str(template_file.relative_to(Path(self.template_dirs[0])))
            
            # メタデータファイルをチェック
            meta_file = template_file.with_suffix('.meta.json')
            
            template_info = TemplateInfo(
                name=template_name,
                path=str(template_file),
                created=datetime.fromtimestamp(template_file.stat().st_ctime).isoformat(),
                modified=datetime.fromtimestamp(template_file.stat().st_mtime).isoformat()
            )
            
            # メタデータファイルが存在する場合は読み込み
            if meta_file.exists():
                try:
                    meta_data = json.loads(meta_file.read_text(encoding='utf-8'))
                    
                    template_info.description = meta_data.get('description', '')
                    template_info.language = meta_data.get('language', '')
                    template_info.category = meta_data.get('category', '')
                    template_info.author = meta_data.get('author', '')
                    template_info.version = meta_data.get('version', '1.0.0')
                    template_info.tags = meta_data.get('tags', [])
                    template_info.variables = meta_data.get('variables', [])
                    
                except Exception as e:
                    logger.warning(f"メタデータ読み込みエラー {meta_file}: {e}")
            
            # テンプレート内容から変数を抽出
            if not template_info.variables:
                template_info.variables = self._extract_template_variables(template_file)
            
            # 言語を推定
            if not template_info.language:
                template_info.language = self._detect_template_language(template_file)
            
            self.template_cache[template_name] = template_info
            
        except Exception as e:
            logger.error(f"テンプレート情報読み込みエラー {template_file}: {e}")
    
    def _extract_template_variables(self, template_file: Path) -> List[str]:
        """テンプレートから変数を抽出"""
        variables = set()
        
        try:
            content = template_file.read_text(encoding='utf-8')
            
            # Jinja2変数パターンを検索
            variable_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
            matches = re.findall(variable_pattern, content)
            variables.update(matches)
            
            # forループ変数を除外
            for_pattern = r'\{%\s*for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in'
            for_matches = re.findall(for_pattern, content)
            variables.difference_update(for_matches)
            
        except Exception as e:
            logger.warning(f"変数抽出エラー {template_file}: {e}")
        
        return list(variables)
    
    def _detect_template_language(self, template_file: Path) -> str:
        """テンプレートの言語を推定"""
        # ファイル名から推定
        name_lower = template_file.name.lower()
        
        if 'python' in name_lower or '.py' in name_lower:
            return 'python'
        elif 'javascript' in name_lower or '.js' in name_lower:
            return 'javascript'
        elif 'html' in name_lower or '.html' in name_lower:
            return 'html'
        elif 'css' in name_lower or '.css' in name_lower:
            return 'css'
        elif 'java' in name_lower and 'javascript' not in name_lower:
            return 'java'
        elif 'cpp' in name_lower or '.cpp' in name_lower:
            return 'cpp'
        elif 'csharp' in name_lower or '.cs' in name_lower:
            return 'csharp'
        
        return 'text'
    
    def get_templates(self, category: str = "", language: str = "") -> List[TemplateInfo]:
        """
        テンプレート一覧を取得
        
        Args:
            category: カテゴリフィルター
            language: 言語フィルター
            
        Returns:
            List[TemplateInfo]: テンプレート情報リスト
        """
        templates = list(self.template_cache.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if language:
            templates = [t for t in templates if t.language == language]
        
        return sorted(templates, key=lambda t: t.name)
    
    def get_template_info(self, template_name: str) -> Optional[TemplateInfo]:
        """
        テンプレート情報を取得
        
        Args:
            template_name: テンプレート名
            
        Returns:
            Optional[TemplateInfo]: テンプレート情報
        """
        return self.template_cache.get(template_name)
    
    def render_template(self, template_name: str, context: Dict[str, Any] = None,
                       template_context: Optional[TemplateContext] = None) -> Optional[str]:
        """
        テンプレートをレンダリング
        
        Args:
            template_name: テンプレート名
            context: コンテキスト変数
            template_context: テンプレートコンテキスト
            
        Returns:
            Optional[str]: レンダリング結果
        """
        try:
            # テンプレートを取得
            template = self.env.get_template(template_name)
            
            # コンテキストを準備
            render_context = context or {}
            
            # テンプレートコンテキストを適用
            if template_context:
                render_context.update(template_context.variables)
                
                # カスタムフィルターを追加
                for name, filter_func in template_context.filters.items():
                    self.env.filters[name] = filter_func
                
                # カスタムファンクションを追加
                for name, func in template_context.functions.items():
                    self.env.globals[name] = func
                
                # グローバル変数を追加
                render_context.update(template_context.globals)
            
            # レンダリング実行
            result = template.render(**render_context)
            
            logger.debug(f"テンプレートをレンダリングしました: {template_name}")
            return result
            
        except TemplateNotFound as e:
            logger.error(f"テンプレートが見つかりません: {template_name}")
            return None
        except TemplateSyntaxError as e:
            logger.error(f"テンプレート構文エラー: {e}")
            return None
        except Exception as e:
            logger.error(f"テンプレートレンダリングエラー: {e}")
            return None
    
    def render_string(self, template_string: str, context: Dict[str, Any] = None) -> Optional[str]:
        """
        テンプレート文字列をレンダリング
        
        Args:
            template_string: テンプレート文字列
            context: コンテキスト変数
            
        Returns:
            Optional[str]: レンダリング結果
        """
        try:
            template = self.env.from_string(template_string)
            result = template.render(**(context or {}))
            
            logger.debug("テンプレート文字列をレンダリングしました")
            return result
            
        except Exception as e:
            logger.error(f"テンプレート文字列レンダリングエラー: {e}")
            return None
    
    def create_template(self, name: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        新しいテンプレートを作成
        
        Args:
            name: テンプレート名
            content: テンプレート内容
            metadata: メタデータ
            
        Returns:
            bool: 作成成功フラグ
        """
        try:
            if not self.template_dirs:
                logger.error("テンプレートディレクトリが設定されていません")
                return False
            
            # テンプレートファイルパス
            template_path = Path(self.template_dirs[0]) / name
            template_path.parent.mkdir(parents=True, exist_ok=True)
            
            # テンプレート内容を保存
            template_path.write_text(content, encoding='utf-8')
            
            # メタデータを保存
            if metadata:
                meta_path = template_path.with_suffix('.meta.json')
                meta_path.write_text(
                    json.dumps(metadata, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )
            
            # テンプレート情報を更新
            self._load_single_template_info(template_path)
            
            logger.info(f"テンプレートを作成しました: {name}")
            return True
            
        except Exception as e:
            logger.error(f"テンプレート作成エラー: {e}")
            return False
    
    def update_template(self, name: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        テンプレートを更新
        
        Args:
            name: テンプレート名
            content: テンプレート内容
            metadata: メタデータ
            
        Returns:
            bool: 更新成功フラグ
        """
        try:
            template_info = self.template_cache.get(name)
            if not template_info:
                logger.error(f"テンプレートが見つかりません: {name}")
                return False
            
            template_path = Path(template_info.path)
            
            # テンプレート内容を更新
            template_path.write_text(content, encoding='utf-8')
            
            # メタデータを更新
            if metadata:
                meta_path = template_path.with_suffix('.meta.json')
                meta_path.write_text(
                    json.dumps(metadata, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )
            
            # テンプレート情報を更新
            self._load_single_template_info(template_path)
            
            logger.info(f"テンプレートを更新しました: {name}")
            return True
            
        except Exception as e:
            logger.error(f"テンプレート更新エラー: {e}")
            return False
    
    def delete_template(self, name: str) -> bool:
        """
        テンプレートを削除
        
        Args:
            name: テンプレート名
            
        Returns:
            bool: 削除成功フラグ
        """
        try:
            template_info = self.template_cache.get(name)
            if not template_info:
                logger.error(f"テンプレートが見つかりません: {name}")
                return False
            
            template_path = Path(template_info.path)
            meta_path = template_path.with_suffix('.meta.json')
            
            # ファイルを削除
            if template_path.exists():
                template_path.unlink()
            
            if meta_path.exists():
                meta_path.unlink()
            
            # キャッシュから削除
            del self.template_cache[name]
            
            logger.info(f"テンプレートを削除しました: {name}")
            return True
            
        except Exception as e:
            logger.error(f"テンプレート削除エラー: {e}")
            return False
    
    def validate_template(self, template_content: str) -> Dict[str, Any]:
        """
        テンプレートを検証
        
        Args:
            template_content: テンプレート内容
            
        Returns:
            Dict[str, Any]: 検証結果
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'variables': []
        }
        
        try:
            # 構文チェック
            template = self.env.from_string(template_content)
            
            # 変数を抽出
            variables = set()
            variable_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
            matches = re.findall(variable_pattern, template_content)
            variables.update(matches)
            
            result['valid'] = True
            result['variables'] = list(variables)
            
        except TemplateSyntaxError as e:
            result['errors'].append(f"構文エラー: {e}")
        except Exception as e:
            result['errors'].append(f"検証エラー: {e}")
        
        return result
    
    def export_templates(self, export_path: str, templates: List[str] = None) -> bool:
        """
        テンプレートをエクスポート
        
        Args:
            export_path: エクスポート先パス
            templates: エクスポートするテンプレート名リスト（Noneの場合は全て）
            
        Returns:
            bool: エクスポート成功フラグ
        """
        try:
            export_dir = Path(export_path)
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # エクスポート対象を決定
            if templates is None:
                templates = list(self.template_cache.keys())
            
            exported_count = 0
            
            for template_name in templates:
                template_info = self.template_cache.get(template_name)
                if not template_info:
                    continue
                
                # テンプレートファイルをコピー
                src_path = Path(template_info.path)
                dst_path = export_dir / template_name
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                if src_path.exists():
                    dst_path.write_text(src_path.read_text(encoding='utf-8'), encoding='utf-8')
                    exported_count += 1
                
                # メタデータファイルをコピー
                meta_src = src_path.with_suffix('.meta.json')
                if meta_src.exists():
                    meta_dst = dst_path.with_suffix('.meta.json')
                    meta_dst.write_text(meta_src.read_text(encoding='utf-8'), encoding='utf-8')
            
            logger.info(f"{exported_count}個のテンプレートをエクスポートしました: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"テンプレートエクスポートエラー: {e}")
            return False
    
    def import_templates(self, import_path: str) -> bool:
        """
        テンプレートをインポート
        
        Args:
            import_path: インポート元パス
            
        Returns:
            bool: インポート成功フラグ
        """
        try:
            import_dir = Path(import_path)
            if not import_dir.exists():
                logger.error(f"インポートパスが存在しません: {import_path}")
                return False
            
            if not self.template_dirs:
                logger.error("テンプレートディレクトリが設定されていません")
                return False
            
            target_dir = Path(self.template_dirs[0])
            imported_count = 0
            
            # テンプレートファイルを検索してコピー
            for template_file in import_dir.rglob("*.template"):
                rel_path = template_file.relative_to(import_dir)
                dst_path = target_dir / rel_path
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                dst_path.write_text(template_file.read_text(encoding='utf-8'), encoding='utf-8')
                imported_count += 1
                
                # メタデータファイルもコピー
                meta_src = template_file.with_suffix('.meta.json')
                if meta_src.exists():
                    meta_dst = dst_path.with_suffix('.meta.json')
                    meta_dst.write_text(meta_src.read_text(encoding='utf-8'), encoding='utf-8')
            
            # テンプレート情報を再読み込み
            self._load_template_info()
            
            logger.info(f"{imported_count}個のテンプレートをインポートしました: {import_path}")
            return True
            
        except Exception as e:
            logger.error(f"テンプレートインポートエラー: {e}")
            return False

class TemplateEngine:
    """テンプレートエンジンクラス"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        """
        イベントシステムの初期化
        
        Args:
            config: アプリケーション設定
        """
        from src.core.config_manager import get_config
        
        self.config = config or get_config()
        
        # 設定の取得（get メソッドを使用）
        event_config = self.config.get('event_system', {})
        
        self.enabled = event_config.get('enabled', True)
        self.max_listeners = event_config.get('max_listeners', 100)
        self.async_enabled = event_config.get('async_enabled', True)
        self.debug = event_config.get('debug', False)

    def render(self, template_name: str, **kwargs) -> Optional[str]:
        """
        テンプレートをレンダリング
        
        Args:
            template_name: テンプレート名
            **kwargs: テンプレート変数
            
        Returns:
            Optional[str]: レンダリング結果
        """
        return self.template_manager.render_template(template_name, kwargs)
    
    def render_string(self, template_string: str, **kwargs) -> Optional[str]:
        """
        テンプレート文字列をレンダリング
        
        Args:
            template_string: テンプレート文字列
            **kwargs: テンプレート変数
            
        Returns:
            Optional[str]: レンダリング結果
        """
        return self.template_manager.render_string(template_string, kwargs)
    
    def get_templates(self, **filters) -> List[TemplateInfo]:
        """テンプレート一覧を取得"""
        return self.template_manager.get_templates(**filters)
    
    def create_template(self, name: str, content: str, **metadata) -> bool:
        """テンプレートを作成"""
        return self.template_manager.create_template(name, content, metadata)

# グローバルテンプレートエンジンインスタンス
template_engine = TemplateEngine()

def get_template_engine() -> TemplateEngine:
    """グローバルテンプレートエンジンを取得"""
    return template_engine

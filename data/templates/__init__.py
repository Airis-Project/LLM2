# data/templates/__init__.py
# LLM Code Assistant - テンプレートパッケージ初期化

"""
LLM Code Assistant - テンプレートパッケージ

このパッケージには、コード生成用のテンプレートファイルが含まれています。
様々なプログラミング言語とフレームワークに対応したテンプレートを提供します。

テンプレート種類:
- Python: クラス、関数、モジュールテンプレート
- JavaScript: コンポーネント、関数テンプレート
- HTML: ページ、コンポーネントテンプレート
- CSS: スタイルシート、コンポーネントテンプレート

機能:
- テンプレートの動的読み込み
- 変数置換機能
- テンプレートの検証
- カスタムテンプレートの追加

作成者: LLM Code Assistant Team
バージョン: 1.0.0
作成日: 2024-01-01
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from string import Template
import json
from datetime import datetime

# ロガーの設定
logger = logging.getLogger(__name__)

# テンプレートディレクトリのパス
TEMPLATES_DIR = Path(__file__).parent
DATA_DIR = TEMPLATES_DIR.parent
PROJECT_ROOT = DATA_DIR.parent

# テンプレートファイルの定義
TEMPLATE_FILES = {
    'python_class': 'python_class.py.template',
    'python_function': 'python_function.py.template',
    'javascript_component': 'javascript_component.js.template',
    'html_page': 'html_page.html.template'
}

# サポートされるプログラミング言語
SUPPORTED_LANGUAGES = {
    'python': {
        'extensions': ['.py'],
        'comment_style': '#',
        'templates': ['python_class', 'python_function']
    },
    'javascript': {
        'extensions': ['.js', '.jsx', '.ts', '.tsx'],
        'comment_style': '//',
        'templates': ['javascript_component']
    },
    'html': {
        'extensions': ['.html', '.htm'],
        'comment_style': '<!-- -->',
        'templates': ['html_page']
    },
    'css': {
        'extensions': ['.css', '.scss', '.sass'],
        'comment_style': '/* */',
        'templates': []
    }
}

# デフォルトテンプレート変数
DEFAULT_TEMPLATE_VARS = {
    'author': 'LLM Code Assistant',
    'date': datetime.now().strftime('%Y-%m-%d'),
    'year': datetime.now().strftime('%Y'),
    'project_name': 'LLM Code Assistant Project',
    'version': '1.0.0'
}

class TemplateManager:
    """
    テンプレート管理クラス
    
    テンプレートファイルの読み込み、変数置換、生成を行います。
    """
    
    def __init__(self):
        """初期化"""
        self.template_cache = {}
        self.custom_templates = {}
        self.template_vars = DEFAULT_TEMPLATE_VARS.copy()
        self._load_templates()
    
    def _load_templates(self) -> None:
        """テンプレートファイルを読み込み"""
        try:
            for template_name, filename in TEMPLATE_FILES.items():
                template_path = TEMPLATES_DIR / filename
                
                if template_path.exists():
                    with open(template_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self.template_cache[template_name] = {
                        'content': content,
                        'path': template_path,
                        'variables': self._extract_variables(content)
                    }
                    logger.debug(f"テンプレートを読み込み: {template_name}")
                else:
                    logger.warning(f"テンプレートファイルが見つかりません: {template_path}")
            
            logger.info(f"{len(self.template_cache)}個のテンプレートを読み込みました")
            
        except Exception as e:
            logger.error(f"テンプレート読み込みエラー: {e}")
    
    def _extract_variables(self, content: str) -> List[str]:
        """
        テンプレート内の変数を抽出
        
        Args:
            content: テンプレート内容
            
        Returns:
            変数名のリスト
        """
        # $変数名 または ${変数名} の形式を検索
        pattern = r'\$\{([^}]+)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)'
        matches = re.findall(pattern, content)
        
        variables = []
        for match in matches:
            # match[0] は ${} 形式、match[1] は $ 形式
            var_name = match[0] if match[0] else match[1]
            if var_name and var_name not in variables:
                variables.append(var_name)
        
        return variables
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        テンプレート情報を取得
        
        Args:
            template_name: テンプレート名
            
        Returns:
            テンプレート情報（見つからない場合はNone）
        """
        if template_name in self.template_cache:
            return self.template_cache[template_name].copy()
        elif template_name in self.custom_templates:
            return self.custom_templates[template_name].copy()
        else:
            logger.warning(f"テンプレートが見つかりません: {template_name}")
            return None
    
    def get_template_list(self) -> List[str]:
        """
        利用可能なテンプレートの一覧を取得
        
        Returns:
            テンプレート名のリスト
        """
        templates = list(self.template_cache.keys()) + list(self.custom_templates.keys())
        return sorted(templates)
    
    def generate_code(self, template_name: str, variables: Dict[str, Any] = None) -> Optional[str]:
        """
        テンプレートからコードを生成
        
        Args:
            template_name: テンプレート名
            variables: 置換する変数の辞書
            
        Returns:
            生成されたコード（失敗時はNone）
        """
        template_info = self.get_template(template_name)
        if not template_info:
            return None
        
        try:
            # 変数の準備
            template_vars = self.template_vars.copy()
            if variables:
                template_vars.update(variables)
            
            # テンプレートの処理
            template = Template(template_info['content'])
            generated_code = template.safe_substitute(template_vars)
            
            logger.debug(f"コードを生成: {template_name}")
            return generated_code
            
        except Exception as e:
            logger.error(f"コード生成エラー: {template_name} - {e}")
            return None
    
    def add_custom_template(self, name: str, content: str, 
                          description: str = "") -> bool:
        """
        カスタムテンプレートを追加
        
        Args:
            name: テンプレート名
            content: テンプレート内容
            description: 説明
            
        Returns:
            追加成功フラグ
        """
        try:
            self.custom_templates[name] = {
                'content': content,
                'description': description,
                'variables': self._extract_variables(content),
                'created_at': datetime.now().isoformat()
            }
            
            logger.info(f"カスタムテンプレートを追加: {name}")
            return True
            
        except Exception as e:
            logger.error(f"カスタムテンプレート追加エラー: {name} - {e}")
            return False
    
    def remove_custom_template(self, name: str) -> bool:
        """
        カスタムテンプレートを削除
        
        Args:
            name: テンプレート名
            
        Returns:
            削除成功フラグ
        """
        if name in self.custom_templates:
            del self.custom_templates[name]
            logger.info(f"カスタムテンプレートを削除: {name}")
            return True
        else:
            logger.warning(f"カスタムテンプレートが見つかりません: {name}")
            return False
    
    def set_template_variable(self, name: str, value: Any) -> None:
        """
        テンプレート変数を設定
        
        Args:
            name: 変数名
            value: 値
        """
        self.template_vars[name] = str(value)
        logger.debug(f"テンプレート変数を設定: {name} = {value}")
    
    def get_template_variables(self) -> Dict[str, str]:
        """
        現在のテンプレート変数を取得
        
        Returns:
            テンプレート変数の辞書
        """
        return self.template_vars.copy()
    
    def validate_template(self, content: str) -> Tuple[bool, List[str]]:
        """
        テンプレート内容の妥当性を検証
        
        Args:
            content: テンプレート内容
            
        Returns:
            (妥当性フラグ, エラーメッセージのリスト)
        """
        errors = []
        
        try:
            # Template クラスでの構文チェック
            template = Template(content)
            
            # 変数の抽出テスト
            variables = self._extract_variables(content)
            
            # 基本的な置換テスト
            test_vars = {var: f"test_{var}" for var in variables}
            test_result = template.safe_substitute(test_vars)
            
            logger.debug(f"テンプレート検証成功: {len(variables)}個の変数を検出")
            
        except Exception as e:
            errors.append(f"テンプレート構文エラー: {e}")
        
        return len(errors) == 0, errors
    
    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        テンプレートの詳細情報を取得
        
        Args:
            template_name: テンプレート名
            
        Returns:
            テンプレート詳細情報
        """
        template_info = self.get_template(template_name)
        if not template_info:
            return None
        
        # 言語情報の取得
        language = self._detect_language(template_name)
        
        return {
            'name': template_name,
            'variables': template_info.get('variables', []),
            'language': language,
            'path': str(template_info.get('path', '')),
            'description': template_info.get('description', ''),
            'is_custom': template_name in self.custom_templates,
            'created_at': template_info.get('created_at', '')
        }
    
    def _detect_language(self, template_name: str) -> str:
        """
        テンプレート名から言語を推定
        
        Args:
            template_name: テンプレート名
            
        Returns:
            言語名
        """
        for language, info in SUPPORTED_LANGUAGES.items():
            if template_name.startswith(language):
                return language
        
        return 'unknown'
    
    def export_custom_templates(self, file_path: Union[str, Path]) -> bool:
        """
        カスタムテンプレートをファイルにエクスポート
        
        Args:
            file_path: エクスポート先ファイルパス
            
        Returns:
            エクスポート成功フラグ
        """
        try:
            export_data = {
                'templates': self.custom_templates,
                'exported_at': datetime.now().isoformat(),
                'version': '1.0.0'
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"カスタムテンプレートをエクスポート: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"エクスポートエラー: {e}")
            return False
    
    def import_custom_templates(self, file_path: Union[str, Path]) -> bool:
        """
        カスタムテンプレートをファイルからインポート
        
        Args:
            file_path: インポート元ファイルパス
            
        Returns:
            インポート成功フラグ
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if 'templates' in import_data:
                imported_count = 0
                for name, template_info in import_data['templates'].items():
                    self.custom_templates[name] = template_info
                    imported_count += 1
                
                logger.info(f"{imported_count}個のカスタムテンプレートをインポート")
                return True
            else:
                logger.error("無効なインポートファイル形式")
                return False
                
        except Exception as e:
            logger.error(f"インポートエラー: {e}")
            return False

# テンプレートマネージャーのシングルトンインスタンス
_template_manager = None

def get_template_manager() -> TemplateManager:
    """
    テンプレートマネージャーのシングルトンインスタンスを取得
    
    Returns:
        TemplateManager インスタンス
    """
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager

def get_available_templates() -> List[str]:
    """
    利用可能なテンプレートの一覧を取得
    
    Returns:
        テンプレート名のリスト
    """
    manager = get_template_manager()
    return manager.get_template_list()

def generate_code_from_template(template_name: str, variables: Dict[str, Any] = None) -> Optional[str]:
    """
    テンプレートからコードを生成
    
    Args:
        template_name: テンプレート名
        variables: 置換する変数の辞書
        
    Returns:
        生成されたコード
    """
    manager = get_template_manager()
    return manager.generate_code(template_name, variables)

def get_template_package_info() -> Dict[str, Any]:
    """
    テンプレートパッケージ情報を取得
    
    Returns:
        パッケージ情報
    """
    manager = get_template_manager()
    
    return {
        'templates_dir': str(TEMPLATES_DIR),
        'template_files': TEMPLATE_FILES,
        'supported_languages': SUPPORTED_LANGUAGES,
        'default_variables': DEFAULT_TEMPLATE_VARS,
        'available_templates': manager.get_template_list(),
        'custom_templates_count': len(manager.custom_templates)
    }

# パッケージレベルでエクスポートする要素
__all__ = [
    'TemplateManager',
    'get_template_manager',
    'get_available_templates',
    'generate_code_from_template',
    'get_template_package_info',
    'TEMPLATES_DIR',
    'TEMPLATE_FILES',
    'SUPPORTED_LANGUAGES',
    'DEFAULT_TEMPLATE_VARS'
]

# パッケージ初期化時の処理
try:
    # テンプレートマネージャーの初期化
    manager = get_template_manager()
    logger.info("テンプレートパッケージが初期化されました")
    
except Exception as e:
    logger.error(f"テンプレートパッケージ初期化エラー: {e}")

# デバッグ情報の出力
if __name__ == "__main__":
    print("LLM Code Assistant - テンプレートパッケージ")
    print(f"テンプレートディレクトリ: {TEMPLATES_DIR}")
    
    print("\nテンプレートファイル:")
    for name, filename in TEMPLATE_FILES.items():
        print(f"  - {name}: {filename}")
    
    print("\nサポートされる言語:")
    for lang, info in SUPPORTED_LANGUAGES.items():
        print(f"  - {lang}: {info['extensions']}")
    
    print("\nパッケージ情報:")
    info = get_template_package_info()
    print(f"  利用可能テンプレート数: {len(info['available_templates'])}")
    print(f"  カスタムテンプレート数: {info['custom_templates_count']}")

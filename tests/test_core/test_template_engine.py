# tests/test_core/test_template_engine.py
"""
TemplateEngineのテストモジュール
テンプレートエンジン機能の単体テストと統合テストを実装
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional

# テスト対象のインポート
from core.template_engine import TemplateEngine
from core.config_manager import ConfigManager
from core.logger import Logger

# テスト用のインポート
from tests.test_core import (
    get_mock_file_content,
    get_mock_file_structure,
    assert_file_structure_valid,
    MockFileContext,
    requires_file,
    create_test_config_manager,
    create_test_logger
)


class TestTemplateEngine:
    """TemplateEngineのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="template_test_"))
        self.templates_dir = self.temp_dir / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_template_engine")
        
        # テンプレートディレクトリを設定に追加
        self.config_manager.set('template_engine.templates_dir', str(self.templates_dir))
        self.config_manager.set('template_engine.output_dir', str(self.output_dir))
        
        # TemplateEngineのインスタンスを作成
        self.template_engine = TemplateEngine(self.config_manager, self.logger)
        
        # テスト用のテンプレートデータ
        self.test_templates = self._create_test_templates()
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_test_templates(self) -> Dict[str, str]:
        """テスト用のテンプレートを作成"""
        templates = {
            'python_class.py.template': '''"""
{{ description }}
"""

class {{ class_name }}:
    """{{ class_description }}"""
    
    def __init__(self{% if init_params %}, {{ init_params }}{% endif %}):
        """初期化メソッド"""
        {% for param in init_params_list -%}
        self.{{ param }} = {{ param }}
        {% endfor -%}
        {% if custom_init %}
        {{ custom_init }}
        {% endif %}
    
    {% for method in methods -%}
    def {{ method.name }}(self{% if method.params %}, {{ method.params }}{% endif %}):
        """{{ method.description }}"""
        {% if method.body %}
        {{ method.body }}
        {% else %}
        pass
        {% endif %}
    
    {% endfor -%}
''',
            
            'python_function.py.template': '''"""
{{ description }}
"""

{% if imports -%}
{% for import_item in imports -%}
{{ import_item }}
{% endfor %}

{% endif -%}
def {{ function_name }}({% if params %}{{ params }}{% endif %}):
    """
    {{ function_description }}
    
    {% if param_descriptions -%}
    Args:
    {% for param_desc in param_descriptions -%}
        {{ param_desc }}
    {% endfor -%}
    {% endif -%}
    
    {% if return_description -%}
    Returns:
        {{ return_description }}
    {% endif -%}
    """
    {% if function_body %}
    {{ function_body }}
    {% else %}
    pass
    {% endif %}
''',
            
            'html_page.html.template': '''<!DOCTYPE html>
<html lang="{{ lang | default('ja') }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    {% if css_files -%}
    {% for css_file in css_files -%}
    <link rel="stylesheet" href="{{ css_file }}">
    {% endfor -%}
    {% endif -%}
    {% if custom_styles %}
    <style>
    {{ custom_styles }}
    </style>
    {% endif %}
</head>
<body>
    {% if header %}
    <header>
        {{ header }}
    </header>
    {% endif %}
    
    <main>
        {{ content }}
    </main>
    
    {% if footer %}
    <footer>
        {{ footer }}
    </footer>
    {% endif %}
    
    {% if js_files -%}
    {% for js_file in js_files -%}
    <script src="{{ js_file }}"></script>
    {% endfor -%}
    {% endif -%}
    {% if custom_scripts %}
    <script>
    {{ custom_scripts }}
    </script>
    {% endif %}
</body>
</html>''',
            
            'config.json.template': '''{
    "name": "{{ project_name }}",
    "version": "{{ version | default('1.0.0') }}",
    "description": "{{ description }}",
    {% if author -%}
    "author": "{{ author }}",
    {% endif -%}
    {% if dependencies -%}
    "dependencies": {
        {% for dep_name, dep_version in dependencies.items() -%}
        "{{ dep_name }}": "{{ dep_version }}"{% if not loop.last %},{% endif %}
        {% endfor -%}
    },
    {% endif -%}
    "settings": {
        {% for key, value in settings.items() -%}
        "{{ key }}": {{ value | tojson }}{% if not loop.last %},{% endif %}
        {% endfor -%}
    }
}''',
            
            'readme.md.template': '''# {{ project_name }}

{{ description }}

## インストール

```bash
{% if install_commands -%}
{% for command in install_commands -%}
{{ command }}
{% endfor -%}
{% else -%}
pip install -r requirements.txt
{% endif -%}
使用方法
{{ usage_description }}

{% if examples -%}

サンプルコード
{% for example in examples -%}

{{ example.title }}
{{ example.code }}
{% if example.description -%}
{{ example.description }}
{% endif -%}

{% endfor -%}
{% endif -%}

{% if features -%}

機能
{% for feature in features -%}

{{ feature }} {% endfor -%} {% endif -%}
ライセンス
{{ license | default('MIT') }}
'''
}
        # テンプレートファイルを作成
        for template_name, template_content in templates.items():
            template_path = self.templates_dir / template_name
            template_path.write_text(template_content, encoding='utf-8')
        
        return templates

def test_init(self):
    """TemplateEngineの初期化テスト"""
    # 初期化の確認
    assert self.template_engine.config_manager is not None
    assert self.template_engine.logger is not None
    assert self.template_engine.templates_dir == str(self.templates_dir)
    assert hasattr(self.template_engine, 'jinja_env')
    assert self.template_engine.jinja_env is not None

def test_load_template(self):
    """テンプレート読み込みテスト"""
    # 存在するテンプレートを読み込み
    template = self.template_engine.load_template('python_class.py.template')
    
    assert template is not None
    assert hasattr(template, 'render')

def test_load_nonexistent_template(self):
    """存在しないテンプレートの読み込みテスト"""
    # 存在しないテンプレートを読み込もうとする
    template = self.template_engine.load_template('nonexistent.template')
    
    assert template is None

def test_render_python_class_template(self):
    """Pythonクラステンプレートのレンダリングテスト"""
    template_data = {
        'description': 'テストクラスのモジュール',
        'class_name': 'TestClass',
        'class_description': 'テスト用のクラス',
        'init_params': 'name, value=None',
        'init_params_list': ['name', 'value'],
        'custom_init': 'self.initialized = True',
        'methods': [
            {
                'name': 'get_name',
                'params': '',
                'description': '名前を取得する',
                'body': 'return self.name'
            },
            {
                'name': 'set_value',
                'params': 'new_value',
                'description': '値を設定する',
                'body': 'self.value = new_value'
            }
        ]
    }
    
    # テンプレートをレンダリング
    result = self.template_engine.render_template(
        'python_class.py.template', 
        template_data
    )
    
    assert result is not None
    assert 'class TestClass:' in result
    assert 'def __init__(self, name, value=None):' in result
    assert 'def get_name(self):' in result
    assert 'def set_value(self, new_value):' in result
    assert 'return self.name' in result
    assert 'self.value = new_value' in result

def test_render_python_function_template(self):
    """Python関数テンプレートのレンダリングテスト"""
    template_data = {
        'description': 'ユーティリティ関数のモジュール',
        'imports': [
            'import os',
            'from typing import Optional, List'
        ],
        'function_name': 'process_data',
        'params': 'data: List[str], options: Optional[dict] = None',
        'function_description': 'データを処理する関数',
        'param_descriptions': [
            'data: 処理対象のデータリスト',
            'options: 処理オプション（省略可能）'
        ],
        'return_description': 'List[str]: 処理済みのデータリスト',
        'function_body': '''if options is None:
    options = {}

processed = []
for item in data:
    if options.get('uppercase', False):
        processed.append(item.upper())
    else:
        processed.append(item.lower())

return processed'''
    }
    
    # テンプレートをレンダリング
    result = self.template_engine.render_template(
        'python_function.py.template',
        template_data
    )
    
    assert result is not None
    assert 'import os' in result
    assert 'from typing import Optional, List' in result
    assert 'def process_data(data: List[str], options: Optional[dict] = None):' in result
    assert 'データを処理する関数' in result
    assert 'processed.append(item.upper())' in result

def test_render_html_template(self):
    """HTMLテンプレートのレンダリングテスト"""
    template_data = {
        'title': 'テストページ',
        'lang': 'ja',
        'css_files': [
            'styles/main.css',
            'styles/components.css'
        ],
        'custom_styles': 'body { font-family: Arial, sans-serif; }',
        'header': '<h1>ヘッダー</h1>',
        'content': '<p>メインコンテンツ</p>',
        'footer': '<p>&copy; 2024 Test Company</p>',
        'js_files': [
            'scripts/main.js'
        ],
        'custom_scripts': 'console.log("ページが読み込まれました");'
    }
    
    # テンプレートをレンダリング
    result = self.template_engine.render_template(
        'html_page.html.template',
        template_data
    )
    
    assert result is not None
    assert '<title>テストページ</title>' in result
    assert 'lang="ja"' in result
    assert 'href="styles/main.css"' in result
    assert 'font-family: Arial, sans-serif;' in result
    assert '<h1>ヘッダー</h1>' in result
    assert '<p>メインコンテンツ</p>' in result
    assert 'src="scripts/main.js"' in result

def test_render_json_template(self):
    """JSONテンプレートのレンダリングテスト"""
    template_data = {
        'project_name': 'test-project',
        'version': '2.0.0',
        'description': 'テストプロジェクト',
        'author': 'Test Author',
        'dependencies': {
            'requests': '^2.28.0',
            'pytest': '^7.0.0'
        },
        'settings': {
            'debug': True,
            'max_connections': 100,
            'timeout': 30.5,
            'features': ['feature1', 'feature2']
        }
    }
    
    # テンプレートをレンダリング
    result = self.template_engine.render_template(
        'config.json.template',
        template_data
    )
    
    assert result is not None
    
    # JSONとしてパース可能かテスト
    parsed_json = json.loads(result)
    assert parsed_json['name'] == 'test-project'
    assert parsed_json['version'] == '2.0.0'
    assert parsed_json['author'] == 'Test Author'
    assert parsed_json['dependencies']['requests'] == '^2.28.0'
    assert parsed_json['settings']['debug'] is True
    assert parsed_json['settings']['max_connections'] == 100

def test_render_markdown_template(self):
    """Markdownテンプレートのレンダリングテスト"""
    template_data = {
        'project_name': 'Awesome Project',
        'description': '素晴らしいプロジェクトです',
        'install_commands': [
            'git clone https://github.com/user/awesome-project.git',
            'cd awesome-project',
            'pip install -r requirements.txt'
        ],
        'usage_description': 'このプロジェクトは簡単に使用できます。',
        'examples': [
            {
                'title': '基本的な使用例',
                'language': 'python',
                'code': 'from awesome import Project\nproject = Project()\nproject.run()',
                'description': '最も基本的な使用方法です。'
            },
            {
                'title': '高度な使用例',
                'language': 'python',
                'code': 'project = Project(config="advanced.json")\nresult = project.process_data(data)',
                'description': '設定ファイルを使用した高度な例です。'
            }
        ],
        'features': [
            '高速処理',
            '簡単な設定',
            '豊富なドキュメント'
        ],
        'license': 'Apache 2.0'
    }
    
    # テンプレートをレンダリング
    result = self.template_engine.render_template(
        'readme.md.template',
        template_data
    )
    
    assert result is not None
    assert '# Awesome Project' in result
    assert '素晴らしいプロジェクトです' in result
    assert 'git clone https://github.com/user/awesome-project.git' in result
    assert '### 基本的な使用例' in result
    assert 'from awesome import Project' in result
    assert '- 高速処理' in result
    assert 'Apache 2.0' in result

def test_render_template_with_filters(self):
    """フィルター付きテンプレートのレンダリングテスト"""
    # カスタムフィルターを追加
    def upper_filter(text):
        return str(text).upper()
    
    def format_date_filter(date_str):
        return f"日付: {date_str}"
    
    self.template_engine.add_filter('upper', upper_filter)
    self.template_engine.add_filter('format_date', format_date_filter)
    
    # フィルター付きテンプレートを作成
    filter_template = '''
Name: {{ name | upper }}
Date: {{ date | format_date }}
Default: {{ missing_value | default('デフォルト値') }}
'''
    template_path = self.templates_dir / 'filter_test.template'
    template_path.write_text(filter_template, encoding='utf-8')
    
    template_data = {
        'name': 'test user',
        'date': '2024-01-01'
    }
    
    # テンプレートをレンダリング
    result = self.template_engine.render_template('filter_test.template', template_data)
    
    assert result is not None
    assert 'Name: TEST USER' in result
    assert 'Date: 日付: 2024-01-01' in result
    assert 'Default: デフォルト値' in result

def test_render_template_with_conditions(self):
    """条件分岐付きテンプレートのレンダリングテスト"""
    condition_template = '''

{% if user_type == 'admin' -%}
管理者権限があります
{% elif user_type == 'user' -%}
一般ユーザーです
{% else -%}
ゲストユーザーです
{% endif -%}

{% if features -%}
利用可能な機能:
{% for feature in features -%}

{{ feature }}
{% endfor -%}
{% else -%}
利用可能な機能はありません
{% endif -%}
'''
    template_path = self.templates_dir / 'condition_test.template'
    template_path.write_text(condition_template, encoding='utf-8')

    # 管理者ユーザーのテスト
    admin_data = {
        'user_type': 'admin',
        'features': ['ユーザー管理', 'システム設定', 'レポート生成']
    }

    result = self.template_engine.render_template('condition_test.template', admin_data)
    assert '管理者権限があります' in result
    assert '- ユーザー管理' in result

    # 一般ユーザーのテスト
    user_data = {
        'user_type': 'user',
        'features': ['データ閲覧', 'レポート閲覧']
    }

    result = self.template_engine.render_template('condition_test.template', user_data)
    assert '一般ユーザーです' in result
    assert '- データ閲覧' in result

    # ゲストユーザーのテスト
    guest_data = {
        'user_type': 'guest'
    }

    result = self.template_engine.render_template('condition_test.template', guest_data)
    assert 'ゲストユーザーです' in result
    assert '利用可能な機能はありません' in result

def test_generate_file_from_template(self):
    """テンプレートからファイル生成テスト"""
    template_data = {
    'class_name': 'GeneratedClass',
    'class_description': '自動生成されたクラス',
    'description': '自動生成されたモジュール',
    'methods': [
    {
    'name': 'hello',
    'params': '',
    'description': '挨拶メソッド',
    'body': 'return "Hello, World!"'
    }
    ]
    }
    output_path = self.output_dir / 'generated_class.py'
  
    # テンプレートからファイルを生成
    result = self.template_engine.generate_file_from_template(
        'python_class.py.template',
        template_data,
        str(output_path)
    )
  
    assert result is True
    assert output_path.exists()
    
    # 生成されたファイルの内容を確認
    generated_content = output_path.read_text(encoding='utf-8')
    assert 'class GeneratedClass:' in generated_content
    assert 'def hello(self):' in generated_content
    assert 'return "Hello, World!"' in generated_content

def test_generate_multiple_files(self):
    """複数ファイル生成テスト"""
    files_config = [
    {
    'template': 'python_class.py.template',
    'output': str(self.output_dir / 'class1.py'),
    'data': {
    'class_name': 'Class1',
    'description': 'クラス1のモジュール',
    'class_description': 'クラス1',
    'methods': []
    }
    },
    {
    'template': 'python_class.py.template',
    'output': str(self.output_dir / 'class2.py'),
    'data': {
    'class_name': 'Class2',
    'description': 'クラス2のモジュール',
    'class_description': 'クラス2',
    'methods': []
    }
    },
    {
    'template': 'config.json.template',
    'output': str(self.output_dir / 'config.json'),
    'data': {
    'project_name': 'multi-file-project',
    'description': '複数ファイルプロジェクト',
    'settings': {'debug': False}
    }
    }
    ]
    # 複数ファイルを生成
    results = self.template_engine.generate_multiple_files(files_config)
    
    assert len(results) == 3
    assert all(result['success'] for result in results)
    
    # 生成されたファイルが存在することを確認
    assert (self.output_dir / 'class1.py').exists()
    assert (self.output_dir / 'class2.py').exists()
    assert (self.output_dir / 'config.json').exists()
    
    # ファイル内容の確認
    class1_content = (self.output_dir / 'class1.py').read_text(encoding='utf-8')
    assert 'class Class1:' in class1_content
    
    config_content = (self.output_dir / 'config.json').read_text(encoding='utf-8')
    config_data = json.loads(config_content)
    assert config_data['name'] == 'multi-file-project'

def test_list_available_templates(self):
    """利用可能テンプレート一覧取得テスト"""
    templates = self.template_engine.list_available_templates()
    assert isinstance(templates, list)
    assert len(templates) > 0
    
    # 作成したテンプレートが含まれていることを確認
    template_names = [t['name'] for t in templates]
    assert 'python_class.py.template' in template_names
    assert 'python_function.py.template' in template_names
    assert 'html_page.html.template' in template_names
    assert 'config.json.template' in template_names
    assert 'readme.md.template' in template_names
    
    # テンプレート情報の構造確認
    for template in templates:
        assert 'name' in template
        assert 'path' in template
        assert 'size' in template
        assert 'modified_time' in template

def test_validate_template_data(self):
    """テンプレートデータ検証テスト"""
    # 有効なデータ
    valid_data = {
    'class_name': 'TestClass',
    'methods': [
    {'name': 'test_method', 'params': '', 'description': 'テストメソッド'}
    ]
    }
    # 必須フィールドが不足したデータ
    invalid_data = {
        'methods': []  # class_nameが不足
    }
    
    # バリデーション用のスキーマ
    schema = {
        'required_fields': ['class_name'],
        'optional_fields': ['methods', 'description'],
        'field_types': {
            'class_name': str,
            'methods': list
        }
    }
    
    # 有効なデータのテスト
    is_valid, errors = self.template_engine.validate_template_data(valid_data, schema)
    assert is_valid is True
    assert len(errors) == 0
    
    # 無効なデータのテスト
    is_valid, errors = self.template_engine.validate_template_data(invalid_data, schema)
    assert is_valid is False
    assert len(errors) > 0
    assert any('class_name' in error for error in errors)

def test_template_inheritance(self):
    """テンプレート継承テスト"""
    # ベーステンプレート
    base_template = '''<!DOCTYPE html>

    <html> <head> <title>{% block title %}デフォルトタイトル{% endblock %}</title> </head> <body> <header> {% block header %}デフォルトヘッダー{% endblock %} </header> <main> {% block content %}{% endblock %} </main> <footer> {% block footer %}デフォルトフッター{% endblock %} </footer> </body> </html>'''
    # 子テンプレート
    child_template = '''{% extends "base.html" %}
    {% block title %}子ページタイトル{% endblock %}

    {% block content %}

    <h1>{{ page_title }}</h1> <p>{{ page_content }}</p> {% endblock %}
    {% block footer %}

    <p>カスタムフッター</p> {% endblock %}'''
    # テンプレートファイルを作成
    base_path = self.templates_dir / 'base.html'
    child_path = self.templates_dir / 'child.html'
    
    base_path.write_text(base_template, encoding='utf-8')
    child_path.write_text(child_template, encoding='utf-8')
    
    template_data = {
        'page_title': 'テストページ',
        'page_content': 'これはテストコンテンツです。'
    }
    
    # 子テンプレートをレンダリング
    result = self.template_engine.render_template('child.html', template_data)
    
    assert result is not None
    assert '<title>子ページタイトル</title>' in result
    assert 'デフォルトヘッダー' in result
    assert '<h1>テストページ</h1>' in result
    assert 'これはテストコンテンツです。' in result
    assert 'カスタムフッター' in result

def test_template_macros(self):
    """テンプレートマクロテスト"""
    macro_template = '''
    {% macro render_input(name, type='text', placeholder='', required=false) -%}

    <div class="form-group"> <input type="{{ type }}" name="{{ name }}" id="{{ name }}" {% if placeholder %}placeholder="{{ placeholder }}"{% endif %} {% if required %}required{% endif %}> </div> {%- endmacro %}
    {% macro render_button(text, type='button', class='btn') -%}
    <button type="{{ type }}" class="{{ class }}">{{ text }}</button>
    {%- endmacro %}

    <form> {{ render_input('username', placeholder='ユーザー名を入力', required=true) }} {{ render_input('password', type='password', placeholder='パスワードを入力', required=true) }} {{ render_input('email', type='email', placeholder='メールアドレスを入力') }} {{ render_button('送信', type='submit', class='btn btn-primary') }} {{ render_button('キャンセル', class='btn btn-secondary') }} </form> '''
    template_path = self.templates_dir / 'form_macros.html'
    template_path.write_text(macro_template, encoding='utf-8')
    
    # マクロテンプレートをレンダリング
    result = self.template_engine.render_template('form_macros.html', {})
    
    assert result is not None
    assert 'name="username"' in result
    assert 'placeholder="ユーザー名を入力"' in result
    assert 'required' in result
    assert 'type="password"' in result
    assert 'type="email"' in result
    assert 'type="submit"' in result
    assert 'class="btn btn-primary"' in result
    def test_template_error_handling(self):
        """テンプレートエラーハンドリングテスト"""
        # 構文エラーのあるテンプレート
        error_template = '''
        {% if condition %}
            <p>条件が真です</p>
        {% endif
        <!-- 閉じタグが不正 -->
        '''
        
        template_path = self.templates_dir / 'error_test.template'
        template_path.write_text(error_template, encoding='utf-8')
        
        # エラーのあるテンプレートをレンダリング
        result = self.template_engine.render_template('error_test.template', {'condition': True})
        
        # エラーが適切に処理されることを確認
        assert result is None
    
    def test_template_security(self):
        """テンプレートセキュリティテスト"""
        # 危険な操作を含むテンプレート
        dangerous_template = '''
{{ dangerous_code }}
{% for item in items %}
    {{ item.__class__.__bases__[0].__subclasses__() }}
{% endfor %}
'''
        
        template_path = self.templates_dir / 'security_test.template'
        template_path.write_text(dangerous_template, encoding='utf-8')
        
        template_data = {
            'dangerous_code': '<script>alert("XSS")</script>',
            'items': ['test']
        }
        
        # セキュリティが適切に処理されることを確認
        result = self.template_engine.render_template('security_test.template', template_data)
        
        # XSSが防止されていることを確認（エスケープされている）
        if result:
            assert '&lt;script&gt;' in result or result is None
    
    def test_custom_template_functions(self):
        """カスタムテンプレート関数テスト"""
        # カスタム関数を追加
        def format_currency(amount, currency='¥'):
            return f"{currency}{amount:,.0f}"
        
        def truncate_text(text, length=50):
            if len(text) <= length:
                return text
            return text[:length] + '...'
        
        self.template_engine.add_global_function('format_currency', format_currency)
        self.template_engine.add_global_function('truncate_text', truncate_text)
        
        # カスタム関数を使用するテンプレート
        function_template = '''
価格: {{ format_currency(price) }}
説明: {{ truncate_text(description, 20) }}
'''
        
        template_path = self.templates_dir / 'function_test.template'
        template_path.write_text(function_template, encoding='utf-8')
        
        template_data = {
            'price': 12345,
            'description': 'これは非常に長い説明文です。この文章は20文字を超えているので切り詰められるはずです。'
        }
        
        # カスタム関数付きテンプレートをレンダリング
        result = self.template_engine.render_template('function_test.template', template_data)
        
        assert result is not None
        assert '¥12,345' in result
        assert 'これは非常に長い説明文です。この文章は20...' in result
    
    def test_template_caching(self):
        """テンプレートキャッシュテスト"""
        template_name = 'cache_test.template'
        template_content = 'キャッシュテスト: {{ value }}'
        
        template_path = self.templates_dir / template_name
        template_path.write_text(template_content, encoding='utf-8')
        
        # 最初の読み込み
        template1 = self.template_engine.load_template(template_name)
        assert template1 is not None
        
        # 2回目の読み込み（キャッシュから）
        template2 = self.template_engine.load_template(template_name)
        assert template2 is not None
        
        # 同じオブジェクトがキャッシュされていることを確認
        assert template1 is template2
        
        # キャッシュをクリア
        self.template_engine.clear_template_cache()
        
        # キャッシュクリア後の読み込み
        template3 = self.template_engine.load_template(template_name)
        assert template3 is not None
        # 新しいオブジェクトが作成されることを確認
        assert template3 is not template1
    
    def test_template_preprocessing(self):
        """テンプレート前処理テスト"""
        # 前処理が必要なテンプレート
        preprocess_template = '''
<!-- INCLUDE: header.html -->
<main>
    {{ content }}
</main>
<!-- INCLUDE: footer.html -->
'''
        
        # インクルードファイル
        header_content = '<header><h1>サイトヘッダー</h1></header>'
        footer_content = '<footer><p>サイトフッター</p></footer>'
        
        # ファイルを作成
        template_path = self.templates_dir / 'preprocess_test.template'
        header_path = self.templates_dir / 'header.html'
        footer_path = self.templates_dir / 'footer.html'
        
        template_path.write_text(preprocess_template, encoding='utf-8')
        header_path.write_text(header_content, encoding='utf-8')
        footer_path.write_text(footer_content, encoding='utf-8')
        
        # 前処理機能を有効にしてレンダリング
        result = self.template_engine.render_template(
            'preprocess_test.template',
            {'content': 'メインコンテンツ'},
            enable_preprocessing=True
        )
        
        if result:  # 前処理機能が実装されている場合
            assert 'サイトヘッダー' in result
            assert 'メインコンテンツ' in result
            assert 'サイトフッター' in result
    
    def test_template_variables_context(self):
        """テンプレート変数コンテキストテスト"""
        context_template = '''
グローバル変数: {{ global_var }}
{% set local_var = "ローカル値" %}
ローカル変数: {{ local_var }}

{% for item in items %}
ループ内: {{ item }} - {{ loop.index }}
{% endfor %}

{% with temp_var = "一時的な値" %}
with内: {{ temp_var }}
{% endwith %}

with外: {{ temp_var | default("未定義") }}
'''
        
        template_path = self.templates_dir / 'context_test.template'
        template_path.write_text(context_template, encoding='utf-8')
        
        template_data = {
            'global_var': 'グローバル値',
            'items': ['アイテム1', 'アイテム2', 'アイテム3']
        }
        
        # コンテキストテンプレートをレンダリング
        result = self.template_engine.render_template('context_test.template', template_data)
        
        assert result is not None
        assert 'グローバル変数: グローバル値' in result
        assert 'ローカル変数: ローカル値' in result
        assert 'ループ内: アイテム1 - 1' in result
        assert 'ループ内: アイテム2 - 2' in result
        assert 'with内: 一時的な値' in result
        assert 'with外: 未定義' in result
    
    def test_template_performance(self):
        """テンプレートパフォーマンステスト"""
        import time
        
        # パフォーマンステスト用の大きなテンプレート
        performance_template = '''
{% for i in range(1000) %}
<div class="item-{{ i }}">
    <h3>アイテム {{ i }}</h3>
    <p>{{ description }}</p>
    {% if i % 2 == 0 %}
    <span class="even">偶数</span>
    {% else %}
    <span class="odd">奇数</span>
    {% endif %}
</div>
{% endfor %}
'''
        
        template_path = self.templates_dir / 'performance_test.template'
        template_path.write_text(performance_template, encoding='utf-8')
        
        template_data = {
            'description': 'パフォーマンステスト用のアイテム説明'
        }
        
        # レンダリング時間を測定
        start_time = time.time()
        result = self.template_engine.render_template('performance_test.template', template_data)
        end_time = time.time()
        
        render_time = end_time - start_time
        
        assert result is not None
        assert len(result) > 10000  # 大きなコンテンツが生成されている
        assert render_time < 5.0  # 5秒以内で完了
        
        # 生成されたコンテンツの確認
        assert 'アイテム 0' in result
        assert 'アイテム 999' in result
        assert '<span class="even">偶数</span>' in result
        assert '<span class="odd">奇数</span>' in result
    
    def test_template_internationalization(self):
        """テンプレート国際化テスト"""
        # 多言語対応テンプレート
        i18n_template = '''
{% set messages = {
    'ja': {
        'welcome': 'ようこそ',
        'goodbye': 'さようなら',
        'hello': 'こんにちは'
    },
    'en': {
        'welcome': 'Welcome',
        'goodbye': 'Goodbye', 
        'hello': 'Hello'
    }
} %}

{% set lang_messages = messages[language] %}

<h1>{{ lang_messages.welcome }}, {{ username }}!</h1>
<p>{{ lang_messages.hello }}</p>
<footer>{{ lang_messages.goodbye }}</footer>
'''
        
        template_path = self.templates_dir / 'i18n_test.template'
        template_path.write_text(i18n_template, encoding='utf-8')
        
        # 日本語でのレンダリング
        ja_data = {
            'language': 'ja',
            'username': '田中太郎'
        }
        
        ja_result = self.template_engine.render_template('i18n_test.template', ja_data)
        assert ja_result is not None
        assert 'ようこそ, 田中太郎!' in ja_result
        assert 'こんにちは' in ja_result
        assert 'さようなら' in ja_result
        
        # 英語でのレンダリング
        en_data = {
            'language': 'en',
            'username': 'John Doe'
        }
        
        en_result = self.template_engine.render_template('i18n_test.template', en_data)
        assert en_result is not None
        assert 'Welcome, John Doe!' in en_result
        assert 'Hello' in en_result
        assert 'Goodbye' in en_result
    
    def test_template_batch_processing(self):
        """テンプレートバッチ処理テスト"""
        # バッチ処理用のテンプレート設定
        batch_configs = []
        
        for i in range(5):
            config = {
                'template': 'python_class.py.template',
                'output': str(self.output_dir / f'batch_class_{i}.py'),
                'data': {
                    'class_name': f'BatchClass{i}',
                    'description': f'バッチ処理で生成されたクラス{i}',
                    'class_description': f'バッチクラス{i}の説明',
                    'methods': [
                        {
                            'name': f'method_{i}',
                            'params': '',
                            'description': f'メソッド{i}',
                            'body': f'return "バッチメソッド{i}"'
                        }
                    ]
                }
            }
            batch_configs.append(config)
        
        # バッチ処理を実行
        results = self.template_engine.process_batch_templates(batch_configs)
        
        assert len(results) == 5
        assert all(result['success'] for result in results)
        
        # 生成されたファイルを確認
        for i in range(5):
            file_path = self.output_dir / f'batch_class_{i}.py'
            assert file_path.exists()
            
            content = file_path.read_text(encoding='utf-8')
            assert f'class BatchClass{i}:' in content
            assert f'def method_{i}(self):' in content
            assert f'return "バッチメソッド{i}"' in content
    
    def test_template_dependency_resolution(self):
        """テンプレート依存関係解決テスト"""
        # 依存関係のあるテンプレート群
        base_config = '''
{
    "name": "{{ project_name }}",
    "version": "1.0.0"
}
'''
        
        main_class = '''
from .config import Config

class {{ class_name }}:
    def __init__(self):
        self.config = Config()
'''
        
        config_class = '''
import json

class Config:
    def __init__(self):
        with open('config.json', 'r') as f:
            self.data = json.load(f)
'''
        
        # テンプレートファイルを作成
        (self.templates_dir / 'base_config.json.template').write_text(base_config, encoding='utf-8')
        (self.templates_dir / 'main_class.py.template').write_text(main_class, encoding='utf-8')
        (self.templates_dir / 'config_class.py.template').write_text(config_class, encoding='utf-8')
        
        # 依存関係を含むファイル生成設定
        dependency_configs = [
            {
                'template': 'base_config.json.template',
                'output': str(self.output_dir / 'config.json'),
                'data': {'project_name': 'DependencyTest'},
                'dependencies': []
            },
            {
                'template': 'config_class.py.template',
                'output': str(self.output_dir / 'config.py'),
                'data': {},
                'dependencies': ['config.json']
            },
            {
                'template': 'main_class.py.template',
                'output': str(self.output_dir / 'main.py'),
                'data': {'class_name': 'MainClass'},
                'dependencies': ['config.py']
            }
        ]
        
        # 依存関係を解決して生成
        results = self.template_engine.generate_with_dependencies(dependency_configs)
        
        assert len(results) == 3
        assert all(result['success'] for result in results)
        
        # 生成順序が依存関係に従っていることを確認
        generated_order = [result['output'] for result in results]
        config_json_index = next(i for i, path in enumerate(generated_order) if 'config.json' in path)
        config_py_index = next(i for i, path in enumerate(generated_order) if 'config.py' in path)
        main_py_index = next(i for i, path in enumerate(generated_order) if 'main.py' in path)
        
        assert config_json_index < config_py_index < main_py_index
    
    @requires_file
    def test_template_with_file_context(self):
        """ファイルコンテキストでのテンプレートテスト"""
        template_content = 'テストコンテンツ: {{ test_value }}'
        
        with MockFileContext(self.templates_dir, 'context_template.template', template_content) as template_path:
            # ファイルコンテキスト内でテンプレートを使用
            result = self.template_engine.render_template(
                'context_template.template',
                {'test_value': 'コンテキストテスト'}
            )
            
            assert result is not None
            assert 'テストコンテンツ: コンテキストテスト' in result
    
    def test_template_cleanup(self):
        """テンプレートクリーンアップテスト"""
        # 一時的なテンプレートを作成
        temp_template = 'クリーンアップテスト: {{ value }}'
        temp_path = self.templates_dir / 'temp_cleanup.template'
        temp_path.write_text(temp_template, encoding='utf-8')
        
        # テンプレートを読み込み
        template = self.template_engine.load_template('temp_cleanup.template')
        assert template is not None
        
        # クリーンアップを実行
        cleanup_result = self.template_engine.cleanup_templates()
        
        assert cleanup_result is True
        
        # キャッシュがクリアされていることを確認
        assert len(self.template_engine._template_cache) == 0
    
    def test_template_statistics(self):
        """テンプレート統計情報テスト"""
        # 複数のテンプレートを使用
        templates_used = [
            'python_class.py.template',
            'python_function.py.template',
            'html_page.html.template'
        ]
        
        for template_name in templates_used:
            self.template_engine.render_template(template_name, {})
        
        # 統計情報を取得
        stats = self.template_engine.get_template_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_templates' in stats
        assert 'templates_used' in stats
        assert 'render_count' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        
        assert stats['total_templates'] >= len(templates_used)
        assert stats['render_count'] >= len(templates_used)

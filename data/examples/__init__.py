# data/examples/__init__.py
# LLM Code Assistant - サンプル・例データモジュール

"""
LLM Code Assistant - サンプル・例データモジュール

このモジュールは、LLM Code Assistantで使用するサンプルデータや
例となるコード、プロジェクト構成などを提供します。

主な機能:
- サンプルプロジェクトの定義
- デモ用コードの提供
- テンプレート使用例の提供
- 学習用データの管理

作成者: LLM Code Assistant
バージョン: 1.0.0
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# ロガーの設定
logger = logging.getLogger(__name__)

# モジュール情報
__version__ = "1.0.0"
__author__ = "LLM Code Assistant"
__description__ = "LLM Code Assistant サンプル・例データモジュール"

# サンプルデータのパス
EXAMPLES_DIR = Path(__file__).parent
SAMPLE_PROJECT_PATH = EXAMPLES_DIR / "sample_project.json"
DEMO_CODE_PATH = EXAMPLES_DIR / "demo_code.py"

class ExampleDataError(Exception):
    """サンプルデータに関するエラー"""
    pass

class ExampleDataManager:
    """
    サンプルデータ管理クラス
    
    サンプルプロジェクト、デモコード、使用例などを管理します。
    """
    
    def __init__(self):
        """初期化"""
        self.examples_dir = EXAMPLES_DIR
        self._sample_projects = {}
        self._demo_codes = {}
        self._load_examples()
    
    def _load_examples(self):
        """サンプルデータの読み込み"""
        try:
            # サンプルプロジェクトの読み込み
            if SAMPLE_PROJECT_PATH.exists():
                with open(SAMPLE_PROJECT_PATH, 'r', encoding='utf-8') as f:
                    self._sample_projects = json.load(f)
                logger.info("サンプルプロジェクトを読み込みました")
            
            # デモコードの読み込み
            if DEMO_CODE_PATH.exists():
                with open(DEMO_CODE_PATH, 'r', encoding='utf-8') as f:
                    demo_content = f.read()
                    self._demo_codes['python_demo'] = demo_content
                logger.info("デモコードを読み込みました")
                
        except Exception as e:
            logger.error(f"サンプルデータの読み込みに失敗しました: {e}")
            raise ExampleDataError(f"サンプルデータの読み込みエラー: {e}")
    
    def get_sample_project(self, project_name: str = "default") -> Dict[str, Any]:
        """
        サンプルプロジェクトを取得
        
        Args:
            project_name: プロジェクト名
            
        Returns:
            サンプルプロジェクトデータ
        """
        if project_name not in self._sample_projects:
            available_projects = list(self._sample_projects.keys())
            raise ExampleDataError(
                f"プロジェクト '{project_name}' が見つかりません。"
                f"利用可能なプロジェクト: {available_projects}"
            )
        
        return self._sample_projects[project_name].copy()
    
    def get_demo_code(self, language: str = "python") -> str:
        """
        デモコードを取得
        
        Args:
            language: プログラミング言語
            
        Returns:
            デモコード
        """
        demo_key = f"{language}_demo"
        if demo_key not in self._demo_codes:
            available_demos = list(self._demo_codes.keys())
            raise ExampleDataError(
                f"デモコード '{language}' が見つかりません。"
                f"利用可能なデモ: {available_demos}"
            )
        
        return self._demo_codes[demo_key]
    
    def get_template_examples(self) -> Dict[str, Dict[str, Any]]:
        """
        テンプレート使用例を取得
        
        Returns:
            テンプレート使用例のディクショナリ
        """
        return {
            "python_class": {
                "template_name": "python_class.py.template",
                "variables": {
                    "class_name": "SampleClass",
                    "description": "サンプルクラスの説明",
                    "author": "開発者名",
                    "creation_date": "2024-01-01",
                    "version": "1.0.0",
                    "base_class": "object",
                    "imports": "import os\nimport sys\nfrom typing import Optional",
                    "class_attributes": "sample_attribute = 'default_value'",
                    "init_parameters": "name: str, value: int = 0",
                    "init_body": "self.name = name\nself.value = value",
                    "methods": """
    def get_name(self) -> str:
        \"\"\"名前を取得\"\"\"
        return self.name
    
    def set_value(self, value: int) -> None:
        \"\"\"値を設定\"\"\"
        self.value = value
                    """.strip(),
                    "properties": """
    @property
    def display_name(self) -> str:
        \"\"\"表示名を取得\"\"\"
        return f"{self.name} ({self.value})"
                    """.strip()
                }
            },
            "python_function": {
                "template_name": "python_function.py.template",
                "variables": {
                    "function_name": "sample_function",
                    "description": "サンプル関数の説明",
                    "author": "開発者名",
                    "creation_date": "2024-01-01",
                    "version": "1.0.0",
                    "imports": "from typing import List, Optional",
                    "parameters": "data: List[str], filter_value: Optional[str] = None",
                    "return_type": "List[str]",
                    "function_body": """
    # データのフィルタリング
    if filter_value:
        filtered_data = [item for item in data if filter_value in item]
    else:
        filtered_data = data.copy()
    
    # 結果の返却
    return filtered_data
                    """.strip(),
                    "examples": """
    >>> sample_function(['apple', 'banana', 'cherry'], 'a')
    ['apple', 'banana']
    >>> sample_function(['test1', 'test2'], None)
    ['test1', 'test2']
                    """.strip()
                }
            },
            "javascript_component": {
                "template_name": "javascript_component.js.template",
                "variables": {
                    "component_name": "SampleComponent",
                    "description": "サンプルJavaScriptコンポーネント",
                    "author": "開発者名",
                    "creation_date": "2024-01-01",
                    "version": "1.0.0",
                    "imports": "// 必要な依存関係をここにインポート",
                    "feature_1": "データの処理と表示",
                    "feature_2": "イベントハンドリング",
                    "feature_3": "状態管理",
                    "default_data": "{ message: 'Hello, World!', count: 0 }",
                    "custom_methods": """
    // カスタムメソッドの実装例
    incrementCount() {
        if (this._data && typeof this._data.count === 'number') {
            this._data.count++;
            this.emit('countChanged', this._data.count);
        }
    }
    
    updateMessage(message) {
        if (this._data) {
            this._data.message = message;
            this.emit('messageChanged', message);
        }
    }
                    """.strip()
                }
            },
            "html_page": {
                "template_name": "html_page.html.template",
                "variables": {
                    "title": "サンプルページ",
                    "description": "LLM Code Assistantのサンプルページ",
                    "keywords": "LLM, Code Assistant, サンプル",
                    "author": "開発者名",
                    "theme_color": "#007bff",
                    "page_url": "https://example.com/sample",
                    "og_image": "/assets/images/og-image.jpg",
                    "twitter_image": "/assets/images/twitter-image.jpg",
                    "favicon_path": "/favicon.ico",
                    "apple_touch_icon": "/apple-touch-icon.png",
                    "css_framework_url": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css",
                    "custom_css_path": "/assets/css/custom.css",
                    "font_url": "https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&display=swap",
                    "font_family": "'Noto Sans JP', sans-serif",
                    "primary_color": "#007bff",
                    "secondary_color": "#6c757d",
                    "accent_color": "#28a745",
                    "background_color": "#ffffff",
                    "text_color": "#333333",
                    "border_color": "#dee2e6",
                    "site_name": "LLM Code Assistant",
                    "home_url": "/",
                    "current_year": "2024",
                    "footer_text": "All rights reserved.",
                    "js_framework_url": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js",
                    "custom_styles": "/* カスタムスタイルをここに追加 */",
                    "custom_javascript": "// カスタムJavaScriptをここに追加"
                }
            }
        }
    
    def get_project_structure_example(self) -> Dict[str, Any]:
        """
        プロジェクト構造の例を取得
        
        Returns:
            プロジェクト構造の例
        """
        return {
            "name": "sample-web-app",
            "type": "web_application",
            "description": "サンプルWebアプリケーション",
            "structure": {
                "src/": {
                    "type": "directory",
                    "description": "ソースコードディレクトリ",
                    "files": {
                        "app.py": {
                            "type": "file",
                            "language": "python",
                            "description": "メインアプリケーションファイル"
                        },
                        "config.py": {
                            "type": "file",
                            "language": "python",
                            "description": "設定ファイル"
                        },
                        "models/": {
                            "type": "directory",
                            "description": "データモデル",
                            "files": {
                                "__init__.py": {
                                    "type": "file",
                                    "language": "python"
                                },
                                "user.py": {
                                    "type": "file",
                                    "language": "python",
                                    "description": "ユーザーモデル"
                                }
                            }
                        },
                        "views/": {
                            "type": "directory",
                            "description": "ビューファイル",
                            "files": {
                                "__init__.py": {
                                    "type": "file",
                                    "language": "python"
                                },
                                "main.py": {
                                    "type": "file",
                                    "language": "python",
                                    "description": "メインビュー"
                                }
                            }
                        }
                    }
                },
                "static/": {
                    "type": "directory",
                    "description": "静的ファイル",
                    "files": {
                        "css/": {
                            "type": "directory",
                            "files": {
                                "style.css": {
                                    "type": "file",
                                    "language": "css"
                                }
                            }
                        },
                        "js/": {
                            "type": "directory",
                            "files": {
                                "app.js": {
                                    "type": "file",
                                    "language": "javascript"
                                }
                            }
                        }
                    }
                },
                "templates/": {
                    "type": "directory",
                    "description": "HTMLテンプレート",
                    "files": {
                        "base.html": {
                            "type": "file",
                            "language": "html",
                            "description": "ベーステンプレート"
                        },
                        "index.html": {
                            "type": "file",
                            "language": "html",
                            "description": "インデックスページ"
                        }
                    }
                },
                "tests/": {
                    "type": "directory",
                    "description": "テストファイル",
                    "files": {
                        "test_app.py": {
                            "type": "file",
                            "language": "python",
                            "description": "アプリケーションテスト"
                        }
                    }
                },
                "requirements.txt": {
                    "type": "file",
                    "description": "Python依存関係"
                },
                "README.md": {
                    "type": "file",
                    "language": "markdown",
                    "description": "プロジェクト説明"
                }
            }
        }
    
    def get_code_snippets(self) -> Dict[str, Dict[str, str]]:
        """
        コードスニペットを取得
        
        Returns:
            言語別のコードスニペット
        """
        return {
            "python": {
                "class_definition": '''
class ExampleClass:
    """サンプルクラス"""
    
    def __init__(self, name: str):
        self.name = name
    
    def greet(self) -> str:
        return f"Hello, {self.name}!"
                '''.strip(),
                "function_definition": '''
def calculate_sum(numbers: List[int]) -> int:
    """数値のリストの合計を計算"""
    return sum(numbers)
                '''.strip(),
                "error_handling": '''
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"エラーが発生しました: {e}")
    raise
except Exception as e:
    logger.error(f"予期しないエラー: {e}")
    return None
finally:
    cleanup_resources()
                '''.strip()
            },
            "javascript": {
                "class_definition": '''
class ExampleClass {
    constructor(name) {
        this.name = name;
    }
    
    greet() {
        return `Hello, ${this.name}!`;
    }
}
                '''.strip(),
                "async_function": '''
async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}
                '''.strip(),
                "event_handling": '''
document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('myButton');
    button.addEventListener('click', handleClick);
});

function handleClick(event) {
    event.preventDefault();
    console.log('Button clicked!');
}
                '''.strip()
            },
            "html": {
                "basic_structure": '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ページタイトル</title>
</head>
<body>
    <header>
        <h1>ヘッダー</h1>
    </header>
    <main>
        <p>メインコンテンツ</p>
    </main>
    <footer>
        <p>フッター</p>
    </footer>
</body>
</html>
                '''.strip(),
                "form_example": '''
<form id="contactForm" method="post" action="/contact">
    <div class="form-group">
        <label for="name">お名前:</label>
        <input type="text" id="name" name="name" required>
    </div>
    <div class="form-group">
        <label for="email">メールアドレス:</label>
        <input type="email" id="email" name="email" required>
    </div>
    <div class="form-group">
        <label for="message">メッセージ:</label>
        <textarea id="message" name="message" rows="5" required></textarea>
    </div>
    <button type="submit">送信</button>
</form>
                '''.strip()
            },
            "css": {
                "responsive_grid": '''
.grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1rem;
    padding: 1rem;
}

@media (max-width: 768px) {
    .grid-container {
        grid-template-columns: 1fr;
    }
}
                '''.strip(),
                "button_styles": '''
.btn {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    background-color: #007bff;
    color: white;
    text-decoration: none;
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.btn:hover {
    background-color: #0056b3;
    transform: translateY(-1px);
}
                '''.strip()
            }
        }
    
    def list_available_examples(self) -> Dict[str, List[str]]:
        """
        利用可能なサンプルの一覧を取得
        
        Returns:
            カテゴリ別のサンプル一覧
        """
        return {
            "projects": list(self._sample_projects.keys()),
            "demo_codes": list(self._demo_codes.keys()),
            "templates": list(self.get_template_examples().keys()),
            "snippets": list(self.get_code_snippets().keys())
        }

# グローバルインスタンス
_example_manager = None

def get_example_manager() -> ExampleDataManager:
    """
    サンプルデータマネージャーのシングルトンインスタンスを取得
    
    Returns:
        ExampleDataManagerインスタンス
    """
    global _example_manager
    if _example_manager is None:
        _example_manager = ExampleDataManager()
    return _example_manager

# 便利関数
def get_sample_project(project_name: str = "default") -> Dict[str, Any]:
    """サンプルプロジェクトを取得"""
    return get_example_manager().get_sample_project(project_name)

def get_demo_code(language: str = "python") -> str:
    """デモコードを取得"""
    return get_example_manager().get_demo_code(language)

def get_template_examples() -> Dict[str, Dict[str, Any]]:
    """テンプレート使用例を取得"""
    return get_example_manager().get_template_examples()

def get_code_snippets() -> Dict[str, Dict[str, str]]:
    """コードスニペットを取得"""
    return get_example_manager().get_code_snippets()

def list_available_examples() -> Dict[str, List[str]]:
    """利用可能なサンプルの一覧を取得"""
    return get_example_manager().list_available_examples()

# モジュール情報のエクスポート
__all__ = [
    'ExampleDataError',
    'ExampleDataManager',
    'get_example_manager',
    'get_sample_project',
    'get_demo_code',
    'get_template_examples',
    'get_code_snippets',
    'list_available_examples',
    '__version__',
    '__author__',
    '__description__'
]

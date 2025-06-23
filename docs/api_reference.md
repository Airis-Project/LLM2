<!-- docs/api_reference.md -->
# LLM Code Assistant - API リファレンス

## 概要

LLM Code Assistant のAPIリファレンスです。各モジュール、クラス、関数の詳細な仕様を記載しています。

## 目次

- [Core モジュール](#core-モジュール)
- [LLM モジュール](#llm-モジュール)
- [UI モジュール](#ui-モジュール)
- [Utils モジュール](#utils-モジュール)
- [Plugins モジュール](#plugins-モジュール)
- [Data モジュール](#data-モジュール)

---

## Core モジュール

### ConfigManager

設定管理を行うクラスです。

#### クラス: `ConfigManager`

```python
class ConfigManager:
    """アプリケーション設定の管理"""
    
    def __init__(self, config_file: str = None)
    def load_config(self) -> Dict[str, Any]
    def save_config(self, config: Dict[str, Any]) -> bool
    def get_setting(self, key: str, default: Any = None) -> Any
    def set_setting(self, key: str, value: Any) -> None
    def reset_to_defaults(self) -> None


メソッド詳細:

load_config(): 設定ファイルから設定を読み込み
save_config(config): 設定をファイルに保存
get_setting(key, default): 指定キーの設定値を取得
set_setting(key, value): 指定キーに設定値を保存
reset_to_defaults(): 設定をデフォルト値にリセット
ProjectManager
プロジェクト管理を行うクラスです。

クラス: ProjectManager
class ProjectManager:
    """プロジェクトの管理"""
    
    def __init__(self)
    def create_project(self, name: str, path: str, template: str = None) -> bool
    def open_project(self, path: str) -> bool
    def close_project(self) -> bool
    def get_current_project(self) -> Optional[Dict[str, Any]]
    def get_project_files(self) -> List[str]
    def add_file_to_project(self, file_path: str) -> bool
    def remove_file_from_project(self, file_path: str) -> bool

メソッド詳細:

create_project(name, path, template): 新しいプロジェクトを作成
open_project(path): 既存のプロジェクトを開く
close_project(): 現在のプロジェクトを閉じる
get_current_project(): 現在のプロジェクト情報を取得
get_project_files(): プロジェクト内のファイル一覧を取得
add_file_to_project(file_path): ファイルをプロジェクトに追加
remove_file_from_project(file_path): ファイルをプロジェクトから削除
FileManager
ファイル操作を行うクラスです。

クラス: FileManager
class FileManager:
    """ファイル操作の管理"""
    
    def __init__(self)
    def read_file(self, file_path: str) -> Optional[str]
    def write_file(self, file_path: str, content: str) -> bool
    def create_file(self, file_path: str, content: str = "") -> bool
    def delete_file(self, file_path: str) -> bool
    def copy_file(self, src_path: str, dst_path: str) -> bool
    def move_file(self, src_path: str, dst_path: str) -> bool
    def get_file_info(self, file_path: str) -> Dict[str, Any]

メソッド詳細:

read_file(file_path): ファイルの内容を読み込み
write_file(file_path, content): ファイルに内容を書き込み
create_file(file_path, content): 新しいファイルを作成
delete_file(file_path): ファイルを削除
copy_file(src_path, dst_path): ファイルをコピー
move_file(src_path, dst_path): ファイルを移動
get_file_info(file_path): ファイル情報を取得

LLM モジュール
BaseLLM
LLMクライアントの基底クラスです。

抽象クラス: BaseLLM
class BaseLLM(ABC):
    """LLMクライアントの基底クラス"""
    
    def __init__(self, config: Dict[str, Any])
    @abstractmethod
    def generate_response(self, prompt: str, context: str = None) -> str
    @abstractmethod
    def generate_code(self, description: str, language: str = "python") -> str
    @abstractmethod
    def analyze_code(self, code: str) -> Dict[str, Any]
    def set_temperature(self, temperature: float) -> None
    def set_max_tokens(self, max_tokens: int) -> None

LMFactory
LLMクライアントのファクトリクラスです。

クラス: LLMFactory
class LLMFactory:
    """LLMクライアントのファクトリ"""
    
    @staticmethod
    def create_llm(llm_type: str, config: Dict[str, Any]) -> BaseLLM
    @staticmethod
    def get_available_llms() -> List[str]
    @staticmethod
    def validate_config(llm_type: str, config: Dict[str, Any]) -> bool

メソッド詳細:

create_llm(llm_type, config): 指定タイプのLLMクライアントを作成
get_available_llms(): 利用可能なLLMタイプの一覧を取得
validate_config(llm_type, config): 設定の妥当性を検証

UI モジュール
MainWindow
メインウィンドウクラスです。

クラス: MainWindow
class MainWindow(QMainWindow):
    """メインウィンドウ"""
    
    def __init__(self)
    def setup_ui(self) -> None
    def setup_menu_bar(self) -> None
    def setup_toolbar(self) -> None
    def setup_status_bar(self) -> None
    def open_file(self, file_path: str = None) -> None
    def save_file(self) -> None
    def new_file(self) -> None
    def show_settings(self) -> None
    def show_about(self) -> None

CodeEditor
コードエディタクラスです。

クラス: CodeEditor
class CodeEditor(QPlainTextEdit):
    """コードエディタ"""
    
    def __init__(self, parent=None)
    def set_language(self, language: str) -> None
    def set_theme(self, theme: str) -> None
    def insert_text(self, text: str) -> None
    def get_selected_text(self) -> str
    def find_text(self, text: str, case_sensitive: bool = False) -> bool
    def replace_text(self, find_text: str, replace_text: str) -> int
    def goto_line(self, line_number: int) -> None

Utils モジュール
FileUtils
ファイルユーティリティ関数群です。

関数一覧:
def get_file_extension(file_path: str) -> str
def get_file_size(file_path: str) -> int
def is_text_file(file_path: str) -> bool
def backup_file(file_path: str, backup_dir: str = None) -> str
def restore_file(backup_path: str, original_path: str) -> bool
def get_file_encoding(file_path: str) -> str
def normalize_path(path: str) -> str
def ensure_directory(directory: str) -> bool

TextUtils
テキスト処理ユーティリティ関数群です。

関数一覧:
def count_lines(text: str) -> int
def count_words(text: str) -> int
def count_characters(text: str) -> int
def extract_functions(code: str, language: str) -> List[Dict[str, Any]]
def extract_classes(code: str, language: str) -> List[Dict[str, Any]]
def format_code(code: str, language: str) -> str
def remove_comments(code: str, language: str) -> str
def add_line_numbers(text: str) -> str

ValidationUtils
バリデーションユーティリティ関数群です。

関数一覧:
def validate_file_path(file_path: str) -> bool
def validate_project_name(name: str) -> bool
def validate_email(email: str) -> bool
def validate_url(url: str) -> bool
def validate_json(json_string: str) -> bool
def validate_python_syntax(code: str) -> Tuple[bool, str]
def validate_javascript_syntax(code: str) -> Tuple[bool, str]
def sanitize_filename(filename: str) -> str

Plugins モジュール
BasePlugin
プラグインの基底クラスです。

抽象クラス: BasePlugin
class BasePlugin(ABC):
    """プラグインの基底クラス"""
    
    def __init__(self, name: str, version: str)
    @abstractmethod
    def initialize(self) -> bool
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any
    @abstractmethod
    def cleanup(self) -> None
    def get_info(self) -> Dict[str, Any]
    def is_enabled(self) -> bool
    def set_enabled(self, enabled: bool) -> None

PluginManager
プラグイン管理クラスです。

クラス: PluginManager
class PluginManager:
    """プラグインの管理"""
    
    def __init__(self)
    def load_plugins(self) -> None
    def get_plugin(self, name: str) -> Optional[BasePlugin]
    def get_all_plugins(self) -> List[BasePlugin]
    def enable_plugin(self, name: str) -> bool
    def disable_plugin(self, name: str) -> bool
    def execute_plugin(self, name: str, *args, **kwargs) -> Any

Data モジュール
DataManager
データ管理クラスです。

クラス: DataManager
class DataManager:
    """データファイルの管理"""
    
    def __init__(self)
    def load_json_file(self, file_path: str) -> Optional[Dict[str, Any]]
    def load_yaml_file(self, file_path: str) -> Optional[Dict[str, Any]]
    def load_text_file(self, file_path: str) -> Optional[str]
    def save_json_file(self, file_path: str, data: Dict[str, Any]) -> bool
    def get_template_files(self) -> List[str]
    def get_example_files(self) -> List[str]

TemplateManager
テンプレート管理クラスです。

クラス: TemplateManager
class TemplateManager:
    """テンプレートの管理"""
    
    def __init__(self)
    def get_template(self, template_name: str) -> Optional[str]
    def get_template_list(self) -> List[str]
    def generate_code(self, template_name: str, variables: Dict[str, Any]) -> str
    def add_custom_template(self, name: str, content: str) -> bool
    def remove_custom_template(self, name: str) -> bool
    def validate_template(self, content: str) -> Tuple[bool, List[str]]

エラーハンドリング
例外クラス
class LLMCodeAssistantError(Exception):
    """基底例外クラス"""
    pass

class ConfigurationError(LLMCodeAssistantError):
    """設定エラー"""
    pass

class FileOperationError(LLMCodeAssistantError):
    """ファイル操作エラー"""
    pass

class LLMConnectionError(LLMCodeAssistantError):
    """LLM接続エラー"""
    pass

class PluginError(LLMCodeAssistantError):
    """プラグインエラー"""
    pass

class TemplateError(LLMCodeAssistantError):
    """テンプレートエラー"""
    pass

設定パラメータ
アプリケーション設定
{
  "app": {
    "name": "LLM Code Assistant",
    "version": "1.0.0",
    "language": "ja",
    "theme": "light"
  },
  "editor": {
    "font_family": "Consolas",
    "font_size": 12,
    "tab_size": 4,
    "word_wrap": true,
    "show_line_numbers": true,
    "syntax_highlighting": true
  },
  "llm": {
    "default_provider": "openai",
    "temperature": 0.7,
    "max_tokens": 2048,
    "timeout": 30
  },
  "project": {
    "auto_save": true,
    "backup_enabled": true,
    "recent_projects_limit": 10
  }
}
イベントシステム
イベントタイプ
class EventType(Enum):
    """イベントタイプ"""
    FILE_OPENED = "file_opened"
    FILE_SAVED = "file_saved"
    FILE_CLOSED = "file_closed"
    PROJECT_OPENED = "project_opened"
    PROJECT_CLOSED = "project_closed"
    LLM_RESPONSE_RECEIVED = "llm_response_received"
    PLUGIN_LOADED = "plugin_loaded"
    SETTINGS_CHANGED = "settings_changed"

EventSystem
class EventSystem:
    """イベントシステム"""
    
    def __init__(self)
    def subscribe(self, event_type: EventType, callback: Callable) -> None
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None
    def emit(self, event_type: EventType, data: Any = None) -> None

使用例
基本的な使用方法
from src.core.config_manager import ConfigManager
from src.core.project_manager import ProjectManager
from src.llm.llm_factory import LLMFactory

# 設定管理
config_manager = ConfigManager()
config = config_manager.load_config()

# プロジェクト管理
project_manager = ProjectManager()
project_manager.create_project("MyProject", "/path/to/project")

# LLM使用
llm = LLMFactory.create_llm("openai", config["llm"])
response = llm.generate_response("Hello, how are you?")

プラグイン開発例
from src.plugins.base_plugin import BasePlugin

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__("MyPlugin", "1.0.0")
    
    def initialize(self) -> bool:
        # 初期化処理
        return True
    
    def execute(self, *args, **kwargs) -> Any:
        # プラグイン処理
        return "Plugin executed"
    
    def cleanup(self) -> None:
        # クリーンアップ処理
        pass

バージョン情報
API バージョン: 1.0.0
最終更新: 2024-01-01
互換性: Python 3.11.9+
サポート
API に関する質問やバグ報告は、プロジェクトの GitHub Issues ページまでお願いします。

ライセンス
このAPIドキュメントは MIT ライセンスの下で提供されています。
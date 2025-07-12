#plugins/code_formatter/__init__.py
"""
コードフォーマッタープラグイン
様々な言語のコードフォーマット機能を提供
"""

from .formatter_plugin import FormatterPlugin
from .language_formatters import (
    PythonFormatter,
    JavaScriptFormatter,
    HTMLFormatter,
    CSSFormatter,
    JSONFormatter,
    XMLFormatter,
    SQLFormatter
)

__all__ = [
    'FormatterPlugin',
    'PythonFormatter',
    'JavaScriptFormatter',
    'HTMLFormatter',
    'CSSFormatter',
    'JSONFormatter',
    'XMLFormatter',
    'SQLFormatter'
]

# プラグイン情報
PLUGIN_NAME = "Code Formatter"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "様々なプログラミング言語のコードフォーマット機能を提供します"
PLUGIN_AUTHOR = "LLM Code Assistant Team"
PLUGIN_LICENSE = "MIT"
PLUGIN_DEPENDENCIES = [
    "black",
    "autopep8", 
    "isort",
    "prettier",
    "beautifulsoup4",
    "lxml",
    "sqlparse"
]

# サポートする言語とフォーマッター
SUPPORTED_LANGUAGES = {
    'python': 'PythonFormatter',
    'javascript': 'JavaScriptFormatter',
    'typescript': 'JavaScriptFormatter',
    'html': 'HTMLFormatter',
    'css': 'CSSFormatter',
    'json': 'JSONFormatter',
    'xml': 'XMLFormatter',
    'sql': 'SQLFormatter'
}

# デフォルトフォーマット設定
DEFAULT_FORMAT_SETTINGS = {
    'python': {
        'line_length': 88,
        'use_black': True,
        'use_autopep8': False,
        'use_isort': True,
        'skip_string_normalization': False
    },
    'javascript': {
        'indent_size': 2,
        'use_semicolons': True,
        'use_single_quotes': False,
        'trailing_comma': 'es5'
    },
    'html': {
        'indent_size': 2,
        'wrap_line_length': 120,
        'preserve_newlines': True,
        'max_preserve_newlines': 2
    },
    'css': {
        'indent_size': 2,
        'selector_separator_newline': True,
        'newline_between_rules': True
    },
    'json': {
        'indent_size': 2,
        'sort_keys': False,
        'ensure_ascii': False
    },
    'xml': {
        'indent_size': 2,
        'preserve_whitespace': False,
        'self_closing_tags': True
    },
    'sql': {
        'keyword_case': 'upper',
        'identifier_case': 'lower',
        'strip_comments': False,
        'reindent': True
    }
}



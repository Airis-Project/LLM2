# src/plugins/__init__.py
"""
プラグインシステム
各種プラグインの初期化とエクスポート
"""

from .base_plugin import BasePlugin, PluginInfo, PluginStatus, PluginError
from .git_integration import GitPlugin
from .code_formatter import FormatterPlugin
from .export_tools import ExportPlugin

__all__ = [
    'BasePlugin',
    'PluginInfo',
    'PluginStatus', 
    'PluginError',
    'GitPlugin',
    'FormatterPlugin',
    'ExportPlugin'
]

# バージョン情報
__version__ = '1.0.0'

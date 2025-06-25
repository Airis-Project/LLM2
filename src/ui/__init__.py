# src/ui/__init__.py
"""
User Interface Module
ユーザーインターフェース モジュール
"""

from .cli import CLIInterface

__all__ = ['CLIInterface']

# GUIが利用可能な場合のみインポート
try:
    from .gui import GUIInterface
    __all__.append('GUIInterface')
except ImportError:
    # GUI依存関係が利用できない場合
    pass

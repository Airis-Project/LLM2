# src/plugins/git_integration/__init__.py
"""
Git統合プラグイン
バージョン管理機能を提供
"""

from .git_plugin import GitPlugin
from .git_commands import GitCommands

__all__ = [
    'GitPlugin',
    'GitCommands'
]

# プラグイン情報
PLUGIN_NAME = "Git Integration"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Gitバージョン管理システムとの統合機能を提供します"
PLUGIN_AUTHOR = "LLM Code Assistant Team"
PLUGIN_LICENSE = "MIT"
PLUGIN_DEPENDENCIES = ["gitpython"]

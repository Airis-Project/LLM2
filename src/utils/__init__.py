"""
ユーティリティパッケージ

このパッケージは共通のユーティリティ機能を提供します：
- ファイル操作 (FileUtils)
- バリデーション (ValidationUtils)
- テキスト処理
- その他の汎用機能
"""

from .file_utils import FileUtils
from .validation_utils import ValidationUtils

# バージョン情報
__version__ = "1.0.0"

# エクスポートする要素
__all__ = [
    'FileUtils',
    'ValidationUtils',
    '__version__'
]

def get_utils_info():
    """
    ユーティリティパッケージの情報を取得
    
    Returns:
        dict: パッケージ情報
    """
    return {
        'version': __version__,
        'components': [
            'FileUtils',
            'ValidationUtils'
        ]
    }

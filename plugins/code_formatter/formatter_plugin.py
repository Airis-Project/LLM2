"""
コードフォーマッタープラグイン
様々な言語のコードフォーマット機能を提供するプラグイン
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from ..base_plugin import BasePlugin
from ...core.logger import get_logger
from ...core.event_system import EventSystem
from .language_formatters import (
    PythonFormatter,
    JavaScriptFormatter,
    HTMLFormatter,
    CSSFormatter,
    JSONFormatter,
    XMLFormatter,
    SQLFormatter
)


class FormatterPlugin(BasePlugin):
    """コードフォーマッタープラグイン"""
    
    def __init__(self):
        super().__init__(
            name="Code Formatter",
            version="1.0.0",
            description="様々なプログラミング言語のコードフォーマット機能を提供します",
            author="LLM Code Assistant Team"
        )
        
        self.logger = get_logger("formatter_plugin")
        self.event_system = EventSystem()
        
        # フォーマッター辞書
        self._formatters: Dict[str, Any] = {}
        
        # サポートする言語とファイル拡張子のマッピング
        self.language_extensions = {
            'python': ['.py', '.pyw', '.pyi'],
            'javascript': ['.js', '.jsx', '.mjs'],
            'typescript': ['.ts', '.tsx'],
            'html': ['.html', '.htm', '.xhtml'],
            'css': ['.css', '.scss', '.sass', '.less'],
            'json': ['.json'],
            'xml': ['.xml', '.xsd', '.xsl', '.xslt'],
            'sql': ['.sql', '.mysql', '.pgsql', '.sqlite']
        }
        
        # デフォルト設定
        self.default_settings = {
            'python': {
                'line_length': 88,
                'use_black': True,
                'use_autopep8': False,
                'use_isort': True,
                'skip_string_normalization': False,
                'target_version': ['py311']
            },
            'javascript': {
                'indent_size': 2,
                'use_semicolons': True,
                'use_single_quotes': False,
                'trailing_comma': 'es5',
                'bracket_spacing': True,
                'arrow_parens': 'avoid'
            },
            'html': {
                'indent_size': 2,
                'wrap_line_length': 120,
                'preserve_newlines': True,
                'max_preserve_newlines': 2,
                'indent_inner_html': True
            },
            'css': {
                'indent_size': 2,
                'selector_separator_newline': True,
                'newline_between_rules': True,
                'space_around_combinator': True
            },
            'json': {
                'indent_size': 2,
                'sort_keys': False,
                'ensure_ascii': False,
                'separators': (',', ': ')
            },
            'xml': {
                'indent_size': 2,
                'preserve_whitespace': False,
                'self_closing_tags': True,
                'short_empty_elements': True
            },
            'sql': {
                'keyword_case': 'upper',
                'identifier_case': 'lower',
                'strip_comments': False,
                'reindent': True,
                'indent_width': 2
            }
        }
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """プラグインを初期化"""
        try:
            self.logger.info("コードフォーマッタープラグインを初期化中...")
            
            # 設定を読み込み
            self.settings = config.get('formatter', {})
            
            # フォーマッターを初期化
            self._initialize_formatters()
            
            # イベントハンドラーを登録
            self._register_event_handlers()
            
            self.logger.info("コードフォーマッタープラグインの初期化が完了しました")
            return True
            
        except Exception as e:
            self.logger.error(f"プラグイン初期化エラー: {e}")
            return False
    
    def _initialize_formatters(self):
        """フォーマッターを初期化"""
        try:
            # 各言語のフォーマッターを作成
            self._formatters = {
                'python': PythonFormatter(self._get_language_settings('python')),
                'javascript': JavaScriptFormatter(self._get_language_settings('javascript')),
                'typescript': JavaScriptFormatter(self._get_language_settings('javascript')),
                'html': HTMLFormatter(self._get_language_settings('html')),
                'css': CSSFormatter(self._get_language_settings('css')),
                'json': JSONFormatter(self._get_language_settings('json')),
                'xml': XMLFormatter(self._get_language_settings('xml')),
                'sql': SQLFormatter(self._get_language_settings('sql'))
            }
            
            self.logger.info(f"フォーマッターを初期化しました: {list(self._formatters.keys())}")
            
        except Exception as e:
            self.logger.error(f"フォーマッター初期化エラー: {e}")
    
    def _get_language_settings(self, language: str) -> Dict[str, Any]:
        """言語固有の設定を取得"""
        user_settings = self.settings.get(language, {})
        default_settings = self.default_settings.get(language, {})
        
        # デフォルト設定にユーザー設定をマージ
        merged_settings = default_settings.copy()
        merged_settings.update(user_settings)
        
        return merged_settings
    
    def _register_event_handlers(self):
        """イベントハンドラーを登録"""
        try:
            # ファイル保存前のフォーマット
            self.event_system.subscribe('file_before_save', self._on_file_before_save)
            
            # フォーマット要求
            self.event_system.subscribe('format_request', self._on_format_request)
            
            self.logger.debug("イベントハンドラーを登録しました")
            
        except Exception as e:
            self.logger.error(f"イベントハンドラー登録エラー: {e}")
    
    def _on_file_before_save(self, event_data: Dict[str, Any]):
        """ファイル保存前のイベントハンドラー"""
        try:
            file_path = event_data.get('file_path')
            if not file_path:
                return
            
            # 自動フォーマットが有効かチェック
            if not self.settings.get('auto_format_on_save', False):
                return
            
            # ファイルの言語を判定
            language = self.detect_language(file_path)
            if not language:
                return
            
            # フォーマット実行
            content = event_data.get('content', '')
            formatted_content = self.format_code(content, language)
            
            if formatted_content != content:
                event_data['content'] = formatted_content
                self.logger.info(f"ファイルを自動フォーマットしました: {file_path}")
            
        except Exception as e:
            self.logger.error(f"自動フォーマットエラー: {e}")
    
    def _on_format_request(self, event_data: Dict[str, Any]):
        """フォーマット要求のイベントハンドラー"""
        try:
            content = event_data.get('content', '')
            language = event_data.get('language', '')
            
            if not content or not language:
                return
            
            formatted_content = self.format_code(content, language)
            event_data['formatted_content'] = formatted_content
            
        except Exception as e:
            self.logger.error(f"フォーマット要求処理エラー: {e}")
    
    def detect_language(self, file_path: str) -> Optional[str]:
        """ファイルパスから言語を検出"""
        try:
            file_path = Path(file_path)
            extension = file_path.suffix.lower()
            
            for language, extensions in self.language_extensions.items():
                if extension in extensions:
                    return language
            
            return None
            
        except Exception as e:
            self.logger.error(f"言語検出エラー: {e}")
            return None
    
    def format_code(self, content: str, language: str) -> str:
        """コードをフォーマット"""
        try:
            if not content.strip():
                return content
            
            formatter = self._formatters.get(language.lower())
            if not formatter:
                self.logger.warning(f"サポートされていない言語: {language}")
                return content
            
            # フォーマット実行
            formatted_content = formatter.format(content)
            
            if formatted_content is None:
                self.logger.warning(f"フォーマットに失敗しました: {language}")
                return content
            
            return formatted_content
            
        except Exception as e:
            self.logger.error(f"コードフォーマットエラー: {e}")
            return content
    
    def format_file(self, file_path: str) -> bool:
        """ファイルをフォーマット"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                self.logger.error(f"ファイルが存在しません: {file_path}")
                return False
            
            # 言語を検出
            language = self.detect_language(str(file_path))
            if not language:
                self.logger.warning(f"サポートされていない言語のファイル: {file_path}")
                return False
            
            # ファイル内容を読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # フォーマット実行
            formatted_content = self.format_code(content, language)
            
            # 変更があった場合のみ書き込み
            if formatted_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_content)
                
                self.logger.info(f"ファイルをフォーマットしました: {file_path}")
                return True
            
            return True
            
        except Exception as e:
            self.logger.error(f"ファイルフォーマットエラー: {e}")
            return False
    
    def get_supported_languages(self) -> List[str]:
        """サポートする言語一覧を取得"""
        return list(self._formatters.keys())
    
    def get_language_extensions(self, language: str) -> List[str]:
        """言語のファイル拡張子一覧を取得"""
        return self.language_extensions.get(language, [])
    
    def is_formatter_available(self, language: str) -> bool:
        """指定言語のフォーマッターが利用可能かチェック"""
        formatter = self._formatters.get(language.lower())
        return formatter is not None and formatter.is_available()
    
    def get_formatter_info(self, language: str) -> Dict[str, Any]:
        """フォーマッター情報を取得"""
        formatter = self._formatters.get(language.lower())
        if not formatter:
            return {}
        
        return {
            'name': formatter.name,
            'version': getattr(formatter, 'version', 'unknown'),
            'available': formatter.is_available(),
            'settings': self._get_language_settings(language)
        }
    
    def update_settings(self, language: str, settings: Dict[str, Any]) -> bool:
        """言語設定を更新"""
        try:
            if language not in self._formatters:
                self.logger.error(f"サポートされていない言語: {language}")
                return False
            
            # 設定を更新
            if 'formatter' not in self.settings:
                self.settings['formatter'] = {}
            
            self.settings['formatter'][language] = settings
            
            # フォーマッターの設定を更新
            formatter = self._formatters[language]
            formatter.update_settings(settings)
            
            self.logger.info(f"言語設定を更新しました: {language}")
            return True
            
        except Exception as e:
            self.logger.error(f"設定更新エラー: {e}")
            return False
    
    def validate_code(self, content: str, language: str) -> Tuple[bool, List[str]]:
        """コードの構文チェック"""
        try:
            formatter = self._formatters.get(language.lower())
            if not formatter:
                return True, []
            
            if hasattr(formatter, 'validate'):
                return formatter.validate(content)
            
            # 基本的な検証として、フォーマットを試行
            try:
                formatter.format(content)
                return True, []
            except Exception as e:
                return False, [str(e)]
            
        except Exception as e:
            self.logger.error(f"コード検証エラー: {e}")
            return False, [str(e)]
    
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """メニューアイテムを取得"""
        return [
            {
                'text': 'コードフォーマット',
                'action': 'format_current_file',
                'shortcut': 'Ctrl+Shift+F',
                'icon': 'format.png'
            },
            {
                'text': 'フォーマット設定',
                'action': 'open_formatter_settings',
                'icon': 'settings.png'
            },
            {
                'separator': True
            },
            {
                'text': '自動フォーマット切り替え',
                'action': 'toggle_auto_format',
                'checkable': True,
                'checked': self.settings.get('auto_format_on_save', False)
            }
        ]
    
    def get_toolbar_items(self) -> List[Dict[str, Any]]:
        """ツールバーアイテムを取得"""
        return [
            {
                'text': 'フォーマット',
                'action': 'format_current_file',
                'tooltip': 'コードをフォーマット (Ctrl+Shift+F)',
                'icon': 'format.png'
            }
        ]
    
    def cleanup(self):
        """プラグインのクリーンアップ"""
        try:
            # イベントハンドラーの登録解除
            self.event_system.unsubscribe('file_before_save', self._on_file_before_save)
            self.event_system.unsubscribe('format_request', self._on_format_request)
            
            # フォーマッターのクリーンアップ
            for formatter in self._formatters.values():
                if hasattr(formatter, 'cleanup'):
                    formatter.cleanup()
            
            self._formatters.clear()
            
            self.logger.info("コードフォーマッタープラグインをクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"プラグインクリーンアップエラー: {e}")

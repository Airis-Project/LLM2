# src/ui/components/syntax_highlighter.py
"""
シンタックスハイライター
コードエディタでの構文強調表示を提供
"""

import re
from typing import Dict, List, Tuple, Optional
from enum import Enum

from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import (
    QColor, QTextCharFormat, QFont, QSyntaxHighlighter,
    QTextDocument, QPalette
)

from ...core.logger import get_logger


class HighlightRule:
    """ハイライトルールクラス"""
    
    def __init__(self, pattern: str, format_style: QTextCharFormat, 
                 is_multiline: bool = False):
        self.pattern = QRegularExpression(pattern)
        self.format = format_style
        self.is_multiline = is_multiline


class SyntaxTheme(Enum):
    """シンタックスハイライトテーマ"""
    LIGHT = "light"
    DARK = "dark"
    MONOKAI = "monokai"
    GITHUB = "github"


class BaseSyntaxHighlighter(QSyntaxHighlighter):
    """基本シンタックスハイライター"""
    
    def __init__(self, document: QTextDocument, theme: SyntaxTheme = SyntaxTheme.LIGHT):
        super().__init__(document)
        self.logger = get_logger(__name__)
        self.theme = theme
        self.highlighting_rules: List[HighlightRule] = []
        
        # テーマに基づく色設定
        self.colors = self._get_theme_colors()
        
        # フォーマット初期化
        self._init_formats()
        
        # ルール初期化
        self._init_rules()
    
    def _get_theme_colors(self) -> Dict[str, QColor]:
        """テーマに基づく色設定を取得"""
        try:
            if self.theme == SyntaxTheme.DARK:
                return {
                    'keyword': QColor(86, 156, 214),      # ブルー
                    'string': QColor(206, 145, 120),      # オレンジ
                    'comment': QColor(106, 153, 85),      # グリーン
                    'number': QColor(181, 206, 168),      # ライトグリーン
                    'operator': QColor(212, 212, 212),    # ホワイト
                    'builtin': QColor(78, 201, 176),      # シアン
                    'function': QColor(220, 220, 170),    # イエロー
                    'class': QColor(78, 201, 176),        # シアン
                    'decorator': QColor(255, 198, 109),   # ゴールド
                    'background': QColor(30, 30, 30),     # ダークグレー
                    'text': QColor(212, 212, 212)         # ライトグレー
                }
            elif self.theme == SyntaxTheme.MONOKAI:
                return {
                    'keyword': QColor(249, 38, 114),      # ピンク
                    'string': QColor(230, 219, 116),      # イエロー
                    'comment': QColor(117, 113, 94),      # グレー
                    'number': QColor(174, 129, 255),      # パープル
                    'operator': QColor(249, 38, 114),     # ピンク
                    'builtin': QColor(102, 217, 239),     # シアン
                    'function': QColor(166, 226, 46),     # グリーン
                    'class': QColor(166, 226, 46),        # グリーン
                    'decorator': QColor(102, 217, 239),   # シアン
                    'background': QColor(39, 40, 34),     # ダークグリーン
                    'text': QColor(248, 248, 242)         # ホワイト
                }
            else:  # LIGHT or GITHUB
                return {
                    'keyword': QColor(0, 0, 255),         # ブルー
                    'string': QColor(163, 21, 21),        # レッド
                    'comment': QColor(0, 128, 0),         # グリーン
                    'number': QColor(0, 0, 139),          # ダークブルー
                    'operator': QColor(0, 0, 0),          # ブラック
                    'builtin': QColor(128, 0, 128),       # パープル
                    'function': QColor(0, 0, 139),        # ダークブルー
                    'class': QColor(0, 0, 139),           # ダークブルー
                    'decorator': QColor(128, 128, 0),     # オリーブ
                    'background': QColor(255, 255, 255),  # ホワイト
                    'text': QColor(0, 0, 0)               # ブラック
                }
        except Exception as e:
            self.logger.error(f"テーマ色取得エラー: {e}")
            # デフォルト色を返す
            return {
                'keyword': QColor(0, 0, 255),
                'string': QColor(163, 21, 21),
                'comment': QColor(0, 128, 0),
                'number': QColor(0, 0, 139),
                'operator': QColor(0, 0, 0),
                'builtin': QColor(128, 0, 128),
                'function': QColor(0, 0, 139),
                'class': QColor(0, 0, 139),
                'decorator': QColor(128, 128, 0),
                'background': QColor(255, 255, 255),
                'text': QColor(0, 0, 0)
            }
    
    def _init_formats(self):
        """フォーマットを初期化"""
        try:
            # キーワードフォーマット
            self.keyword_format = QTextCharFormat()
            self.keyword_format.setForeground(self.colors['keyword'])
            self.keyword_format.setFontWeight(QFont.Weight.Bold)
            
            # 文字列フォーマット
            self.string_format = QTextCharFormat()
            self.string_format.setForeground(self.colors['string'])
            
            # コメントフォーマット
            self.comment_format = QTextCharFormat()
            self.comment_format.setForeground(self.colors['comment'])
            self.comment_format.setFontItalic(True)
            
            # 数値フォーマット
            self.number_format = QTextCharFormat()
            self.number_format.setForeground(self.colors['number'])
            
            # 演算子フォーマット
            self.operator_format = QTextCharFormat()
            self.operator_format.setForeground(self.colors['operator'])
            
            # 組み込み関数フォーマット
            self.builtin_format = QTextCharFormat()
            self.builtin_format.setForeground(self.colors['builtin'])
            self.builtin_format.setFontWeight(QFont.Weight.Bold)
            
            # 関数フォーマット
            self.function_format = QTextCharFormat()
            self.function_format.setForeground(self.colors['function'])
            
            # クラスフォーマット
            self.class_format = QTextCharFormat()
            self.class_format.setForeground(self.colors['class'])
            self.class_format.setFontWeight(QFont.Weight.Bold)
            
            # デコレータフォーマット
            self.decorator_format = QTextCharFormat()
            self.decorator_format.setForeground(self.colors['decorator'])
            
        except Exception as e:
            self.logger.error(f"フォーマット初期化エラー: {e}")
    
    def _init_rules(self):
        """基本ルールを初期化（サブクラスでオーバーライド）"""
        pass
    
    def highlightBlock(self, text: str):
        """ブロックをハイライト"""
        try:
            # 各ルールを適用
            for rule in self.highlighting_rules:
                iterator = rule.pattern.globalMatch(text)
                while iterator.hasNext():
                    match = iterator.next()
                    self.setFormat(match.capturedStart(), match.capturedLength(), rule.format)
            
            # 複数行コメントの処理
            self._highlight_multiline_comments(text)
            
        except Exception as e:
            self.logger.error(f"ハイライト処理エラー: {e}")
    
    def _highlight_multiline_comments(self, text: str):
        """複数行コメントをハイライト（サブクラスでオーバーライド）"""
        pass
    
    def set_theme(self, theme: SyntaxTheme):
        """テーマを設定"""
        try:
            self.theme = theme
            self.colors = self._get_theme_colors()
            self._init_formats()
            self.rehighlight()
            
        except Exception as e:
            self.logger.error(f"テーマ設定エラー: {e}")


class PythonHighlighter(BaseSyntaxHighlighter):
    """Pythonシンタックスハイライター"""
    
    def __init__(self, document: QTextDocument, theme: SyntaxTheme = SyntaxTheme.LIGHT):
        super().__init__(document, theme)
    
    def _init_rules(self):
        """Pythonのハイライトルールを初期化"""
        try:
            self.highlighting_rules = []
            
            # Pythonキーワード
            python_keywords = [
                'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
                'del', 'elif', 'else', 'except', 'exec', 'finally', 'for',
                'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
                'not', 'or', 'pass', 'print', 'raise', 'return', 'try',
                'while', 'with', 'yield', 'None', 'True', 'False', 'async',
                'await', 'nonlocal'
            ]
            
            keyword_pattern = r'\b(' + '|'.join(python_keywords) + r')\b'
            self.highlighting_rules.append(
                HighlightRule(keyword_pattern, self.keyword_format)
            )
            
            # 組み込み関数
            builtin_functions = [
                'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes',
                'callable', 'chr', 'classmethod', 'compile', 'complex',
                'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval',
                'filter', 'float', 'format', 'frozenset', 'getattr',
                'globals', 'hasattr', 'hash', 'help', 'hex', 'id', 'input',
                'int', 'isinstance', 'issubclass', 'iter', 'len', 'list',
                'locals', 'map', 'max', 'memoryview', 'min', 'next',
                'object', 'oct', 'open', 'ord', 'pow', 'property', 'range',
                'repr', 'reversed', 'round', 'set', 'setattr', 'slice',
                'sorted', 'staticmethod', 'str', 'sum', 'super', 'tuple',
                'type', 'vars', 'zip', '__import__'
            ]
            
            builtin_pattern = r'\b(' + '|'.join(builtin_functions) + r')\b'
            self.highlighting_rules.append(
                HighlightRule(builtin_pattern, self.builtin_format)
            )
            
            # 文字列（ダブルクォート）
            self.highlighting_rules.append(
                HighlightRule(r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format)
            )
            
            # 文字列（シングルクォート）
            self.highlighting_rules.append(
                HighlightRule(r"'[^'\\]*(\\.[^'\\]*)*'", self.string_format)
            )
            
            # トリプルクォート文字列
            self.highlighting_rules.append(
                HighlightRule(r'""".*?"""', self.string_format)
            )
            
            self.highlighting_rules.append(
                HighlightRule(r"'''.*?'''", self.string_format)
            )
            
            # 数値
            self.highlighting_rules.append(
                HighlightRule(r'\b\d+\.?\d*([eE][+-]?\d+)?\b', self.number_format)
            )
            
            # 16進数
            self.highlighting_rules.append(
                HighlightRule(r'\b0[xX][0-9a-fA-F]+\b', self.number_format)
            )
            
            # 8進数
            self.highlighting_rules.append(
                HighlightRule(r'\b0[oO][0-7]+\b', self.number_format)
            )
            
            # 2進数
            self.highlighting_rules.append(
                HighlightRule(r'\b0[bB][01]+\b', self.number_format)
            )
            
            # 関数定義
            self.highlighting_rules.append(
                HighlightRule(r'\bdef\s+([A-Za-z_][A-Za-z0-9_]*)', self.function_format)
            )
            
            # クラス定義
            self.highlighting_rules.append(
                HighlightRule(r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)', self.class_format)
            )
            
            # デコレータ
            self.highlighting_rules.append(
                HighlightRule(r'@[A-Za-z_][A-Za-z0-9_]*', self.decorator_format)
            )
            
            # 単行コメント
            self.highlighting_rules.append(
                HighlightRule(r'#[^\n]*', self.comment_format)
            )
            
            # 演算子
            operators = [
                r'\+', r'-', r'\*', r'/', r'//', r'%', r'\*\*',
                r'==', r'!=', r'<', r'>', r'<=', r'>=',
                r'=', r'\+=', r'-=', r'\*=', r'/=', r'//=', r'%=', r'\*\*=',
                r'&', r'\|', r'\^', r'~', r'<<', r'>>',
                r'&=', r'\|=', r'\^=', r'<<=', r'>>=',
                r'and', r'or', r'not', r'in', r'is'
            ]
            
            for op in operators:
                self.highlighting_rules.append(
                    HighlightRule(fr'\b{op}\b' if op.isalpha() else op, self.operator_format)
                )
            
        except Exception as e:
            self.logger.error(f"Pythonルール初期化エラー: {e}")
    
    def _highlight_multiline_comments(self, text: str):
        """Python複数行コメントをハイライト"""
        try:
            # トリプルクォート文字列/コメントの処理
            self.setCurrentBlockState(0)
            
            # """ で始まる複数行文字列
            start_expression = QRegularExpression('"""')
            end_expression = QRegularExpression('"""')
            
            self._highlight_multiline_string(text, start_expression, end_expression, 1)
            
            # ''' で始まる複数行文字列
            start_expression = QRegularExpression("'''")
            end_expression = QRegularExpression("'''")
            
            self._highlight_multiline_string(text, start_expression, end_expression, 2)
            
        except Exception as e:
            self.logger.error(f"Python複数行コメントハイライトエラー: {e}")
    
    def _highlight_multiline_string(self, text: str, start_expr: QRegularExpression, 
                                  end_expr: QRegularExpression, state: int):
        """複数行文字列をハイライト"""
        try:
            start_index = 0
            if self.previousBlockState() != state:
                start_match = start_expr.match(text)
                start_index = start_match.capturedStart() if start_match.hasMatch() else -1
            
            while start_index >= 0:
                end_match = end_expr.match(text, start_index)
                end_index = end_match.capturedStart() if end_match.hasMatch() else -1
                
                if end_index == -1:
                    self.setCurrentBlockState(state)
                    comment_length = len(text) - start_index
                else:
                    comment_length = end_index - start_index + end_match.capturedLength()
                
                self.setFormat(start_index, comment_length, self.string_format)
                
                if end_index >= 0:
                    start_match = start_expr.match(text, start_index + comment_length)
                    start_index = start_match.capturedStart() if start_match.hasMatch() else -1
                else:
                    break
            
        except Exception as e:
            self.logger.error(f"複数行文字列ハイライトエラー: {e}")


class JavaScriptHighlighter(BaseSyntaxHighlighter):
    """JavaScriptシンタックスハイライター"""
    
    def __init__(self, document: QTextDocument, theme: SyntaxTheme = SyntaxTheme.LIGHT):
        super().__init__(document, theme)
    
    def _init_rules(self):
        """JavaScriptのハイライトルールを初期化"""
        try:
            self.highlighting_rules = []
            
            # JavaScriptキーワード
            js_keywords = [
                'break', 'case', 'catch', 'class', 'const', 'continue',
                'debugger', 'default', 'delete', 'do', 'else', 'export',
                'extends', 'finally', 'for', 'function', 'if', 'import',
                'in', 'instanceof', 'let', 'new', 'return', 'super',
                'switch', 'this', 'throw', 'try', 'typeof', 'var',
                'void', 'while', 'with', 'yield', 'async', 'await',
                'true', 'false', 'null', 'undefined'
            ]
            
            keyword_pattern = r'\b(' + '|'.join(js_keywords) + r')\b'
            self.highlighting_rules.append(
                HighlightRule(keyword_pattern, self.keyword_format)
            )
            
            # 文字列（ダブルクォート）
            self.highlighting_rules.append(
                HighlightRule(r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format)
            )
            
            # 文字列（シングルクォート）
            self.highlighting_rules.append(
                HighlightRule(r"'[^'\\]*(\\.[^'\\]*)*'", self.string_format)
            )
            
            # テンプレートリテラル
            self.highlighting_rules.append(
                HighlightRule(r'`[^`\\]*(\\.[^`\\]*)*`', self.string_format)
            )
            
            # 数値
            self.highlighting_rules.append(
                HighlightRule(r'\b\d+\.?\d*([eE][+-]?\d+)?\b', self.number_format)
            )
            
            # 関数定義
            self.highlighting_rules.append(
                HighlightRule(r'\bfunction\s+([A-Za-z_$][A-Za-z0-9_$]*)', self.function_format)
            )
            
            # 単行コメント
            self.highlighting_rules.append(
                HighlightRule(r'//[^\n]*', self.comment_format)
            )
            
        except Exception as e:
            self.logger.error(f"JavaScriptルール初期化エラー: {e}")
    
    def _highlight_multiline_comments(self, text: str):
        """JavaScript複数行コメントをハイライト"""
        try:
            self.setCurrentBlockState(0)
            
            start_expression = QRegularExpression(r'/\*')
            end_expression = QRegularExpression(r'\*/')
            
            start_index = 0
            if self.previousBlockState() != 1:
                start_match = start_expression.match(text)
                start_index = start_match.capturedStart() if start_match.hasMatch() else -1
            
            while start_index >= 0:
                end_match = end_expression.match(text, start_index)
                end_index = end_match.capturedStart() if end_match.hasMatch() else -1
                
                if end_index == -1:
                    self.setCurrentBlockState(1)
                    comment_length = len(text) - start_index
                else:
                    comment_length = end_index - start_index + end_match.capturedLength()
                
                self.setFormat(start_index, comment_length, self.comment_format)
                
                if end_index >= 0:
                    start_match = start_expression.match(text, start_index + comment_length)
                    start_index = start_match.capturedStart() if start_match.hasMatch() else -1
                else:
                    break
            
        except Exception as e:
            self.logger.error(f"JavaScript複数行コメントハイライトエラー: {e}")


class HTMLHighlighter(BaseSyntaxHighlighter):
    """HTMLシンタックスハイライター"""
    
    def __init__(self, document: QTextDocument, theme: SyntaxTheme = SyntaxTheme.LIGHT):
        super().__init__(document, theme)
    
    def _init_rules(self):
        """HTMLのハイライトルールを初期化"""
        try:
            self.highlighting_rules = []
            
            # XMLタグ
            self.highlighting_rules.append(
                HighlightRule(r'<[!?/]?\b[A-Za-z0-9-]+\b[^>]*>', self.keyword_format)
            )
            
            # 属性名
            self.highlighting_rules.append(
                HighlightRule(r'\b[A-Za-z0-9-]+(?=\s*=)', self.function_format)
            )
            
            # 属性値（ダブルクォート）
            self.highlighting_rules.append(
                HighlightRule(r'"[^"]*"', self.string_format)
            )
            
            # 属性値（シングルクォート）
            self.highlighting_rules.append(
                HighlightRule(r"'[^']*'", self.string_format)
            )
            
            # HTMLコメント
            self.highlighting_rules.append(
                HighlightRule(r'<!--.*?-->', self.comment_format)
            )
            
        except Exception as e:
            self.logger.error(f"HTMLルール初期化エラー: {e}")


class CSSHighlighter(BaseSyntaxHighlighter):
    """CSSシンタックスハイライター"""
    
    def __init__(self, document: QTextDocument, theme: SyntaxTheme = SyntaxTheme.LIGHT):
        super().__init__(document, theme)
    
    def _init_rules(self):
        """CSSのハイライトルールを初期化"""
        try:
            self.highlighting_rules = []
            
            # セレクタ
            self.highlighting_rules.append(
                HighlightRule(r'[.#]?[A-Za-z0-9_-]+(?=\s*{)', self.class_format)
            )
            
            # プロパティ名
            self.highlighting_rules.append(
                HighlightRule(r'[A-Za-z-]+(?=\s*:)', self.function_format)
            )
            
            # プロパティ値
            self.highlighting_rules.append(
                HighlightRule(r':\s*[^;}]+', self.string_format)
            )
            
            # 数値と単位
            self.highlighting_rules.append(
                HighlightRule(r'\b\d+\.?\d*(px|em|rem|%|vh|vw|pt|pc|in|cm|mm)?\b', self.number_format)
            )
            
            # 色（16進数）
            self.highlighting_rules.append(
                HighlightRule(r'#[0-9a-fA-F]{3,6}\b', self.number_format)
            )
            
            # CSSコメント
            self.highlighting_rules.append(
                HighlightRule(r'/\*.*?\*/', self.comment_format)
            )
            
        except Exception as e:
            self.logger.error(f"CSSルール初期化エラー: {e}")


def create_highlighter(language: str, document: QTextDocument, 
                      theme: SyntaxTheme = SyntaxTheme.LIGHT) -> Optional[BaseSyntaxHighlighter]:
    """言語に応じたハイライターを作成"""
    try:
        language = language.lower()
        
        if language in ['python', 'py']:
            return PythonHighlighter(document, theme)
        elif language in ['javascript', 'js']:
            return JavaScriptHighlighter(document, theme)
        elif language in ['html', 'htm']:
            return HTMLHighlighter(document, theme)
        elif language in ['css']:
            return CSSHighlighter(document, theme)
        else:
            # サポートされていない言語の場合は基本ハイライターを返す
            return BaseSyntaxHighlighter(document, theme)
    
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"ハイライター作成エラー: {e}")
        return None

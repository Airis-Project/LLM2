# src/llm/response_parser.py
"""
LLMレスポンスパーサーモジュール
LLMからの応答を解析・構造化し、適切な形式に変換
"""

import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import ast
import markdown
from bs4 import BeautifulSoup

from ..core.logger import get_logger
from ..core.config_manager import get_config
from ..utils.text_utils import TextUtils
from ..utils.validation_utils import ValidationUtils

logger = get_logger(__name__)

class ResponseType(Enum):
    """レスポンスタイプ列挙型"""
    CODE = "code"
    EXPLANATION = "explanation"
    REVIEW = "review"
    DEBUG = "debug"
    DOCUMENTATION = "documentation"
    GENERAL = "general"
    ERROR = "error"
    MIXED = "mixed"

class CodeLanguage(Enum):
    """コード言語列挙型"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    HTML = "html"
    CSS = "css"
    SQL = "sql"
    BASH = "bash"
    POWERSHELL = "powershell"
    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"

@dataclass
class CodeBlock:
    """コードブロック"""
    language: CodeLanguage
    code: str
    line_start: int = 0
    line_end: int = 0
    filename: Optional[str] = None
    description: Optional[str] = None
    is_complete: bool = True
    has_syntax_error: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReviewItem:
    """レビュー項目"""
    category: str  # "quality", "security", "performance", "bug", "style"
    severity: str  # "critical", "major", "minor", "info"
    line_number: Optional[int]
    title: str
    description: str
    suggestion: Optional[str] = None
    example_code: Optional[str] = None

@dataclass
class ParsedResponse:
    """解析済みレスポンス"""
    response_type: ResponseType
    original_text: str
    summary: str
    code_blocks: List[CodeBlock] = field(default_factory=list)
    review_items: List[ReviewItem] = field(default_factory=list)
    explanations: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    parsing_timestamp: Optional[datetime] = None

class ResponseParser:
    """レスポンスパーサークラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = get_logger(self.__class__.__name__)
        self.text_utils = TextUtils()
        self.validation_utils = ValidationUtils()
        
        # 言語検出パターン
        self.language_patterns = {
            CodeLanguage.PYTHON: [r'def\s+\w+', r'import\s+\w+', r'from\s+\w+\s+import', r'class\s+\w+'],
            CodeLanguage.JAVASCRIPT: [r'function\s+\w+', r'const\s+\w+\s*=', r'let\s+\w+\s*=', r'var\s+\w+\s*='],
            CodeLanguage.JAVA: [r'public\s+class', r'private\s+\w+', r'public\s+static\s+void\s+main'],
            CodeLanguage.CSHARP: [r'using\s+System', r'namespace\s+\w+', r'public\s+class'],
            CodeLanguage.HTML: [r'<html', r'<div', r'<script', r'<!DOCTYPE'],
            CodeLanguage.CSS: [r'\.\w+\s*{', r'#\w+\s*{', r'@media'],
            CodeLanguage.SQL: [r'SELECT\s+', r'INSERT\s+INTO', r'UPDATE\s+', r'DELETE\s+FROM'],
        }
        
        # コードブロックパターン
        self.code_block_pattern = re.compile(
            r'```(\w+)?\n?(.*?)\n?```',
            re.DOTALL | re.MULTILINE
        )
        
        # インラインコードパターン
        self.inline_code_pattern = re.compile(r'`([^`]+)`')
        
        # レビューパターン
        self.review_patterns = {
            'critical': [r'重大', r'クリティカル', r'危険', r'脆弱性'],
            'major': [r'重要', r'メジャー', r'問題', r'バグ'],
            'minor': [r'軽微', r'マイナー', r'改善', r'推奨'],
            'info': [r'情報', r'参考', r'ヒント', r'補足']
        }
        
        self.logger.info("レスポンスパーサーを初期化しました")
    
    def parse_response(self, response_text: str, expected_type: Optional[ResponseType] = None) -> ParsedResponse:
        """
        レスポンスを解析
        
        Args:
            response_text: レスポンステキスト
            expected_type: 期待するレスポンスタイプ
            
        Returns:
            ParsedResponse: 解析済みレスポンス
        """
        try:
            # 基本情報を設定
            parsed = ParsedResponse(
                response_type=expected_type or self._detect_response_type(response_text),
                original_text=response_text,
                summary=self._extract_summary(response_text),
                parsing_timestamp=datetime.now()
            )
            
            # コードブロックを抽出
            parsed.code_blocks = self._extract_code_blocks(response_text)
            
            # レスポンスタイプ別の解析
            if parsed.response_type == ResponseType.CODE:
                self._parse_code_response(response_text, parsed)
            elif parsed.response_type == ResponseType.REVIEW:
                self._parse_review_response(response_text, parsed)
            elif parsed.response_type == ResponseType.DEBUG:
                self._parse_debug_response(response_text, parsed)
            elif parsed.response_type == ResponseType.EXPLANATION:
                self._parse_explanation_response(response_text, parsed)
            elif parsed.response_type == ResponseType.DOCUMENTATION:
                self._parse_documentation_response(response_text, parsed)
            else:
                self._parse_general_response(response_text, parsed)
            
            # 信頼度スコアを計算
            parsed.confidence_score = self._calculate_confidence_score(parsed)
            
            self.logger.info(f"レスポンスを解析しました: {parsed.response_type.value}")
            return parsed
            
        except Exception as e:
            self.logger.error(f"レスポンス解析エラー: {e}")
            # エラー時のフォールバック
            return ParsedResponse(
                response_type=ResponseType.ERROR,
                original_text=response_text,
                summary="解析エラーが発生しました",
                errors=[str(e)],
                parsing_timestamp=datetime.now()
            )
    
    def _detect_response_type(self, text: str) -> ResponseType:
        """レスポンスタイプを検出"""
        try:
            text_lower = text.lower()
            
            # コードブロックの存在チェック
            if self.code_block_pattern.search(text):
                # レビュー関連キーワードをチェック
                review_keywords = ['レビュー', 'review', '問題', '改善', '提案', '評価']
                if any(keyword in text_lower for keyword in review_keywords):
                    return ResponseType.REVIEW
                
                # デバッグ関連キーワードをチェック
                debug_keywords = ['エラー', 'error', 'バグ', 'bug', 'デバッグ', 'debug', '修正']
                if any(keyword in text_lower for keyword in debug_keywords):
                    return ResponseType.DEBUG
                
                return ResponseType.CODE
            
            # 説明関連キーワードをチェック
            explanation_keywords = ['説明', '解説', 'について', 'とは', '仕組み', '動作']
            if any(keyword in text_lower for keyword in explanation_keywords):
                return ResponseType.EXPLANATION
            
            # ドキュメント関連キーワードをチェック
            doc_keywords = ['ドキュメント', 'document', 'api', 'リファレンス', '使用方法']
            if any(keyword in text_lower for keyword in doc_keywords):
                return ResponseType.DOCUMENTATION
            
            return ResponseType.GENERAL
            
        except Exception as e:
            self.logger.error(f"レスポンスタイプ検出エラー: {e}")
            return ResponseType.GENERAL
    
    def _extract_summary(self, text: str) -> str:
        """要約を抽出"""
        try:
            # 最初の段落または最初の文を要約として使用
            paragraphs = text.split('\n\n')
            if paragraphs:
                first_paragraph = paragraphs[0].strip()
                # コードブロックでない場合は要約として使用
                if not first_paragraph.startswith('```'):
                    return first_paragraph[:200] + ('...' if len(first_paragraph) > 200 else '')
            
            # フォールバック: 最初の100文字
            return text[:100] + ('...' if len(text) > 100 else '')
            
        except Exception as e:
            self.logger.error(f"要約抽出エラー: {e}")
            return "要約を抽出できませんでした"
    
    def _extract_code_blocks(self, text: str) -> List[CodeBlock]:
        """コードブロックを抽出"""
        try:
            code_blocks = []
            
            # マークダウン形式のコードブロックを検索
            matches = self.code_block_pattern.findall(text)
            
            for i, (lang_hint, code_content) in enumerate(matches):
                # 言語を検出
                language = self._detect_language(code_content, lang_hint)
                
                # 構文チェック
                has_syntax_error = self._check_syntax_error(code_content, language)
                
                # コードブロックを作成
                code_block = CodeBlock(
                    language=language,
                    code=code_content.strip(),
                    has_syntax_error=has_syntax_error,
                    is_complete=self._is_code_complete(code_content, language),
                    metadata={'block_index': i}
                )
                
                code_blocks.append(code_block)
            
            return code_blocks
            
        except Exception as e:
            self.logger.error(f"コードブロック抽出エラー: {e}")
            return []
    
    def _detect_language(self, code: str, lang_hint: Optional[str] = None) -> CodeLanguage:
        """コード言語を検出"""
        try:
            # ヒントがある場合は優先
            if lang_hint:
                lang_hint_lower = lang_hint.lower()
                for lang in CodeLanguage:
                    if lang.value == lang_hint_lower:
                        return lang
            
            # パターンマッチングで検出
            for language, patterns in self.language_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, code, re.IGNORECASE):
                        return language
            
            # 拡張子ベースの推測
            if lang_hint:
                if lang_hint in ['py', 'python']:
                    return CodeLanguage.PYTHON
                elif lang_hint in ['js', 'javascript']:
                    return CodeLanguage.JAVASCRIPT
                elif lang_hint in ['ts', 'typescript']:
                    return CodeLanguage.TYPESCRIPT
                elif lang_hint in ['java']:
                    return CodeLanguage.JAVA
                elif lang_hint in ['cs', 'csharp']:
                    return CodeLanguage.CSHARP
                elif lang_hint in ['cpp', 'c++']:
                    return CodeLanguage.CPP
                elif lang_hint in ['c']:
                    return CodeLanguage.C
                elif lang_hint in ['go']:
                    return CodeLanguage.GO
                elif lang_hint in ['rs', 'rust']:
                    return CodeLanguage.RUST
                elif lang_hint in ['html']:
                    return CodeLanguage.HTML
                elif lang_hint in ['css']:
                    return CodeLanguage.CSS
                elif lang_hint in ['sql']:
                    return CodeLanguage.SQL
                elif lang_hint in ['bash', 'sh']:
                    return CodeLanguage.BASH
                elif lang_hint in ['ps1', 'powershell']:
                    return CodeLanguage.POWERSHELL
                elif lang_hint in ['json']:
                    return CodeLanguage.JSON
                elif lang_hint in ['xml']:
                    return CodeLanguage.XML
                elif lang_hint in ['yaml', 'yml']:
                    return CodeLanguage.YAML
                elif lang_hint in ['md', 'markdown']:
                    return CodeLanguage.MARKDOWN
            
            return CodeLanguage.UNKNOWN
            
        except Exception as e:
            self.logger.error(f"言語検出エラー: {e}")
            return CodeLanguage.UNKNOWN
    
    def _check_syntax_error(self, code: str, language: CodeLanguage) -> bool:
        """構文エラーをチェック"""
        try:
            if language == CodeLanguage.PYTHON:
                try:
                    ast.parse(code)
                    return False
                except SyntaxError:
                    return True
            elif language == CodeLanguage.JSON:
                try:
                    json.loads(code)
                    return False
                except json.JSONDecodeError:
                    return True
            elif language == CodeLanguage.XML:
                try:
                    ET.fromstring(code)
                    return False
                except ET.ParseError:
                    return True
            
            # その他の言語は基本的なチェックのみ
            return False
            
        except Exception as e:
            self.logger.error(f"構文チェックエラー: {e}")
            return False
    
    def _is_code_complete(self, code: str, language: CodeLanguage) -> bool:
        """コードが完全かチェック"""
        try:
            code = code.strip()
            
            if language == CodeLanguage.PYTHON:
                # インデントレベルをチェック
                lines = code.split('\n')
                if lines and lines[-1].strip().endswith(':'):
                    return False
                
                # 括弧の対応をチェック
                open_brackets = code.count('(') + code.count('[') + code.count('{')
                close_brackets = code.count(')') + code.count(']') + code.count('}')
                return open_brackets == close_brackets
            
            elif language in [CodeLanguage.JAVASCRIPT, CodeLanguage.JAVA, CodeLanguage.CSHARP]:
                # 括弧の対応をチェック
                open_brackets = code.count('{')
                close_brackets = code.count('}')
                return open_brackets == close_brackets
            
            # デフォルトは完全とみなす
            return True
            
        except Exception as e:
            self.logger.error(f"完全性チェックエラー: {e}")
            return True
    
    def _parse_code_response(self, text: str, parsed: ParsedResponse):
        """コードレスポンスを解析"""
        try:
            # 説明部分を抽出
            explanations = []
            
            # コードブロック以外の部分を説明として抽出
            text_without_code = self.code_block_pattern.sub('', text)
            paragraphs = [p.strip() for p in text_without_code.split('\n\n') if p.strip()]
            
            for paragraph in paragraphs:
                if len(paragraph) > 10:  # 短すぎる段落は除外
                    explanations.append(paragraph)
            
            parsed.explanations = explanations
            
            # 提案を抽出
            suggestions = self._extract_suggestions(text)
            parsed.suggestions = suggestions
            
        except Exception as e:
            self.logger.error(f"コードレスポンス解析エラー: {e}")
    
    def _parse_review_response(self, text: str, parsed: ParsedResponse):
        """レビューレスポンスを解析"""
        try:
            review_items = []
            
            # レビュー項目を抽出
            sections = re.split(r'\n(?=\d+\.|\*\s|\-\s)', text)
            
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                
                # 重要度を判定
                severity = self._determine_severity(section)
                
                # カテゴリを判定
                category = self._determine_category(section)
                
                # タイトルと説明を分離
                lines = section.split('\n')
                title = lines[0] if lines else section[:50]
                description = '\n'.join(lines[1:]) if len(lines) > 1 else section
                
                # 行番号を抽出
                line_number = self._extract_line_number(section)
                
                # 提案を抽出
                suggestion = self._extract_suggestion_from_section(section)
                
                review_item = ReviewItem(
                    category=category,
                    severity=severity,
                    line_number=line_number,
                    title=title,
                    description=description,
                    suggestion=suggestion
                )
                
                review_items.append(review_item)
            
            parsed.review_items = review_items
            
        except Exception as e:
            self.logger.error(f"レビューレスポンス解析エラー: {e}")
    
    def _parse_debug_response(self, text: str, parsed: ParsedResponse):
        """デバッグレスポンスを解析"""
        try:
            # エラー情報を抽出
            errors = []
            
            # エラーパターンを検索
            error_patterns = [
                r'エラー[:：]\s*(.+)',
                r'Error[:：]\s*(.+)',
                r'Exception[:：]\s*(.+)',
                r'問題[:：]\s*(.+)'
            ]
            
            for pattern in error_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                errors.extend(matches)
            
            parsed.errors = errors
            
            # 解決策を抽出
            suggestions = self._extract_debug_suggestions(text)
            parsed.suggestions = suggestions
            
            # 説明を抽出
            explanations = self._extract_debug_explanations(text)
            parsed.explanations = explanations
            
        except Exception as e:
            self.logger.error(f"デバッグレスポンス解析エラー: {e}")
    
    def _parse_explanation_response(self, text: str, parsed: ParsedResponse):
        """説明レスポンスを解析"""
        try:
            # 段落ごとに説明を分割
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            explanations = []
            for paragraph in paragraphs:
                # コードブロックでない段落を説明として追加
                if not paragraph.startswith('```') and len(paragraph) > 20:
                    explanations.append(paragraph)
            
            parsed.explanations = explanations
            
        except Exception as e:
            self.logger.error(f"説明レスポンス解析エラー: {e}")
    
    def _parse_documentation_response(self, text: str, parsed: ParsedResponse):
        """ドキュメントレスポンスを解析"""
        try:
            # マークダウン形式の解析
            if '##' in text or '###' in text:
                # セクション別に分割
                sections = re.split(r'\n#+\s', text)
                explanations = [section.strip() for section in sections if section.strip()]
                parsed.explanations = explanations
            else:
                # 通常の段落分割
                self._parse_explanation_response(text, parsed)
            
        except Exception as e:
            self.logger.error(f"ドキュメントレスポンス解析エラー: {e}")
    
    def _parse_general_response(self, text: str, parsed: ParsedResponse):
        """一般レスポンスを解析"""
        try:
            # 基本的な段落分割
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            parsed.explanations = paragraphs
            
            # 提案があれば抽出
            suggestions = self._extract_suggestions(text)
            parsed.suggestions = suggestions
            
        except Exception as e:
            self.logger.error(f"一般レスポンス解析エラー: {e}")
    
    def _determine_severity(self, text: str) -> str:
        """重要度を判定"""
        try:
            text_lower = text.lower()
            
            for severity, patterns in self.review_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text_lower):
                        return severity
            
            return 'info'
            
        except Exception as e:
            self.logger.error(f"重要度判定エラー: {e}")
            return 'info'
    
    def _determine_category(self, text: str) -> str:
        """カテゴリを判定"""
        try:
            text_lower = text.lower()
            
            categories = {
                'security': ['セキュリティ', 'security', '脆弱性', 'vulnerability'],
                'performance': ['パフォーマンス', 'performance', '性能', '速度'],
                'quality': ['品質', 'quality', '可読性', 'readability'],
                'bug': ['バグ', 'bug', 'エラー', 'error'],
                'style': ['スタイル', 'style', '書式', 'format']
            }
            
            for category, keywords in categories.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        return category
            
            return 'general'
            
        except Exception as e:
            self.logger.error(f"カテゴリ判定エラー: {e}")
            return 'general'
    
    def _extract_line_number(self, text: str) -> Optional[int]:
        """行番号を抽出"""
        try:
            # 行番号パターンを検索
            patterns = [
                r'行\s*(\d+)',
                r'line\s*(\d+)',
                r'L(\d+)',
                r'(\d+)行目'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            return None
            
        except Exception as e:
            self.logger.error(f"行番号抽出エラー: {e}")
            return None
    
    def _extract_suggestions(self, text: str) -> List[str]:
        """提案を抽出"""
        try:
            suggestions = []
            
            # 提案パターンを検索
            suggestion_patterns = [
                r'提案[:：]\s*(.+)',
                r'推奨[:：]\s*(.+)',
                r'改善[:：]\s*(.+)',
                r'suggestion[:：]\s*(.+)',
                r'recommend[:：]\s*(.+)'
            ]
            
            for pattern in suggestion_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                suggestions.extend(matches)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"提案抽出エラー: {e}")
            return []
    
    def _extract_suggestion_from_section(self, section: str) -> Optional[str]:
        """セクションから提案を抽出"""
        try:
            lines = section.split('\n')
            for line in lines:
                if any(keyword in line.lower() for keyword in ['提案', '推奨', '改善', 'suggestion']):
                    return line.strip()
            return None
            
        except Exception as e:
            self.logger.error(f"セクション提案抽出エラー: {e}")
            return None
    
    def _extract_debug_suggestions(self, text: str) -> List[str]:
        """デバッグ提案を抽出"""
        try:
            suggestions = []
            
            # デバッグ特有の提案パターン
            debug_patterns = [
                r'解決策[:：]\s*(.+)',
                r'修正方法[:：]\s*(.+)',
                r'対処法[:：]\s*(.+)',
                r'solution[:：]\s*(.+)',
                r'fix[:：]\s*(.+)'
            ]
            
            for pattern in debug_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                suggestions.extend(matches)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"デバッグ提案抽出エラー: {e}")
            return []
    
    def _extract_debug_explanations(self, text: str) -> List[str]:
        """デバッグ説明を抽出"""
        try:
            explanations = []
            
            # 原因説明パターン
            cause_patterns = [
                r'原因[:：]\s*(.+)',
                r'理由[:：]\s*(.+)',
                r'cause[:：]\s*(.+)',
                r'reason[:：]\s*(.+)'
            ]
            
            for pattern in cause_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                explanations.extend(matches)
            
            return explanations
            
        except Exception as e:
            self.logger.error(f"デバッグ説明抽出エラー: {e}")
            return []
    
    def _calculate_confidence_score(self, parsed: ParsedResponse) -> float:
        """信頼度スコアを計算"""
        try:
            score = 0.0
            
            # 基本スコア
            score += 0.3
            
            # コードブロックがある場合
            if parsed.code_blocks:
                score += 0.3
                
                # 構文エラーがない場合
                if not any(block.has_syntax_error for block in parsed.code_blocks):
                    score += 0.2
            
            # 説明がある場合
            if parsed.explanations:
                score += 0.1
            
            # 提案がある場合
            if parsed.suggestions:
                score += 0.1
            
            # レビュー項目がある場合（レビューレスポンスの場合）
            if parsed.review_items and parsed.response_type == ResponseType.REVIEW:
                score += 0.2
            
            # エラーがある場合はスコアを下げる
            if parsed.errors:
                score -= 0.2
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            self.logger.error(f"信頼度スコア計算エラー: {e}")
            return 0.5
    
    def extract_code_from_response(self, response_text: str) -> List[str]:
        """
        レスポンスからコードのみを抽出（便利メソッド）
        
        Args:
            response_text: レスポンステキスト
            
        Returns:
            List[str]: コード一覧
        """
        try:
            parsed = self.parse_response(response_text)
            return [block.code for block in parsed.code_blocks]
            
        except Exception as e:
            self.logger.error(f"コード抽出エラー: {e}")
            return []
    
    def format_parsed_response(self, parsed: ParsedResponse, format_type: str = "markdown") -> str:
        """
        解析済みレスポンスをフォーマット
        
        Args:
            parsed: 解析済みレスポンス
            format_type: フォーマットタイプ（markdown, html, text）
            
        Returns:
            str: フォーマット済みテキスト
        """
        try:
            if format_type == "markdown":
                return self._format_as_markdown(parsed)
            elif format_type == "html":
                return self._format_as_html(parsed)
            else:
                return self._format_as_text(parsed)
                
        except Exception as e:
            self.logger.error(f"レスポンスフォーマットエラー: {e}")
            return parsed.original_text
    
    def _format_as_markdown(self, parsed: ParsedResponse) -> str:
        """マークダウン形式でフォーマット"""
        try:
            lines = []
            
            # タイトル
            lines.append(f"# {parsed.response_type.value.title()} Response")
            lines.append("")
            
            # 要約
            if parsed.summary:
                lines.append("## 要約")
                lines.append(parsed.summary)
                lines.append("")
            
            # エラー
            if parsed.errors:
                lines.append("## エラー")
                for error in parsed.errors:
                    lines.append(f"- {error}")
                lines.append("")
            
            # コードブロック
            if parsed.code_blocks:
                lines.append("## コード")
                for i, block in enumerate(parsed.code_blocks):
                    lines.append(f"### コードブロック {i+1}")
                    if block.filename:
                        lines.append(f"**ファイル名**: {block.filename}")
                    if block.description:
                        lines.append(f"**説明**: {block.description}")
                    lines.append(f"**言語**: {block.language.value}")
                    lines.append(f"**完全性**: {'完全' if block.is_complete else '不完全'}")
                    if block.has_syntax_error:
                        lines.append("**⚠️ 構文エラーあり**")
                    lines.append("")
                    lines.append(f"```{block.language.value}")
                    lines.append(block.code)
                    lines.append("```")
                    lines.append("")
            
            # レビュー項目
            if parsed.review_items:
                lines.append("## レビュー項目")
                for item in parsed.review_items:
                    severity_icon = {
                        'critical': '🔴',
                        'major': '🟡',
                        'minor': '🟢',
                        'info': 'ℹ️'
                    }.get(item.severity, '⚪')
                    
                    lines.append(f"### {severity_icon} {item.title}")
                    lines.append(f"**カテゴリ**: {item.category}")
                    lines.append(f"**重要度**: {item.severity}")
                    if item.line_number:
                        lines.append(f"**行番号**: {item.line_number}")
                    lines.append("")
                    lines.append(item.description)
                    if item.suggestion:
                        lines.append("")
                        lines.append(f"**提案**: {item.suggestion}")
                    if item.example_code:
                        lines.append("")
                        lines.append("**修正例**:")
                        lines.append("```")
                        lines.append(item.example_code)
                        lines.append("```")
                    lines.append("")
            
            # 説明
            if parsed.explanations:
                lines.append("## 説明")
                for explanation in parsed.explanations:
                    lines.append(explanation)
                    lines.append("")
            
            # 提案
            if parsed.suggestions:
                lines.append("## 提案")
                for suggestion in parsed.suggestions:
                    lines.append(f"- {suggestion}")
                lines.append("")
            
            # メタデータ
            if parsed.metadata:
                lines.append("## メタデータ")
                for key, value in parsed.metadata.items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
            
            # 信頼度スコア
            lines.append(f"## 信頼度スコア")
            lines.append(f"{parsed.confidence_score:.2f} / 1.00")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"マークダウンフォーマットエラー: {e}")
            return parsed.original_text
    
    def _format_as_html(self, parsed: ParsedResponse) -> str:
        """HTML形式でフォーマット"""
        try:
            # マークダウンを生成してHTMLに変換
            markdown_text = self._format_as_markdown(parsed)
            html = markdown.markdown(markdown_text, extensions=['codehilite', 'tables'])
            
            # CSSスタイルを追加
            styled_html = f"""
            <div class="parsed-response">
                <style>
                    .parsed-response {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .parsed-response h1 {{
                        color: #2c3e50;
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 10px;
                    }}
                    .parsed-response h2 {{
                        color: #34495e;
                        margin-top: 30px;
                        margin-bottom: 15px;
                    }}
                    .parsed-response h3 {{
                        color: #7f8c8d;
                        margin-top: 20px;
                        margin-bottom: 10px;
                    }}
                    .parsed-response code {{
                        background-color: #f8f9fa;
                        padding: 2px 4px;
                        border-radius: 3px;
                        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    }}
                    .parsed-response pre {{
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 5px;
                        overflow-x: auto;
                        border-left: 4px solid #3498db;
                    }}
                    .parsed-response ul {{
                        padding-left: 20px;
                    }}
                    .parsed-response li {{
                        margin-bottom: 5px;
                    }}
                </style>
                {html}
            </div>
            """
            
            return styled_html
            
        except Exception as e:
            self.logger.error(f"HTMLフォーマットエラー: {e}")
            return f"<pre>{parsed.original_text}</pre>"
    
    def _format_as_text(self, parsed: ParsedResponse) -> str:
        """テキスト形式でフォーマット"""
        try:
            lines = []
            
            # タイトル
            title = f"{parsed.response_type.value.upper()} RESPONSE"
            lines.append(title)
            lines.append("=" * len(title))
            lines.append("")
            
            # 要約
            if parsed.summary:
                lines.append("要約:")
                lines.append("-" * 10)
                lines.append(parsed.summary)
                lines.append("")
            
            # エラー
            if parsed.errors:
                lines.append("エラー:")
                lines.append("-" * 10)
                for error in parsed.errors:
                    lines.append(f"• {error}")
                lines.append("")
            
            # コードブロック
            if parsed.code_blocks:
                lines.append("コード:")
                lines.append("-" * 10)
                for i, block in enumerate(parsed.code_blocks):
                    lines.append(f"[コードブロック {i+1}]")
                    if block.filename:
                        lines.append(f"ファイル名: {block.filename}")
                    if block.description:
                        lines.append(f"説明: {block.description}")
                    lines.append(f"言語: {block.language.value}")
                    lines.append(f"完全性: {'完全' if block.is_complete else '不完全'}")
                    if block.has_syntax_error:
                        lines.append("⚠️ 構文エラーあり")
                    lines.append("")
                    lines.append(block.code)
                    lines.append("")
            
            # レビュー項目
            if parsed.review_items:
                lines.append("レビュー項目:")
                lines.append("-" * 15)
                for item in parsed.review_items:
                    severity_mark = {
                        'critical': '[重大]',
                        'major': '[重要]',
                        'minor': '[軽微]',
                        'info': '[情報]'
                    }.get(item.severity, '[一般]')
                    
                    lines.append(f"{severity_mark} {item.title}")
                    lines.append(f"カテゴリ: {item.category}")
                    if item.line_number:
                        lines.append(f"行番号: {item.line_number}")
                    lines.append("")
                    lines.append(item.description)
                    if item.suggestion:
                        lines.append(f"提案: {item.suggestion}")
                    if item.example_code:
                        lines.append("修正例:")
                        lines.append(item.example_code)
                    lines.append("")
            
            # 説明
            if parsed.explanations:
                lines.append("説明:")
                lines.append("-" * 10)
                for explanation in parsed.explanations:
                    lines.append(explanation)
                    lines.append("")
            
            # 提案
            if parsed.suggestions:
                lines.append("提案:")
                lines.append("-" * 10)
                for suggestion in parsed.suggestions:
                    lines.append(f"• {suggestion}")
                lines.append("")
            
            # 信頼度スコア
            lines.append(f"信頼度スコア: {parsed.confidence_score:.2f} / 1.00")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"テキストフォーマットエラー: {e}")
            return parsed.original_text
    
    def validate_parsed_response(self, parsed: ParsedResponse) -> Dict[str, Any]:
        """
        解析済みレスポンスを検証
        
        Args:
            parsed: 解析済みレスポンス
            
        Returns:
            Dict[str, Any]: 検証結果
        """
        try:
            result = {
                'valid': True,
                'warnings': [],
                'errors': [],
                'suggestions': []
            }
            
            # 基本検証
            if not parsed.summary:
                result['warnings'].append("要約が設定されていません")
            
            if parsed.confidence_score < 0.3:
                result['warnings'].append("信頼度スコアが低いです")
            
            # レスポンスタイプ別検証
            if parsed.response_type == ResponseType.CODE:
                if not parsed.code_blocks:
                    result['errors'].append("コードレスポンスにコードブロックがありません")
                    result['valid'] = False
                else:
                    # 構文エラーチェック
                    error_blocks = [b for b in parsed.code_blocks if b.has_syntax_error]
                    if error_blocks:
                        result['warnings'].append(f"{len(error_blocks)}個のコードブロックに構文エラーがあります")
            
            elif parsed.response_type == ResponseType.REVIEW:
                if not parsed.review_items:
                    result['warnings'].append("レビューレスポンスにレビュー項目がありません")
            
            elif parsed.response_type == ResponseType.DEBUG:
                if not parsed.suggestions and not parsed.explanations:
                    result['warnings'].append("デバッグレスポンスに解決策や説明がありません")
            
            # 品質チェック
            if len(parsed.original_text) < 50:
                result['warnings'].append("レスポンスが短すぎます")
            
            if not parsed.explanations and not parsed.code_blocks and not parsed.review_items:
                result['warnings'].append("有用な情報が不足している可能性があります")
            
            return result
            
        except Exception as e:
            self.logger.error(f"レスポンス検証エラー: {e}")
            return {
                'valid': False,
                'warnings': [],
                'errors': [str(e)],
                'suggestions': []
            }
    
    def merge_parsed_responses(self, responses: List[ParsedResponse]) -> ParsedResponse:
        """
        複数の解析済みレスポンスをマージ
        
        Args:
            responses: 解析済みレスポンス一覧
            
        Returns:
            ParsedResponse: マージされたレスポンス
        """
        try:
            if not responses:
                raise ValueError("レスポンスが空です")
            
            if len(responses) == 1:
                return responses[0]
            
            # 最初のレスポンスをベースにマージ
            merged = ParsedResponse(
                response_type=ResponseType.MIXED,
                original_text="\n\n".join(r.original_text for r in responses),
                summary=responses[0].summary,
                parsing_timestamp=datetime.now()
            )
            
            # 各要素をマージ
            for response in responses:
                merged.code_blocks.extend(response.code_blocks)
                merged.review_items.extend(response.review_items)
                merged.explanations.extend(response.explanations)
                merged.suggestions.extend(response.suggestions)
                merged.errors.extend(response.errors)
                merged.metadata.update(response.metadata)
            
            # 重複を除去
            merged.explanations = list(dict.fromkeys(merged.explanations))
            merged.suggestions = list(dict.fromkeys(merged.suggestions))
            merged.errors = list(dict.fromkeys(merged.errors))
            
            # 信頼度スコアを再計算
            merged.confidence_score = self._calculate_confidence_score(merged)
            
            return merged
            
        except Exception as e:
            self.logger.error(f"レスポンスマージエラー: {e}")
            # エラー時は最初のレスポンスを返す
            return responses[0] if responses else ParsedResponse(
                response_type=ResponseType.ERROR,
                original_text="",
                summary="マージエラー",
                errors=[str(e)],
                parsing_timestamp=datetime.now()
            )

# グローバルパーサーインスタンス
_parser_instance: Optional[ResponseParser] = None

def get_response_parser() -> ResponseParser:
    """
    レスポンスパーサーのシングルトンインスタンスを取得
    
    Returns:
        ResponseParser: パーサーインスタンス
    """
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = ResponseParser()
    return _parser_instance

def parse_llm_response(response_text: str, 
                      expected_type: Optional[ResponseType] = None) -> ParsedResponse:
    """
    LLMレスポンスを解析（便利関数）
    
    Args:
        response_text: レスポンステキスト
        expected_type: 期待するレスポンスタイプ
        
    Returns:
        ParsedResponse: 解析済みレスポンス
    """
    parser = get_response_parser()
    return parser.parse_response(response_text, expected_type)

def extract_code_blocks(response_text: str) -> List[CodeBlock]:
    """
    レスポンスからコードブロックを抽出（便利関数）
    
    Args:
        response_text: レスポンステキスト
        
    Returns:
        List[CodeBlock]: コードブロック一覧
    """
    parser = get_response_parser()
    parsed = parser.parse_response(response_text)
    return parsed.code_blocks

def format_response(response_text: str, 
                   format_type: str = "markdown",
                   expected_type: Optional[ResponseType] = None) -> str:
    """
    レスポンスをフォーマット（便利関数）
    
    Args:
        response_text: レスポンステキスト
        format_type: フォーマットタイプ
        expected_type: 期待するレスポンスタイプ
        
    Returns:
        str: フォーマット済みテキスト
    """
    parser = get_response_parser()
    parsed = parser.parse_response(response_text, expected_type)
    return parser.format_parsed_response(parsed, format_type)


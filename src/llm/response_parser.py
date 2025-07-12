# src/llm/response_parser.py
"""
LLMレスポンス解析モジュール
LLMからのレスポンスを解析し、構造化されたデータに変換する
"""

import re
import json
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
import markdown
from bs4 import BeautifulSoup

from ..core.logger import get_logger

logger = get_logger(__name__)

class ResponseType(Enum):
    """レスポンスタイプの定義"""
    TEXT = "text"
    CODE = "code"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    REVIEW = "review"
    DEBUG = "debug"
    DOCUMENTATION = "documentation"
    EXPLANATION = "explanation"

@dataclass
class ParsedResponse:
    """解析されたレスポンスデータ"""
    response_type: ResponseType
    content: str
    metadata: Dict[str, Any]
    code_blocks: List[Dict[str, str]]
    structured_data: Optional[Dict[str, Any]] = None
    confidence: float = 1.0

@dataclass
class CodeBlock:
    """コードブロック情報"""
    language: str
    code: str
    line_start: int
    line_end: int
    description: Optional[str] = None

class ResponseParser:
    """レスポンス解析クラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = get_logger(self.__class__.__name__)
        
        # コードブロック検出パターン
        self.code_block_pattern = re.compile(
            r'```(\w+)?\n(.*?)\n```',
            re.DOTALL | re.MULTILINE
        )
        
        # インラインコード検出パターン
        self.inline_code_pattern = re.compile(r'`([^`]+)`')
        
        # JSON検出パターン
        self.json_pattern = re.compile(
            r'\{.*?\}|\[.*?\]',
            re.DOTALL
        )
        
        # マークダウンヘッダー検出パターン
        self.header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        
        # リスト検出パターン
        self.list_pattern = re.compile(r'^[\s]*[-*+]\s+(.+)$', re.MULTILINE)
        
        self.logger.info("ResponseParser を初期化しました")
    
    def parse_response(self, content: str, expected_type: Optional[ResponseType] = None) -> ParsedResponse:
        """
        レスポンスを解析
        
        Args:
            content: 解析するコンテンツ
            expected_type: 期待するレスポンスタイプ
            
        Returns:
            ParsedResponse: 解析結果
        """
        try:
            # コンテンツの基本情報を取得
            metadata = self._extract_metadata(content)
            
            # コードブロックを抽出
            code_blocks = self._extract_code_blocks(content)
            
            # レスポンスタイプを判定
            response_type = self._detect_response_type(content, expected_type)
            
            # 構造化データを抽出
            structured_data = self._extract_structured_data(content, response_type)
            
            # 信頼度を計算
            confidence = self._calculate_confidence(content, response_type, expected_type)
            
            parsed_response = ParsedResponse(
                response_type=response_type,
                content=content,
                metadata=metadata,
                code_blocks=code_blocks,
                structured_data=structured_data,
                confidence=confidence
            )
            
            self.logger.debug(f"レスポンスを解析しました: タイプ={response_type.value}, コードブロック数={len(code_blocks)}")
            return parsed_response
            
        except Exception as e:
            self.logger.error(f"レスポンス解析エラー: {e}")
            # エラー時はテキストタイプとして返す
            return ParsedResponse(
                response_type=ResponseType.TEXT,
                content=content,
                metadata={},
                code_blocks=[],
                confidence=0.0
            )
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """コンテンツからメタデータを抽出"""
        try:
            metadata = {
                'length': len(content),
                'lines': len(content.split('\n')),
                'words': len(content.split()),
                'has_code': bool(self.code_block_pattern.search(content)),
                'has_json': bool(self.json_pattern.search(content)),
                'has_markdown': bool(self.header_pattern.search(content)),
                'language_hints': self._detect_languages(content)
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"メタデータ抽出エラー: {e}")
            return {}
    
    def _extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """コードブロックを抽出"""
        try:
            code_blocks = []
            
            # マークダウン形式のコードブロック
            for match in self.code_block_pattern.finditer(content):
                language = match.group(1) or 'text'
                code = match.group(2).strip()
                
                code_blocks.append({
                    'language': language,
                    'code': code,
                    'start_pos': match.start(),
                    'end_pos': match.end(),
                    'type': 'block'
                })
            
            # インラインコード
            for match in self.inline_code_pattern.finditer(content):
                code = match.group(1).strip()
                
                code_blocks.append({
                    'language': 'inline',
                    'code': code,
                    'start_pos': match.start(),
                    'end_pos': match.end(),
                    'type': 'inline'
                })
            
            return code_blocks
            
        except Exception as e:
            self.logger.error(f"コードブロック抽出エラー: {e}")
            return []
    
    def _detect_response_type(self, content: str, expected_type: Optional[ResponseType]) -> ResponseType:
        """レスポンスタイプを検出"""
        try:
            # 期待するタイプが指定されている場合は優先
            if expected_type:
                if self._validate_response_type(content, expected_type):
                    return expected_type
            
            # コンテンツの特徴から判定
            if self._is_code_response(content):
                return ResponseType.CODE
            elif self._is_json_response(content):
                return ResponseType.JSON
            elif self._is_markdown_response(content):
                return ResponseType.MARKDOWN
            elif self._is_review_response(content):
                return ResponseType.REVIEW
            elif self._is_debug_response(content):
                return ResponseType.DEBUG
            elif self._is_documentation_response(content):
                return ResponseType.DOCUMENTATION
            elif self._is_explanation_response(content):
                return ResponseType.EXPLANATION
            else:
                return ResponseType.TEXT
            
        except Exception as e:
            self.logger.error(f"レスポンスタイプ検出エラー: {e}")
            return ResponseType.TEXT
    
    def _validate_response_type(self, content: str, response_type: ResponseType) -> bool:
        """レスポンスタイプの妥当性を検証"""
        try:
            validation_map = {
                ResponseType.CODE: self._is_code_response,
                ResponseType.JSON: self._is_json_response,
                ResponseType.MARKDOWN: self._is_markdown_response,
                ResponseType.REVIEW: self._is_review_response,
                ResponseType.DEBUG: self._is_debug_response,
                ResponseType.DOCUMENTATION: self._is_documentation_response,
                ResponseType.EXPLANATION: self._is_explanation_response,
            }
            
            validator = validation_map.get(response_type)
            if validator:
                return validator(content)
            
            return True  # TEXT や HTML は常に有効
            
        except Exception as e:
            self.logger.error(f"レスポンスタイプ検証エラー: {e}")
            return False
    
    def _is_code_response(self, content: str) -> bool:
        """コードレスポンスかどうか判定"""
        code_indicators = [
            r'```\w+',  # コードブロック
            r'def\s+\w+\(',  # Python関数定義
            r'function\s+\w+\(',  # JavaScript関数定義
            r'class\s+\w+',  # クラス定義
            r'import\s+\w+',  # import文
            r'#include\s*<',  # C/C++ include
        ]
        
        code_count = sum(1 for pattern in code_indicators if re.search(pattern, content))
        return code_count >= 2 or len(self.code_block_pattern.findall(content)) > 0
    
    def _is_json_response(self, content: str) -> bool:
        """JSONレスポンスかどうか判定"""
        try:
            # JSON形式の文字列を検出
            json_matches = self.json_pattern.findall(content)
            if not json_matches:
                return False
            
            # 実際にJSONとしてパースできるか確認
            for match in json_matches:
                try:
                    json.loads(match)
                    return True
                except json.JSONDecodeError:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _is_markdown_response(self, content: str) -> bool:
        """Markdownレスポンスかどうか判定"""
        markdown_indicators = [
            r'^#{1,6}\s+',  # ヘッダー
            r'^\*\*.*\*\*',  # 太字
            r'^\*.*\*',  # 斜体
            r'^\s*[-*+]\s+',  # リスト
            r'^\s*\d+\.\s+',  # 番号付きリスト
            r'\[.*\]\(.*\)',  # リンク
        ]
        
        markdown_count = sum(1 for pattern in markdown_indicators 
                           if re.search(pattern, content, re.MULTILINE))
        return markdown_count >= 2
    
    def _is_review_response(self, content: str) -> bool:
        """レビューレスポンスかどうか判定"""
        review_keywords = [
            'レビュー', 'review', '改善', 'improvement', '問題', 'issue',
            '提案', 'suggestion', '修正', 'fix', 'バグ', 'bug',
            '推奨', 'recommend', '最適化', 'optimization'
        ]
        
        keyword_count = sum(1 for keyword in review_keywords 
                          if keyword.lower() in content.lower())
        return keyword_count >= 3
    
    def _is_debug_response(self, content: str) -> bool:
        """デバッグレスポンスかどうか判定"""
        debug_keywords = [
            'エラー', 'error', 'デバッグ', 'debug', '例外', 'exception',
            'トレースバック', 'traceback', '修正', 'fix', '解決', 'solve'
        ]
        
        keyword_count = sum(1 for keyword in debug_keywords 
                          if keyword.lower() in content.lower())
        return keyword_count >= 2
    
    def _is_documentation_response(self, content: str) -> bool:
        """ドキュメントレスポンスかどうか判定"""
        doc_keywords = [
            'ドキュメント', 'documentation', '説明', 'description',
            '使用方法', 'usage', 'API', 'パラメータ', 'parameter',
            '戻り値', 'return', '例', 'example'
        ]
        
        keyword_count = sum(1 for keyword in doc_keywords 
                          if keyword.lower() in content.lower())
        return keyword_count >= 3 and self._is_markdown_response(content)
    
    def _is_explanation_response(self, content: str) -> bool:
        """説明レスポンスかどうか判定"""
        explanation_keywords = [
            '説明', 'explanation', '解説', 'description', '理由', 'reason',
            'なぜ', 'why', 'どのように', 'how', '仕組み', 'mechanism'
        ]
        
        keyword_count = sum(1 for keyword in explanation_keywords 
                          if keyword.lower() in content.lower())
        return keyword_count >= 2
    
    def _detect_languages(self, content: str) -> List[str]:
        """コンテンツから使用言語を検出"""
        try:
            languages = []
            
            # コードブロックから言語を抽出
            for match in self.code_block_pattern.finditer(content):
                language = match.group(1)
                if language and language not in languages:
                    languages.append(language)
            
            # キーワードベースの言語検出
            language_patterns = {
                'python': [r'def\s+\w+\(', r'import\s+\w+', r'from\s+\w+\s+import'],
                'javascript': [r'function\s+\w+\(', r'const\s+\w+\s*=', r'let\s+\w+\s*='],
                'java': [r'public\s+class\s+\w+', r'public\s+static\s+void\s+main'],
                'cpp': [r'#include\s*<', r'int\s+main\s*\(', r'std::'],
                'sql': [r'SELECT\s+', r'FROM\s+', r'WHERE\s+', r'INSERT\s+INTO'],
                'html': [r'<html>', r'<div>', r'<p>', r'<script>'],
                'css': [r'\w+\s*\{', r'color\s*:', r'background\s*:']
            }
            
            for lang, patterns in language_patterns.items():
                if any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns):
                    if lang not in languages:
                        languages.append(lang)
            
            return languages
            
        except Exception as e:
            self.logger.error(f"言語検出エラー: {e}")
            return []
    
    def _extract_structured_data(self, content: str, response_type: ResponseType) -> Optional[Dict[str, Any]]:
        """構造化データを抽出"""
        try:
            if response_type == ResponseType.JSON:
                return self._extract_json_data(content)
            elif response_type == ResponseType.MARKDOWN:
                return self._extract_markdown_structure(content)
            elif response_type == ResponseType.CODE:
                return self._extract_code_structure(content)
            elif response_type == ResponseType.REVIEW:
                return self._extract_review_structure(content)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"構造化データ抽出エラー: {e}")
            return None
    
    def _extract_json_data(self, content: str) -> Optional[Dict[str, Any]]:
        """JSONデータを抽出"""
        try:
            json_matches = self.json_pattern.findall(content)
            
            for match in json_matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"JSONデータ抽出エラー: {e}")
            return None
    
    def _extract_markdown_structure(self, content: str) -> Dict[str, Any]:
        """Markdown構造を抽出"""
        try:
            structure = {
                'headers': [],
                'lists': [],
                'links': [],
                'code_blocks': []
            }
            
            # ヘッダーを抽出
            for match in self.header_pattern.finditer(content):
                level = len(match.group(1))
                title = match.group(2).strip()
                structure['headers'].append({'level': level, 'title': title})
            
            # リストを抽出
            for match in self.list_pattern.finditer(content):
                item = match.group(1).strip()
                structure['lists'].append(item)
            
            # リンクを抽出
            link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
            for match in link_pattern.finditer(content):
                text = match.group(1)
                url = match.group(2)
                structure['links'].append({'text': text, 'url': url})
            
            # コードブロックを抽出
            structure['code_blocks'] = self._extract_code_blocks(content)
            
            return structure
            
        except Exception as e:
            self.logger.error(f"Markdown構造抽出エラー: {e}")
            return {}
    
    def _extract_code_structure(self, content: str) -> Dict[str, Any]:
        """コード構造を抽出"""
        try:
            structure = {
                'functions': [],
                'classes': [],
                'imports': [],
                'variables': []
            }
            
            # 関数定義を抽出
            function_patterns = [
                r'def\s+(\w+)\s*\(',  # Python
                r'function\s+(\w+)\s*\(',  # JavaScript
                r'(\w+)\s*\([^)]*\)\s*\{'  # C/C++/Java
            ]
            
            for pattern in function_patterns:
                for match in re.finditer(pattern, content):
                    structure['functions'].append(match.group(1))
            
            # クラス定義を抽出
            class_patterns = [
                r'class\s+(\w+)',  # Python/JavaScript
                r'public\s+class\s+(\w+)'  # Java
            ]
            
            for pattern in class_patterns:
                for match in re.finditer(pattern, content):
                    structure['classes'].append(match.group(1))
            
            # import文を抽出
            import_patterns = [
                r'import\s+(\w+)',  # Python
                r'from\s+(\w+)\s+import',  # Python
                r'#include\s*<([^>]+)>'  # C/C++
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    structure['imports'].append(match.group(1))
            
            return structure
            
        except Exception as e:
            self.logger.error(f"コード構造抽出エラー: {e}")
            return {}
    
    def _extract_review_structure(self, content: str) -> Dict[str, Any]:
        """レビュー構造を抽出"""
        try:
            structure = {
                'issues': [],
                'suggestions': [],
                'positive_points': [],
                'severity_levels': []
            }
            
            # 問題点を抽出
            issue_keywords = ['問題', 'issue', 'バグ', 'bug', 'エラー', 'error']
            for keyword in issue_keywords:
                pattern = rf'.*{keyword}.*'
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    structure['issues'].append(match.group().strip())
            
            # 提案を抽出
            suggestion_keywords = ['提案', 'suggestion', '改善', 'improvement', '推奨', 'recommend']
            for keyword in suggestion_keywords:
                pattern = rf'.*{keyword}.*'
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    structure['suggestions'].append(match.group().strip())
            
            return structure
            
        except Exception as e:
            self.logger.error(f"レビュー構造抽出エラー: {e}")
            return {}
    
    def _calculate_confidence(self, content: str, detected_type: ResponseType, 
                            expected_type: Optional[ResponseType]) -> float:
        """信頼度を計算"""
        try:
            confidence = 0.5  # ベース信頼度
            
            # 期待するタイプと一致する場合
            if expected_type and detected_type == expected_type:
                confidence += 0.3
            
            # コンテンツの特徴に基づく信頼度調整
            if detected_type == ResponseType.CODE:
                code_blocks = len(self.code_block_pattern.findall(content))
                confidence += min(code_blocks * 0.1, 0.3)
            
            elif detected_type == ResponseType.JSON:
                try:
                    json_matches = self.json_pattern.findall(content)
                    valid_json_count = 0
                    for match in json_matches:
                        try:
                            json.loads(match)
                            valid_json_count += 1
                        except json.JSONDecodeError:
                            pass
                    confidence += min(valid_json_count * 0.2, 0.4)
                except:
                    confidence -= 0.2
            
            elif detected_type == ResponseType.MARKDOWN:
                markdown_features = len(self.header_pattern.findall(content))
                confidence += min(markdown_features * 0.05, 0.2)
            
            # 信頼度を0-1の範囲に制限
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            self.logger.error(f"信頼度計算エラー: {e}")
            return 0.5
    
    def format_parsed_response(self, parsed_response: ParsedResponse, 
                             format_type: str = "text") -> str:
        """
        解析されたレスポンスをフォーマット
        
        Args:
            parsed_response: 解析されたレスポンス
            format_type: フォーマットタイプ（text, html, markdown）
            
        Returns:
            str: フォーマットされたレスポンス
        """
        try:
            if format_type == "html":
                return self._format_as_html(parsed_response)
            elif format_type == "markdown":
                return self._format_as_markdown(parsed_response)
            else:
                return parsed_response.content
                
        except Exception as e:
            self.logger.error(f"レスポンスフォーマットエラー: {e}")
            return parsed_response.content
    
    def _format_as_html(self, parsed_response: ParsedResponse) -> str:
        """HTMLとしてフォーマット"""
        try:
            if parsed_response.response_type == ResponseType.MARKDOWN:
                return markdown.markdown(parsed_response.content)
            else:
                # プレーンテキストをHTMLに変換
                html_content = parsed_response.content.replace('\n', '<br>')
                return f"<div>{html_content}</div>"
                
        except Exception as e:
            self.logger.error(f"HTML フォーマットエラー: {e}")
            return parsed_response.content
    
    def _format_as_markdown(self, parsed_response: ParsedResponse) -> str:
        """Markdownとしてフォーマット"""
        try:
            if parsed_response.response_type == ResponseType.CODE:
                # コードブロックをMarkdown形式に変換
                formatted_content = parsed_response.content
                for code_block in parsed_response.code_blocks:
                    if code_block['type'] == 'block':
                        continue  # 既にMarkdown形式
                    
                # 追加のフォーマット処理
                return formatted_content
            else:
                return parsed_response.content
                
        except Exception as e:
            self.logger.error(f"Markdown フォーマットエラー: {e}")
            return parsed_response.content
    
    def extract_code_from_response(self, content: str) -> List[str]:
        """レスポンスからコードを抽出"""
        try:
            code_blocks = []
            
            # マークダウン形式のコードブロック
            for match in self.code_block_pattern.finditer(content):
                code = match.group(2).strip()
                if code:
                    code_blocks.append(code)
            
            return code_blocks
            
        except Exception as e:
            self.logger.error(f"コード抽出エラー: {e}")
            return []

# シングルトンインスタンス
_response_parser_instance = None

def get_response_parser() -> ResponseParser:
    """ResponseParser のシングルトンインスタンスを取得"""
    global _response_parser_instance
    if _response_parser_instance is None:
        _response_parser_instance = ResponseParser()
    return _response_parser_instance

def parse_llm_response(content: str, expected_type: Optional[ResponseType] = None) -> ParsedResponse:
    """
    LLMレスポンスを解析する便利関数
    
    Args:
        content: 解析するコンテンツ
        expected_type: 期待するレスポンスタイプ
        
    Returns:
        ParsedResponse: 解析結果
    """
    parser = get_response_parser()
    return parser.parse_response(content, expected_type)

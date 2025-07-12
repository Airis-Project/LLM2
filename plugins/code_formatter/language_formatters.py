#plugins/code_formatter/language_formatters.py
"""
各プログラミング言語用のフォーマッター実装
"""

import json
import re
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from xml.dom import minidom
import xml.etree.ElementTree as ET

from ...core.logger import get_logger


class BaseFormatter(ABC):
    """フォーマッターの基底クラス"""
    
    def __init__(self, name: str, settings: Dict[str, Any] = None):
        self.name = name
        self.settings = settings or {}
        self.logger = get_logger(f"formatter_{name.lower()}")
    
    @abstractmethod
    def format(self, content: str) -> Optional[str]:
        """コンテンツをフォーマット"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """フォーマッターが利用可能かチェック"""
        pass
    
    def update_settings(self, settings: Dict[str, Any]):
        """設定を更新"""
        self.settings.update(settings)
    
    def validate(self, content: str) -> Tuple[bool, List[str]]:
        """基本的な構文検証"""
        return True, []


class PythonFormatter(BaseFormatter):
    """Pythonコードフォーマッター"""
    
    def __init__(self, settings: Dict[str, Any] = None):
        super().__init__("Python", settings)
        self._black_available = None
        self._autopep8_available = None
        self._isort_available = None
    
    def is_available(self) -> bool:
        """フォーマッターが利用可能かチェック"""
        use_black = self.settings.get('use_black', True)
        use_autopep8 = self.settings.get('use_autopep8', False)
        
        if use_black:
            return self._check_black_available()
        elif use_autopep8:
            return self._check_autopep8_available()
        
        return True  # 基本的なフォーマットは常に利用可能
    
    def _check_black_available(self) -> bool:
        """blackが利用可能かチェック"""
        if self._black_available is None:
            try:
                import black
                self._black_available = True
            except ImportError:
                self._black_available = False
                self.logger.warning("blackがインストールされていません")
        return self._black_available
    
    def _check_autopep8_available(self) -> bool:
        """autopep8が利用可能かチェック"""
        if self._autopep8_available is None:
            try:
                import autopep8
                self._autopep8_available = True
            except ImportError:
                self._autopep8_available = False
                self.logger.warning("autopep8がインストールされていません")
        return self._autopep8_available
    
    def _check_isort_available(self) -> bool:
        """isortが利用可能かチェック"""
        if self._isort_available is None:
            try:
                import isort
                self._isort_available = True
            except ImportError:
                self._isort_available = False
                self.logger.warning("isortがインストールされていません")
        return self._isort_available
    
    def format(self, content: str) -> Optional[str]:
        """Pythonコードをフォーマット"""
        try:
            formatted_content = content
            
            # isortでimportを整理
            if self.settings.get('use_isort', True) and self._check_isort_available():
                formatted_content = self._format_with_isort(formatted_content)
            
            # blackまたはautopep8でフォーマット
            if self.settings.get('use_black', True) and self._check_black_available():
                formatted_content = self._format_with_black(formatted_content)
            elif self.settings.get('use_autopep8', False) and self._check_autopep8_available():
                formatted_content = self._format_with_autopep8(formatted_content)
            else:
                # 基本的なフォーマット
                formatted_content = self._basic_format(formatted_content)
            
            return formatted_content
            
        except Exception as e:
            self.logger.error(f"Pythonフォーマットエラー: {e}")
            return None
    
    def _format_with_black(self, content: str) -> str:
        """blackでフォーマット"""
        try:
            import black
            
            mode = black.FileMode(
                line_length=self.settings.get('line_length', 88),
                string_normalization=not self.settings.get('skip_string_normalization', False),
                target_versions=set(black.TargetVersion[v.upper()] for v in self.settings.get('target_version', ['PY311']))
            )
            
            return black.format_str(content, mode=mode)
            
        except Exception as e:
            self.logger.error(f"blackフォーマットエラー: {e}")
            return content
    
    def _format_with_autopep8(self, content: str) -> str:
        """autopep8でフォーマット"""
        try:
            import autopep8
            
            options = {
                'max_line_length': self.settings.get('line_length', 88),
                'aggressive': 1
            }
            
            return autopep8.fix_code(content, options=options)
            
        except Exception as e:
            self.logger.error(f"autopep8フォーマットエラー: {e}")
            return content
    
    def _format_with_isort(self, content: str) -> str:
        """isortでimportを整理"""
        try:
            import isort
            
            config = isort.Config(
                line_length=self.settings.get('line_length', 88),
                multi_line_output=3,
                include_trailing_comma=True,
                force_grid_wrap=0,
                use_parentheses=True,
                ensure_newline_before_comments=True
            )
            
            return isort.code(content, config=config)
            
        except Exception as e:
            self.logger.error(f"isortフォーマットエラー: {e}")
            return content
    
    def _basic_format(self, content: str) -> str:
        """基本的なPythonフォーマット"""
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                formatted_lines.append('')
                continue
            
            # インデントレベルを調整
            if stripped.startswith(('def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ')):
                formatted_lines.append('    ' * indent_level + stripped)
                if stripped.endswith(':'):
                    indent_level += 1
            elif stripped in ('else:', 'elif', 'except:', 'finally:'):
                indent_level = max(0, indent_level - 1)
                formatted_lines.append('    ' * indent_level + stripped)
                indent_level += 1
            else:
                formatted_lines.append('    ' * indent_level + stripped)
        
        return '\n'.join(formatted_lines)
    
    def validate(self, content: str) -> Tuple[bool, List[str]]:
        """Python構文検証"""
        try:
            compile(content, '<string>', 'exec')
            return True, []
        except SyntaxError as e:
            return False, [f"構文エラー (行 {e.lineno}): {e.msg}"]
        except Exception as e:
            return False, [f"検証エラー: {str(e)}"]


class JavaScriptFormatter(BaseFormatter):
    """JavaScript/TypeScriptフォーマッター"""
    
    def __init__(self, settings: Dict[str, Any] = None):
        super().__init__("JavaScript", settings)
        self._prettier_available = None
    
    def is_available(self) -> bool:
        """フォーマッターが利用可能かチェック"""
        return True  # 基本的なフォーマットは常に利用可能
    
    def _check_prettier_available(self) -> bool:
        """prettierが利用可能かチェック"""
        if self._prettier_available is None:
            try:
                result = subprocess.run(['prettier', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                self._prettier_available = result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self._prettier_available = False
                self.logger.warning("prettierがインストールされていません")
        return self._prettier_available
    
    def format(self, content: str) -> Optional[str]:
        """JavaScriptコードをフォーマット"""
        try:
            if self._check_prettier_available():
                return self._format_with_prettier(content)
            else:
                return self._basic_format(content)
                
        except Exception as e:
            self.logger.error(f"JavaScriptフォーマットエラー: {e}")
            return None
    
    def _format_with_prettier(self, content: str) -> str:
        """prettierでフォーマット"""
        try:
            prettier_config = {
                'tabWidth': self.settings.get('indent_size', 2),
                'semi': self.settings.get('use_semicolons', True),
                'singleQuote': self.settings.get('use_single_quotes', False),
                'trailingComma': self.settings.get('trailing_comma', 'es5'),
                'bracketSpacing': self.settings.get('bracket_spacing', True),
                'arrowParens': self.settings.get('arrow_parens', 'avoid')
            }
            
            # 一時的な設定ファイルを作成してprettierを実行
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(content)
                temp_file = f.name
            
            try:
                cmd = ['prettier', '--stdin-filepath', temp_file]
                for key, value in prettier_config.items():
                    if isinstance(value, bool):
                        if value:
                            cmd.append(f'--{key.replace("_", "-")}')
                    else:
                        cmd.extend([f'--{key.replace("_", "-")}', str(value)])
                
                result = subprocess.run(cmd, input=content, capture_output=True, 
                                      text=True, timeout=10)
                
                if result.returncode == 0:
                    return result.stdout
                else:
                    self.logger.error(f"prettier実行エラー: {result.stderr}")
                    return content
                    
            finally:
                Path(temp_file).unlink(missing_ok=True)
                
        except Exception as e:
            self.logger.error(f"prettierフォーマットエラー: {e}")
            return content
    
    def _basic_format(self, content: str) -> str:
        """基本的なJavaScriptフォーマット"""
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0
        indent_size = self.settings.get('indent_size', 2)
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                formatted_lines.append('')
                continue
            
            # 閉じ括弧の処理
            if stripped.startswith(('}', ']', ')')):
                indent_level = max(0, indent_level - 1)
            
            # インデント適用
            formatted_line = ' ' * (indent_level * indent_size) + stripped
            formatted_lines.append(formatted_line)
            
            # 開き括弧の処理
            if stripped.endswith(('{', '[', '(')):
                indent_level += 1
            
            # セミコロン追加
            if (self.settings.get('use_semicolons', True) and 
                not stripped.endswith((';', '{', '}', ',', '(', ')', '[', ']')) and
                not stripped.startswith(('if', 'for', 'while', 'function', 'class'))):
                if not formatted_lines[-1].endswith(';'):
                    formatted_lines[-1] += ';'
        
        return '\n'.join(formatted_lines)


class HTMLFormatter(BaseFormatter):
    """HTMLフォーマッター"""
    
    def __init__(self, settings: Dict[str, Any] = None):
        super().__init__("HTML", settings)
    
    def is_available(self) -> bool:
        """フォーマッターが利用可能かチェック"""
        return True
    
    def format(self, content: str) -> Optional[str]:
        """HTMLをフォーマット"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # フォーマット設定
            indent_size = self.settings.get('indent_size', 2)
            
            formatted = soup.prettify(indent=' ' * indent_size)
            
            return formatted
            
        except ImportError:
            # BeautifulSoupが利用できない場合は基本的なフォーマット
            return self._basic_format(content)
        except Exception as e:
            self.logger.error(f"HTMLフォーマットエラー: {e}")
            return None
    
    def _basic_format(self, content: str) -> str:
        """基本的なHTMLフォーマット"""
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0
        indent_size = self.settings.get('indent_size', 2)
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                formatted_lines.append('')
                continue
            
            # 閉じタグの処理
            if stripped.startswith('</'):
                indent_level = max(0, indent_level - 1)
            
            # インデント適用
            formatted_line = ' ' * (indent_level * indent_size) + stripped
            formatted_lines.append(formatted_line)
            
            # 開きタグの処理（自己完結タグを除く）
            if (stripped.startswith('<') and not stripped.startswith('</') and
                not stripped.endswith('/>') and not stripped.startswith('<!') and
                not any(tag in stripped for tag in ['<br', '<hr', '<img', '<input', '<meta', '<link'])):
                indent_level += 1
        
        return '\n'.join(formatted_lines)


class CSSFormatter(BaseFormatter):
    """CSSフォーマッター"""
    
    def __init__(self, settings: Dict[str, Any] = None):
        super().__init__("CSS", settings)
    
    def is_available(self) -> bool:
        """フォーマッターが利用可能かチェック"""
        return True
    
    def format(self, content: str) -> Optional[str]:
        """CSSをフォーマット"""
        try:
            return self._basic_format(content)
        except Exception as e:
            self.logger.error(f"CSSフォーマットエラー: {e}")
            return None
    
    def _basic_format(self, content: str) -> str:
        """基本的なCSSフォーマット"""
        # 基本的な整形
        content = re.sub(r'\s*{\s*', ' {\n', content)
        content = re.sub(r'\s*}\s*', '\n}\n\n', content)
        content = re.sub(r';\s*', ';\n', content)
        content = re.sub(r',\s*', ',\n', content)
        
        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0
        indent_size = self.settings.get('indent_size', 2)
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                if formatted_lines and formatted_lines[-1].strip():
                    formatted_lines.append('')
                continue
            
            if stripped == '}':
                indent_level = max(0, indent_level - 1)
                formatted_lines.append(' ' * (indent_level * indent_size) + stripped)
            elif stripped.endswith('{'):
                formatted_lines.append(' ' * (indent_level * indent_size) + stripped)
                indent_level += 1
            else:
                formatted_lines.append(' ' * (indent_level * indent_size) + stripped)
        
        return '\n'.join(formatted_lines)


class JSONFormatter(BaseFormatter):
    """JSONフォーマッター"""
    
    def __init__(self, settings: Dict[str, Any] = None):
        super().__init__("JSON", settings)
    
    def is_available(self) -> bool:
        """フォーマッターが利用可能かチェック"""
        return True
    
    def format(self, content: str) -> Optional[str]:
        """JSONをフォーマット"""
        try:
            # JSONをパース
            data = json.loads(content)
            
            # フォーマット設定
            indent = self.settings.get('indent_size', 2)
            sort_keys = self.settings.get('sort_keys', False)
            ensure_ascii = self.settings.get('ensure_ascii', False)
            separators = self.settings.get('separators', (',', ': '))
            
            # フォーマット済みJSONを生成
            formatted = json.dumps(
                data,
                indent=indent,
                sort_keys=sort_keys,
                ensure_ascii=ensure_ascii,
                separators=separators
            )
            
            return formatted
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON構文エラー: {e}")
            return None
        except Exception as e:
            self.logger.error(f"JSONフォーマットエラー: {e}")
            return None
    
    def validate(self, content: str) -> Tuple[bool, List[str]]:
        """JSON構文検証"""
        try:
            json.loads(content)
            return True, []
        except json.JSONDecodeError as e:
            return False, [f"JSON構文エラー (行 {e.lineno}, 列 {e.colno}): {e.msg}"]
        except Exception as e:
            return False, [f"検証エラー: {str(e)}"]


class XMLFormatter(BaseFormatter):
    """XMLフォーマッター"""
    
    def __init__(self, settings: Dict[str, Any] = None):
        super().__init__("XML", settings)
    
    def is_available(self) -> bool:
        """フォーマッターが利用可能かチェック"""
        return True
    
    def format(self, content: str) -> Optional[str]:
        """XMLをフォーマット"""
        try:
            # XMLをパース
            root = ET.fromstring(content)
            
            # フォーマット設定
            indent_size = self.settings.get('indent_size', 2)
            
            # インデントを適用
            self._indent_xml(root, 0, ' ' * indent_size)
            
            # XML宣言を追加
            xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
            formatted = xml_declaration + ET.tostring(root, encoding='unicode')
            
            return formatted
            
        except ET.ParseError as e:
            self.logger.error(f"XML構文エラー: {e}")
            return None
        except Exception as e:
            self.logger.error(f"XMLフォーマットエラー: {e}")
            return None
    
    def _indent_xml(self, elem, level=0, indent="  "):
        """XMLにインデントを適用"""
        i = "\n" + level * indent
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + indent
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                self._indent_xml(child, level + 1, indent)
            if not child.tail or not child.tail.strip():
                child.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    def validate(self, content: str) -> Tuple[bool, List[str]]:
        """XML構文検証"""
        try:
            ET.fromstring(content)
            return True, []
        except ET.ParseError as e:
            return False, [f"XML構文エラー (行 {e.lineno}): {e.msg}"]
        except Exception as e:
            return False, [f"検証エラー: {str(e)}"]


class SQLFormatter(BaseFormatter):
    """SQLフォーマッター"""
    
    def __init__(self, settings: Dict[str, Any] = None):
        super().__init__("SQL", settings)
        self._sqlparse_available = None
    
    def is_available(self) -> bool:
        """フォーマッターが利用可能かチェック"""
        return True
    
    def _check_sqlparse_available(self) -> bool:
        """sqlparseが利用可能かチェック"""
        if self._sqlparse_available is None:
            try:
                import sqlparse
                self._sqlparse_available = True
            except ImportError:
                self._sqlparse_available = False
                self.logger.warning("sqlparseがインストールされていません")
        return self._sqlparse_available
    
    def format(self, content: str) -> Optional[str]:
        """SQLをフォーマット"""
        try:
            if self._check_sqlparse_available():
                return self._format_with_sqlparse(content)
            else:
                return self._basic_format(content)
                
        except Exception as e:
            self.logger.error(f"SQLフォーマットエラー: {e}")
            return None
    
    def _format_with_sqlparse(self, content: str) -> str:
        """sqlparseでフォーマット"""
        try:
            import sqlparse
            
            formatted = sqlparse.format(
                content,
                reindent=self.settings.get('reindent', True),
                keyword_case=self.settings.get('keyword_case', 'upper'),
                identifier_case=self.settings.get('identifier_case', 'lower'),
                strip_comments=self.settings.get('strip_comments', False),
                indent_width=self.settings.get('indent_width', 2)
            )
            
            return formatted
            
        except Exception as e:
            self.logger.error(f"sqlparseフォーマットエラー: {e}")
            return content
    
    def _basic_format(self, content: str) -> str:
        """基本的なSQLフォーマット"""
        # 基本的なキーワードを大文字に
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 
                   'ON', 'GROUP BY', 'ORDER BY', 'HAVING', 'INSERT', 'UPDATE', 
                   'DELETE', 'CREATE', 'ALTER', 'DROP', 'TABLE', 'INDEX']
        
        formatted = content
        for keyword in keywords:
            pattern = r'\b' + keyword.lower() + r'\b'
            formatted = re.sub(pattern, keyword, formatted, flags=re.IGNORECASE)
        
        return formatted

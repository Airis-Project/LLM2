# src/utils/text_utils.py
"""
テキストユーティリティ
テキスト処理に関する共通機能を提供
"""

import re
import unicodedata
import difflib
from typing import List, Dict, Optional, Tuple, Union, Iterator, Set
from dataclasses import dataclass
from enum import Enum
import html
import urllib.parse
import base64
import hashlib

from ..core.logger import get_logger


class TextCase(Enum):
    """テキストケース"""
    LOWER = "lower"
    UPPER = "upper"
    TITLE = "title"
    SENTENCE = "sentence"
    CAMEL = "camel"
    PASCAL = "pascal"
    SNAKE = "snake"
    KEBAB = "kebab"
    CONSTANT = "constant"


@dataclass
class TextDiff:
    """テキスト差分情報"""
    line_number: int
    diff_type: str  # 'added', 'deleted', 'modified'
    old_text: str
    new_text: str
    context_before: List[str]
    context_after: List[str]


@dataclass
class TextStats:
    """テキスト統計情報"""
    char_count: int
    word_count: int
    line_count: int
    paragraph_count: int
    sentence_count: int
    whitespace_count: int
    punctuation_count: int
    digit_count: int
    alpha_count: int
    encoding: str = "utf-8"
    language: str = "unknown"


class TextUtils:
    """テキストユーティリティクラス"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # 日本語文字パターン
        self.hiragana_pattern = re.compile(r'[\u3040-\u309F]')
        self.katakana_pattern = re.compile(r'[\u30A0-\u30FF]')
        self.kanji_pattern = re.compile(r'[\u4E00-\u9FAF]')
        self.japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]')
        
        # 英数字パターン
        self.ascii_pattern = re.compile(r'[a-zA-Z0-9]')
        self.alpha_pattern = re.compile(r'[a-zA-Z]')
        self.digit_pattern = re.compile(r'[0-9]')
        
        # 空白文字パターン
        self.whitespace_pattern = re.compile(r'\s')
        
        # 句読点パターン
        self.punctuation_pattern = re.compile(r'[!-/:-@\[-`{-~。、！？]')
        
        # URL・メールパターン
        self.url_pattern = re.compile(
            r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?'
        )
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # プログラミング言語キーワード
        self.programming_keywords = {
            'python': {
                'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif',
                'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import',
                'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
                'try', 'while', 'with', 'yield', 'True', 'False', 'None'
            },
            'javascript': {
                'var', 'let', 'const', 'function', 'return', 'if', 'else', 'for', 'while',
                'do', 'break', 'continue', 'switch', 'case', 'default', 'try', 'catch',
                'finally', 'throw', 'new', 'this', 'typeof', 'instanceof', 'in', 'of',
                'true', 'false', 'null', 'undefined'
            }
        }
    
    def normalize_text(self, text: str, form: str = 'NFC') -> str:
        """テキストを正規化"""
        try:
            return unicodedata.normalize(form, text)
        except Exception as e:
            self.logger.error(f"テキスト正規化エラー: {e}")
            return text
    
    def clean_text(self, text: str, remove_extra_whitespace: bool = True,
                   remove_empty_lines: bool = False, strip_lines: bool = True) -> str:
        """テキストをクリーンアップ"""
        try:
            if not text:
                return text
            
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                if strip_lines:
                    line = line.strip()
                
                if remove_empty_lines and not line:
                    continue
                
                if remove_extra_whitespace:
                    line = re.sub(r'\s+', ' ', line)
                
                cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            self.logger.error(f"テキストクリーンアップエラー: {e}")
            return text
    
    def convert_case(self, text: str, case_type: TextCase) -> str:
        """テキストのケースを変換"""
        try:
            if case_type == TextCase.LOWER:
                return text.lower()
            elif case_type == TextCase.UPPER:
                return text.upper()
            elif case_type == TextCase.TITLE:
                return text.title()
            elif case_type == TextCase.SENTENCE:
                return text.capitalize()
            elif case_type == TextCase.CAMEL:
                return self._to_camel_case(text)
            elif case_type == TextCase.PASCAL:
                return self._to_pascal_case(text)
            elif case_type == TextCase.SNAKE:
                return self._to_snake_case(text)
            elif case_type == TextCase.KEBAB:
                return self._to_kebab_case(text)
            elif case_type == TextCase.CONSTANT:
                return self._to_constant_case(text)
            else:
                return text
                
        except Exception as e:
            self.logger.error(f"ケース変換エラー: {e}")
            return text
    
    def _to_camel_case(self, text: str) -> str:
        """キャメルケースに変換"""
        words = re.split(r'[-_\s]+', text.strip())
        if not words:
            return text
        
        result = words[0].lower()
        for word in words[1:]:
            if word:
                result += word.capitalize()
        return result
    
    def _to_pascal_case(self, text: str) -> str:
        """パスカルケースに変換"""
        words = re.split(r'[-_\s]+', text.strip())
        return ''.join(word.capitalize() for word in words if word)
    
    def _to_snake_case(self, text: str) -> str:
        """スネークケースに変換"""
        # キャメルケース・パスカルケースを分割
        text = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
        # 区切り文字を統一
        text = re.sub(r'[-\s]+', '_', text)
        return text.lower()
    
    def _to_kebab_case(self, text: str) -> str:
        """ケバブケースに変換"""
        # キャメルケース・パスカルケースを分割
        text = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', text)
        # 区切り文字を統一
        text = re.sub(r'[_\s]+', '-', text)
        return text.lower()
    
    def _to_constant_case(self, text: str) -> str:
        """定数ケース（UPPER_SNAKE_CASE）に変換"""
        return self._to_snake_case(text).upper()
    
    def count_words(self, text: str, language: str = 'auto') -> int:
        """単語数をカウント"""
        try:
            if not text:
                return 0
            
            if language == 'auto':
                language = self.detect_language(text)
            
            if language == 'japanese':
                # 日本語の場合は文字数ベース
                japanese_chars = len(self.japanese_pattern.findall(text))
                english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
                return japanese_chars + english_words
            else:
                # 英語などの場合は単語区切り
                words = re.findall(r'\b\w+\b', text)
                return len(words)
                
        except Exception as e:
            self.logger.error(f"単語数カウントエラー: {e}")
            return 0
    
    def count_sentences(self, text: str) -> int:
        """文数をカウント"""
        try:
            if not text:
                return 0
            
            # 日本語と英語の文区切り文字
            sentence_endings = r'[.!?。！？]+'
            sentences = re.split(sentence_endings, text)
            
            # 空の要素を除く
            sentences = [s.strip() for s in sentences if s.strip()]
            return len(sentences)
            
        except Exception as e:
            self.logger.error(f"文数カウントエラー: {e}")
            return 0
    
    def get_text_stats(self, text: str) -> TextStats:
        """テキスト統計を取得"""
        try:
            if not text:
                return TextStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
            
            char_count = len(text)
            word_count = self.count_words(text)
            line_count = len(text.split('\n'))
            paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
            sentence_count = self.count_sentences(text)
            
            whitespace_count = len(self.whitespace_pattern.findall(text))
            punctuation_count = len(self.punctuation_pattern.findall(text))
            digit_count = len(self.digit_pattern.findall(text))
            alpha_count = len(self.alpha_pattern.findall(text))
            
            language = self.detect_language(text)
            
            return TextStats(
                char_count=char_count,
                word_count=word_count,
                line_count=line_count,
                paragraph_count=paragraph_count,
                sentence_count=sentence_count,
                whitespace_count=whitespace_count,
                punctuation_count=punctuation_count,
                digit_count=digit_count,
                alpha_count=alpha_count,
                language=language
            )
            
        except Exception as e:
            self.logger.error(f"テキスト統計取得エラー: {e}")
            return TextStats(0, 0, 0, 0, 0, 0, 0, 0, 0)
    
    def detect_language(self, text: str) -> str:
        """言語を検出"""
        try:
            if not text:
                return 'unknown'
            
            japanese_chars = len(self.japanese_pattern.findall(text))
            ascii_chars = len(self.ascii_pattern.findall(text))
            total_chars = len(text.replace(' ', '').replace('\n', ''))
            
            if total_chars == 0:
                return 'unknown'
            
            japanese_ratio = japanese_chars / total_chars
            
            if japanese_ratio > 0.1:
                return 'japanese'
            elif ascii_chars / total_chars > 0.7:
                return 'english'
            else:
                return 'mixed'
                
        except Exception as e:
            self.logger.error(f"言語検出エラー: {e}")
            return 'unknown'
    
    def extract_urls(self, text: str) -> List[str]:
        """URLを抽出"""
        try:
            return self.url_pattern.findall(text)
        except Exception as e:
            self.logger.error(f"URL抽出エラー: {e}")
            return []
    
    def extract_emails(self, text: str) -> List[str]:
        """メールアドレスを抽出"""
        try:
            return self.email_pattern.findall(text)
        except Exception as e:
            self.logger.error(f"メール抽出エラー: {e}")
            return []
    
    def extract_keywords(self, text: str, language: str = 'python',
                        min_length: int = 3) -> Set[str]:
        """プログラミングキーワードを抽出"""
        try:
            if language not in self.programming_keywords:
                return set()
            
            keywords = self.programming_keywords[language]
            words = re.findall(r'\b\w+\b', text)
            
            found_keywords = set()
            for word in words:
                if word in keywords and len(word) >= min_length:
                    found_keywords.add(word)
            
            return found_keywords
            
        except Exception as e:
            self.logger.error(f"キーワード抽出エラー: {e}")
            return set()
    
    def find_and_replace(self, text: str, find_text: str, replace_text: str,
                        case_sensitive: bool = True, whole_word: bool = False,
                        use_regex: bool = False) -> Tuple[str, int]:
        """テキストを検索・置換"""
        try:
            count = 0
            
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(find_text, flags)
                result = pattern.sub(replace_text, text)
                count = len(pattern.findall(text))
            else:
                if whole_word:
                    # 単語境界を考慮
                    pattern = r'\b' + re.escape(find_text) + r'\b'
                    flags = 0 if case_sensitive else re.IGNORECASE
                    compiled_pattern = re.compile(pattern, flags)
                    result = compiled_pattern.sub(replace_text, text)
                    count = len(compiled_pattern.findall(text))
                else:
                    if case_sensitive:
                        count = text.count(find_text)
                        result = text.replace(find_text, replace_text)
                    else:
                        # 大文字小文字を無視した置換
                        pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                        result = pattern.sub(replace_text, text)
                        count = len(pattern.findall(text))
            
            return result, count
            
        except Exception as e:
            self.logger.error(f"検索置換エラー: {e}")
            return text, 0
    
    def find_text(self, text: str, search_text: str, case_sensitive: bool = True,
                  whole_word: bool = False, use_regex: bool = False) -> List[Tuple[int, int]]:
        """テキストを検索して位置を返す"""
        try:
            matches = []
            
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
                for match in pattern.finditer(text):
                    matches.append((match.start(), match.end()))
            else:
                if whole_word:
                    pattern = r'\b' + re.escape(search_text) + r'\b'
                    flags = 0 if case_sensitive else re.IGNORECASE
                    compiled_pattern = re.compile(pattern, flags)
                    for match in compiled_pattern.finditer(text):
                        matches.append((match.start(), match.end()))
                else:
                    search_target = text if case_sensitive else text.lower()
                    find_target = search_text if case_sensitive else search_text.lower()
                    
                    start = 0
                    while True:
                        pos = search_target.find(find_target, start)
                        if pos == -1:
                            break
                        matches.append((pos, pos + len(search_text)))
                        start = pos + 1
            
            return matches
            
        except Exception as e:
            self.logger.error(f"テキスト検索エラー: {e}")
            return []
    
    def compare_texts(self, text1: str, text2: str, context_lines: int = 3) -> List[TextDiff]:
        """テキストを比較して差分を取得"""
        try:
            lines1 = text1.split('\n')
            lines2 = text2.split('\n')
            
            differ = difflib.unified_diff(lines1, lines2, lineterm='', n=context_lines)
            diff_lines = list(differ)
            
            diffs = []
            line_num = 0
            
            for line in diff_lines:
                if line.startswith('@@'):
                    # ヘッダー行から行番号を抽出
                    match = re.match(r'@@ -(\d+),?\d* \+(\d+),?\d* @@', line)
                    if match:
                        line_num = int(match.group(2))
                elif line.startswith('-'):
                    # 削除行
                    diff = TextDiff(
                        line_number=line_num,
                        diff_type='deleted',
                        old_text=line[1:],
                        new_text='',
                        context_before=[],
                        context_after=[]
                    )
                    diffs.append(diff)
                elif line.startswith('+'):
                    # 追加行
                    diff = TextDiff(
                        line_number=line_num,
                        diff_type='added',
                        old_text='',
                        new_text=line[1:],
                        context_before=[],
                        context_after=[]
                    )
                    diffs.append(diff)
                    line_num += 1
                elif line.startswith(' '):
                    # コンテキスト行
                    line_num += 1
            
            return diffs
            
        except Exception as e:
            self.logger.error(f"テキスト比較エラー: {e}")
            return []
    
    def escape_html(self, text: str) -> str:
        """HTMLエスケープ"""
        try:
            return html.escape(text)
        except Exception as e:
            self.logger.error(f"HTMLエスケープエラー: {e}")
            return text
    
    def unescape_html(self, text: str) -> str:
        """HTMLアンエスケープ"""
        try:
            return html.unescape(text)
        except Exception as e:
            self.logger.error(f"HTMLアンエスケープエラー: {e}")
            return text
    
    def url_encode(self, text: str) -> str:
        """URL エンコード"""
        try:
            return urllib.parse.quote(text, safe='')
        except Exception as e:
            self.logger.error(f"URLエンコードエラー: {e}")
            return text
    
    def url_decode(self, text: str) -> str:
        """URL デコード"""
        try:
            return urllib.parse.unquote(text)
        except Exception as e:
            self.logger.error(f"URLデコードエラー: {e}")
            return text
    
    def base64_encode(self, text: str, encoding: str = 'utf-8') -> str:
        """Base64エンコード"""
        try:
            encoded_bytes = text.encode(encoding)
            base64_bytes = base64.b64encode(encoded_bytes)
            return base64_bytes.decode('ascii')
        except Exception as e:
            self.logger.error(f"Base64エンコードエラー: {e}")
            return text
    
    def base64_decode(self, text: str, encoding: str = 'utf-8') -> str:
        """Base64デコード"""
        try:
            base64_bytes = text.encode('ascii')
            decoded_bytes = base64.b64decode(base64_bytes)
            return decoded_bytes.decode(encoding)
        except Exception as e:
            self.logger.error(f"Base64デコードエラー: {e}")
            return text
    
    def calculate_text_hash(self, text: str, algorithm: str = 'md5') -> str:
        """テキストのハッシュ値を計算"""
        try:
            text_bytes = text.encode('utf-8')
            
            if algorithm.lower() == 'md5':
                hash_obj = hashlib.md5(text_bytes)
            elif algorithm.lower() == 'sha1':
                hash_obj = hashlib.sha1(text_bytes)
            elif algorithm.lower() == 'sha256':
                hash_obj = hashlib.sha256(text_bytes)
            else:
                raise ValueError(f"サポートされていないハッシュアルゴリズム: {algorithm}")
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"テキストハッシュ計算エラー: {e}")
            return ""
    
    def truncate_text(self, text: str, max_length: int, suffix: str = '...') -> str:
        """テキストを切り詰め"""
        try:
            if len(text) <= max_length:
                return text
            
            truncated_length = max_length - len(suffix)
            if truncated_length <= 0:
                return suffix[:max_length]
            
            return text[:truncated_length] + suffix
            
        except Exception as e:
            self.logger.error(f"テキスト切り詰めエラー: {e}")
            return text
    
    def wrap_text(self, text: str, width: int = 80, break_long_words: bool = True) -> str:
        """テキストを指定幅で折り返し"""
        try:
            import textwrap
            
            wrapper = textwrap.TextWrapper(
                width=width,
                break_long_words=break_long_words,
                break_on_hyphens=True
            )
            
            return wrapper.fill(text)
            
        except Exception as e:
            self.logger.error(f"テキスト折り返しエラー: {e}")
            return text
    
    def indent_text(self, text: str, indent: str = '    ') -> str:
        """テキストにインデントを追加"""
        try:
            lines = text.split('\n')
            indented_lines = [indent + line if line.strip() else line for line in lines]
            return '\n'.join(indented_lines)
            
        except Exception as e:
            self.logger.error(f"テキストインデントエラー: {e}")
            return text
    
    def remove_duplicates(self, text: str, preserve_order: bool = True) -> str:
        """重複行を削除"""
        try:
            lines = text.split('\n')
            
            if preserve_order:
                seen = set()
                unique_lines = []
                for line in lines:
                    if line not in seen:
                        seen.add(line)
                        unique_lines.append(line)
                return '\n'.join(unique_lines)
            else:
                return '\n'.join(list(set(lines)))
                
        except Exception as e:
            self.logger.error(f"重複削除エラー: {e}")
            return text
    
    def sort_lines(self, text: str, reverse: bool = False, 
                   case_sensitive: bool = True) -> str:
        """行をソート"""
        try:
            lines = text.split('\n')
            
            if case_sensitive:
                sorted_lines = sorted(lines, reverse=reverse)
            else:
                sorted_lines = sorted(lines, key=str.lower, reverse=reverse)
            
            return '\n'.join(sorted_lines)
            
        except Exception as e:
            self.logger.error(f"行ソートエラー: {e}")
            return text


# グローバルインスタンス
_text_utils: Optional[TextUtils] = None


def get_text_utils() -> TextUtils:
    """グローバルテキストユーティリティを取得"""
    global _text_utils
    if _text_utils is None:
        _text_utils = TextUtils()
    return _text_utils

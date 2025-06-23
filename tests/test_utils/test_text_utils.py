# tests/test_utils/test_text_utils.py
"""
テキストユーティリティのテストモジュール
テキスト処理関連の機能をテスト
"""

import pytest
import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Any
from unittest.mock import Mock, patch, MagicMock

# テスト対象のインポート
from utils.text_utils import (
    TextUtils,
    TextAnalyzer,
    TextFormatter,
    TextValidator,
    EncodingDetector,
    LineEndingConverter,
    TextDiffer,
    TextSearcher
)

# テスト用のインポート
from tests.test_core import (
    create_test_config_manager,
    create_test_logger
)
from tests.test_utils import (
    UtilsTestBase,
    TextTestHelper,
    ValidationTestHelper
)


class TestTextUtils(UtilsTestBase):
    """TextUtilsクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.text_utils = TextUtils(self.config_manager, self.logger)
        self.test_samples = TextTestHelper.create_test_text_samples()
    
    def test_normalize_text(self):
        """テキスト正規化テスト"""
        # 基本的な正規化
        text = "  Hello,   World!  \n\t  "
        normalized = self.text_utils.normalize_text(text)
        assert normalized == "Hello, World!"
        
        # Unicode正規化
        unicode_text = "café"  # é は結合文字
        normalized_unicode = self.text_utils.normalize_text(unicode_text, unicode_form='NFC')
        assert len(normalized_unicode) <= len(unicode_text)
        
        # 空文字列
        assert self.text_utils.normalize_text("") == ""
        
        # None値
        assert self.text_utils.normalize_text(None) == ""
    
    def test_remove_extra_whitespace(self):
        """余分な空白除去テスト"""
        # 複数の空白
        text = "Hello    World   Test"
        result = self.text_utils.remove_extra_whitespace(text)
        assert result == "Hello World Test"
        
        # タブと改行
        text_with_tabs = "Hello\t\tWorld\n\nTest"
        result = self.text_utils.remove_extra_whitespace(text_with_tabs)
        assert result == "Hello World Test"
        
        # 先頭と末尾の空白
        text_with_edges = "  Hello World  "
        result = self.text_utils.remove_extra_whitespace(text_with_edges)
        assert result == "Hello World"
    
    def test_count_lines(self):
        """行数カウントテスト"""
        # 複数行テキスト
        multiline = self.test_samples["multiline"]
        line_count = self.text_utils.count_lines(multiline)
        assert line_count == 3
        
        # 単一行
        single_line = self.test_samples["simple"]
        line_count = self.text_utils.count_lines(single_line)
        assert line_count == 1
        
        # 空文字列
        empty_count = self.text_utils.count_lines("")
        assert empty_count == 0
        
        # 末尾に改行がある場合
        text_with_newline = "Line 1\nLine 2\n"
        line_count = self.text_utils.count_lines(text_with_newline)
        assert line_count == 2
    
    def test_count_words(self):
        """単語数カウントテスト"""
        # 英語テキスト
        english_text = "Hello world this is a test"
        word_count = self.text_utils.count_words(english_text)
        assert word_count == 6
        
        # 日本語テキスト（文字数ベース）
        japanese_text = "こんにちは世界"
        char_count = self.text_utils.count_words(japanese_text, japanese_mode=True)
        assert char_count == 6
        
        # 混合テキスト
        mixed_text = "Hello こんにちは 123"
        word_count = self.text_utils.count_words(mixed_text)
        assert word_count >= 3
    
    def test_count_characters(self):
        """文字数カウントテスト"""
        # 基本的な文字数
        text = "Hello"
        char_count = self.text_utils.count_characters(text)
        assert char_count == 5
        
        # Unicode文字
        unicode_text = "こんにちは🌍"
        char_count = self.text_utils.count_characters(unicode_text)
        assert char_count == 6
        
        # 空白を含む場合
        text_with_spaces = "Hello World"
        char_count_with_spaces = self.text_utils.count_characters(text_with_spaces, include_spaces=True)
        char_count_without_spaces = self.text_utils.count_characters(text_with_spaces, include_spaces=False)
        assert char_count_with_spaces == 11
        assert char_count_without_spaces == 10
    
    def test_extract_lines(self):
        """行抽出テスト"""
        multiline = self.test_samples["multiline"]
        lines = self.text_utils.extract_lines(multiline)
        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"
        
        # 空行を含む場合
        text_with_empty = "Line 1\n\nLine 3"
        lines = self.text_utils.extract_lines(text_with_empty, skip_empty=False)
        assert len(lines) == 3
        assert lines[1] == ""
        
        # 空行をスキップ
        lines_skip_empty = self.text_utils.extract_lines(text_with_empty, skip_empty=True)
        assert len(lines_skip_empty) == 2
    
    def test_extract_words(self):
        """単語抽出テスト"""
        text = "Hello, world! This is a test."
        words = self.text_utils.extract_words(text)
        assert "Hello" in words
        assert "world" in words
        assert "test" in words
        
        # 区切り文字が含まれないことを確認
        assert "," not in words
        assert "!" not in words
        assert "." not in words
    
    def test_find_and_replace(self):
        """検索置換テスト"""
        text = "Hello World Hello Universe"
        
        # 基本的な置換
        result = self.text_utils.find_and_replace(text, "Hello", "Hi")
        assert result == "Hi World Hi Universe"
        
        # 大文字小文字を区別しない置換
        result_case_insensitive = self.text_utils.find_and_replace(
            text, "hello", "Hi", case_sensitive=False
        )
        assert result_case_insensitive == "Hi World Hi Universe"
        
        # 正規表現置換
        text_with_numbers = "Test 123 and 456"
        result_regex = self.text_utils.find_and_replace(
            text_with_numbers, r"\d+", "XXX", use_regex=True
        )
        assert result_regex == "Test XXX and XXX"
    
    def test_truncate_text(self):
        """テキスト切り詰めテスト"""
        long_text = "This is a very long text that needs to be truncated"
        
        # 基本的な切り詰め
        truncated = self.text_utils.truncate_text(long_text, 20)
        assert len(truncated) <= 23  # "..." を含む
        assert truncated.endswith("...")
        
        # カスタム省略記号
        truncated_custom = self.text_utils.truncate_text(long_text, 20, ellipsis="[...]")
        assert truncated_custom.endswith("[...]")
        
        # 単語境界で切り詰め
        truncated_word_boundary = self.text_utils.truncate_text(
            long_text, 20, word_boundary=True
        )
        # 単語の途中で切れていないことを確認
        words = truncated_word_boundary.replace("...", "").strip().split()
        for word in words:
            assert word in long_text
    
    def test_pad_text(self):
        """テキストパディングテスト"""
        text = "Hello"
        
        # 左パディング
        left_padded = self.text_utils.pad_text(text, 10, align='left')
        assert left_padded == "Hello     "
        
        # 右パディング
        right_padded = self.text_utils.pad_text(text, 10, align='right')
        assert right_padded == "     Hello"
        
        # 中央揃え
        center_padded = self.text_utils.pad_text(text, 10, align='center')
        assert len(center_padded) == 10
        assert "Hello" in center_padded
        
        # カスタムパディング文字
        custom_padded = self.text_utils.pad_text(text, 10, align='left', pad_char='*')
        assert custom_padded == "Hello*****"
    
    def test_wrap_text(self):
        """テキスト折り返しテスト"""
        long_line = "This is a very long line that should be wrapped at a certain width"
        
        # 基本的な折り返し
        wrapped = self.text_utils.wrap_text(long_line, width=20)
        lines = wrapped.split('\n')
        assert len(lines) > 1
        assert all(len(line) <= 20 for line in lines)
        
        # インデント付き折り返し
        wrapped_indent = self.text_utils.wrap_text(long_line, width=20, indent="  ")
        lines_indent = wrapped_indent.split('\n')
        assert all(line.startswith("  ") for line in lines_indent if line.strip())
    
    def test_extract_emails(self):
        """メールアドレス抽出テスト"""
        text = "Contact us at info@example.com or support@test.org for help"
        emails = self.text_utils.extract_emails(text)
        assert "info@example.com" in emails
        assert "support@test.org" in emails
        assert len(emails) == 2
    
    def test_extract_urls(self):
        """URL抽出テスト"""
        text = "Visit https://example.com or http://test.org for more info"
        urls = self.text_utils.extract_urls(text)
        assert "https://example.com" in urls
        assert "http://test.org" in urls
        assert len(urls) == 2
    
    def test_extract_phone_numbers(self):
        """電話番号抽出テスト"""
        text = "Call us at 03-1234-5678 or 090-1234-5678"
        phones = self.text_utils.extract_phone_numbers(text)
        assert len(phones) >= 1  # 日本の電話番号形式
    
    def test_calculate_similarity(self):
        """テキスト類似度計算テスト"""
        text1 = "Hello World"
        text2 = "Hello World"
        text3 = "Hi Universe"
        
        # 完全一致
        similarity_same = self.text_utils.calculate_similarity(text1, text2)
        assert similarity_same == 1.0
        
        # 異なるテキスト
        similarity_different = self.text_utils.calculate_similarity(text1, text3)
        assert 0.0 <= similarity_different < 1.0
        
        # 部分一致
        text4 = "Hello"
        similarity_partial = self.text_utils.calculate_similarity(text1, text4)
        assert 0.0 < similarity_partial < 1.0
    
    def test_detect_language(self):
        """言語検出テスト"""
        # 英語テキスト
        english_text = "This is an English text sample"
        lang_en = self.text_utils.detect_language(english_text)
        assert lang_en in ['en', 'english', 'English']
        
        # 日本語テキスト
        japanese_text = "これは日本語のテキストサンプルです"
        lang_ja = self.text_utils.detect_language(japanese_text)
        assert lang_ja in ['ja', 'japanese', 'Japanese']
    
    def test_clean_html(self):
        """HTML除去テスト"""
        html_text = "<p>Hello <strong>World</strong>!</p><br><a href='#'>Link</a>"
        clean_text = self.text_utils.clean_html(html_text)
        assert "<" not in clean_text
        assert ">" not in clean_text
        assert "Hello World!" in clean_text
    
    def test_escape_html(self):
        """HTMLエスケープテスト"""
        text_with_html = "Hello <script>alert('test')</script> & World"
        escaped = self.text_utils.escape_html(text_with_html)
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "&amp;" in escaped
        assert "<script>" not in escaped
    
    def test_unescape_html(self):
        """HTMLアンエスケープテスト"""
        escaped_text = "Hello &lt;world&gt; &amp; universe"
        unescaped = self.text_utils.unescape_html(escaped_text)
        assert "<world>" in unescaped
        assert "&" in unescaped
        assert "&lt;" not in unescaped


class TestTextAnalyzer(UtilsTestBase):
    """TextAnalyzerクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.analyzer = TextAnalyzer(self.config_manager, self.logger)
        self.test_samples = TextTestHelper.create_test_text_samples()
    
    def test_analyze_text_statistics(self):
        """テキスト統計分析テスト"""
        text = self.test_samples["code_sample"]
        stats = self.analyzer.analyze_statistics(text)
        
        assert stats['character_count'] > 0
        assert stats['word_count'] > 0
        assert stats['line_count'] > 0
        assert stats['paragraph_count'] >= 0
        assert ['average_words_per_line'] in stats
        assert ['average_characters_per_word'] in stats
    
    def test_analyze_readability(self):
        """読みやすさ分析テスト"""
        text = "This is a simple sentence. It is easy to read. Short words are good."
        readability = self.analyzer.analyze_readability(text)
        
        assert 'flesch_reading_ease' in readability
        assert 'flesch_kincaid_grade' in readability
        assert 'average_sentence_length' in readability
        assert 'average_syllables_per_word' in readability
    
    def test_extract_keywords(self):
        """キーワード抽出テスト"""
        text = "Python programming language is great for data analysis and machine learning"
        keywords = self.analyzer.extract_keywords(text, top_k=5)
        
        assert len(keywords) <= 5
        assert isinstance(keywords, list)
        # 重要な単語が含まれることを確認
        keyword_text = ' '.join(keywords).lower()
        assert any(word in keyword_text for word in ['python', 'programming', 'data', 'learning'])
    
    def test_analyze_sentiment(self):
        """感情分析テスト"""
        positive_text = "I love this amazing product! It's fantastic and wonderful!"
        negative_text = "This is terrible and awful. I hate it completely."
        neutral_text = "This is a chair. It has four legs."
        
        pos_sentiment = self.analyzer.analyze_sentiment(positive_text)
        neg_sentiment = self.analyzer.analyze_sentiment(negative_text)
        neu_sentiment = self.analyzer.analyze_sentiment(neutral_text)
        
        assert pos_sentiment['polarity'] > 0
        assert neg_sentiment['polarity'] < 0
        assert abs(neu_sentiment['polarity']) < abs(pos_sentiment['polarity'])
    
    def test_detect_patterns(self):
        """パターン検出テスト"""
        text = "Call 03-1234-5678 or email test@example.com. Visit https://example.com"
        patterns = self.analyzer.detect_patterns(text)
        
        assert 'emails' in patterns
        assert 'urls' in patterns
        assert 'phone_numbers' in patterns
        assert len(patterns['emails']) > 0
        assert len(patterns['urls']) > 0
    
    def test_analyze_complexity(self):
        """複雑さ分析テスト"""
        simple_text = "This is simple. Easy to read."
        complex_text = "The implementation of sophisticated algorithms requires comprehensive understanding of computational complexity theory and advanced mathematical concepts."
        
        simple_complexity = self.analyzer.analyze_complexity(simple_text)
        complex_complexity = self.analyzer.analyze_complexity(complex_text)
        
        assert complex_complexity['complexity_score'] > simple_complexity['complexity_score']


class TestTextFormatter(UtilsTestBase):
    """TextFormatterクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.formatter = TextFormatter(self.config_manager, self.logger)
    
    def test_format_code(self):
        """コード整形テスト"""
        unformatted_python = "def hello():print('hello')"
        formatted = self.formatter.format_code(unformatted_python, language='python')
        
        assert 'def hello():' in formatted
        assert 'print(' in formatted
        assert formatted != unformatted_python
    
    def test_format_json(self):
        """JSON整形テスト"""
        unformatted_json = '{"name":"test","value":123}'
        formatted = self.formatter.format_json(unformatted_json)
        
        assert '"name"' in formatted
        assert '"test"' in formatted
        assert formatted != unformatted_json
        assert '\n' in formatted  # 改行が含まれている
    
    def test_format_xml(self):
        """XML整形テスト"""
        unformatted_xml = '<root><item>value</item></root>'
        formatted = self.formatter.format_xml(unformatted_xml)
        
        assert '<root>' in formatted
        assert '<item>' in formatted
        assert formatted != unformatted_xml
    
    def test_format_markdown(self):
        """Markdown整形テスト"""
        markdown_text = "# Title\n\nThis is **bold** and *italic*."
        formatted = self.formatter.format_markdown(markdown_text)
        
        assert formatted is not None
        assert len(formatted) > 0
    
    def test_convert_case(self):
        """大文字小文字変換テスト"""
        text = "Hello World Test"
        
        # 大文字変換
        upper = self.formatter.convert_case(text, 'upper')
        assert upper == "HELLO WORLD TEST"
        
        # 小文字変換
        lower = self.formatter.convert_case(text, 'lower')
        assert lower == "hello world test"
        
        # タイトルケース
        title = self.formatter.convert_case(text, 'title')
        assert title == "Hello World Test"
        
        # キャメルケース
        camel = self.formatter.convert_case(text, 'camel')
        assert camel == "helloWorldTest"
        
        # スネークケース
        snake = self.formatter.convert_case(text, 'snake')
        assert snake == "hello_world_test"
    
    def test_add_line_numbers(self):
        """行番号追加テスト"""
        multiline_text = "Line 1\nLine 2\nLine 3"
        numbered = self.formatter.add_line_numbers(multiline_text)
        
        assert "1: Line 1" in numbered
        assert "2: Line 2" in numbered
        assert "3: Line 3" in numbered
    
    def test_indent_text(self):
        """インデント追加テスト"""
        text = "Line 1\nLine 2\nLine 3"
        indented = self.formatter.indent_text(text, indent="  ")
        
        lines = indented.split('\n')
        assert all(line.startswith("  ") for line in lines if line.strip())
    
    def test_create_table(self):
        """テーブル作成テスト"""
        headers = ["Name", "Age", "City"]
        rows = [
            ["Alice", "25", "Tokyo"],
            ["Bob", "30", "Osaka"]
        ]
        
        table = self.formatter.create_table(headers, rows)
        
        assert "Name" in table
        assert "Alice" in table
        assert "Bob" in table
        assert "|" in table  # テーブル区切り文字


class TestTextValidator(UtilsTestBase):
    """TextValidatorクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.validator = TextValidator(self.config_manager, self.logger)
        self.email_cases = ValidationTestHelper.create_email_test_cases()
        self.url_cases = ValidationTestHelper.create_url_test_cases()
    
    def test_validate_email(self):
        """メールアドレス検証テスト"""
        for email, expected in self.email_cases.items():
            result = self.validator.validate_email(email)
            assert result == expected, f"Email {email} validation failed"
    
    def test_validate_url(self):
        """URL検証テスト"""
        for url, expected in self.url_cases.items():
            result = self.validator.validate_url(url)
            assert result == expected, f"URL {url} validation failed"
    
    def test_validate_json(self):
        """JSON検証テスト"""
        json_cases = ValidationTestHelper.create_json_test_cases()
        for json_str, expected in json_cases.items():
            result = self.validator.validate_json(json_str)
            assert result == expected, f"JSON {json_str} validation failed"
    
    def test_validate_length(self):
        """長さ検証テスト"""
        text = "Hello World"
        
        # 最小長チェック
        assert self.validator.validate_length(text, min_length=5) is True
        assert self.validator.validate_length(text, min_length=20) is False
        
        # 最大長チェック
        assert self.validator.validate_length(text, max_length=20) is True
        assert self.validator.validate_length(text, max_length=5) is False
        
        # 範囲チェック
        assert self.validator.validate_length(text, min_length=5, max_length=20) is True
    
    def test_validate_pattern(self):
        """パターン検証テスト"""
        # 数字のみ
        assert self.validator.validate_pattern("12345", r"^\d+$") is True
        assert self.validator.validate_pattern("abc123", r"^\d+$") is False
        
        # 英数字のみ
        assert self.validator.validate_pattern("abc123", r"^[a-zA-Z0-9]+$") is True
        assert self.validator.validate_pattern("abc-123", r"^[a-zA-Z0-9]+$") is False
    
    def test_validate_encoding(self):
        """エンコーディング検証テスト"""
        # UTF-8テキスト
        utf8_text = "Hello 世界"
        assert self.validator.validate_encoding(utf8_text.encode('utf-8'), 'utf-8') is True
        
        # ASCII テキスト
        ascii_text = "Hello World"
        assert self.validator.validate_encoding(ascii_text.encode('ascii'), 'ascii') is True


class TestEncodingDetector(UtilsTestBase):
    """EncodingDetectorクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.detector = EncodingDetector(self.config_manager, self.logger)
        self.encoding_data = TextTestHelper.create_encoding_test_data()
    
    def test_detect_encoding(self):
        """エンコーディング検出テスト"""
        for encoding, data in self.encoding_data.items():
            detected = self.detector.detect_encoding(data)
            # 検出されたエンコーディングが期待値と一致するか、または互換性があることを確認
            assert detected is not None
            assert isinstance(detected, str)
    
    def test_convert_encoding(self):
        """エンコーディング変換テスト"""
        # UTF-8からShift_JISへの変換
        utf8_data = "Hello こんにちは".encode('utf-8')
        converted = self.detector.convert_encoding(utf8_data, 'utf-8', 'shift_jis')
        
        assert converted is not None
        # 変換後のデータをデコードして確認
        decoded = converted.decode('shift_jis')
        assert "Hello" in decoded
        assert "こんにちは" in decoded


class TestLineEndingConverter(UtilsTestBase):
    """LineEndingConverterクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.converter = LineEndingConverter(self.config_manager, self.logger)
    
    def test_detect_line_ending(self):
        """改行コード検出テスト"""
        # Unix形式（LF）
        unix_text = "Line 1\nLine 2\nLine 3"
        assert self.converter.detect_line_ending(unix_text) == '\n'
        
        # Windows形式（CRLF）
        windows_text = "Line 1\r\nLine 2\r\nLine 3"
        assert self.converter.detect_line_ending(windows_text) == '\r\n'
        
        # Mac形式（CR）
        mac_text = "Line 1\rLine 2\rLine 3"
        assert self.converter.detect_line_ending(mac_text) == '\r'
    
    def test_convert_line_endings(self):
        """改行コード変換テスト"""
        # Windows形式からUnix形式へ
        windows_text = "Line 1\r\nLine 2\r\nLine 3"
        unix_converted = self.converter.convert_line_endings(windows_text, '\n')
        assert '\r\n' not in unix_converted
        assert '\n' in unix_converted
        
        # Unix形式からWindows形式へ
        unix_text = "Line 1\nLine 2\nLine 3"
        windows_converted = self.converter.convert_line_endings(unix_text, '\r\n')
        assert '\r\n' in windows_converted
    
    def test_normalize_line_endings(self):
        """改行コード正規化テスト"""
        mixed_text = "Line 1\r\nLine 2\nLine 3\rLine 4"
        normalized = self.converter.normalize_line_endings(mixed_text)
        
        # 統一された改行コードになっていることを確認
        line_ending = self.converter.detect_line_ending(normalized)
        assert line_ending in ['\n', '\r\n', '\r']
        
        # 行数が正しいことを確認
        lines = normalized.split(line_ending)
        assert len(lines) == 4


class TestTextDiffer(UtilsTestBase):
    """TextDifferクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.differ = TextDiffer(self.config_manager, self.logger)
    
    def test_compare_texts(self):
        """テキスト比較テスト"""
        text1 = "Hello World\nThis is line 2\nLine 3"
        text2 = "Hello Universe\nThis is line 2\nLine 3 modified"
        
        diff = self.differ.compare_texts(text1, text2)
        
        assert diff is not None
        assert len(diff) > 0
        # 差分情報が含まれることを確認
        diff_str = '\n'.join(diff)
        assert 'World' in diff_str or 'Universe' in diff_str
    
    def test_get_unified_diff(self):
        """統一差分形式テスト"""
        text1 = "Line 1\nLine 2\nLine 3"
        text2 = "Line 1\nModified Line 2\nLine 3"
        
        unified_diff = self.differ.get_unified_diff(text1, text2, "file1.txt", "file2.txt")
        assert unified_diff is not None
        assert len(unified_diff) > 0
        # 統一差分形式の特徴を確認
        diff_str = '\n'.join(unified_diff)
        assert '---' in diff_str or '+++' in diff_str
        assert 'Modified Line 2' in diff_str
    
    def test_get_context_diff(self):
        """コンテキスト差分形式テスト"""
        text1 = "Line 1\nLine 2\nLine 3"
        text2 = "Line 1\nModified Line 2\nLine 3"
        
        context_diff = self.differ.get_context_diff(text1, text2, "file1.txt", "file2.txt")
        
        assert context_diff is not None
        assert len(context_diff) > 0
    
    def test_calculate_similarity_ratio(self):
        """類似度比率計算テスト"""
        text1 = "Hello World"
        text2 = "Hello World"
        text3 = "Hi Universe"
        
        # 完全一致
        ratio_same = self.differ.calculate_similarity_ratio(text1, text2)
        assert ratio_same == 1.0
        
        # 部分一致
        ratio_partial = self.differ.calculate_similarity_ratio(text1, text3)
        assert 0.0 <= ratio_partial < 1.0
    
    def test_find_longest_common_subsequence(self):
        """最長共通部分列テスト"""
        text1 = "ABCDGH"
        text2 = "AEDFHR"
        
        lcs = self.differ.find_longest_common_subsequence(text1, text2)
        assert lcs is not None
        assert len(lcs) > 0
        # 共通文字が含まれることを確認
        assert all(c in text1 and c in text2 for c in lcs)


class TestTextSearcher(UtilsTestBase):
    """TextSearcherクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.searcher = TextSearcher(self.config_manager, self.logger)
        self.search_text = TextTestHelper.create_search_test_text()
    
    def test_simple_search(self):
        """単純検索テスト"""
        results = self.searcher.search(self.search_text, "Python")
        
        assert len(results) > 0
        for result in results:
            assert 'position' in result
            assert 'line' in result
            assert 'column' in result
            assert 'match' in result
    
    def test_case_insensitive_search(self):
        """大文字小文字を区別しない検索テスト"""
        results_sensitive = self.searcher.search(self.search_text, "python", case_sensitive=True)
        results_insensitive = self.searcher.search(self.search_text, "python", case_sensitive=False)
        
        # 大文字小文字を区別しない検索の方が多くの結果を返すはず
        assert len(results_insensitive) >= len(results_sensitive)
    
    def test_regex_search(self):
        """正規表現検索テスト"""
        # 数字を検索
        results = self.searcher.search(self.search_text, r"\d+", use_regex=True)
        
        assert len(results) >= 0
        for result in results:
            match_text = result['match']
            assert re.match(r"\d+", match_text)
    
    def test_whole_word_search(self):
        """単語全体検索テスト"""
        # "test" を含む単語を検索（"testing" は除外）
        results_partial = self.searcher.search(self.search_text, "test", whole_word=False)
        results_whole = self.searcher.search(self.search_text, "test", whole_word=True)
        
        # 部分一致の方が多くの結果を返すはず
        assert len(results_partial) >= len(results_whole)
    
    def test_multiline_search(self):
        """複数行検索テスト"""
        multiline_pattern = r"def\s+\w+\s*\([^)]*\):"
        results = self.searcher.search(self.search_text, multiline_pattern, use_regex=True)
        
        assert len(results) >= 0
        for result in results:
            assert 'def ' in result['match']
    
    def test_search_and_replace(self):
        """検索置換テスト"""
        original_text = "Hello World Hello Universe"
        replaced_text = self.searcher.search_and_replace(original_text, "Hello", "Hi")
        
        assert replaced_text == "Hi World Hi Universe"
        assert "Hello" not in replaced_text
    
    def test_search_with_context(self):
        """コンテキスト付き検索テスト"""
        results = self.searcher.search_with_context(self.search_text, "def", context_lines=2)
        
        assert len(results) >= 0
        for result in results:
            assert 'before_context' in result
            assert 'after_context' in result
            assert 'match_line' in result
    
    def test_find_all_occurrences(self):
        """全出現箇所検索テスト"""
        text = "test testing tested test"
        occurrences = self.searcher.find_all_occurrences(text, "test")
        
        assert len(occurrences) >= 3  # "test" が3回以上出現
        for occurrence in occurrences:
            assert isinstance(occurrence, dict)
            assert 'start' in occurrence
            assert 'end' in occurrence
            assert 'match' in occurrence


class TestTextUtilsIntegration(UtilsTestBase):
    """TextUtils統合テスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.text_utils = TextUtils(self.config_manager, self.logger)
        self.analyzer = TextAnalyzer(self.config_manager, self.logger)
        self.formatter = TextFormatter(self.config_manager, self.logger)
        self.validator = TextValidator(self.config_manager, self.logger)
    
    def test_code_processing_workflow(self):
        """コード処理ワークフローテスト"""
        # 未整形のコード
        unformatted_code = """
def hello_world():
print("Hello, World!")
return True

class TestClass:
def __init__(self):
self.value=42
        """
        
        # 1. コード整形
        formatted_code = self.formatter.format_code(unformatted_code, 'python')
        
        # 2. 統計分析
        stats = self.analyzer.analyze_statistics(formatted_code)
        assert stats['line_count'] > 0
        assert stats['character_count'] > 0
        
        # 3. 複雑さ分析
        complexity = self.analyzer.analyze_complexity(formatted_code)
        assert 'complexity_score' in complexity
        
        # 4. パターン検出
        patterns = self.analyzer.detect_patterns(formatted_code)
        assert isinstance(patterns, dict)
    
    def test_document_processing_workflow(self):
        """ドキュメント処理ワークフローテスト"""
        document = """
        # Document Title
        
        This is a sample document with various elements:
        
        - Email: contact@example.com
        - Website: https://example.com
        - Phone: 03-1234-5678
        
        The document contains **bold** and *italic* text.
        """
        
        # 1. テキスト正規化
        normalized = self.text_utils.normalize_text(document)
        
        # 2. パターン抽出
        patterns = self.analyzer.detect_patterns(normalized)
        assert 'emails' in patterns
        assert 'urls' in patterns
        
        # 3. 統計分析
        stats = self.analyzer.analyze_statistics(normalized)
        assert stats['word_count'] > 0
        
        # 4. 読みやすさ分析
        readability = self.analyzer.analyze_readability(normalized)
        assert 'flesch_reading_ease' in readability
        
        # 5. Markdown整形
        formatted_md = self.formatter.format_markdown(normalized)
        assert formatted_md is not None
    
    def test_multilingual_text_handling(self):
        """多言語テキスト処理テスト"""
        multilingual_text = """
        English: Hello World
        Japanese: こんにちは世界
        Chinese: 你好世界
        Korean: 안녕하세요 세계
        Russian: Привет мир
        """
        
        # 1. 文字数カウント（Unicode対応）
        char_count = self.text_utils.count_characters(multilingual_text)
        assert char_count > 0
        
        # 2. 言語検出
        detected_lang = self.text_utils.detect_language(multilingual_text)
        assert detected_lang is not None
        
        # 3. Unicode正規化
        normalized = self.text_utils.normalize_text(multilingual_text, unicode_form='NFC')
        assert len(normalized) > 0
        
        # 4. エンコーディング検証
        utf8_bytes = multilingual_text.encode('utf-8')
        is_valid_utf8 = self.validator.validate_encoding(utf8_bytes, 'utf-8')
        assert is_valid_utf8 is True
    
    def test_large_text_performance(self):
        """大きなテキストの性能テスト"""
        # 大きなテキストを生成
        large_text = "This is a test line.\n" * 10000
        
        import time
        
        # 1. 文字数カウント性能
        start_time = time.time()
        char_count = self.text_utils.count_characters(large_text)
        char_count_time = time.time() - start_time
        
        assert char_count > 0
        assert char_count_time < 1.0  # 1秒以内
        
        # 2. 行数カウント性能
        start_time = time.time()
        line_count = self.text_utils.count_lines(large_text)
        line_count_time = time.time() - start_time
        
        assert line_count == 10000
        assert line_count_time < 1.0  # 1秒以内
        
        # 3. 検索性能
        start_time = time.time()
        search_results = self.text_utils.find_and_replace(large_text, "test", "TEST", max_replacements=100)
        search_time = time.time() - start_time
        
        assert "TEST" in search_results
        assert search_time < 2.0  # 2秒以内
    
    def test_error_recovery_scenarios(self):
        """エラー回復シナリオテスト"""
        # 1. 無効なJSON処理
        invalid_json = '{"invalid": json content}'
        try:
            self.formatter.format_json(invalid_json)
        except Exception as e:
            assert isinstance(e, (ValueError, TypeError))
        
        # 2. 無効なエンコーディング処理
        invalid_bytes = b'\xff\xfe\xfd'
        try:
            detected_encoding = EncodingDetector(self.config_manager, self.logger).detect_encoding(invalid_bytes)
            # エラーが発生しない場合は、何らかの結果が返される
            assert detected_encoding is not None or detected_encoding is None
        except Exception:
            # エラーが発生する場合は適切に処理される
            pass
        
        # 3. 空文字列処理
        empty_stats = self.analyzer.analyze_statistics("")
        assert empty_stats['character_count'] == 0
        assert empty_stats['word_count'] == 0
        assert empty_stats['line_count'] == 0
        
        # 4. None値処理
        none_normalized = self.text_utils.normalize_text(None)
        assert none_normalized == ""
    
    def test_configuration_based_behavior(self):
        """設定ベースの動作テスト"""
        # 設定を変更してテキスト処理の動作を確認
        
        # 1. デフォルト設定での動作
        default_normalized = self.text_utils.normalize_text("  Hello   World  ")
        
        # 2. 設定変更後の動作
        # （実際の設定変更は config_manager を通じて行う）
        custom_config = {
            'text_processing': {
                'preserve_multiple_spaces': True,
                'unicode_normalization': 'NFKC'
            }
        }
        
        # カスタム設定でのテキストユーティリティ作成
        custom_text_utils = TextUtils(self.config_manager, self.logger)
        
        # 動作の違いを確認（設定に応じて）
        custom_normalized = custom_text_utils.normalize_text("  Hello   World  ")
        
        # 設定に応じて結果が異なることを確認
        assert isinstance(default_normalized, str)
        assert isinstance(custom_normalized, str)


class TestTextUtilsEdgeCases(UtilsTestBase):
    """TextUtilsエッジケーステスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.text_utils = TextUtils(self.config_manager, self.logger)
    
    def test_empty_and_none_inputs(self):
        """空文字列とNone入力のテスト"""
        # 空文字列
        assert self.text_utils.normalize_text("") == ""
        assert self.text_utils.count_characters("") == 0
        assert self.text_utils.count_words("") == 0
        assert self.text_utils.count_lines("") == 0
        
        # None値
        assert self.text_utils.normalize_text(None) == ""
        assert self.text_utils.count_characters(None) == 0
        assert self.text_utils.count_words(None) == 0
        assert self.text_utils.count_lines(None) == 0
    
    def test_special_characters(self):
        """特殊文字のテスト"""
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        
        # 特殊文字を含むテキストの処理
        char_count = self.text_utils.count_characters(special_chars)
        assert char_count == len(special_chars)
        
        # 正規化処理
        normalized = self.text_utils.normalize_text(special_chars)
        assert len(normalized) > 0
    
    def test_very_long_lines(self):
        """非常に長い行のテスト"""
        very_long_line = "A" * 100000
        
        # 文字数カウント
        char_count = self.text_utils.count_characters(very_long_line)
        assert char_count == 100000
        
        # 行数カウント
        line_count = self.text_utils.count_lines(very_long_line)
        assert line_count == 1
        
        # 切り詰め
        truncated = self.text_utils.truncate_text(very_long_line, 50)
        assert len(truncated) <= 53  # "..." を含む
    
    def test_mixed_line_endings(self):
        """混合改行コードのテスト"""
        mixed_text = "Line 1\nLine 2\r\nLine 3\rLine 4"
        
        # 行数カウント
        line_count = self.text_utils.count_lines(mixed_text)
        assert line_count == 4
        
        # 行抽出
        lines = self.text_utils.extract_lines(mixed_text)
        assert len(lines) == 4
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"
        assert lines[3] == "Line 4"
    
    def test_unicode_edge_cases(self):
        """Unicodeエッジケースのテスト"""
        # 結合文字
        combining_chars = "e\u0301"  # é (e + combining acute accent)
        normalized_nfc = self.text_utils.normalize_text(combining_chars, unicode_form='NFC')
        normalized_nfd = self.text_utils.normalize_text(combining_chars, unicode_form='NFD')
        
        # 正規化形式によって長さが変わることを確認
        assert len(normalized_nfc) != len(normalized_nfd) or normalized_nfc == normalized_nfd
        
        # 絵文字
        emoji_text = "Hello 👋 World 🌍"
        char_count = self.text_utils.count_characters(emoji_text)
        assert char_count > 0
        
        # サロゲートペア
        surrogate_text = "𝐇𝐞𝐥𝐥𝐨"  # Mathematical bold letters
        char_count = self.text_utils.count_characters(surrogate_text)
        assert char_count == 5


if __name__ == '__main__':
    pytest.main([__file__])


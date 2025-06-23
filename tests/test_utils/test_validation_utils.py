# tests/test_utils/test_validation_utils.py
"""
バリデーションユーティリティのテストモジュール
データ検証関連の機能をテスト
"""

import pytest
import re
import json
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any, Union
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os

# テスト対象のインポート
from utils.validation_utils import (
    ValidationUtils,
    DataValidator,
    SchemaValidator,
    FileValidator,
    SecurityValidator,
    FormatValidator,
    BusinessRuleValidator,
    ValidationResult,
    ValidationError,
    ValidationRule
)

# テスト用のインポート
from tests.test_core import (
    create_test_config_manager,
    create_test_logger
)
from tests.test_utils import (
    UtilsTestBase,
    ValidationTestHelper,
    SecurityTestHelper
)


class TestValidationUtils(UtilsTestBase):
    """ValidationUtilsクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.validation_utils = ValidationUtils(self.config_manager, self.logger)
        self.test_data = ValidationTestHelper.create_test_validation_data()
    
    def test_validate_email(self):
        """メールアドレス検証テスト"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.jp",
            "user+tag@example.org",
            "123@example.com"
        ]
        
        invalid_emails = [
            "invalid.email",
            "@example.com",
            "user@",
            "user@.com",
            "user name@example.com",
            ""
        ]
        
        # 有効なメールアドレス
        for email in valid_emails:
            result = self.validation_utils.validate_email(email)
            assert result.is_valid, f"Valid email {email} should pass validation"
            assert result.errors == []
        
        # 無効なメールアドレス
        for email in invalid_emails:
            result = self.validation_utils.validate_email(email)
            assert not result.is_valid, f"Invalid email {email} should fail validation"
            assert len(result.errors) > 0
    
    def test_validate_url(self):
        """URL検証テスト"""
        valid_urls = [
            "https://example.com",
            "http://test.org",
            "https://subdomain.example.com/path",
            "https://example.com:8080/path?query=value",
            "ftp://files.example.com/file.txt"
        ]
        
        invalid_urls = [
            "not_a_url",
            "http://",
            "https://",
            "://example.com",
            "http:example.com",
            ""
        ]
        
        # 有効なURL
        for url in valid_urls:
            result = self.validation_utils.validate_url(url)
            assert result.is_valid, f"Valid URL {url} should pass validation"
        
        # 無効なURL
        for url in invalid_urls:
            result = self.validation_utils.validate_url(url)
            assert not result.is_valid, f"Invalid URL {url} should fail validation"
    
    def test_validate_phone_number(self):
        """電話番号検証テスト"""
        valid_phones = [
            "03-1234-5678",
            "090-1234-5678",
            "080-1234-5678",
            "+81-3-1234-5678",
            "0312345678"
        ]
        
        invalid_phones = [
            "123-456",
            "abc-defg-hijk",
            "03-1234-567",
            "090-1234-56789",
            ""
        ]
        
        # 有効な電話番号
        for phone in valid_phones:
            result = self.validation_utils.validate_phone_number(phone)
            assert result.is_valid, f"Valid phone {phone} should pass validation"
        
        # 無効な電話番号
        for phone in invalid_phones:
            result = self.validation_utils.validate_phone_number(phone)
            assert not result.is_valid, f"Invalid phone {phone} should fail validation"
    
    def test_validate_date(self):
        """日付検証テスト"""
        valid_dates = [
            "2023-12-31",
            "2023/12/31",
            "31/12/2023",
            "2023-01-01",
            datetime.now().strftime("%Y-%m-%d")
        ]
        
        invalid_dates = [
            "2023-13-01",  # 無効な月
            "2023-02-30",  # 無効な日
            "invalid-date",
            "2023/13/01",
            ""
        ]
        
        # 有効な日付
        for date_str in valid_dates:
            result = self.validation_utils.validate_date(date_str)
            assert result.is_valid, f"Valid date {date_str} should pass validation"
        
        # 無効な日付
        for date_str in invalid_dates:
            result = self.validation_utils.validate_date(date_str)
            assert not result.is_valid, f"Invalid date {date_str} should fail validation"
    
    def test_validate_numeric(self):
        """数値検証テスト"""
        # 整数検証
        assert self.validation_utils.validate_numeric("123", numeric_type='int').is_valid
        assert self.validation_utils.validate_numeric("-456", numeric_type='int').is_valid
        assert not self.validation_utils.validate_numeric("12.34", numeric_type='int').is_valid
        assert not self.validation_utils.validate_numeric("abc", numeric_type='int').is_valid
        
        # 浮動小数点数検証
        assert self.validation_utils.validate_numeric("123.45", numeric_type='float').is_valid
        assert self.validation_utils.validate_numeric("-67.89", numeric_type='float').is_valid
        assert self.validation_utils.validate_numeric("123", numeric_type='float').is_valid
        assert not self.validation_utils.validate_numeric("abc", numeric_type='float').is_valid
        
        # 範囲検証
        result = self.validation_utils.validate_numeric("50", min_value=0, max_value=100)
        assert result.is_valid
        
        result = self.validation_utils.validate_numeric("150", min_value=0, max_value=100)
        assert not result.is_valid
        
        result = self.validation_utils.validate_numeric("-10", min_value=0, max_value=100)
        assert not result.is_valid
    
    def test_validate_length(self):
        """長さ検証テスト"""
        text = "Hello World"
        
        # 最小長検証
        result = self.validation_utils.validate_length(text, min_length=5)
        assert result.is_valid
        
        result = self.validation_utils.validate_length(text, min_length=20)
        assert not result.is_valid
        
        # 最大長検証
        result = self.validation_utils.validate_length(text, max_length=20)
        assert result.is_valid
        
        result = self.validation_utils.validate_length(text, max_length=5)
        assert not result.is_valid
        
        # 範囲検証
        result = self.validation_utils.validate_length(text, min_length=5, max_length=20)
        assert result.is_valid
        
        result = self.validation_utils.validate_length(text, min_length=15, max_length=20)
        assert not result.is_valid
    
    def test_validate_pattern(self):
        """パターン検証テスト"""
        # 数字のみ
        result = self.validation_utils.validate_pattern("12345", r"^\d+$")
        assert result.is_valid
        
        result = self.validation_utils.validate_pattern("abc123", r"^\d+$")
        assert not result.is_valid
        
        # 英数字のみ
        result = self.validation_utils.validate_pattern("abc123", r"^[a-zA-Z0-9]+$")
        assert result.is_valid
        
        result = self.validation_utils.validate_pattern("abc-123", r"^[a-zA-Z0-9]+$")
        assert not result.is_valid
        
        # カスタムパターン
        postal_code_pattern = r"^\d{3}-\d{4}$"
        result = self.validation_utils.validate_pattern("123-4567", postal_code_pattern)
        assert result.is_valid
        
        result = self.validation_utils.validate_pattern("1234567", postal_code_pattern)
        assert not result.is_valid
    
    def test_validate_required(self):
        """必須項目検証テスト"""
        # 有効な値
        assert self.validation_utils.validate_required("value").is_valid
        assert self.validation_utils.validate_required("0").is_valid
        assert self.validation_utils.validate_required(0).is_valid
        assert self.validation_utils.validate_required(False).is_valid
        
        # 無効な値
        assert not self.validation_utils.validate_required("").is_valid
        assert not self.validation_utils.validate_required(None).is_valid
        assert not self.validation_utils.validate_required("   ").is_valid  # 空白のみ
    
    def test_validate_choice(self):
        """選択肢検証テスト"""
        valid_choices = ["option1", "option2", "option3"]
        
        # 有効な選択
        result = self.validation_utils.validate_choice("option1", valid_choices)
        assert result.is_valid
        
        result = self.validation_utils.validate_choice("option2", valid_choices)
        assert result.is_valid
        
        # 無効な選択
        result = self.validation_utils.validate_choice("invalid_option", valid_choices)
        assert not result.is_valid
        
        result = self.validation_utils.validate_choice("", valid_choices)
        assert not result.is_valid
    
    def test_validate_unique(self):
        """一意性検証テスト"""
        existing_values = ["value1", "value2", "value3"]
        
        # 一意な値
        result = self.validation_utils.validate_unique("new_value", existing_values)
        assert result.is_valid
        
        # 重複する値
        result = self.validation_utils.validate_unique("value1", existing_values)
        assert not result.is_valid
        
        # 大文字小文字を区別しない場合
        result = self.validation_utils.validate_unique("VALUE1", existing_values, case_sensitive=False)
        assert not result.is_valid
        
        result = self.validation_utils.validate_unique("VALUE1", existing_values, case_sensitive=True)
        assert result.is_valid
    
    def test_validate_multiple_rules(self):
        """複数ルール検証テスト"""
        rules = [
            ValidationRule("required", {}),
            ValidationRule("length", {"min_length": 5, "max_length": 20}),
            ValidationRule("pattern", {"pattern": r"^[a-zA-Z0-9]+$"})
        ]
        
        # すべてのルールを満たす値
        result = self.validation_utils.validate_multiple("abc123", rules)
        assert result.is_valid
        assert len(result.errors) == 0
        
        # 一部のルールを満たさない値
        result = self.validation_utils.validate_multiple("ab", rules)  # 長さが不足
        assert not result.is_valid
        assert len(result.errors) > 0
        
        result = self.validation_utils.validate_multiple("abc-123", rules)  # パターン不一致
        assert not result.is_valid
        assert len(result.errors) > 0


class TestDataValidator(UtilsTestBase):
    """DataValidatorクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.data_validator = DataValidator(self.config_manager, self.logger)
        self.test_data = ValidationTestHelper.create_test_data_samples()
    
    def test_validate_dictionary(self):
        """辞書データ検証テスト"""
        schema = {
            "name": {"required": True, "type": "string", "min_length": 2},
            "age": {"required": True, "type": "integer", "min_value": 0, "max_value": 150},
            "email": {"required": False, "type": "email"}
        }
        
        # 有効なデータ
        valid_data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com"
        }
        result = self.data_validator.validate_dictionary(valid_data, schema)
        assert result.is_valid
        
        # 無効なデータ（必須項目不足）
        invalid_data1 = {
            "age": 30
        }
        result = self.data_validator.validate_dictionary(invalid_data1, schema)
        assert not result.is_valid
        assert "name" in str(result.errors)
        
        # 無効なデータ（型不一致）
        invalid_data2 = {
            "name": "John",
            "age": "thirty",  # 文字列だが整数が期待される
            "email": "john@example.com"
        }
        result = self.data_validator.validate_dictionary(invalid_data2, schema)
        assert not result.is_valid
        
        # 無効なデータ（範囲外）
        invalid_data3 = {
            "name": "John",
            "age": 200,  # 範囲外
            "email": "john@example.com"
        }
        result = self.data_validator.validate_dictionary(invalid_data3, schema)
        assert not result.is_valid
    
    def test_validate_list(self):
        """リストデータ検証テスト"""
        # 文字列リストの検証
        string_list = ["apple", "banana", "cherry"]
        result = self.data_validator.validate_list(string_list, item_type="string")
        assert result.is_valid
        
        # 混合型リスト（無効）
        mixed_list = ["apple", 123, "cherry"]
        result = self.data_validator.validate_list(mixed_list, item_type="string")
        assert not result.is_valid
        
        # 整数リストの検証
        int_list = [1, 2, 3, 4, 5]
        result = self.data_validator.validate_list(int_list, item_type="integer")
        assert result.is_valid
        
        # 範囲チェック付きリスト
        result = self.data_validator.validate_list(int_list, item_type="integer", min_value=1, max_value=10)
        assert result.is_valid
        
        out_of_range_list = [1, 2, 15, 4, 5]  # 15が範囲外
        result = self.data_validator.validate_list(out_of_range_list, item_type="integer", min_value=1, max_value=10)
        assert not result.is_valid
        
        # リスト長の検証
        result = self.data_validator.validate_list(int_list, min_length=3, max_length=10)
        assert result.is_valid
        
        result = self.data_validator.validate_list(int_list, min_length=10)
        assert not result.is_valid
    
    def test_validate_nested_data(self):
        """ネストしたデータ検証テスト"""
        schema = {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "required": True},
                    "contacts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "choices": ["email", "phone"]},
                                "value": {"type": "string", "required": True}
                            }
                        }
                    }
                }
            }
        }
        
        # 有効なネストデータ
        valid_nested = {
            "user": {
                "name": "John Doe",
                "contacts": [
                    {"type": "email", "value": "john@example.com"},
                    {"type": "phone", "value": "123-456-7890"}
                ]
            }
        }
        result = self.data_validator.validate_nested(valid_nested, schema)
        assert result.is_valid
        
        # 無効なネストデータ
        invalid_nested = {
            "user": {
                "name": "John Doe",
                "contacts": [
                    {"type": "invalid_type", "value": "john@example.com"}  # 無効な選択肢
                ]
            }
        }
        result = self.data_validator.validate_nested(invalid_nested, schema)
        assert not result.is_valid
    
    def test_validate_data_types(self):
        """データ型検証テスト"""
        # 文字列型
        assert self.data_validator.validate_type("hello", "string").is_valid
        assert not self.data_validator.validate_type(123, "string").is_valid
        
        # 整数型
        assert self.data_validator.validate_type(123, "integer").is_valid
        assert not self.data_validator.validate_type("123", "integer").is_valid
        assert not self.data_validator.validate_type(12.34, "integer").is_valid
        
        # 浮動小数点型
        assert self.data_validator.validate_type(12.34, "float").is_valid
        assert self.data_validator.validate_type(123, "float").is_valid  # 整数も浮動小数点として有効
        assert not self.data_validator.validate_type("12.34", "float").is_valid
        
        # ブール型
        assert self.data_validator.validate_type(True, "boolean").is_valid
        assert self.data_validator.validate_type(False, "boolean").is_valid
        assert not self.data_validator.validate_type("true", "boolean").is_valid
        
        # リスト型
        assert self.data_validator.validate_type([1, 2, 3], "array").is_valid
        assert not self.data_validator.validate_type({"a": 1}, "array").is_valid
        
        # オブジェクト型
        assert self.data_validator.validate_type({"a": 1}, "object").is_valid
        assert not self.data_validator.validate_type([1, 2, 3], "object").is_valid


class TestSchemaValidator(UtilsTestBase):
    """SchemaValidatorクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.schema_validator = SchemaValidator(self.config_manager, self.logger)
        self.test_schemas = ValidationTestHelper.create_test_schemas()
    
    def test_validate_json_schema(self):
        """JSONスキーマ検証テスト"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number", "minimum": 0},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name", "age"]
        }
        
        # 有効なデータ
        valid_data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com"
        }
        result = self.schema_validator.validate_json_schema(valid_data, schema)
        assert result.is_valid
        
        # 無効なデータ
        invalid_data = {
            "name": "John Doe"
            # age が不足
        }
        result = self.schema_validator.validate_json_schema(invalid_data, schema)
        assert not result.is_valid
    
    def test_validate_xml_schema(self):
        """XMLスキーマ検証テスト"""
        xsd_schema = """
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
            <xs:element name="person">
                <xs:complexType>
                    <xs:sequence>
                        <xs:element name="name" type="xs:string"/>
                        <xs:element name="age" type="xs:int"/>
                    </xs:sequence>
                </xs:complexType>
            </xs:element>
        </xs:schema>
        """
        
        # 有効なXML
        valid_xml = """
        <person>
            <name>John Doe</name>
            <age>30</age>
        </person>
        """
        result = self.schema_validator.validate_xml_schema(valid_xml, xsd_schema)
        assert result.is_valid
        
        # 無効なXML
        invalid_xml = """
        <person>
            <name>John Doe</name>
            <!-- age要素が不足 -->
        </person>
        """
        result = self.schema_validator.validate_xml_schema(invalid_xml, xsd_schema)
        assert not result.is_valid
    
    def test_create_schema_from_data(self):
        """データからスキーマ生成テスト"""
        sample_data = {
            "name": "John Doe",
            "age": 30,
            "email": "john@example.com",
            "active": True,
            "scores": [85, 90, 78]
        }
        
        schema = self.schema_validator.create_schema_from_data(sample_data)
        
        assert schema is not None
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "number"
        assert schema["properties"]["active"]["type"] == "boolean"
        assert schema["properties"]["scores"]["type"] == "array"
    
    def test_validate_schema_compatibility(self):
        """スキーマ互換性検証テスト"""
        old_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"}
            },
            "required": ["name"]
        }
        
        # 互換性のある新スキーマ（フィールド追加）
        compatible_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"},
                "email": {"type": "string"}  # 新しいフィールド（オプション）
            },
            "required": ["name"]
        }
        
        result = self.schema_validator.validate_schema_compatibility(old_schema, compatible_schema)
        assert result.is_valid
        
        # 互換性のない新スキーマ（必須フィールド追加）
        incompatible_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"},
                "email": {"type": "string"}
            },
            "required": ["name", "email"]  # 新しい必須フィールド
        }
        
        result = self.schema_validator.validate_schema_compatibility(old_schema, incompatible_schema)
        assert not result.is_valid


class TestFileValidator(UtilsTestBase):
    """FileValidatorクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.file_validator = FileValidator(self.config_manager, self.logger)
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_file_existence(self):
        """ファイル存在検証テスト"""
        # 存在するファイルを作成
        existing_file = Path(self.temp_dir) / "existing.txt"
        existing_file.write_text("test content")
        
        # 存在するファイル
        result = self.file_validator.validate_file_existence(str(existing_file))
        assert result.is_valid
        
        # 存在しないファイル
        non_existing_file = Path(self.temp_dir) / "non_existing.txt"
        result = self.file_validator.validate_file_existence(str(non_existing_file))
        assert not result.is_valid
    
    def test_validate_file_extension(self):
        """ファイル拡張子検証テスト"""
        allowed_extensions = [".txt", ".py", ".json"]
        
        # 許可された拡張子
        result = self.file_validator.validate_file_extension("test.txt", allowed_extensions)
        assert result.is_valid
        
        result = self.file_validator.validate_file_extension("script.py", allowed_extensions)
        assert result.is_valid
        
        # 許可されていない拡張子
        result = self.file_validator.validate_file_extension("test.exe", allowed_extensions)
        assert not result.is_valid
        
        result = self.file_validator.validate_file_extension("document.doc", allowed_extensions)
        assert not result.is_valid
    
    def test_validate_file_size(self):
        """ファイルサイズ検証テスト"""
        # テストファイルを作成
        test_file = Path(self.temp_dir) / "size_test.txt"
        test_content = "A" * 1000  # 1000バイト
        test_file.write_text(test_content)
        
        # サイズ制限内
        result = self.file_validator.validate_file_size(str(test_file), max_size=2000)
        assert result.is_valid
        
        # サイズ制限超過
        result = self.file_validator.validate_file_size(str(test_file), max_size=500)
        assert not result.is_valid
        
        # 最小サイズチェック
        result = self.file_validator.validate_file_size(str(test_file), min_size=500, max_size=2000)
        assert result.is_valid
        
        result = self.file_validator.validate_file_size(str(test_file), min_size=1500)
        assert not result.is_valid
    
    def test_validate_file_content(self):
        """ファイル内容検証テスト"""
        # JSONファイルテスト
        json_file = Path(self.temp_dir) / "test.json"
        json_file.write_text('{"name": "test", "value": 123}')
        
        result = self.file_validator.validate_file_content(str(json_file), content_type="json")
        assert result.is_valid
        
        # 無効なJSONファイル
        invalid_json_file = Path(self.temp_dir) / "invalid.json"
        invalid_json_file.write_text('{"name": "test", "value":}')  # 無効なJSON
        
        result = self.file_validator.validate_file_content(str(invalid_json_file), content_type="json")
        assert not result.is_valid
        
        # XMLファイルテスト
        xml_file = Path(self.temp_dir) / "test.xml"
        xml_file.write_text('<?xml version="1.0"?><root><item>value</item></root>')
        
        result = self.file_validator.validate_file_content(str(xml_file), content_type="xml")
        assert result.is_valid
        
        # 無効なXMLファイル
        invalid_xml_file = Path(self.temp_dir) / "invalid.xml"
        invalid_xml_file.write_text('<root><item>value</root>')  # 閉じタグが不正
        
        result = self.file_validator.validate_file_content(str(invalid_xml_file), content_type="xml")
        assert not result.is_valid
    
    def test_validate_file_encoding(self):
        """ファイルエンコーディング検証テスト"""
        # UTF-8ファイル
        utf8_file = Path(self.temp_dir) / "utf8.txt"
        utf8_file.write_text("Hello 世界", encoding="utf-8")
        
        result = self.file_validator.validate_file_encoding(str(utf8_file), expected_encoding="utf-8")
        assert result.is_valid
        
        # Shift_JISファイル
        sjis_file = Path(self.temp_dir) / "sjis.txt"
        sjis_file.write_text("Hello 世界", encoding="shift_jis")
        
        result = self.file_validator.validate_file_encoding(str(sjis_file), expected_encoding="shift_jis")
        assert result.is_valid
        
        # エンコーディング不一致
        result = self.file_validator.validate_file_encoding(str(utf8_file), expected_encoding="shift_jis")
        assert not result.is_valid
    
    def test_validate_file_permissions(self):
        """ファイル権限検証テスト"""
        # テストファイルを作成
        test_file = Path(self.temp_dir) / "permission_test.txt"
        test_file.write_text("test content")
        
        # 読み取り権限チェック
        result = self.file_validator.validate_file_permissions(str(test_file), readable=True)
        assert result.is_valid
        
        # 書き込み権限チェック
        result = self.file_validator.validate_file_permissions(str(test_file), writable=True)
        assert result.is_valid
        
        # 実行権限チェック（通常のテキストファイルは実行権限なし）
        result = self.file_validator.validate_file_permissions(str(test_file), executable=True)
        # OSによって結果が異なる可能性があるため、結果の型のみチェック
        assert isinstance(result.is_valid, bool)
    
    def test_validate_directory(self):
        """ディレクトリ検証テスト"""
        # 存在するディレクトリ
        result = self.file_validator.validate_directory(self.temp_dir)
        assert result.is_valid
        
        # 存在しないディレクトリ
        non_existing_dir = Path(self.temp_dir) / "non_existing"
        result = self.file_validator.validate_directory(str(non_existing_dir))
        assert not result.is_valid
        
        # ファイルをディレクトリとして検証（失敗するはず）
        test_file = Path(self.temp_dir) / "not_a_directory.txt"
        test_file.write_text("content")
        result = self.file_validator.validate_directory(str(test_file))
        assert not result.is_valid


class TestSecurityValidator(UtilsTestBase):
    """SecurityValidatorクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.security_validator = SecurityValidator(self.config_manager, self.logger)
        self.security_test_data = SecurityTestHelper.create_security_test_data()
    
    def test_validate_password_strength(self):
        """パスワード強度検証テスト"""
        # 強いパスワード
        strong_passwords = [
            "StrongP@ssw0rd123",
            "MySecure#Password2023",
            "C0mpl3x!P@ssw0rd"
        ]
        
        for password in strong_passwords:
            result = self.security_validator.validate_password_strength(password)
            assert result.is_valid, f"Strong password {password} should pass validation"
        
        # 弱いパスワード
        weak_passwords = [
            "password",          # 単純すぎる
            "123456",           # 数字のみ
            "PASSWORD",         # 大文字のみ
            "pass",             # 短すぎる
            "password123",      # 一般的なパターン
            ""                  # 空文字
        ]
        
        for password in weak_passwords:
            result = self.security_validator.validate_password_strength(password)
            assert not result.is_valid, f"Weak password {password} should fail validation"
    
    def test_validate_input_sanitization(self):
        """入力サニタイゼーション検証テスト"""
        # 安全な入力
        safe_inputs = [
            "Hello World",
            "user@example.com",
            "123-456-7890",
            "Normal text input"
        ]
        
        for input_text in safe_inputs:
            result = self.security_validator.validate_input_sanitization(input_text)
            assert result.is_valid, f"Safe input {input_text} should pass validation"
        
        # 危険な入力
        dangerous_inputs = [
            "<script>alert('XSS')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "{{7*7}}",  # テンプレートインジェクション
            "${7*7}",   # 式インジェクション
        ]
        
        for input_text in dangerous_inputs:
            result = self.security_validator.validate_input_sanitization(input_text)
            assert not result.is_valid, f"Dangerous input {input_text} should fail validation"
    
    def test_validate_sql_injection(self):
        """SQLインジェクション検証テスト"""
        # 安全なクエリ
        safe_queries = [
            "SELECT * FROM users WHERE id = ?",
            "INSERT INTO products (name, price) VALUES (?, ?)",
            "UPDATE users SET email = ? WHERE id = ?"
        ]
        
        for query in safe_queries:
            result = self.security_validator.validate_sql_injection(query)
            assert result.is_valid, f"Safe query should pass validation"
        
        # SQLインジェクションの可能性があるクエリ
        injection_queries = [
            "SELECT * FROM users WHERE id = '" + "1' OR '1'='1" + "'",
            "SELECT * FROM users WHERE name = 'admin'; DROP TABLE users; --'",
            "SELECT * FROM products WHERE price < 100 UNION SELECT * FROM users",
            "SELECT * FROM users WHERE id = 1; DELETE FROM users WHERE 1=1"
        ]
        
        for query in injection_queries:
            result = self.security_validator.validate_sql_injection(query)
            assert not result.is_valid, f"Injection query should fail validation"
    
    def test_validate_xss_prevention(self):
        """XSS防止検証テスト"""
        # 安全なHTML
        safe_html = [
            "<p>Hello World</p>",
            "<div class='content'>Safe content</div>",
            "<strong>Bold text</strong>",
            "Plain text without HTML"
        ]
        
        for html in safe_html:
            result = self.security_validator.validate_xss_prevention(html)
            assert result.is_valid, f"Safe HTML should pass validation"
        
        # XSSの可能性があるHTML
        xss_html = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<div onclick='alert(\"XSS\")'>Click me</div>",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<object data='javascript:alert(\"XSS\")'></object>",
            "<embed src='javascript:alert(\"XSS\")'></embed>"
        ]
        
        for html in xss_html:
            result = self.security_validator.validate_xss_prevention(html)
            assert not result.is_valid, f"XSS HTML should fail validation"
    
    def test_validate_csrf_token(self):
        """CSRFトークン検証テスト"""
        # 有効なトークン形式
        valid_tokens = [
            "abc123def456ghi789",
            "1234567890abcdef1234567890abcdef",
            "token_with_underscores_123",
            "TOKEN-WITH-DASHES-456"
        ]
        
        for token in valid_tokens:
            result = self.security_validator.validate_csrf_token(token)
            assert result.is_valid, f"Valid token format should pass validation"
        
        # 無効なトークン
        invalid_tokens = [
            "",                    # 空文字
            "short",              # 短すぎる
            "token with spaces",  # スペースを含む
            "token<script>",      # HTMLタグを含む
            None                  # None値
        ]
        
        for token in invalid_tokens:
            result = self.security_validator.validate_csrf_token(token)
            assert not result.is_valid, f"Invalid token should fail validation"
    
    def test_validate_file_upload_security(self):
        """ファイルアップロードセキュリティ検証テスト"""
        # 安全なファイル
        safe_files = [
            {"filename": "document.pdf", "content_type": "application/pdf"},
            {"filename": "image.jpg", "content_type": "image/jpeg"},
            {"filename": "data.csv", "content_type": "text/csv"},
            {"filename": "script.py", "content_type": "text/x-python"}
        ]
        
        for file_info in safe_files:
            result = self.security_validator.validate_file_upload_security(
                file_info["filename"], 
                file_info["content_type"]
            )
            assert result.is_valid, f"Safe file should pass validation"
        
        # 危険なファイル
        dangerous_files = [
            {"filename": "malware.exe", "content_type": "application/x-executable"},
            {"filename": "script.bat", "content_type": "application/x-bat"},
            {"filename": "shell.sh", "content_type": "application/x-sh"},
            {"filename": "macro.xlsm", "content_type": "application/vnd.ms-excel.sheet.macroEnabled.12"},
            {"filename": "../../../etc/passwd", "content_type": "text/plain"},  # パストラバーサル
            {"filename": "file.php.jpg", "content_type": "image/jpeg"}  # 偽装ファイル
        ]
        
        for file_info in dangerous_files:
            result = self.security_validator.validate_file_upload_security(
                file_info["filename"], 
                file_info["content_type"]
            )
            assert not result.is_valid, f"Dangerous file should fail validation"


class TestFormatValidator(UtilsTestBase):
    """FormatValidatorクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.format_validator = FormatValidator(self.config_manager, self.logger)
    
    def test_validate_json_format(self):
        """JSON形式検証テスト"""
        # 有効なJSON
        valid_json = [
            '{"name": "test", "value": 123}',
            '["item1", "item2", "item3"]',
            '{"nested": {"key": "value"}}',
            'null',
            'true',
            '42'
        ]
        
        for json_str in valid_json:
            result = self.format_validator.validate_json_format(json_str)
            assert result.is_valid, f"Valid JSON should pass validation: {json_str}"
        
        # 無効なJSON
        invalid_json = [
            '{"name": "test", "value":}',  # 値が不完全
            '{"name": "test" "value": 123}',  # カンマ不足
            "{'name': 'test'}",  # シングルクォート
            '{"name": "test",}',  # 末尾のカンマ
            'undefined',  # 未定義値
            ''  # 空文字
        ]
        
        for json_str in invalid_json:
            result = self.format_validator.validate_json_format(json_str)
            assert not result.is_valid, f"Invalid JSON should fail validation: {json_str}"
    
    def test_validate_xml_format(self):
        """XML形式検証テスト"""
        # 有効なXML
        valid_xml = [
            '<?xml version="1.0"?><root><item>value</item></root>',
            '<root><item attr="value">content</item></root>',
            '<root/>',
            '<root><empty/></root>'
        ]
        
        for xml_str in valid_xml:
            result = self.format_validator.validate_xml_format(xml_str)
            assert result.is_valid, f"Valid XML should pass validation"
        
        # 無効なXML
        invalid_xml = [
            '<root><item>value</root>',  # 閉じタグが不正
            '<root><item>value</item>',  # 閉じタグ不足
            '<root attr="value>content</root>',  # 属性値のクォート不足
            '<root><item>value</item><item>value</root>',  # 構造が不正
            ''  # 空文字
        ]
        
        for xml_str in invalid_xml:
            result = self.format_validator.validate_xml_format(xml_str)
            assert not result.is_valid, f"Invalid XML should fail validation"
    
    def test_validate_csv_format(self):
        """CSV形式検証テスト"""
        # 有効なCSV
        valid_csv = [
            'name,age,email\nJohn,30,john@example.com\nJane,25,jane@example.com',
            '"Name","Age","Email"\n"John Doe",30,"john@example.com"',
            'a,b,c\n1,2,3\n4,5,6',
            'single_column\nvalue1\nvalue2'
        ]
        
        for csv_str in valid_csv:
            result = self.format_validator.validate_csv_format(csv_str)
            assert result.is_valid, f"Valid CSV should pass validation"
        
        # 無効なCSV（構造的な問題）
        invalid_csv = [
            'name,age,email\nJohn,30\nJane,25,jane@example.com,extra',  # 列数不一致
            '"Name","Age","Email\nJohn,30,john@example.com',  # クォート不完全
        ]
        
        for csv_str in invalid_csv:
            result = self.format_validator.validate_csv_format(csv_str)
            assert not result.is_valid, f"Invalid CSV should fail validation"
    
    def test_validate_yaml_format(self):
        """YAML形式検証テスト"""
        # 有効なYAML
        valid_yaml = [
            'name: test\nvalue: 123',
            'list:\n  - item1\n  - item2\n  - item3',
            'nested:\n  key: value\n  number: 42',
            'boolean: true\nnull_value: null'
        ]
        
        for yaml_str in valid_yaml:
            result = self.format_validator.validate_yaml_format(yaml_str)
            assert result.is_valid, f"Valid YAML should pass validation"
        
        # 無効なYAML
        invalid_yaml = [
            'name: test\n  value: 123',  # インデント不正
            'list:\n- item1\n  - item2',  # インデント不一致
            'name: test\nvalue:',  # 値が不完全
            'name: "test\nvalue: 123'  # クォート不完全
        ]
        
        for yaml_str in invalid_yaml:
            result = self.format_validator.validate_yaml_format(yaml_str)
            assert not result.is_valid, f"Invalid YAML should fail validation"
    
    def test_validate_code_syntax(self):
        """コード構文検証テスト"""
        # 有効なPythonコード
        valid_python = [
            'def hello():\n    print("Hello, World!")',
            'x = 1\ny = 2\nz = x + y',
            'class MyClass:\n    def __init__(self):\n        self.value = 42',
            'import os\nprint(os.getcwd())'
        ]
        
        for code in valid_python:
            result = self.format_validator.validate_code_syntax(code, language='python')
            assert result.is_valid, f"Valid Python code should pass validation"
        
        # 無効なPythonコード
        invalid_python = [
            'def hello(\n    print("Hello")',  # 構文エラー
            'x = 1\ny = 2\nz = x +',  # 不完全な式
            'if True\n    print("test")',  # コロン不足
            'def hello():\nprint("indentation error")'  # インデントエラー
        ]
        
        for code in invalid_python:
            result = self.format_validator.validate_code_syntax(code, language='python')
            assert not result.is_valid, f"Invalid Python code should fail validation"


class TestBusinessRuleValidator(UtilsTestBase):
    """BusinessRuleValidatorクラスのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.business_validator = BusinessRuleValidator(self.config_manager, self.logger)
    
    def test_validate_age_rules(self):
        """年齢ルール検証テスト"""
        # 有効な年齢
        valid_ages = [0, 18, 25, 65, 100]
        for age in valid_ages:
            result = self.business_validator.validate_age_rules(age)
            assert result.is_valid, f"Valid age {age} should pass validation"
        
        # 無効な年齢
        invalid_ages = [-1, 151, 200]
        for age in invalid_ages:
            result = self.business_validator.validate_age_rules(age)
            assert not result.is_valid, f"Invalid age {age} should fail validation"
    
    def test_validate_business_hours(self):
        """営業時間ルール検証テスト"""
        from datetime import time
        
        # 営業時間内
        business_hours = [
            time(9, 0),   # 9:00
            time(12, 0),  # 12:00
            time(17, 0),  # 17:00
        ]
        
        for hour in business_hours:
            result = self.business_validator.validate_business_hours(hour)
            assert result.is_valid, f"Business hour {hour} should pass validation"
        
        # 営業時間外
        non_business_hours = [
            time(8, 0),   # 8:00 (営業開始前)
            time(18, 0),  # 18:00 (営業終了後)
            time(22, 0),  # 22:00 (営業終了後)
        ]
        
        for hour in non_business_hours:
            result = self.business_validator.validate_business_hours(hour)
            assert not result.is_valid, f"Non-business hour {hour} should fail validation"
    
    def test_validate_price_rules(self):
        """価格ルール検証テスト"""
        # 有効な価格
        valid_prices = [0.01, 100.00, 999.99, 10000.00]
        for price in valid_prices:
            result = self.business_validator.validate_price_rules(price)
            assert result.is_valid, f"Valid price {price} should pass validation"
        
        # 無効な価格
        invalid_prices = [-1.00, 0.00, 100000.00]  # 負の値、0、上限超過
        for price in invalid_prices:
            result = self.business_validator.validate_price_rules(price)
            assert not result.is_valid, f"Invalid price {price} should fail validation"
    
    def test_validate_inventory_rules(self):
        """在庫ルール検証テスト"""
        # 有効な在庫数
        valid_inventory = [0, 1, 100, 1000]
        for inventory in valid_inventory:
            result = self.business_validator.validate_inventory_rules(inventory)
            assert result.is_valid, f"Valid inventory {inventory} should pass validation"
        
        # 無効な在庫数
        invalid_inventory = [-1, -10]  # 負の値
        for inventory in invalid_inventory:
            result = self.business_validator.validate_inventory_rules(inventory)
            assert not result.is_valid, f"Invalid inventory {inventory} should fail validation"
    
    def test_validate_discount_rules(self):
        """割引ルール検証テスト"""
        # 有効な割引率
        valid_discounts = [0.0, 0.1, 0.5, 0.9, 1.0]  # 0%から100%
        for discount in valid_discounts:
            result = self.business_validator.validate_discount_rules(discount)
            assert result.is_valid, f"Valid discount {discount} should pass validation"
        
        # 無効な割引率
        invalid_discounts = [-0.1, 1.1, 2.0]  # 負の値、100%超過
        for discount in invalid_discounts:
            result = self.business_validator.validate_discount_rules(discount)
            assert not result.is_valid, f"Invalid discount {discount} should fail validation"


class TestValidationResult:
    """ValidationResultクラスのテストクラス"""
    
    def test_validation_result_creation(self):
        """ValidationResult作成テスト"""
        # 成功結果
        success_result = ValidationResult(is_valid=True)
        assert success_result.is_valid is True
        assert success_result.errors == []
        assert success_result.warnings == []
        
        # 失敗結果
        error_result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        assert error_result.is_valid is False
        assert len(error_result.errors) == 2
        assert len(error_result.warnings) == 1
    
    def test_validation_result_methods(self):
        """ValidationResultメソッドテスト"""
        result = ValidationResult(is_valid=False, errors=["Test error"])
        
        # エラー追加
        result.add_error("Another error")
        assert len(result.errors) == 2
        assert "Another error" in result.errors
        
        # 警告追加
        result.add_warning("Test warning")
        assert len(result.warnings) == 1
        assert "Test warning" in result.warnings
        
        # 文字列表現
        str_result = str(result)
        assert "Test error" in str_result
        assert "Another error" in str_result


class TestValidationUtilsIntegration(UtilsTestBase):
    """ValidationUtils統合テスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        super().setup_method()
        self.validation_utils = ValidationUtils(self.config_manager, self.logger)
        self.data_validator = DataValidator(self.config_manager, self.logger)
        self.security_validator = SecurityValidator(self.config_manager, self.logger)
    
    def test_user_registration_validation(self):
        """ユーザー登録検証統合テスト"""
        # 有効なユーザーデータ
        valid_user = {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "SecureP@ssw0rd123",
            "age": 25,
            "phone": "03-1234-5678"
        }
        
        # 各フィールドの検証
        username_result = self.validation_utils.validate_pattern(
            valid_user["username"], r"^[a-zA-Z0-9_]{3,20}$"
        )
        assert username_result.is_valid
        
        email_result = self.validation_utils.validate_email(valid_user["email"])
        assert email_result.is_valid
        
        password_result = self.security_validator.validate_password_strength(valid_user["password"])
        assert password_result.is_valid
        
        age_result = self.validation_utils.validate_numeric(
            str(valid_user["age"]), numeric_type='int', min_value=0, max_value=150
        )
        assert age_result.is_valid
        
        phone_result = self.validation_utils.validate_phone_number(valid_user["phone"])
        assert phone_result.is_valid
    
    def test_file_upload_validation_workflow(self):
        """ファイルアップロード検証ワークフローテスト"""
        # テストファイル情報
        file_info = {
            "filename": "document.pdf",
            "content_type": "application/pdf",
            "size": 1024 * 1024,  # 1MB
            "content": b"%PDF-1.4\n%test content"
        }
        
        # ファイル拡張子検証
        file_validator = FileValidator(self.config_manager, self.logger)
        extension_result = file_validator.validate_file_extension(
            file_info["filename"], [".pdf", ".doc", ".docx"]
        )
        assert extension_result.is_valid
        
        # ファイルサイズ検証
        size_result = file_validator.validate_file_size_from_bytes(
            file_info["size"], max_size=5 * 1024 * 1024  # 5MB制限
        )
        assert size_result.is_valid
        
        # セキュリティ検証
        security_result = self.security_validator.validate_file_upload_security(
            file_info["filename"], file_info["content_type"]
        )
        assert security_result.is_valid
    
    def test_api_input_validation_workflow(self):
        """API入力検証ワークフローテスト"""
        # APIリクエストデータ
        api_request = {
            "action": "create_user",
            "data": {
                "name": "John Doe",
                "email": "john@example.com",
                "role": "user"
            },
            "csrf_token": "abc123def456ghi789"
        }
        
        # 入力サニタイゼーション
        for key, value in api_request["data"].items():
            if isinstance(value, str):
                sanitization_result = self.security_validator.validate_input_sanitization(value)
                assert sanitization_result.is_valid, f"Field {key} failed sanitization"
        
        # CSRFトークン検証
        csrf_result = self.security_validator.validate_csrf_token(api_request["csrf_token"])
        assert csrf_result.is_valid
        
        # 選択肢検証
        role_result = self.validation_utils.validate_choice(
            api_request["data"]["role"], ["admin", "user", "guest"]
        )
        assert role_result.is_valid
    
    def test_configuration_validation_workflow(self):
        """設定検証ワークフローテスト"""
        # 設定データ
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "myapp",
                "ssl": True
            },
            "cache": {
                "ttl": 3600,
                "max_size": 1000
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        }
        
        # データベース設定検証
        db_config = config_data["database"]
        port_result = self.validation_utils.validate_numeric(
            str(db_config["port"]), numeric_type='int', min_value=1, max_value=65535
        )
        assert port_result.is_valid
        
        # キャッシュ設定検証
        cache_config = config_data["cache"]
        ttl_result = self.validation_utils.validate_numeric(
            str(cache_config["ttl"]), numeric_type='int', min_value=0
        )
        assert ttl_result.is_valid
        
        # ログレベル検証
        log_config = config_data["logging"]
        level_result = self.validation_utils.validate_choice(
            log_config["level"], ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        assert level_result.is_valid


if __name__ == '__main__':
    pytest.main([__file__])


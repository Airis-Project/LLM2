# src/utils/validation_utils.py
"""
バリデーションユーティリティ
入力値検証に関する共通機能を提供
"""

import re
import os
import ipaddress
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import yaml
from datetime import datetime, date
from urllib.parse import urlparse

from ..core.logger import get_logger


class ValidationLevel(Enum):
    """バリデーションレベル"""
    STRICT = "strict"
    NORMAL = "normal"
    LENIENT = "lenient"


@dataclass
class ValidationResult:
    """バリデーション結果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    value: Any = None
    
    def add_error(self, message: str):
        """エラーを追加"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """警告を追加"""
        self.warnings.append(message)
    
    def has_errors(self) -> bool:
        """エラーがあるかチェック"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """警告があるかチェック"""
        return len(self.warnings) > 0


class ValidationUtils:
    """バリデーションユーティリティクラス"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # 正規表現パターン
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        self.url_pattern = re.compile(
            r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
        )
        self.phone_pattern = re.compile(
            r'^(?:\+81|0)[0-9]{1,4}-?[0-9]{1,4}-?[0-9]{4}$'
        )
        self.postal_code_pattern = re.compile(
            r'^\d{3}-?\d{4}$'
        )
        
        # プログラミング言語のファイル拡張子
        self.programming_extensions = {
            '.py', '.js', '.ts', '.html', '.htm', '.css', '.scss', '.sass',
            '.json', '.xml', '.yaml', '.yml', '.md', '.txt', '.sql',
            '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.php', '.rb',
            '.go', '.rs', '.swift', '.kt', '.dart', '.vue', '.jsx', '.tsx'
        }
        
        # 危険なファイル拡張子
        self.dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.msi', '.dll', '.sys', '.drv'
        }
    
    def validate_required(self, value: Any, field_name: str = "値") -> ValidationResult:
        """必須チェック"""
        result = ValidationResult(True, [], [])
        
        try:
            if value is None:
                result.add_error(f"{field_name}は必須です")
            elif isinstance(value, str) and not value.strip():
                result.add_error(f"{field_name}は必須です")
            elif isinstance(value, (list, dict, tuple)) and len(value) == 0:
                result.add_error(f"{field_name}は必須です")
            else:
                result.value = value
            
            return result
            
        except Exception as e:
            self.logger.error(f"必須チェックエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_string(self, value: Any, field_name: str = "文字列",
                       min_length: int = None, max_length: int = None,
                       pattern: str = None, allowed_chars: str = None) -> ValidationResult:
        """文字列バリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            # 型チェック
            if not isinstance(value, str):
                result.add_error(f"{field_name}は文字列である必要があります")
                return result
            
            # 長さチェック
            if min_length is not None and len(value) < min_length:
                result.add_error(f"{field_name}は{min_length}文字以上である必要があります")
            
            if max_length is not None and len(value) > max_length:
                result.add_error(f"{field_name}は{max_length}文字以下である必要があります")
            
            # パターンチェック
            if pattern and not re.match(pattern, value):
                result.add_error(f"{field_name}の形式が正しくありません")
            
            # 許可文字チェック
            if allowed_chars:
                invalid_chars = set(value) - set(allowed_chars)
                if invalid_chars:
                    result.add_error(f"{field_name}に使用できない文字が含まれています: {''.join(invalid_chars)}")
            
            if result.is_valid:
                result.value = value
            
            return result
            
        except Exception as e:
            self.logger.error(f"文字列バリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_number(self, value: Any, field_name: str = "数値",
                       min_value: Union[int, float] = None,
                       max_value: Union[int, float] = None,
                       allow_float: bool = True) -> ValidationResult:
        """数値バリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            # 型チェック・変換
            if isinstance(value, str):
                try:
                    if allow_float and '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    result.add_error(f"{field_name}は有効な数値である必要があります")
                    return result
            elif not isinstance(value, (int, float)):
                result.add_error(f"{field_name}は数値である必要があります")
                return result
            
            # 整数チェック
            if not allow_float and isinstance(value, float) and not value.is_integer():
                result.add_error(f"{field_name}は整数である必要があります")
            
            # 範囲チェック
            if min_value is not None and value < min_value:
                result.add_error(f"{field_name}は{min_value}以上である必要があります")
            
            if max_value is not None and value > max_value:
                result.add_error(f"{field_name}は{max_value}以下である必要があります")
            
            if result.is_valid:
                result.value = int(value) if not allow_float and isinstance(value, float) else value
            
            return result
            
        except Exception as e:
            self.logger.error(f"数値バリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_email(self, value: Any, field_name: str = "メールアドレス") -> ValidationResult:
        """メールアドレスバリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            if not isinstance(value, str):
                result.add_error(f"{field_name}は文字列である必要があります")
                return result
            
            if not self.email_pattern.match(value):
                result.add_error(f"{field_name}の形式が正しくありません")
            else:
                result.value = value.lower()
            
            return result
            
        except Exception as e:
            self.logger.error(f"メールバリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_url(self, value: Any, field_name: str = "URL",
                    allowed_schemes: List[str] = None) -> ValidationResult:
        """URLバリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            if not isinstance(value, str):
                result.add_error(f"{field_name}は文字列である必要があります")
                return result
            
            try:
                parsed = urlparse(value)
                
                if not parsed.scheme:
                    result.add_error(f"{field_name}にスキーマが含まれていません")
                elif allowed_schemes and parsed.scheme not in allowed_schemes:
                    result.add_error(f"{field_name}のスキーマが許可されていません: {parsed.scheme}")
                
                if not parsed.netloc:
                    result.add_error(f"{field_name}にホスト名が含まれていません")
                
                if result.is_valid:
                    result.value = value
                
            except Exception:
                result.add_error(f"{field_name}の形式が正しくありません")
            
            return result
            
        except Exception as e:
            self.logger.error(f"URLバリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_ip_address(self, value: Any, field_name: str = "IPアドレス",
                           version: int = None) -> ValidationResult:
        """IPアドレスバリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            if not isinstance(value, str):
                result.add_error(f"{field_name}は文字列である必要があります")
                return result
            
            try:
                ip = ipaddress.ip_address(value)
                
                if version == 4 and not isinstance(ip, ipaddress.IPv4Address):
                    result.add_error(f"{field_name}はIPv4アドレスである必要があります")
                elif version == 6 and not isinstance(ip, ipaddress.IPv6Address):
                    result.add_error(f"{field_name}はIPv6アドレスである必要があります")
                
                if result.is_valid:
                    result.value = str(ip)
                
            except ValueError:
                result.add_error(f"{field_name}の形式が正しくありません")
            
            return result
            
        except Exception as e:
            self.logger.error(f"IPアドレスバリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_phone(self, value: Any, field_name: str = "電話番号") -> ValidationResult:
        """電話番号バリデーション（日本）"""
        result = ValidationResult(True, [], [])
        
        try:
            if not isinstance(value, str):
                result.add_error(f"{field_name}は文字列である必要があります")
                return result
            
            # ハイフンを除去して数字のみにする
            cleaned = re.sub(r'[-\s()]', '', value)
            
            if not self.phone_pattern.match(value):
                result.add_error(f"{field_name}の形式が正しくありません")
            else:
                result.value = value
            
            return result
            
        except Exception as e:
            self.logger.error(f"電話番号バリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_postal_code(self, value: Any, field_name: str = "郵便番号") -> ValidationResult:
        """郵便番号バリデーション（日本）"""
        result = ValidationResult(True, [], [])
        
        try:
            if not isinstance(value, str):
                result.add_error(f"{field_name}は文字列である必要があります")
                return result
            
            if not self.postal_code_pattern.match(value):
                result.add_error(f"{field_name}の形式が正しくありません（例: 123-4567）")
            else:
                result.value = value
            
            return result
            
        except Exception as e:
            self.logger.error(f"郵便番号バリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_date(self, value: Any, field_name: str = "日付",
                     date_format: str = "%Y-%m-%d",
                     min_date: date = None, max_date: date = None) -> ValidationResult:
        """日付バリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            parsed_date = None
            
            if isinstance(value, str):
                try:
                    parsed_date = datetime.strptime(value, date_format).date()
                except ValueError:
                    result.add_error(f"{field_name}の形式が正しくありません（形式: {date_format}）")
                    return result
            elif isinstance(value, datetime):
                parsed_date = value.date()
            elif isinstance(value, date):
                parsed_date = value
            else:
                result.add_error(f"{field_name}は日付である必要があります")
                return result
            
            # 範囲チェック
            if min_date and parsed_date < min_date:
                result.add_error(f"{field_name}は{min_date}以降である必要があります")
            
            if max_date and parsed_date > max_date:
                result.add_error(f"{field_name}は{max_date}以前である必要があります")
            
            if result.is_valid:
                result.value = parsed_date
            
            return result
            
        except Exception as e:
            self.logger.error(f"日付バリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_file_path(self, value: Any, field_name: str = "ファイルパス",
                          must_exist: bool = False, must_be_file: bool = False,
                          must_be_dir: bool = False, allowed_extensions: List[str] = None,
                          check_permissions: bool = False) -> ValidationResult:
        """ファイルパスバリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            if not isinstance(value, str):
                result.add_error(f"{field_name}は文字列である必要があります")
                return result
            
            path = Path(value)
            
            # 存在チェック
            if must_exist and not path.exists():
                result.add_error(f"{field_name}が存在しません: {value}")
                return result
            
            if path.exists():
                # ファイル・ディレクトリチェック
                if must_be_file and not path.is_file():
                    result.add_error(f"{field_name}はファイルである必要があります")
                
                if must_be_dir and not path.is_dir():
                    result.add_error(f"{field_name}はディレクトリである必要があります")
                
                # 権限チェック
                if check_permissions:
                    if not os.access(path, os.R_OK):
                        result.add_warning(f"{field_name}の読み取り権限がありません")
                    if not os.access(path, os.W_OK):
                        result.add_warning(f"{field_name}の書き込み権限がありません")
            
            # 拡張子チェック
            if allowed_extensions and path.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
                result.add_error(f"{field_name}の拡張子が許可されていません: {path.suffix}")
            
            # 危険な拡張子チェック
            if path.suffix.lower() in self.dangerous_extensions:
                result.add_warning(f"{field_name}は危険な可能性のあるファイル形式です: {path.suffix}")
            
            if result.is_valid:
                result.value = str(path.absolute())
            
            return result
            
        except Exception as e:
            self.logger.error(f"ファイルパスバリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_json(self, value: Any, field_name: str = "JSON") -> ValidationResult:
        """JSONバリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    result.value = parsed
                except json.JSONDecodeError as e:
                    result.add_error(f"{field_name}の形式が正しくありません: {e}")
            elif isinstance(value, (dict, list)):
                # 既にパース済みの場合はシリアライズ可能かチェック
                try:
                    json.dumps(value)
                    result.value = value
                except (TypeError, ValueError) as e:
                    result.add_error(f"{field_name}をJSONにシリアライズできません: {e}")
            else:
                result.add_error(f"{field_name}は文字列またはオブジェクトである必要があります")
            
            return result
            
        except Exception as e:
            self.logger.error(f"JSONバリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_yaml(self, value: Any, field_name: str = "YAML") -> ValidationResult:
        """YAMLバリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            if isinstance(value, str):
                try:
                    parsed = yaml.safe_load(value)
                    result.value = parsed
                except yaml.YAMLError as e:
                    result.add_error(f"{field_name}の形式が正しくありません: {e}")
            else:
                result.add_error(f"{field_name}は文字列である必要があります")
            
            return result
            
        except Exception as e:
            self.logger.error(f"YAMLバリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_list(self, value: Any, field_name: str = "リスト",
                     min_length: int = None, max_length: int = None,
                     item_validator: Callable = None) -> ValidationResult:
        """リストバリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            if not isinstance(value, list):
                result.add_error(f"{field_name}はリストである必要があります")
                return result
            
            # 長さチェック
            if min_length is not None and len(value) < min_length:
                result.add_error(f"{field_name}は{min_length}個以上の要素が必要です")
            
            if max_length is not None and len(value) > max_length:
                result.add_error(f"{field_name}は{max_length}個以下の要素である必要があります")
            
            # 各要素のバリデーション
            if item_validator:
                validated_items = []
                for i, item in enumerate(value):
                    item_result = item_validator(item, f"{field_name}[{i}]")
                    if not item_result.is_valid:
                        result.errors.extend(item_result.errors)
                        result.warnings.extend(item_result.warnings)
                    else:
                        validated_items.append(item_result.value)
                
                if result.is_valid:
                    result.value = validated_items
            else:
                result.value = value
            
            return result
            
        except Exception as e:
            self.logger.error(f"リストバリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_dict(self, value: Any, field_name: str = "辞書",
                     required_keys: List[str] = None,
                     optional_keys: List[str] = None,
                     key_validators: Dict[str, Callable] = None) -> ValidationResult:
        """辞書バリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            if not isinstance(value, dict):
                result.add_error(f"{field_name}は辞書である必要があります")
                return result
            
            # 必須キーチェック
            if required_keys:
                missing_keys = set(required_keys) - set(value.keys())
                if missing_keys:
                    result.add_error(f"{field_name}に必須キーが不足しています: {', '.join(missing_keys)}")
            
            # 許可されていないキーチェック
            if required_keys is not None or optional_keys is not None:
                allowed_keys = set()
                if required_keys:
                    allowed_keys.update(required_keys)
                if optional_keys:
                    allowed_keys.update(optional_keys)
                
                extra_keys = set(value.keys()) - allowed_keys
                if extra_keys:
                    result.add_warning(f"{field_name}に不明なキーが含まれています: {', '.join(extra_keys)}")
            
            # 各値のバリデーション
            if key_validators:
                validated_dict = {}
                for key, validator in key_validators.items():
                    if key in value:
                        key_result = validator(value[key], f"{field_name}.{key}")
                        if not key_result.is_valid:
                            result.errors.extend(key_result.errors)
                            result.warnings.extend(key_result.warnings)
                        else:
                            validated_dict[key] = key_result.value
                    elif required_keys and key in required_keys:
                        # 必須キーが不足している場合は既にエラーが追加されている
                        pass
                
                # バリデーション対象外のキーもコピー
                for key, val in value.items():
                    if key not in key_validators:
                        validated_dict[key] = val
                
                if result.is_valid:
                    result.value = validated_dict
            else:
                result.value = value
            
            return result
            
        except Exception as e:
            self.logger.error(f"辞書バリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_choice(self, value: Any, choices: List[Any],
                       field_name: str = "選択値") -> ValidationResult:
        """選択肢バリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            if value not in choices:
                result.add_error(f"{field_name}は次の値から選択してください: {', '.join(map(str, choices))}")
            else:
                result.value = value
            
            return result
            
        except Exception as e:
            self.logger.error(f"選択肢バリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_custom(self, value: Any, validator_func: Callable,
                       field_name: str = "値") -> ValidationResult:
        """カスタムバリデーション"""
        result = ValidationResult(True, [], [])
        
        try:
            custom_result = validator_func(value)
            
            if isinstance(custom_result, ValidationResult):
                return custom_result
            elif isinstance(custom_result, bool):
                if not custom_result:
                    result.add_error(f"{field_name}のバリデーションに失敗しました")
                else:
                    result.value = value
            elif isinstance(custom_result, tuple) and len(custom_result) == 2:
                is_valid, message = custom_result
                if not is_valid:
                    result.add_error(message)
                else:
                    result.value = value
            else:
                result.add_error(f"カスタムバリデーターの戻り値が不正です")
            
            return result
            
        except Exception as e:
            self.logger.error(f"カスタムバリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result
    
    def validate_schema(self, data: Dict[str, Any], schema: Dict[str, Dict]) -> ValidationResult:
        """スキーマバリデーション"""
        result = ValidationResult(True, [], [])
        validated_data = {}
        
        try:
            for field_name, field_schema in schema.items():
                field_value = data.get(field_name)
                
                # 必須チェック
                if field_schema.get('required', False):
                    required_result = self.validate_required(field_value, field_name)
                    if not required_result.is_valid:
                        result.errors.extend(required_result.errors)
                        continue
                elif field_value is None:
                    # 必須でない場合はスキップ
                    continue
                
                # 型別バリデーション
                field_type = field_schema.get('type')
                field_result = None
                
                if field_type == 'string':
                    field_result = self.validate_string(
                        field_value, field_name,
                        min_length=field_schema.get('min_length'),
                        max_length=field_schema.get('max_length'),
                        pattern=field_schema.get('pattern')
                    )
                elif field_type == 'number':
                    field_result = self.validate_number(
                        field_value, field_name,
                        min_value=field_schema.get('min_value'),
                        max_value=field_schema.get('max_value'),
                        allow_float=field_schema.get('allow_float', True)
                    )
                elif field_type == 'email':
                    field_result = self.validate_email(field_value, field_name)
                elif field_type == 'url':
                    field_result = self.validate_url(field_value, field_name)
                elif field_type == 'file_path':
                    field_result = self.validate_file_path(
                        field_value, field_name,
                        must_exist=field_schema.get('must_exist', False)
                    )
                elif field_type == 'choice':
                    field_result = self.validate_choice(
                        field_value, field_schema.get('choices', []), field_name
                    )
                elif field_type == 'list':
                    field_result = self.validate_list(
                        field_value, field_name,
                        min_length=field_schema.get('min_length'),
                        max_length=field_schema.get('max_length')
                    )
                elif field_type == 'dict':
                    field_result = self.validate_dict(field_value, field_name)
                else:
                    # 型指定なしの場合はそのまま通す
                    field_result = ValidationResult(True, [], [])
                    field_result.value = field_value
                
                if field_result:
                    if not field_result.is_valid:
                        result.errors.extend(field_result.errors)
                        result.warnings.extend(field_result.warnings)
                    else:
                        validated_data[field_name] = field_result.value
            
            if result.is_valid:
                result.value = validated_data
            
            return result
            
        except Exception as e:
            self.logger.error(f"スキーマバリデーションエラー: {e}")
            result.add_error(f"バリデーションエラーが発生しました: {e}")
            return result


# グローバルインスタンス
_validation_utils: Optional[ValidationUtils] = None


def get_validation_utils() -> ValidationUtils:
    """グローバルバリデーションユーティリティを取得"""
    global _validation_utils
    if _validation_utils is None:
        _validation_utils = ValidationUtils()
    return _validation_utils

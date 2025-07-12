# config/config_schema.py
"""
設定スキーマ管理システム
JSONスキーマベースの設定検証とバリデーション
"""

import json
import jsonschema
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from src.core.logger import get_logger

logger = get_logger(__name__)


class SchemaType(Enum):
    """スキーマタイプ"""
    JSON_SCHEMA = "json_schema"
    PYDANTIC = "pydantic"
    CUSTOM = "custom"


@dataclass
class SchemaValidationResult:
    """スキーマ検証結果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    schema_name: str
    validated_at: datetime
    
    def __post_init__(self):
        if self.validated_at is None:
            self.validated_at = datetime.now()


class ConfigSchema:
    """設定スキーマ管理クラス"""
    
    def __init__(self, schema_dir: Union[str, Path] = None):
        self.schema_dir = Path(schema_dir) if schema_dir else Path("config")
        self.schema_dir.mkdir(parents=True, exist_ok=True)
        
        # スキーマキャッシュ
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, jsonschema.protocols.Validator] = {}
        
        # メインスキーマファイル
        self.main_schema_file = self.schema_dir / "schema.json"
        
        # 初期化
        self._load_schemas()
        
        logger.info(f"設定スキーマ管理初期化完了: {self.schema_dir}")
    
    def _load_schemas(self):
        """スキーマ読み込み"""
        try:
            # メインスキーマファイル読み込み
            if self.main_schema_file.exists():
                self._load_main_schema()
            
            # 個別スキーマファイル読み込み
            self._load_individual_schemas()
            
            # デフォルトスキーマ作成
            self._create_default_schemas()
            
            logger.info(f"スキーマ読み込み完了: {len(self._schemas)}個")
            
        except Exception as e:
            logger.error(f"スキーマ読み込みエラー: {e}")
            self._create_fallback_schemas()
    
    def _load_main_schema(self):
        """メインスキーマファイル読み込み"""
        try:
            with open(self.main_schema_file, 'r', encoding='utf-8') as f:
                main_schema = json.load(f)
            
            # プロパティから個別スキーマを抽出
            if 'properties' in main_schema:
                for section_name, section_schema in main_schema['properties'].items():
                    if section_name not in ['version', '_metadata']:
                        self._schemas[section_name] = section_schema
                        self._create_validator(section_name, section_schema)
            
            # 全体スキーマも保存
            self._schemas['_main'] = main_schema
            self._create_validator('_main', main_schema)
            
            logger.debug(f"メインスキーマ読み込み完了: {self.main_schema_file}")
            
        except Exception as e:
            logger.error(f"メインスキーマ読み込みエラー: {e}")
    
    def _load_individual_schemas(self):
        """個別スキーマファイル読み込み"""
        schema_files = list(self.schema_dir.glob("*_schema.json"))
        
        for schema_file in schema_files:
            try:
                section_name = schema_file.stem.replace('_schema', '')
                
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                
                self._schemas[section_name] = schema
                self._create_validator(section_name, schema)
                
                logger.debug(f"個別スキーマ読み込み: {section_name}")
                
            except Exception as e:
                logger.error(f"個別スキーマ読み込みエラー {schema_file}: {e}")
    
    def _create_validator(self, schema_name: str, schema: Dict[str, Any]):
        """バリデータ作成"""
        try:
            # JSONスキーマバリデータ作成
            validator_class = jsonschema.validators.validator_for(schema)
            validator_class.check_schema(schema)
            validator = validator_class(schema)
            
            self._validators[schema_name] = validator
            
        except Exception as e:
            logger.error(f"バリデータ作成エラー {schema_name}: {e}")
    
    def _create_default_schemas(self):
        """デフォルトスキーマ作成"""
        default_schemas = {
            'application': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'minLength': 1},
                    'version': {'type': 'string', 'pattern': r'^\d+\.\d+\.\d+$'},
                    'debug': {'type': 'boolean', 'default': False},
                    'log_level': {
                        'type': 'string',
                        'enum': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        'default': 'INFO'
                    }
                },
                'required': ['name', 'version']
            },
            'llm': {
                'type': 'object',
                'properties': {
                    'default_provider': {'type': 'string', 'minLength': 1},
                    'default_model': {'type': 'string', 'minLength': 1},
                    'timeout': {'type': 'number', 'minimum': 1.0, 'maximum': 300.0},
                    'retry_count': {'type': 'integer', 'minimum': 0, 'maximum': 10},
                    'providers': {
                        'type': 'object',
                        'patternProperties': {
                            '^[a-zA-Z][a-zA-Z0-9_]*$': {
                                'type': 'object',
                                'properties': {
                                    'enabled': {'type': 'boolean'},
                                    'api_key': {'type': 'string'},
                                    'base_url': {'type': 'string', 'format': 'uri'},
                                    'models': {
                                        'type': 'array',
                                        'items': {'type': 'string'},
                                        'minItems': 1
                                    }
                                },
                                'required': ['enabled', 'api_key']
                            }
                        }
                    }
                },
                'required': ['default_provider', 'providers']
            },
            'ui': {
                'type': 'object',
                'properties': {
                    'theme': {
                        'type': 'string',
                        'enum': ['light', 'dark', 'auto'],
                        'default': 'light'
                    },
                    'language': {'type': 'string', 'default': 'ja'},
                    'window': {
                        'type': 'object',
                        'properties': {
                            'width': {'type': 'integer', 'minimum': 400},
                            'height': {'type': 'integer', 'minimum': 300},
                            'maximized': {'type': 'boolean', 'default': False}
                        }
                    },
                    'chat': {
                        'type': 'object',
                        'properties': {
                            'font_size': {'type': 'integer', 'minimum': 8, 'maximum': 24},
                            'font_family': {'type': 'string'},
                            'auto_save': {'type': 'boolean', 'default': True},
                            'history_limit': {'type': 'integer', 'minimum': 10}
                        }
                    }
                }
            },
            'security': {
                'type': 'object',
                'properties': {
                    'encryption_enabled': {'type': 'boolean', 'default': False},
                    'api_key_encryption': {'type': 'boolean', 'default': True},
                    'session_timeout': {'type': 'integer', 'minimum': 60},
                    'max_login_attempts': {'type': 'integer', 'minimum': 1}
                }
            },
            'logging': {
                'type': 'object',
                'properties': {
                    'level': {
                        'type': 'string',
                        'enum': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        'default': 'INFO'
                    },
                    'file_path': {'type': 'string'},
                    'max_file_size': {'type': 'string', 'pattern': r'^\d+[KMGT]?B$'},
                    'backup_count': {'type': 'integer', 'minimum': 1},
                    'console_output': {'type': 'boolean', 'default': True},
                    'file_output': {'type': 'boolean', 'default': True}
                }
            }
        }
        
        # 未定義のスキーマを追加
        for schema_name, schema in default_schemas.items():
            if schema_name not in self._schemas:
                self._schemas[schema_name] = schema
                self._create_validator(schema_name, schema)
                logger.debug(f"デフォルトスキーマ作成: {schema_name}")
    
    def _create_fallback_schemas(self):
        """フォールバックスキーマ作成"""
        fallback_schema = {
            'type': 'object',
            'additionalProperties': True
        }
        
        self._schemas['_fallback'] = fallback_schema
        self._create_validator('_fallback', fallback_schema)
        
        logger.warning("フォールバックスキーマを使用")
    
    def validate_config(self, schema_name: str, config_data: Dict[str, Any]) -> SchemaValidationResult:
        """設定検証"""
        try:
            validator = self._validators.get(schema_name)
            if not validator:
                return SchemaValidationResult(
                    is_valid=False,
                    errors=[f"スキーマが見つかりません: {schema_name}"],
                    warnings=[],
                    schema_name=schema_name,
                    validated_at=datetime.now()
                )
            
            # 検証実行
            errors = []
            warnings = []
            
            try:
                validator.validate(config_data)
                is_valid = True
            except jsonschema.ValidationError as e:
                is_valid = False
                errors.append(f"検証エラー: {e.message}")
                
                # 詳細エラー情報
                if e.path:
                    errors.append(f"パス: {' -> '.join(str(p) for p in e.path)}")
                if e.schema_path:
                    errors.append(f"スキーマパス: {' -> '.join(str(p) for p in e.schema_path)}")
            
            except jsonschema.SchemaError as e:
                is_valid = False
                errors.append(f"スキーマエラー: {e.message}")
            
            # 警告チェック
            warnings.extend(self._check_warnings(schema_name, config_data))
            
            result = SchemaValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                schema_name=schema_name,
                validated_at=datetime.now()
            )
            
            if is_valid:
                logger.debug(f"設定検証成功: {schema_name}")
            else:
                logger.warning(f"設定検証失敗: {schema_name}, エラー: {len(errors)}個")
            
            return result
            
        except Exception as e:
            logger.error(f"設定検証エラー {schema_name}: {e}")
            return SchemaValidationResult(
                is_valid=False,
                errors=[f"検証処理エラー: {e}"],
                warnings=[],
                schema_name=schema_name,
                validated_at=datetime.now()
            )
    
    def _check_warnings(self, schema_name: str, config_data: Dict[str, Any]) -> List[str]:
        """警告チェック"""
        warnings = []
        
        try:
            schema = self._schemas.get(schema_name, {})
            
            # 非推奨設定チェック
            deprecated_keys = schema.get('_deprecated', [])
            for key in deprecated_keys:
                if key in config_data:
                    warnings.append(f"非推奨設定: {key}")
            
            # 必須だが未設定の推奨項目
            recommended_keys = schema.get('_recommended', [])
            for key in recommended_keys:
                if key not in config_data:
                    warnings.append(f"推奨設定が未設定: {key}")
            
            # セキュリティ警告
            if schema_name == 'security':
                if not config_data.get('encryption_enabled', False):
                    warnings.append("暗号化が無効になっています")
                if config_data.get('session_timeout', 3600) > 86400:
                    warnings.append("セッションタイムアウトが長すぎます")
            
            # LLM設定警告
            if schema_name == 'llm':
                providers = config_data.get('providers', {})
                for provider_name, provider_config in providers.items():
                    if not provider_config.get('api_key'):
                        warnings.append(f"APIキーが未設定: {provider_name}")
            
        except Exception as e:
            logger.error(f"警告チェックエラー: {e}")
        
        return warnings
    
    def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """スキーマ取得"""
        return self._schemas.get(schema_name)
    
    def list_schemas(self) -> List[str]:
        """スキーマ一覧取得"""
        return list(self._schemas.keys())
    
    def register_schema(self, schema_name: str, schema: Dict[str, Any]) -> bool:
        """スキーマ登録"""
        try:
            # スキーマ検証
            jsonschema.validators.validator_for(schema).check_schema(schema)
            
            # 登録
            self._schemas[schema_name] = schema
            self._create_validator(schema_name, schema)
            
            logger.info(f"スキーマ登録完了: {schema_name}")
            return True
            
        except Exception as e:
            logger.error(f"スキーマ登録エラー {schema_name}: {e}")
            return False
    
    def save_schema(self, schema_name: str, file_path: Optional[Path] = None) -> bool:
        """スキーマ保存"""
        try:
            schema = self._schemas.get(schema_name)
            if not schema:
                logger.error(f"スキーマが見つかりません: {schema_name}")
                return False
            
            if not file_path:
                file_path = self.schema_dir / f"{schema_name}_schema.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)
            
            logger.info(f"スキーマ保存完了: {schema_name} -> {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"スキーマ保存エラー {schema_name}: {e}")
            return False
    
    def validate_all_sections(self, config_data: Dict[str, Dict[str, Any]]) -> Dict[str, SchemaValidationResult]:
        """全セクション検証"""
        results = {}
        
        for section_name, section_data in config_data.items():
            if section_name.startswith('_'):
                continue  # メタデータはスキップ
            
            result = self.validate_config(section_name, section_data)
            results[section_name] = result
        
        return results
    
    def get_default_config(self, schema_name: str) -> Dict[str, Any]:
        """デフォルト設定生成"""
        try:
            schema = self._schemas.get(schema_name)
            if not schema:
                return {}
            
            return self._extract_defaults(schema)
            
        except Exception as e:
            logger.error(f"デフォルト設定生成エラー {schema_name}: {e}")
            return {}
    
    def _extract_defaults(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """スキーマからデフォルト値抽出"""
        defaults = {}
        
        if schema.get('type') == 'object' and 'properties' in schema:
            for key, prop_schema in schema['properties'].items():
                if 'default' in prop_schema:
                    defaults[key] = prop_schema['default']
                elif prop_schema.get('type') == 'object':
                    nested_defaults = self._extract_defaults(prop_schema)
                    if nested_defaults:
                        defaults[key] = nested_defaults
        
        return defaults
    
    def get_schema_info(self) -> Dict[str, Any]:
        """スキーマ情報取得"""
        return {
            'schemas_count': len(self._schemas),
            'validators_count': len(self._validators),
            'schema_names': list(self._schemas.keys()),
            'schema_dir': str(self.schema_dir),
            'main_schema_exists': self.main_schema_file.exists()
        }


# グローバルインスタンス
_config_schema_instance: Optional[ConfigSchema] = None


def get_config_schema() -> ConfigSchema:
    """ConfigSchemaのシングルトンインスタンスを取得"""
    global _config_schema_instance
    if _config_schema_instance is None:
        _config_schema_instance = ConfigSchema()
    return _config_schema_instance


# 使用例とテスト
if __name__ == "__main__":
    def test_config_schema():
        """設定スキーマテスト"""
        print("=== 設定スキーマテスト ===")
        
        try:
            schema = ConfigSchema()
            
            # スキーマ一覧表示
            print(f"登録スキーマ: {schema.list_schemas()}")
            
            # テスト設定
            test_config = {
                'name': 'Test App',
                'version': '1.0.0',
                'debug': True,
                'log_level': 'DEBUG'
            }
            
            # 検証テスト
            result = schema.validate_config('application', test_config)
            print(f"検証結果: {result.is_valid}")
            if result.errors:
                print(f"エラー: {result.errors}")
            if result.warnings:
                print(f"警告: {result.warnings}")
            
            # デフォルト設定生成
            defaults = schema.get_default_config('application')
            print(f"デフォルト設定: {defaults}")
            
            # スキーマ情報
            info = schema.get_schema_info()
            print(f"スキーマ情報: {info}")
            
        except Exception as e:
            print(f"テストエラー: {e}")
    
    test_config_schema()

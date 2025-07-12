#!/usr/bin/env python3
#config/config_validator.py
"""
設定検証システム
JSONスキーマベースの設定検証
"""

import json
import jsonschema
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.core.logger import get_logger

logger = get_logger(__name__)

class ConfigValidationError(Exception):
    """設定検証エラー"""
    pass

class ConfigValidator:
    """設定検証システム"""
    
    def __init__(self, schema_dir: Path = None):
        self.schema_dir = schema_dir or Path("schemas")
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self.load_schemas()
    
    def load_schemas(self):
        """スキーマ読み込み"""
        try:
            if self.schema_dir.exists():
                for schema_file in self.schema_dir.glob("*.json"):
                    schema_name = schema_file.stem
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema = json.load(f)
                    self._schemas[schema_name] = schema
                    logger.debug(f"スキーマ読み込み: {schema_name}")
            
            # 組み込みスキーマ登録
            self._register_builtin_schemas()
            
            logger.info(f"スキーマ読み込み完了: {len(self._schemas)}個")
            
        except Exception as e:
            logger.error(f"スキーマ読み込みエラー: {e}")
    
    def _register_builtin_schemas(self):
        """組み込みスキーマ登録"""
        builtin_schemas = {
            'app': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'minLength': 1},
                    'version': {'type': 'string', 'pattern': r'^\d+\.\d+\.\d+$'},
                    'debug': {'type': 'boolean'},
                    'log_level': {
                        'type': 'string',
                        'enum': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                    },
                    'auto_save': {'type': 'boolean'},
                    'backup_enabled': {'type': 'boolean'},
                    'max_backups': {'type': 'integer', 'minimum': 1}
                },
                'required': ['name', 'version'],
                'additionalProperties': True
            },
            'llm': {
                'type': 'object',
                'properties': {
                    'default_provider': {'type': 'string', 'minLength': 1},
                    'default_model': {'type': 'string', 'minLength': 1},
                    'timeout': {'type': 'number', 'minimum': 1.0, 'maximum': 300.0},
                    'retry_count': {'type': 'integer', 'minimum': 0, 'maximum': 10},
                    'max_tokens': {'type': 'integer', 'minimum': 1, 'maximum': 32768},
                    'temperature': {'type': 'number', 'minimum': 0.0, 'maximum': 2.0},
                    'top_p': {'type': 'number', 'minimum': 0.0, 'maximum': 1.0},
                    'providers': {
                        'type': 'object',
                        'patternProperties': {
                            '^[a-zA-Z][a-zA-Z0-9_]*$': {
                                'type': 'object',
                                'properties': {
                                    'api_key': {'type': 'string'},
                                    'base_url': {'type': 'string', 'format': 'uri'},
                                    'models': {
                                        'type': 'array',
                                        'items': {'type': 'string', 'minLength': 1},
                                        'minItems': 1
                                    },
                                    'enabled': {'type': 'boolean'},
                                    'timeout': {'type': 'number', 'minimum': 1.0},
                                    'retry_count': {'type': 'integer', 'minimum': 0},
                                    'rate_limit': {'type': 'integer', 'minimum': 1},
                                    'custom_headers': {
                                        'type': 'object',
                                        'patternProperties': {
                                            '^[a-zA-Z][a-zA-Z0-9-]*$': {'type': 'string'}
                                        }
                                    }
                                },
                                'required': ['base_url', 'models'],
                                'additionalProperties': False
                            }
                        }
                    }
                },
                'required': ['default_provider', 'default_model', 'providers'],
                'additionalProperties': True
            },
            'ui': {
                'type': 'object',
                'properties': {
                    'theme': {'type': 'string', 'enum': ['light', 'dark', 'auto']},
                    'language': {'type': 'string', 'pattern': r'^[a-z]{2}(-[A-Z]{2})?$'},
                    'font_family': {'type': 'string', 'minLength': 1},
                    'font_size': {'type': 'integer', 'minimum': 8, 'maximum': 72},
                    'window': {
                        'type': 'object',
                        'properties': {
                            'width': {'type': 'integer', 'minimum': 400, 'maximum': 4000},
                            'height': {'type': 'integer', 'minimum': 300, 'maximum': 3000},
                            'x': {'type': 'integer'},
                            'y': {'type': 'integer'},
                            'maximized': {'type': 'boolean'},
                            'fullscreen': {'type': 'boolean'}
                        },
                        'required': ['width', 'height'],
                        'additionalProperties': False
                    },
                    'chat': {
                        'type': 'object',
                        'properties': {
                            'auto_save': {'type': 'boolean'},
                            'history_limit': {'type': 'integer', 'minimum': 10, 'maximum': 10000},
                            'word_wrap': {'type': 'boolean'},
                            'syntax_highlight': {'type': 'boolean'},
                            'show_timestamps': {'type': 'boolean'},
                            'export_format': {'type': 'string', 'enum': ['json', 'markdown', 'html', 'txt']}
                        },
                        'additionalProperties': False
                    }
                },
                'required': ['theme', 'language'],
                'additionalProperties': True
            },
            'security': {
                'type': 'object',
                'properties': {
                    'encryption_enabled': {'type': 'boolean'},
                    'api_key_encryption': {'type': 'boolean'},
                    'session_timeout': {'type': 'integer', 'minimum': 300, 'maximum': 86400},
                    'max_login_attempts': {'type': 'integer', 'minimum': 1, 'maximum': 10},
                    'password_policy': {
                        'type': 'object',
                        'properties': {
                            'min_length': {'type': 'integer', 'minimum': 4, 'maximum': 128},
                            'require_uppercase': {'type': 'boolean'},
                            'require_lowercase': {'type': 'boolean'},
                            'require_numbers': {'type': 'boolean'},
                            'require_symbols': {'type': 'boolean'}
                        },
                        'additionalProperties': False
                    },
                    'allowed_hosts': {
                        'type': 'array',
                        'items': {'type': 'string', 'format': 'hostname'}
                    },
                    'ssl_verify': {'type': 'boolean'},
                    'proxy_settings': {
                        'type': 'object',
                        'properties': {
                            'enabled': {'type': 'boolean'},
                            'host': {'type': 'string'},
                            'port': {'type': 'integer', 'minimum': 1, 'maximum': 65535},
                            'username': {'type': 'string'},
                            'password': {'type': 'string'}
                        },
                        'additionalProperties': False
                    }
                },
                'required': ['encryption_enabled', 'session_timeout'],
                'additionalProperties': True
            }
        }
        
        for schema_name, schema in builtin_schemas.items():
            self._schemas[schema_name] = schema
    
    def register_schema(self, name: str, schema: Dict[str, Any]):
        """スキーマ登録"""
        try:
            # スキーマ自体の検証
            jsonschema.Draft7Validator.check_schema(schema)
            self._schemas[name] = schema
            logger.debug(f"スキーマ登録: {name}")
            
        except jsonschema.SchemaError as e:
            logger.error(f"無効なスキーマ {name}: {e}")
            raise ConfigValidationError(f"無効なスキーマ: {e}")
    
    def validate_section(self, section_name: str, data: Dict[str, Any]) -> bool:
        """セクション検証"""
        try:
            schema = self._schemas.get(section_name)
            if not schema:
                logger.warning(f"スキーマが見つかりません: {section_name}")
                return True  # スキーマがない場合は検証をスキップ
            
            # 検証実行
            validator = jsonschema.Draft7Validator(schema)
            errors = list(validator.iter_errors(data))
            
            if errors:
                error_messages = []
                for error in errors:
                    path = '.'.join(str(p) for p in error.path) if error.path else 'root'
                    error_messages.append(f"{path}: {error.message}")
                
                raise ConfigValidationError(
                    f"設定検証エラー ({section_name}):\n" + '\n'.join(error_messages)
                )
            
            logger.debug(f"設定検証成功: {section_name}")
            return True
            
        except jsonschema.ValidationError as e:
            logger.error(f"設定検証エラー {section_name}: {e}")
            raise ConfigValidationError(f"設定検証エラー: {e}")
    
    def validate_value(self, section_name: str, key: str, value: Any) -> bool:
        """個別値検証"""
        try:
            schema = self._schemas.get(section_name)
            if not schema:
                return True
            
            # キーのスキーマ抽出
            properties = schema.get('properties', {})
            if key not in properties:
                return True  # プロパティが定義されていない場合はスキップ
            
            key_schema = properties[key]
            
            # 検証実行
            jsonschema.validate(value, key_schema)
            return True
            
        except jsonschema.ValidationError as e:
            logger.error(f"値検証エラー {section_name}.{key}: {e}")
            raise ConfigValidationError(f"値検証エラー: {e}")
    
    def get_schema(self, section_name: str) -> Optional[Dict[str, Any]]:
        """スキーマ取得"""
        return self._schemas.get(section_name)
    
    def list_schemas(self) -> List[str]:
        """スキーマ一覧取得"""
        return list(self._schemas.keys())
    
    def get_default_value(self, section_name: str, key: str) -> Any:
        """デフォルト値取得"""
        try:
            schema = self._schemas.get(section_name)
            if not schema:
                return None
            
            properties = schema.get('properties', {})
            if key not in properties:
                return None
            
            key_schema = properties[key]
            return key_schema.get('default')
            
        except Exception as e:
            logger.error(f"デフォルト値取得エラー {section_name}.{key}: {e}")
            return None
    
    def generate_sample_config(self, section_name: str) -> Dict[str, Any]:
        """サンプル設定生成"""
        try:
            schema = self._schemas.get(section_name)
            if not schema:
                return {}
            
            return self._generate_sample_from_schema(schema)
            
        except Exception as e:
            logger.error(f"サンプル設定生成エラー {section_name}: {e}")
            return {}
    
    def _generate_sample_from_schema(self, schema: Dict[str, Any]) -> Any:
        """スキーマからサンプル生成"""
        schema_type = schema.get('type')
        
        if schema_type == 'object':
            result = {}
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            for prop_name, prop_schema in properties.items():
                if prop_name in required or 'default' in prop_schema:
                    if 'default' in prop_schema:
                        result[prop_name] = prop_schema['default']
                    else:
                        result[prop_name] = self._generate_sample_from_schema(prop_schema)
            
            return result
            
        elif schema_type == 'array':
            items_schema = schema.get('items', {})
            min_items = schema.get('minItems', 1)
            return [self._generate_sample_from_schema(items_schema) for _ in range(min_items)]
            
        elif schema_type == 'string':
            if 'enum' in schema:
                return schema['enum'][0]
            elif 'default' in schema:
                return schema['default']
            else:
                return "sample_string"
                
        elif schema_type == 'integer':
            if 'default' in schema:
                return schema['default']
            elif 'minimum' in schema:
                return schema['minimum']
            else:
                return 0
                
        elif schema_type == 'number':
            if 'default' in schema:
                return schema['default']
            elif 'minimum' in schema:
                return float(schema['minimum'])
            else:
                return 0.0
                
        elif schema_type == 'boolean':
            return schema.get('default', False)
        
        return None

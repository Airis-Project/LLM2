#!/usr/bin/env python3
"""
LLM設定管理システム
新LLMシステムと統合された設定管理
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from src.llm import (
    LLMConfig, 
    LLMProvider, 
    get_available_providers,
    create_llm_client,
    validate_llm_config
)
from src.core.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ProviderConfig:
    """プロバイダー設定"""
    name: str
    api_key: str = ""
    base_url: str = ""
    models: List[str] = None
    enabled: bool = True
    timeout: float = 30.0
    retry_count: int = 3
    rate_limit: int = 60  # requests per minute
    custom_headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.models is None:
            self.models = []
        if self.custom_headers is None:
            self.custom_headers = {}

class LLMConfigManager:
    """LLM設定管理"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self._provider_configs: Dict[str, ProviderConfig] = {}
        self._default_configs = self._create_default_configs()
        
        # 初期化
        self.load_llm_configs()
    
    def _create_default_configs(self) -> Dict[str, ProviderConfig]:
        """デフォルト設定作成"""
        return {
            'openai': ProviderConfig(
                name='openai',
                base_url='https://api.openai.com/v1',
                models=['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o'],
                timeout=30.0,
                retry_count=3,
                rate_limit=60
            ),
            'claude': ProviderConfig(
                name='claude',
                base_url='https://api.anthropic.com',
                models=['claude-3-sonnet-20240229', 'claude-3-haiku-20240307', 'claude-3-opus-20240229'],
                timeout=30.0,
                retry_count=3,
                rate_limit=50
            ),
            'local': ProviderConfig(
                name='local',
                base_url='http://localhost:11434',
                models=['llama2', 'codellama', 'mistral'],
                timeout=60.0,
                retry_count=2,
                rate_limit=100
            ),
            'azure': ProviderConfig(
                name='azure',
                base_url='https://{resource}.openai.azure.com',
                models=['gpt-35-turbo', 'gpt-4'],
                timeout=30.0,
                retry_count=3,
                rate_limit=60,
                custom_headers={'api-version': '2024-02-15-preview'}
            )
        }
    
    def load_llm_configs(self):
        """LLM設定読み込み"""
        try:
            if not self.config_manager:
                logger.warning("設定管理システムが未初期化")
                return
            
            llm_config = self.config_manager.get_section('llm', {})
            
            # プロバイダー設定読み込み
            providers_config = llm_config.get('providers', {})
            
            for provider_name, provider_data in providers_config.items():
                try:
                    # デフォルト設定とマージ
                    default_config = self._default_configs.get(provider_name, ProviderConfig(name=provider_name))
                    
                    config = ProviderConfig(
                        name=provider_name,
                        api_key=provider_data.get('api_key', default_config.api_key),
                        base_url=provider_data.get('base_url', default_config.base_url),
                        models=provider_data.get('models', default_config.models),
                        enabled=provider_data.get('enabled', default_config.enabled),
                        timeout=provider_data.get('timeout', default_config.timeout),
                        retry_count=provider_data.get('retry_count', default_config.retry_count),
                        rate_limit=provider_data.get('rate_limit', default_config.rate_limit),
                        custom_headers=provider_data.get('custom_headers', default_config.custom_headers)
                    )
                    
                    self._provider_configs[provider_name] = config
                    logger.debug(f"プロバイダー設定読み込み: {provider_name}")
                    
                except Exception as e:
                    logger.error(f"プロバイダー設定読み込みエラー {provider_name}: {e}")
            
            # デフォルト設定で不足分を補完
            for provider_name, default_config in self._default_configs.items():
                if provider_name not in self._provider_configs:
                    self._provider_configs[provider_name] = default_config
            
            logger.info(f"LLM設定読み込み完了: {len(self._provider_configs)}個のプロバイダー")
            
        except Exception as e:
            logger.error(f"LLM設定読み込みエラー: {e}")
    
    def save_llm_configs(self):
        """LLM設定保存"""
        try:
            if not self.config_manager:
                logger.warning("設定管理システムが未初期化")
                return
            
            # 現在のLLM設定取得
            current_llm_config = self.config_manager.get_section('llm', {})
            
            # プロバイダー設定更新
            providers_config = {}
            for provider_name, config in self._provider_configs.items():
                providers_config[provider_name] = {
                    'api_key': config.api_key,
                    'base_url': config.base_url,
                    'models': config.models,
                    'enabled': config.enabled,
                    'timeout': config.timeout,
                    'retry_count': config.retry_count,
                    'rate_limit': config.rate_limit,
                    'custom_headers': config.custom_headers
                }
            
            current_llm_config['providers'] = providers_config
            
            # 設定保存
            self.config_manager.set_section('llm', current_llm_config)
            self.config_manager.save_section('llm')
            
            logger.info("LLM設定保存完了")
            
        except Exception as e:
            logger.error(f"LLM設定保存エラー: {e}")
            raise
    
    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """プロバイダー設定取得"""
        return self._provider_configs.get(provider_name)
    
    def set_provider_config(self, provider_name: str, config: ProviderConfig):
        """プロバイダー設定設定"""
        self._provider_configs[provider_name] = config
        logger.info(f"プロバイダー設定更新: {provider_name}")
    
    def get_enabled_providers(self) -> List[str]:
        """有効プロバイダー一覧取得"""
        return [name for name, config in self._provider_configs.items() if config.enabled]
    
    def create_llm_config(self, provider_name: str, model: str = None, **kwargs) -> LLMConfig:
        """LLMConfig作成"""
        try:
            provider_config = self.get_provider_config(provider_name)
            if not provider_config:
                raise ValueError(f"未知のプロバイダー: {provider_name}")
            
            # デフォルトモデル選択
            if not model and provider_config.models:
                model = provider_config.models[0]
            
            # LLMConfig作成
            llm_config = LLMConfig(
                model=model or 'default',
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens', 2048),
                top_p=kwargs.get('top_p', 1.0),
                timeout=provider_config.timeout,
                retry_count=provider_config.retry_count,
                api_key=provider_config.api_key,
                base_url=provider_config.base_url,
                custom_headers=provider_config.custom_headers
            )
            
            # 設定検証
            validate_llm_config(llm_config)
            
            return llm_config
            
        except Exception as e:
            logger.error(f"LLMConfig作成エラー: {e}")
            raise
    
    def create_llm_client(self, provider_name: str, model: str = None, **kwargs):
        """LLMクライアント作成"""
        try:
            llm_config = self.create_llm_config(provider_name, model, **kwargs)
            client = create_llm_client(provider_name, llm_config)
            
            logger.info(f"LLMクライアント作成完了: {provider_name}/{model}")
            return client
            
        except Exception as e:
            logger.error(f"LLMクライアント作成エラー: {e}")
            raise
    
    def test_provider_connection(self, provider_name: str) -> bool:
        """プロバイダー接続テスト"""
        try:
            client = self.create_llm_client(provider_name)
            
            if client and client.is_available():
                # 簡単なテストリクエスト
                test_response = client.generate("Hello", max_tokens=10)
                return bool(test_response)
            
            return False
            
        except Exception as e:
            logger.error(f"プロバイダー接続テストエラー {provider_name}: {e}")
            return False
    
    def get_provider_models(self, provider_name: str) -> List[str]:
        """プロバイダーモデル一覧取得"""
        try:
            client = self.create_llm_client(provider_name)
            
            if client and hasattr(client, 'get_available_models'):
                return client.get_available_models()
            
            # フォールバック: 設定からモデル一覧取得
            provider_config = self.get_provider_config(provider_name)
            return provider_config.models if provider_config else []
            
        except Exception as e:
            logger.error(f"モデル一覧取得エラー {provider_name}: {e}")
            return []
    
    def update_provider_models(self, provider_name: str):
        """プロバイダーモデル一覧更新"""
        try:
            models = self.get_provider_models(provider_name)
            
            if models:
                provider_config = self.get_provider_config(provider_name)
                if provider_config:
                    provider_config.models = models
                    self.set_provider_config(provider_name, provider_config)
                    logger.info(f"モデル一覧更新: {provider_name} ({len(models)}個)")
            
        except Exception as e:
            logger.error(f"モデル一覧更新エラー {provider_name}: {e}")
    
    def get_default_provider(self) -> str:
        """デフォルトプロバイダー取得"""
        if self.config_manager:
            return self.config_manager.get_value('llm', 'default_provider', 'openai')
        return 'openai'
    
    def set_default_provider(self, provider_name: str):
        """デフォルトプロバイダー設定"""
        if self.config_manager:
            self.config_manager.set_value('llm', 'default_provider', provider_name)
            logger.info(f"デフォルトプロバイダー設定: {provider_name}")
    
    def get_default_model(self, provider_name: str = None) -> str:
        """デフォルトモデル取得"""
        if not provider_name:
            provider_name = self.get_default_provider()
        
        if self.config_manager:
            return self.config_manager.get_value('llm', 'default_model', 'gpt-3.5-turbo')
        return 'gpt-3.5-turbo'
    
    def set_default_model(self, model: str):
        """デフォルトモデル設定"""
        if self.config_manager:
            self.config_manager.set_value('llm', 'default_model', model)
            logger.info(f"デフォルトモデル設定: {model}")
    
    def export_provider_config(self, provider_name: str, output_path: Path):
        """プロバイダー設定エクスポート"""
        try:
            provider_config = self.get_provider_config(provider_name)
            if not provider_config:
                raise ValueError(f"プロバイダーが見つかりません: {provider_name}")
            
            config_data = asdict(provider_config)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"プロバイダー設定エクスポート完了: {output_path}")
            
        except Exception as e:
            logger.error(f"プロバイダー設定エクスポートエラー: {e}")
            raise
    
    def import_provider_config(self, provider_name: str, input_path: Path):
        """プロバイダー設定インポート"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            provider_config = ProviderConfig(**config_data)
            self.set_provider_config(provider_name, provider_config)
            
            logger.info(f"プロバイダー設定インポート完了: {provider_name}")
            
        except Exception as e:
            logger.error(f"プロバイダー設定インポートエラー: {e}")
            raise

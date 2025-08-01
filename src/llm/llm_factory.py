# src/llm/llm_factory.py
"""
LLMファクトリーモジュール
異なるLLMプロバイダーのインスタンスを統一的に生成・管理
"""

import asyncio
import traceback
from typing import Dict, List, Optional, Any, Type, Union
from enum import Enum
import importlib
from dataclasses import dataclass
from unittest import result

from src.llm.base_llm import BaseLLM, LLMConfig, LLMRole
from src.llm.openai_client import OpenAIClient
from src.llm.claude_client import ClaudeClient
#from src.llm.local_llm_client import LocalLLMClient #旧文LocalLLMClient

from src.core.logger import get_logger
from src.utils.validation_utils import ValidationUtils

#validate_llm_config関数の定義
def validate_llm_config(config):
    """LLM設定を検証"""
    try:
        if not config:
            return False
        if hasattr(config, 'model') and not config.model:
            return False
        return True
    except ImportError as e:
            logger.warning(f"LLMコンポーネント読み込み失敗: {e}")
            return None, None, None

logger = get_logger(__name__)

class LLMProvider(Enum):
    """LLMプロバイダー列挙型"""
    OPENAI = "openai"
    CLAUDE = "claude"
    LOCAL = "local"
    CUSTOM = "custom"

@dataclass
class LLMProviderInfo:
    """LLMプロバイダー情報"""
    name: str
    display_name: str
    provider: LLMProvider
    client_class: Type[BaseLLM]
    supported_models: List[str]
    requires_api_key: bool
    supports_streaming: bool
    supports_functions: bool
    description: str
    default_config: Optional[Dict[str, Any]] = None

def get_config(*args, **kwargs):
    from src.core.config_manager import get_config
    return get_config(*args, **kwargs)
class LLMFactory:
    """LLMファクトリークラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = get_logger(self.__class__.__name__)
        self.validation_utils = ValidationUtils()
        
        # 登録されたプロバイダー
        self._providers: Dict[str, LLMProviderInfo] = {}
        
        # アクティブなクライアント
        self._active_clients: Dict[str, BaseLLM] = {}
        
        # デフォルトプロバイダー
        self._default_provider: Optional[str] = None
        
        # 初期化
        self._initialize_default_providers()
        
        self.logger.info("LLMファクトリーを初期化しました")
    
    def _initialize_default_providers(self):
        from src.llm_client_v2 import EnhancedLLMClient
        """デフォルトプロバイダーを初期化"""
        try:
            # OpenAIプロバイダー
            self.register_provider(LLMProviderInfo(
                name="openai",
                display_name="OpenAI",
                provider=LLMProvider.OPENAI,
                client_class=OpenAIClient,
                supported_models=[
                    "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
                    "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
                ],
                requires_api_key=True,
                supports_streaming=True,
                supports_functions=True,
                description="OpenAI GPTモデル",
                default_config={
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 2048
                }
            ))
            
            # Claudeプロバイダー
            self.register_provider(LLMProviderInfo(
                name="claude",
                display_name="Anthropic Claude",
                provider=LLMProvider.CLAUDE,
                client_class=ClaudeClient,
                supported_models=[
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                    "claude-2.1",
                    "claude-2.0"
                ],
                requires_api_key=True,
                supports_streaming=True,
                supports_functions=False,
                description="Anthropic Claudeモデル",
                default_config={
                    "model": "claude-3-sonnet-20240229",
                    "temperature": 0.7,
                    "max_tokens": 4096
                }
            ))
            
            # ローカルLLMプロバイダー
            self.register_provider(LLMProviderInfo(
                name="local",
                display_name="Local LLM",
                provider=LLMProvider.LOCAL,
                client_class=EnhancedLLMClient,
                supported_models=[
                    "llama2:7b", "llama2:13b", "llama2:70b",
                    "codellama:7b", "codellama:13b", "codellama:34b",
                    "mistral:7b", "mixtral:8x7b",
                    "gemma:2b", "gemma:7b"
                ],
                requires_api_key=False,
                supports_streaming=True,
                supports_functions=False,
                description="ローカル実行LLMモデル（Ollama、llama.cpp等）",
                default_config={
                    "model": "codellama:7b",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "backend": "ollama",
                    "base_url": "http://localhost:11434"
                }
            ))
            
            # デフォルトプロバイダーを設定
            config = get_config()
            self._default_provider = config.get('llm', {}).get('default_provider', 'openai')
            
            self.logger.info(f"デフォルトプロバイダーを初期化しました (default: {self._default_provider})")
            
        except Exception as e:
            self.logger.error(f"デフォルトプロバイダー初期化エラー: {e}")
    
    def register_provider(self, provider_info: LLMProviderInfo):
        """
        プロバイダーを登録
        
        Args:
            provider_info: プロバイダー情報
        """
        try:
            if not isinstance(provider_info, LLMProviderInfo):
                raise ValueError("プロバイダー情報が正しくありません")
            
            # クライアントクラスの検証
            if not issubclass(provider_info.client_class, BaseLLM):
                raise ValueError("クライアントクラスはBaseLLMを継承する必要があります")
            
            self._providers[provider_info.name] = provider_info
            self.logger.info(f"プロバイダーを登録しました: {provider_info.name}")
            
        except Exception as e:
            self.logger.error(f"プロバイダー登録エラー: {e}")
            raise
    
    def unregister_provider(self, provider_name: str):
        """
        プロバイダーの登録を解除
        
        Args:
            provider_name: プロバイダー名
        """
        try:
            if provider_name in self._providers:
                # アクティブなクライアントがあれば停止
                if provider_name in self._active_clients:
                    self._active_clients[provider_name].cleanup()
                    del self._active_clients[provider_name]
                
                del self._providers[provider_name]
                self.logger.info(f"プロバイダーの登録を解除しました: {provider_name}")
            else:
                self.logger.warning(f"プロバイダーが見つかりません: {provider_name}")
                
        except Exception as e:
            self.logger.error(f"プロバイダー登録解除エラー: {e}")
            raise
    
    def create_client(self, 
        provider_name: Optional[str] = None, 
        config: Optional[LLMConfig] = None,
        **kwargs) -> BaseLLM:
        """
        LLMクライアントを作成
        
        Args:
            provider_name: プロバイダー名（Noneの場合はデフォルト）
            config: LLM設定
            **kwargs: 追加パラメータ
            
        Returns:
            BaseLLM: LLMクライアントインスタンス
        """
        try:
            # プロバイダー名の決定
            effective_provider = provider_name or self._default_provider
            if not effective_provider:
                raise ValueError("プロバイダーが指定されていません")
            
            # プロバイダー情報の取得
            provider_info = self._providers.get(effective_provider)
            if not provider_info:
                raise ValueError(f"プロバイダーが見つかりません: {effective_provider}")
            
            # 設定の構築
            effective_config = self._build_config(provider_info, config, **kwargs)
            
            # クライアントインスタンスの作成
            client = provider_info.client_class(effective_config)
            
            # アクティブクライアントとして登録
            client_key = f"{effective_provider}_{id(client)}"
            self._active_clients[client_key] = client
            
            self.logger.info(f"LLMクライアントを作成しました: {effective_provider}")
            return client
            
        except Exception as e:
            self.logger.error(f"LLMクライアント作成エラー: {e}")
            raise
    
    async def create_client_async(self, 
        provider_name: Optional[str] = None, 
        config: Optional[LLMConfig] = None,
        **kwargs) -> BaseLLM:
        """
        LLMクライアントを非同期で作成
        
        Args:
            provider_name: プロバイダー名
            config: LLM設定
            **kwargs: 追加パラメータ
            
        Returns:
            BaseLLM: LLMクライアントインスタンス
        """
        try:
            # 同期版を非同期で実行
            client = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.create_client, 
                provider_name, 
                config, 
                **kwargs
            )
            
            # 非同期初期化が必要な場合
            if hasattr(client, 'initialize_async'):
                await client.initialize_async()
            
            return client
            
        except Exception as e:
            self.logger.error(f"非同期LLMクライアント作成エラー: {e}")
            raise
    
    def get_client(self, provider_name: Optional[str] = None) -> Optional[BaseLLM]:
        """
        既存のクライアントを取得
        
        Args:
            provider_name: プロバイダー名
            
        Returns:
            Optional[BaseLLM]: LLMクライアント（存在しない場合はNone）
        """
        try:
            effective_provider = provider_name or self._default_provider
            
            # アクティブクライアントから検索
            for key, client in self._active_clients.items():
                if key.startswith(f"{effective_provider}_"):
                    return client
            
            return None
            
        except Exception as e:
            self.logger.error(f"クライアント取得エラー: {e}")
            return None
    
    def get_or_create_client(self, 
        provider_name: Optional[str] = None, 
        config: Optional[LLMConfig] = None,
        **kwargs) -> BaseLLM:
        """
        クライアントを取得または作成
        
        Args:
            provider_name: プロバイダー名
            config: LLM設定
            **kwargs: 追加パラメータ
            
        Returns:
            BaseLLM: LLMクライアントインスタンス
        """
        try:
            # 既存クライアントを確認
            existing_client = self.get_client(provider_name)
            if existing_client:
                return existing_client
            
            # 新規作成
            return self.create_client(provider_name, config, **kwargs)
            
        except Exception as e:
            self.logger.error(f"クライアント取得/作成エラー: {e}")
            raise
    
    def _build_config(self, 
        provider_info: LLMProviderInfo, 
        config: Optional[LLMConfig], 
        **kwargs) -> LLMConfig:
        """
        設定を構築
        
        Args:
            provider_info: プロバイダー情報
            config: ベース設定
            **kwargs: 追加パラメータ
            
        Returns:
            LLMConfig: 構築された設定
        """
        try:
            # ベース設定
            base_config = provider_info.default_config or {}
            
            # 設定ファイルからの設定
            file_config = get_config().get('llm', {}).get(provider_info.name, {})
            
            # 統合設定
            merged_config = {**base_config, **file_config, **kwargs}
            
            # LLMConfigオブジェクトの作成
            if config:
                # 既存設定をベースに更新
                effective_config = LLMConfig(
                    model=merged_config.get('model', config.model),
                    temperature=merged_config.get('temperature', config.temperature),
                    max_tokens=merged_config.get('max_tokens', config.max_tokens),
                    top_p=merged_config.get('top_p', getattr(config, 'top_p', 1.0)),
                    frequency_penalty=merged_config.get('frequency_penalty', getattr(config, 'frequency_penalty', 0.0)),
                    presence_penalty=merged_config.get('presence_penalty', getattr(config, 'presence_penalty', 0.0)),
                    stop_sequences=merged_config.get('stop_sequences', getattr(config, 'stop_sequences', [])),
                    stream=merged_config.get('stream', getattr(config, 'stream', False)),
                    api_key=merged_config.get('api_key', getattr(config, 'api_key', '')),
                    base_url=merged_config.get('base_url', getattr(config, 'base_url', '')),
                    timeout=merged_config.get('timeout', getattr(config, 'timeout', 30)),
                    max_retries=merged_config.get('max_retries', getattr(config, 'max_retries', 3)),
                    metadata=merged_config.get('metadata', getattr(config, 'metadata', {}))
                )
            else:
                # 新規設定作成
                effective_config = LLMConfig(
                    model=merged_config.get('model', ''),
                    temperature=merged_config.get('temperature', 0.7),
                    max_tokens=merged_config.get('max_tokens', 2048),
                    top_p=merged_config.get('top_p', 1.0),
                    frequency_penalty=merged_config.get('frequency_penalty', 0.0),
                    presence_penalty=merged_config.get('presence_penalty', 0.0),
                    stop_sequences=merged_config.get('stop_sequences', []),
                    stream=merged_config.get('stream', False),
                    api_key=merged_config.get('api_key', ''),
                    base_url=merged_config.get('base_url', ''),
                    timeout=merged_config.get('timeout', 30),
                    max_retries=merged_config.get('max_retries', 3),
                    metadata=merged_config.get('metadata', {})
                )
            
            return effective_config
            
        except Exception as e:
            self.logger.error(f"設定構築エラー: {e}")
            raise
    
    def get_available_providers(self) -> List[str]:
        """
        利用可能なプロバイダーを取得
        
        Returns:
            List[str]: 利用可能なプロバイダー名のリスト
        """
        available_providers = []
        
        for provider_name, provider_info in self._providers.items():
            try:
                if provider_info.requires_api_key:
                    # API キーが必要な場合のチェック
                    config = get_config()
                    api_key_config = config.get('llm', {}).get(provider_name, {}).get('api_key')
                    if api_key_config:
                        available_providers.append(provider_name)
                else:
                    # ローカルLLMなどAPI キー不要の場合
                    if provider_name == "local":
                        # ローカルLLMの可用性チェック
                        try:
                            from src.llm_client_v2 import EnhancedLLMClient
                            print("==== local LLM 可用性チェック開始 ====")
                            print(f"default_config: {provider_info.default_config}")
                            temp_config = LLMConfig(
                                model="wizardcoder:33b",
                                temperature=0.7,
                                max_tokens=100
                            )
                            # デフォルト設定を適用
                            default_config = provider_info.default_config or {}
                            for key, value in default_config.items():
                                setattr(temp_config, key, value)
                            print(f"temp_config: {temp_config.__dict__}")

                            temp_client = EnhancedLLMClient(temp_config)
                            print(f"validate_connection result: {result}")
                            # validate_connection メソッドを使用
                            if temp_client.validate_connection():
                                available_providers.append(provider_name)
                        except Exception as e:
                            self.logger.debug(f"ローカルLLM可用性チェックエラー: {e}")
                            traceback.print_exc()
                    else:
                        available_providers.append(provider_name)
                        
            except Exception as e:
                self.logger.warning(f"プロバイダー {provider_name} の可用性チェックでエラー: {e}")
        
        return available_providers
    
    def get_provider_info(self, provider_name: str) -> Optional[LLMProviderInfo]:
        """
        プロバイダー情報を取得
        
        Args:
            provider_name: プロバイダー名
            
        Returns:
            Optional[LLMProviderInfo]: プロバイダー情報
        """
        return self._providers.get(provider_name)
    
    def list_providers(self) -> Dict[str, LLMProviderInfo]:
        """
        すべてのプロバイダー情報を取得
        
        Returns:
            Dict[str, LLMProviderInfo]: プロバイダー情報辞書
        """
        return self._providers.copy()

    def get_all_provider_info(self) -> Dict[str, LLMProviderInfo]:
        """
        全プロバイダー情報を取得
        
        Returns:
            Dict[str, LLMProviderInfo]: プロバイダー情報辞書
        """
        return self._providers.copy()
    
    async def get_available_models(self, provider_name: Optional[str] = None) -> List[str]:
        """
        利用可能なモデル一覧を取得
        
        Args:
            provider_name: プロバイダー名
            
        Returns:
            List[str]: モデル名のリスト
        """
        try:
            effective_provider = provider_name or self._default_provider
            provider_info = self._providers.get(effective_provider)
            
            if not provider_info:
                return []
            
            # クライアントからモデル一覧を取得
            client = self.get_or_create_client(effective_provider)
            if hasattr(client, 'get_available_models'):
                # 同期メソッドを非同期で実行
                models = await asyncio.get_event_loop().run_in_executor(
                    None, client.get_available_models
                )
                return models
            else:
                return provider_info.supported_models
                
        except Exception as e:
            self.logger.error(f"モデル一覧取得エラー: {e}")
            return []
          
    def validate_provider_config(self, provider_name: str, config: Dict[str, Any]) -> bool:
        """
        プロバイダー設定を検証
        
        Args:
            provider_name: プロバイダー名
            config: 設定辞書
            
        Returns:
            bool: 検証結果
        """
        try:
            provider_info = self._providers.get(provider_name)
            if not provider_info:
                return False
            
            # API キーの確認
            if provider_info.requires_api_key:
                api_key = config.get('api_key', '')
                if not api_key:
                    self.logger.warning(f"API キーが設定されていません: {provider_name}")
                    return False
            
            # モデル名の確認
            model = config.get('model', '')
            if model and model not in provider_info.supported_models:
                self.logger.warning(f"サポートされていないモデル: {model}")
                return False
            
            # 数値パラメータの確認
            temperature = config.get('temperature', 0.7)
            if not (0.0 <= temperature <= 2.0):
                self.logger.warning(f"temperatureが範囲外です: {temperature}")
                return False
            
            max_tokens = config.get('max_tokens', 2048)
            if max_tokens <= 0:
                self.logger.warning(f"max_tokensが無効です: {max_tokens}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"プロバイダー設定検証エラー: {e}")
            return False
    
    async def test_provider_connection(self, provider_name: str) -> Dict[str, Any]:
        """
        プロバイダー接続をテスト
        
        Args:
            provider_name: プロバイダー名
            
        Returns:
            Dict[str, Any]: テスト結果
        """
        try:
            provider_info = self._providers.get(provider_name)
            if not provider_info:
                return {
                    'success': False,
                    'error': f'プロバイダーが見つかりません: {provider_name}'
                }
            
            # テスト用クライアントを作成
            test_client = self.create_client(provider_name)
            
            # 接続テスト
            if hasattr(test_client, 'validate_connection'):
                # 同期メソッドを非同期で実行
                success = await asyncio.get_event_loop().run_in_executor(
                    None, test_client.validate_connection
                )
                result = {
                    'success': success,
                    'provider': provider_name,
                    'model': test_client.config.model if test_client.config else 'unknown'
                }
            else:
                # 簡単なテストメッセージで確認
                test_messages = [{"role": "user", "content": "Hello, this is a connection test."}]
                
                try:
                    response = await asyncio.get_event_loop().run_in_executor(
                        None, test_client.generate, test_messages
                    )
                    result = {
                        'success': True,
                        'provider': provider_name,
                        'model': test_client.config.model if test_client.config else 'unknown',
                        'test_response': response[:50] + "..." if len(response) > 50 else response
                    }
                except Exception as e:
                    result = {
                        'success': False,
                        'error': str(e)
                    }
            
            # テスト用クライアントをクリーンアップ
            if hasattr(test_client, 'cleanup'):
                test_client.cleanup()
            
            return result
            
        except Exception as e:
            self.logger.error(f"プロバイダー接続テストエラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def set_default_provider(self, provider_name: str):
        """
        デフォルトプロバイダーを設定
        
        Args:
            provider_name: プロバイダー名
        """
        try:
            if provider_name not in self._providers:
                raise ValueError(f"プロバイダーが見つかりません: {provider_name}")
            
            self._default_provider = provider_name
            self.logger.info(f"デフォルトプロバイダーを設定しました: {provider_name}")
            
        except Exception as e:
            self.logger.error(f"デフォルトプロバイダー設定エラー: {e}")
            raise
    
    def get_default_provider(self) -> Optional[str]:
        """
        デフォルトプロバイダーを取得
        
        Returns:
            Optional[str]: デフォルトプロバイダー名
        """
        return self._default_provider
    
    def get_active_clients(self) -> Dict[str, BaseLLM]:
        """
        アクティブなクライアント一覧を取得
        
        Returns:
            Dict[str, BaseLLM]: アクティブクライアント辞書
        """
        return self._active_clients.copy()
    
    def cleanup_client(self, client: BaseLLM):
        """
        特定のクライアントをクリーンアップ
        
        Args:
            client: クリーンアップするクライアント
        """
        try:
            # アクティブクライアントから削除
            keys_to_remove = []
            for key, active_client in self._active_clients.items():
                if active_client is client:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._active_clients[key]
            
            # クライアントのクリーンアップ
            client.cleanup()
            
            self.logger.info("クライアントをクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"クライアントクリーンアップエラー: {e}")
    
    def cleanup_all_clients(self):
        """全てのアクティブクライアントをクリーンアップ"""
        try:
            for client in self._active_clients.values():
                try:
                    client.cleanup()
                except Exception as e:
                    self.logger.warning(f"クライアントクリーンアップ警告: {e}")
            
            self._active_clients.clear()
            self.logger.info("全てのクライアントをクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"全クライアントクリーンアップエラー: {e}")
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """
        ファクトリー統計情報を取得
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        try:
            stats = {
                'registered_providers': len(self._providers),
                'active_clients': len(self._active_clients),
                'default_provider': self._default_provider,
                'provider_names': list(self._providers.keys()),
                'client_info': {}
            }
            
            # クライアント情報
            for key, client in self._active_clients.items():
                provider_name = key.split('_')[0]
                stats['client_info'][key] = {
                    'provider': provider_name,
                    'status': client.get_status().value,
                    'model': client.config.model if client.config else 'unknown'
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"ファクトリー統計取得エラー: {e}")
            return {}
    
    def load_custom_provider(self, module_path: str, provider_name: str):
        """
        カスタムプロバイダーを動的ロード
        
        Args:
            module_path: モジュールパス
            provider_name: プロバイダー名
        """
        try:
            # モジュールを動的インポート
            module = importlib.import_module(module_path)
            
            # プロバイダー情報を取得
            if hasattr(module, 'get_provider_info'):
                provider_info = module.get_provider_info()
                provider_info.name = provider_name
                provider_info.provider = LLMProvider.CUSTOM
                
                self.register_provider(provider_info)
                self.logger.info(f"カスタムプロバイダーをロードしました: {provider_name}")
            else:
                raise ValueError("get_provider_info関数が見つかりません")
                
        except Exception as e:
            self.logger.error(f"カスタムプロバイダーロードエラー: {e}")
            raise

# グローバルファクトリーインスタンス
_factory_instance: Optional[LLMFactory] = None

def get_llm_factory() -> LLMFactory:
    """
    LLMファクトリーのシングルトンインスタンスを取得
    
    Returns:
        LLMFactory: ファクトリーインスタンス
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = LLMFactory()
    return _factory_instance

def create_llm_client(provider_name: Optional[str] = None, 
    config: Optional[LLMConfig] = None,
    **kwargs) -> BaseLLM:
    """
    LLMクライアントを作成（便利関数）
    
    Args:
        provider_name: プロバイダー名
        config: LLM設定
        **kwargs: 追加パラメータ
        
    Returns:
        BaseLLM: LLMクライアントインスタンス
    """
    factory = get_llm_factory()
    return factory.create_client(provider_name, config, **kwargs)

async def create_llm_client_async(provider_name: Optional[str] = None, 
    config: Optional[LLMConfig] = None,
    **kwargs) -> BaseLLM:
    """
    LLMクライアントを非同期で作成（便利関数）
    
    Args:
        provider_name: プロバイダー名
        config: LLM設定
        **kwargs: 追加パラメータ
        
    Returns:
        BaseLLM: LLMクライアントインスタンス
    """
    factory = get_llm_factory()
    return await factory.create_client_async(provider_name, config, **kwargs)

def initialize_llm_factory():
    """LLMファクトリーを初期化"""
    return get_llm_factory()
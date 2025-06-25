# src/llm/__init__.py
"""
LLM (Large Language Model) パッケージ

このパッケージは様々なLLMプロバイダーとの統合を提供します：
- OpenAI GPT
- Anthropic Claude  
- ローカルLLM (Ollama, llama.cpp等)

主要コンポーネント:
- base_llm: LLMの基底クラスと設定
- llm_factory: LLMインスタンスの生成と管理
- 各種クライアント実装 (OpenAI, Claude, Local)
"""

from .base_llm import BaseLLM, LLMConfig, LLMRole, LLMStatus
from .openai_client import OpenAIClient
from .claude_client import ClaudeClient
from .local_llm_client import LocalLLMClient
from .llm_factory import (
    LLMFactory, 
    LLMProvider, 
    LLMProviderInfo,
    get_llm_factory
)

# バージョン情報
__version__ = "1.0.0"
__author__ = "LLM Code Assistant Team"

# デフォルト設定
DEFAULT_CONFIG = {
    "temperature": 0.7,
    "max_tokens": 2048,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "stream": False,
    "timeout": 30,
    "max_retries": 3
}

# サポートされているプロバイダー
SUPPORTED_PROVIDERS = [
    "openai",
    "claude", 
    "local"
]

# エクスポートする主要クラス
__all__ = [
    # 基底クラス
    "BaseLLM",
    "LLMConfig",
    "LLMRole",
    "LLMStatus",
    
    # クライアント実装
    "OpenAIClient",
    "ClaudeClient", 
    "LocalLLMClient",
    
    # ファクトリー
    "LLMFactory",
    "LLMProvider",
    "LLMProviderInfo",
    "get_llm_factory",
    
    # 便利関数
    "create_llm_client",
    "create_llm_client_async",
    "get_available_providers",
    
    # 設定
    "DEFAULT_CONFIG",
    "SUPPORTED_PROVIDERS",
    
    # バージョン情報
    "__version__",
    "__author__"
]

def get_available_providers():
    """
    利用可能なLLMプロバイダーのリストを取得
    
    Returns:
        List[str]: 利用可能なプロバイダー名のリスト
    """
    factory = get_llm_factory()
    return factory.get_available_providers()

def create_llm_client(provider_name: str, config: LLMConfig = None, **kwargs):
    """
    LLMクライアントの作成（同期版）
    
    Args:
        provider_name: プロバイダー名 ("openai", "claude", "local")
        config: LLM設定
        **kwargs: 追加設定
        
    Returns:
        BaseLLM: LLMクライアントインスタンス
        
    Raises:
        ValueError: サポートされていないプロバイダーの場合
        LLMConfigurationError: 設定エラーの場合
    """
    factory = get_llm_factory()
    return factory.create_client(provider_name, config, **kwargs)

async def create_llm_client_async(provider_name: str, config: LLMConfig = None, **kwargs):
    """
    LLMクライアントの作成（非同期版）
    
    Args:
        provider_name: プロバイダー名
        config: LLM設定
        **kwargs: 追加設定
        
    Returns:
        BaseLLM: LLMクライアントインスタンス
    """
    factory = get_llm_factory()
    return await factory.create_client_async(provider_name, config, **kwargs)

def validate_config(config: dict) -> bool:
    """
    LLM設定の検証
    
    Args:
        config: 設定辞書
        
    Returns:
        bool: 設定が有効な場合True
    """
    try:
        # 必須フィールドの確認
        if "model" not in config:
            return False
            
        # 数値範囲の確認
        if "temperature" in config:
            temp = config["temperature"]
            if not isinstance(temp, (int, float)) or not (0.0 <= temp <= 2.0):
                return False
                
        if "max_tokens" in config:
            tokens = config["max_tokens"]
            if not isinstance(tokens, int) or tokens <= 0:
                return False
                
        return True
        
    except Exception:
        return False

# パッケージ初期化処理
def _initialize_llm_package():
    """LLMパッケージの初期化"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # ファクトリーの初期化
        factory = get_llm_factory()
        
        # 利用可能なプロバイダーをログ出力
        available = get_available_providers()
        if available:
            logger.info(f"利用可能なLLMプロバイダー: {', '.join(available)}")
        else:
            logger.warning("利用可能なLLMプロバイダーが見つかりません")
            
    except Exception as e:
        logger.error(f"LLMパッケージ初期化エラー: {e}")

# パッケージ読み込み時に初期化実行
_initialize_llm_package()

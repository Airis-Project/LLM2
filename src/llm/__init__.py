# src/llm/__init__.py
"""
LLM (Large Language Model) パッケージ

このパッケージは様々なLLMプロバイダーとの統合を提供します：
- OpenAI GPT
- Anthropic Claude  
- ローカルLLM
- その他のLLMプロバイダー

主要コンポーネント:
- base_llm: LLMの基底クラス
- llm_factory: LLMインスタンスの生成
- prompt_templates: プロンプトテンプレート管理
- response_parser: レスポンス解析
- 各種クライアント実装
"""

from .base_llm import BaseLLM, LLMResponse, LLMError
from .llm_factory import LLMFactory, LLMType
from .prompt_templates import PromptTemplateManager, PromptTemplate
from .response_parser import ResponseParser, ParsedResponse

# バージョン情報
__version__ = "1.0.0"
__author__ = "LLM Code Assistant Team"

# パッケージレベルの設定
DEFAULT_MODEL_CONFIG = {
    "max_tokens": 4096,
    "temperature": 0.7,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
}

# サポートされているLLMタイプ
SUPPORTED_LLM_TYPES = [
    "openai",
    "claude", 
    "local",
    "huggingface"
]

# エクスポートする主要クラスとインターfaces
__all__ = [
    # 基底クラス
    "BaseLLM",
    "LLMResponse", 
    "LLMError",
    
    # ファクトリー
    "LLMFactory",
    "LLMType",
    
    # プロンプト管理
    "PromptTemplateManager",
    "PromptTemplate",
    
    # レスポンス解析
    "ResponseParser",
    "ParsedResponse",
    
    # 設定
    "DEFAULT_MODEL_CONFIG",
    "SUPPORTED_LLM_TYPES",
    
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
    providers = []
    
    try:
        # OpenAI の可用性チェック
        import openai
        providers.append("openai")
    except ImportError:
        pass
    
    try:
        # Anthropic Claude の可用性チェック
        import anthropic
        providers.append("claude")
    except ImportError:
        pass
    
    try:
        # Transformers (ローカルLLM) の可用性チェック
        import transformers
        providers.append("local")
    except ImportError:
        pass
    
    try:
        # Hugging Face の可用性チェック
        import huggingface_hub
        providers.append("huggingface")
    except ImportError:
        pass
    
    return providers

def create_llm_client(provider_type: str, **kwargs):
    """
    LLMクライアントの簡易作成関数
    
    Args:
        provider_type: プロバイダータイプ ("openai", "claude", "local", etc.)
        **kwargs: プロバイダー固有の設定
        
    Returns:
        BaseLLM: LLMクライアントインスタンス
        
    Raises:
        ValueError: サポートされていないプロバイダータイプの場合
        ImportError: 必要なライブラリがインストールされていない場合
    """
    factory = LLMFactory()
    return factory.create_llm(provider_type, **kwargs)

def validate_model_config(config: dict) -> bool:
    """
    モデル設定の検証
    
    Args:
        config: モデル設定辞書
        
    Returns:
        bool: 設定が有効な場合True
    """
    required_keys = ["max_tokens", "temperature"]
    
    # 必須キーの存在確認
    for key in required_keys:
        if key not in config:
            return False
    
    # 値の範囲チェック
    if not isinstance(config["max_tokens"], int) or config["max_tokens"] <= 0:
        return False
        
    if not isinstance(config["temperature"], (int, float)) or not (0.0 <= config["temperature"] <= 2.0):
        return False
    
    return True

# パッケージ初期化時の処理
def _initialize_package():
    """パッケージ初期化処理"""
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 利用可能なプロバイダーをログ出力
    available_providers = get_available_providers()
    logger.info(f"利用可能なLLMプロバイダー: {', '.join(available_providers)}")
    
    if not available_providers:
        logger.warning("利用可能なLLMプロバイダーが見つかりません。必要なライブラリをインストールしてください。")

# パッケージ読み込み時に初期化実行
_initialize_package()

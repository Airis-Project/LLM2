# src/llm/__init__.py
"""
LLMパッケージ初期化
低レベルLLMクライアント層とプロンプト管理、レスポンス解析、中間サービス統合
"""

# プロバイダー基底クラス
class LLMProvider:
    """LLMプロバイダー基底クラス"""
    
    def __init__(self, name: str, config: dict = None):
        self.name = name
        self.config = config or {}
    
    def get_name(self) -> str:
        return self.name
    
    def get_config(self) -> dict:
        return self.config
    
    def is_available(self) -> bool:
        """プロバイダーが利用可能かチェック"""
        return True
    
# ベースクラスとデータ型
from typing import List
from .base_llm import (
    BaseLLM,
    LLMMessage,
    LLMResponse,
    LLMConfig,
    LLMRole,
    LLMStatus,
    LLMUsage,
    LLMError,
    LLMException,
    LLMConnectionError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMValidationError
)

# LLMクライアント実装
from .openai_client import OpenAIClient
from .claude_client import ClaudeClient
from .local_llm_client import LocalLLMClient

# ファクトリーとプロバイダー管理
from .llm_factory import (
    LLMFactory,
    LLMProviderInfo,
    get_llm_factory,
    create_llm_client,
    create_llm_client_async,
)

# プロンプトテンプレート管理
from .prompt_templates import (
    PromptTemplate,
    PromptTemplateManager,
    TemplateVariable,
    TemplateCategory,
    get_prompt_template_manager,
    #load_template,
    #load_template_async,
    #render_template,
    #render_template_async
)

# レスポンス解析
from .response_parser import (
    ResponseParser,
    ParsedResponse,
    CodeBlock,
    #ReviewComment,
    #DocumentSection,
    get_response_parser,
    #parse_code_response,
    #parse_review_response,
    #parse_documentation_response,
    #parse_general_response
)

# 中間サービス層
from .llm_service import (
    LLMServiceCore,
    LLMTask,
    LLMResult,
    TaskType,
    TaskPriority,
    get_llm_service,
    execute_llm_task,
    execute_llm_task_async
)

# バージョン情報
__version__ = "1.0.0"
__author__ = "LLM Integration Team"
__description__ = "統合LLMクライアントライブラリ"

# パッケージレベル設定
__all__ = [
    # ベースクラスとデータ型
    "LLMProvider",
    "BaseLLM",
    "LLMMessage", 
    "LLMResponse",
    "LLMConfig",
    "LLMRole",
    "LLMStatus",
    "LLMUsage",
    "LLMError",
    "LLMException",
    "LLMConnectionError",
    "LLMRateLimitError", 
    "LLMAuthenticationError",
    "LLMTimeoutError",
    "LLMValidationError",
    'get_available_providers',
    'validate_llm_config',
    
    # LLMクライアント実装
    "OpenAIClient",
    "ClaudeClient", 
    "LocalLLMClient",
    
    # ファクトリーとプロバイダー管理
    "LLMFactory",
    "LLMProviderInfo",
    "get_llm_factory",
    "create_llm_client",
    "create_llm_client_async",
    "get_available_providers",
    "get_provider_info",
    
    # プロンプトテンプレート管理
    "PromptTemplate",
    "PromptTemplateManager", 
    "TemplateVariable",
    "TemplateCategory",
    "get_prompt_template_manager",
    #"load_template",
    #"load_template_async",
    #"render_template",
    #"render_template_async",
    #"_load_templates",
    
    # レスポンス解析
    "ResponseParser",
    "ParsedResponse",
    "CodeBlock",
    #"ReviewComment", 
    #"DocumentSection",
    "get_response_parser",
    #"parse_code_response",
    #"parse_review_response",
    #"parse_documentation_response",
    #"parse_general_response",
    
    # 中間サービス層
    "LLMServiceCore",
    "LLMTask",
    "LLMResult", 
    "TaskType",
    "TaskPriority",
    "get_llm_service",
    "execute_llm_task",
    "execute_llm_task_async",
]

# パッケージレベル初期化
def initialize_llm_package(config=None):
    """
    LLMパッケージを初期化
    
    Args:
        config: 初期化設定
    """
    try:
        from ..core.logger import get_logger
        logger = get_logger(__name__)
        
        # ファクトリー初期化
        factory = get_llm_factory()
        
        # プロンプトテンプレートマネージャー初期化
        template_manager = get_prompt_template_manager()
        
        # レスポンスパーサー初期化
        response_parser = get_response_parser()
        
        # 中間サービス初期化
        llm_service = get_llm_service()
        
        logger.info("LLMパッケージを初期化しました")
        
        return {
            'factory': factory,
            'template_manager': template_manager,
            'response_parser': response_parser,
            'llm_service': llm_service
        }
        
    except Exception as e:
        print(f"LLMパッケージ初期化エラー: {e}")
        raise

def cleanup_llm_package():
    """
    LLMパッケージをクリーンアップ
    """
    try:
        from ..core.logger import get_logger
        logger = get_logger(__name__)
        
        # 中間サービスクリーンアップ
        llm_service = get_llm_service()
        llm_service.cleanup()
        
        # ファクトリークリーンアップ
        factory = get_llm_factory()
        if hasattr(factory, 'cleanup'):
            factory.cleanup()
        
        logger.info("LLMパッケージをクリーンアップしました")
        
    except Exception as e:
        print(f"LLMパッケージクリーンアップエラー: {e}")

# 便利関数
def quick_generate(prompt: str, 
    provider: str = None,
    model: str = None,
    **kwargs) -> str:
    """
    クイック生成（便利関数）
    
    Args:
        prompt: プロンプト
        provider: プロバイダー名
        model: モデル名
        **kwargs: 追加パラメータ
        
    Returns:
        str: 生成されたテキスト
    """
    try:
        result = execute_llm_task(
            task_type=TaskType.GENERAL,
            prompt=prompt,
            provider=provider,
            model=model,
            **kwargs
        )
        
        if result.success:
            return result.content
        else:
            raise LLMException(f"生成エラー: {result.error}")
            
    except Exception as e:
        raise LLMException(f"クイック生成エラー: {e}")

async def quick_generate_async(prompt: str,
    provider: str = None,
    model: str = None,
    **kwargs) -> str:
    """
    クイック生成（非同期版）
    
    Args:
        prompt: プロンプト
        provider: プロバイダー名
        model: モデル名
        **kwargs: 追加パラメータ
        
    Returns:
        str: 生成されたテキスト
    """
    try:
        result = await execute_llm_task_async(
            task_type=TaskType.GENERAL,
            prompt=prompt,
            provider=provider,
            model=model,
            **kwargs
        )
        
        if result.success:
            return result.content
        else:
            raise LLMException(f"生成エラー: {result.error}")
            
    except Exception as e:
        raise LLMException(f"クイック生成エラー: {e}")

def generate_code(prompt: str,
    language: str = None,
    provider: str = None,
    model: str = None,
    **kwargs) -> dict:
    """
    コード生成（便利関数）
    
    Args:
        prompt: プロンプト
        language: プログラミング言語
        provider: プロバイダー名
        model: モデル名
        **kwargs: 追加パラメータ
        
    Returns:
        dict: 解析されたコード情報
    """
    try:
        # テンプレート変数を準備
        template_vars = {'language': language} if language else {}
        template_vars.update(kwargs.get('template_vars', {}))
        
        result = execute_llm_task(
            task_type=TaskType.CODE_GENERATION,
            prompt=prompt,
            template_name='code_generation',
            template_vars=template_vars,
            provider=provider,
            model=model,
            **kwargs
        )
        
        if result.success:
            return result.parsed_content
        else:
            raise LLMException(f"コード生成エラー: {result.error}")
            
    except Exception as e:
        raise LLMException(f"コード生成エラー: {e}")

async def generate_code_async(prompt: str,
    language: str = None,
    provider: str = None,
    model: str = None,
    **kwargs) -> dict:
    """
    コード生成（非同期版）
    
    Args:
        prompt: プロンプト
        language: プログラミング言語
        provider: プロバイダー名
        model: モデル名
        **kwargs: 追加パラメータ
        
    Returns:
        dict: 解析されたコード情報
    """
    try:
        # テンプレート変数を準備
        template_vars = {'language': language} if language else {}
        template_vars.update(kwargs.get('template_vars', {}))
        
        result = await execute_llm_task_async(
            task_type=TaskType.CODE_GENERATION,
            prompt=prompt,
            template_name='code_generation',
            template_vars=template_vars,
            provider=provider,
            model=model,
            **kwargs
        )
        
        if result.success:
            return result.parsed_content
        else:
            raise LLMException(f"コード生成エラー: {result.error}")
            
    except Exception as e:
        raise LLMException(f"コード生成エラー: {e}")

def review_code(code: str,
               language: str = None,
               provider: str = None,
               model: str = None,
               **kwargs) -> dict:
    """
    コードレビュー（便利関数）
    
    Args:
        code: レビュー対象コード
        language: プログラミング言語
        provider: プロバイダー名
        model: モデル名
        **kwargs: 追加パラメータ
        
    Returns:
        dict: 解析されたレビュー結果
    """
    try:
        # テンプレート変数を準備
        template_vars = {
            'code': code,
            'language': language or 'unknown'
        }
        template_vars.update(kwargs.get('template_vars', {}))
        
        result = execute_llm_task(
            task_type=TaskType.CODE_REVIEW,
            prompt=f"以下のコードをレビューしてください:\n\n```{language or ''}\n{code}\n```",
            template_name='code_review',
            template_vars=template_vars,
            provider=provider,
            model=model,
            **kwargs
        )
        
        if result.success:
            return result.parsed_content
        else:
            raise LLMException(f"コードレビューエラー: {result.error}")
            
    except Exception as e:
        raise LLMException(f"コードレビューエラー: {e}")

async def review_code_async(code: str,
    language: str = None,
    provider: str = None,
    model: str = None,
    **kwargs) -> dict:
    """
    コードレビュー（非同期版）
    
    Args:
        code: レビュー対象コード
        language: プログラミング言語
        provider: プロバイダー名
        model: モデル名
        **kwargs: 追加パラメータ
        
    Returns:
        dict: 解析されたレビュー結果
    """
    try:
        # テンプレート変数を準備
        template_vars = {
            'code': code,
            'language': language or 'unknown'
        }
        template_vars.update(kwargs.get('template_vars', {}))
        
        result = await execute_llm_task_async(
            task_type=TaskType.CODE_REVIEW,
            prompt=f"以下のコードをレビューしてください:\n\n```{language or ''}\n{code}\n```",
            template_name='code_review',
            template_vars=template_vars,
            provider=provider,
            model=model,
            **kwargs
        )
        
        if result.success:
            return result.parsed_content
        else:
            raise LLMException(f"コードレビューエラー: {result.error}")
            
    except Exception as e:
        raise LLMException(f"コードレビューエラー: {e}")

def get_package_info() -> dict:
    """
    パッケージ情報を取得
    
    Returns:
        dict: パッケージ情報
    """
    try:
        # サービス統計を取得
        llm_service = get_llm_service()
        service_stats = llm_service.get_service_stats()
        
        # プロバイダー情報を取得
        factory = get_llm_factory()
        available_providers = factory.get_available_providers()
        
        return {
            'version': __version__,
            'author': __author__,
            'description': __description__,
            'available_providers': available_providers,
            'service_stats': service_stats,
            'components': {
                'factory': bool(factory),
                'template_manager': bool(get_prompt_template_manager()),
                'response_parser': bool(get_response_parser()),
                'llm_service': bool(llm_service)
            }
        }
        
    except Exception as e:
        return {
            'version': __version__,
            'author': __author__,
            'description': __description__,
            'error': str(e)
        }

# パッケージレベル設定
def configure_package(**kwargs):
    """
    パッケージレベル設定
    
    Args:
        **kwargs: 設定パラメータ
    """
    try:
        from ..core.logger import get_logger
        logger = get_logger(__name__)
        
        # 設定を適用
        if 'log_level' in kwargs:
            logger.setLevel(kwargs['log_level'])
        
        if 'default_provider' in kwargs:
            factory = get_llm_factory()
            factory.set_default_provider(kwargs['default_provider'])
        
        if 'template_directory' in kwargs:
            template_manager = get_prompt_template_manager()
            template_manager.set_template_directory(kwargs['template_directory'])
        
        logger.info(f"パッケージ設定を更新しました: {kwargs}")
        
    except Exception as e:
        print(f"パッケージ設定エラー: {e}")
        raise

# 開発・デバッグ用
def debug_info() -> dict:
    """
    デバッグ情報を取得
    
    Returns:
        dict: デバッグ情報
    """
    try:
        import sys
        import platform
        
        info = {
            'package_info': get_package_info(),
            'python_version': sys.version,
            'platform': platform.platform(),
            'available_modules': []
        }
        
        # 利用可能なモジュールをチェック
        modules_to_check = ['openai', 'anthropic', 'requests', 'aiohttp', 'jinja2']
        for module_name in modules_to_check:
            try:
                __import__(module_name)
                info['available_modules'].append(module_name)
            except ImportError:
                pass
        
        return info
        
    except Exception as e:
        return {'error': str(e)}

# 自動初期化（オプション）
try:
    # 環境変数で自動初期化を制御
    import os
    if os.getenv('LLM_AUTO_INIT', 'false').lower() == 'true':
        initialize_llm_package()
except Exception:
    # 初期化エラーは無視（手動初期化を想定）
    pass

#def get_available_providers() -> List[str]:
#    """利用可能なプロバイダーを取得（便利関数）"""
#    factory = get_llm_factory()
#    return factory.get_available_providers()

def validate_llm_config(config: LLMConfig) -> bool:
    """LLM設定を検証（便利関数）"""
    try:
        if not config:
            return False
        if not config.model:
            return False
        if config.temperature < 0 or config.temperature > 2:
            return False
        if config.max_tokens <= 0:
            return False
        return True
    except Exception:
        return False
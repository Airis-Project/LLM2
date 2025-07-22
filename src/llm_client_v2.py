# 改良版LLMクライアント
#src/llm_client_v2.py
#python src/llm_client_v2.py
# -*- coding: utf-8 -*-
"""
拡張LLMクライアント v2.0
スマートモデル選択、性能監視、エラーハンドリングを統合
"""
import requests
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncIterator, Union, AsyncGenerator, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor
import queue
from src.llm.base_llm import BaseLLM

# プロジェクトルートをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
try:
    from .model_selector import SmartModelSelector, TaskType
    from .ollama_client import OllamaClient
except ImportError as e:
    print(f"Import error: {e}")
    # フォールバック用の簡単なクラス
    class TaskType(Enum):
        GENERAL = "general"
        CODE_GENERATION = "code_generation"
    
    class SmartModelSelector:
        def __init__(self, config_path=None):
            pass
        def select_model(self, **kwargs):
            return "starcoder:7b"
        def get_available_models(self):
            return ["starcoder:7b"]
    class OllamaClient:
        def __init__(self):
            pass
        def generate(self, **kwargs):
            return {'success': False, 'error': 'Ollama not available'}
        def list_models(self):
            return []
        def is_available(self):
            return False

# コアインポート
from src.core.logger import get_logger
from src.core.exceptions import (
    LLMError, LLMConnectionError, LLMTimeoutError, 
    LLMRateLimitError, LLMResponseError
)

# LLMクライアントインポート
from src.ollama_client import OllamaClient
from src.llm.openai_client import OpenAIClient

@dataclass
class LLMRequest:
    """LLMリクエスト"""
    prompt: str
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    system_prompt: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class LLMResponse:
    """LLMレスポンス"""
    content: str
    model: str
    usage: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    request_id: Optional[str] = None
    error: Optional[str] = None

class ClientType(Enum):
    """クライアントタイプ"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
# ログ設定
try:
    from src.core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    # フォールバック: 標準ログシステム
    import logging
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedLLMClient(BaseLLM):
    """拡張LLMクライアント - スマート機能統合版"""
    
    def __init__(self, config_path: Optional[str] = None):
        """クライアント初期化"""
        self.logger = logger
        try:
            self.model_selector = SmartModelSelector(config_path)
        except Exception as e:
            self.logger.warning(f"モデルセレクター初期化失敗: {e}")
            self.model_selector = SmartModelSelector()  # フォールバック
        
        try:
            self.ollama_client = OllamaClient()
        except Exception as e:
            self.logger.warning(f"Ollamaクライアント初期化失敗: {e}")
            self.ollama_client = OllamaClient()  # フォールバック

        try:
            from src.core.logger import get_logger
            self.logger = get_logger(__name__)
        except ImportError:
            # フォールバック: 標準ログシステム
            self.logger = logging.getLogger(__name__)
        
        self.model_selector = SmartModelSelector(config_path)
        self.ollama_client = OllamaClient()
        
        # 既存のコードとの互換性のための属性
        self.client_type = ClientType.OLLAMA.value
        self.current_model = None
        self.client = self.ollama_client
        
        # 性能監視
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'model_usage': {},
            'error_counts': {}
        }
        # 設定値の初期化
        self.backend = 'ollama'
        self.base_url = 'http://localhost:11434'  # 必要に応じてconfig等から取得
        
        if self.backend == 'ollama':
            self.api_url = f"{self.base_url}/api"
            self.generate_endpoint = f"{self.api_url}/generate"
            self.chat_endpoint = f"{self.api_url}/chat"
            self.models_endpoint = f"{self.api_url}/tags"
        else:
            self.api_url = self.base_url
            self.generate_endpoint = f"{self.api_url}/completion"
            self.chat_endpoint = f"{self.api_url}/v1/chat/completions"
            self.models_endpoint = f"{self.api_url}/v1/models"
            
        logger.info("拡張LLMクライアントを初期化しました")

    async def generate_async(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        テキスト生成（非同期版）
        
        Args:
            messages: メッセージリスト
            **kwargs: 追加パラメータ
            
        Returns:
            生成されたテキスト
        """
        try:
            if self.backend == 'ollama':
                return await self._generate_ollama_async(messages, **kwargs)
            else:
                return await self._generate_llamacpp_async(messages, **kwargs)
        except Exception as e:
            self.logger.error(f"非同期テキスト生成エラー: {e}")
            raise

    async def generate_stream_async(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[str]:
        """
        ストリーミングテキスト生成（非同期版）
        
        Args:
            messages: メッセージリスト
            **kwargs: 追加パラメータ
            
        Yields:
            生成されたテキストの断片
        """
        try:
            if self.backend == 'ollama':
                async for chunk in self._generate_stream_ollama_async(messages, **kwargs):
                    yield chunk
            else:
                async for chunk in self._generate_stream_llamacpp_async(messages, **kwargs):
                    yield chunk
        except Exception as e:
            self.logger.error(f"非同期ストリーミング生成エラー: {e}")
            raise

    def is_available(self) -> bool:
        """可用性チェック - 追加"""
        try:
            return self.ollama_client.is_available()
        except Exception as e:
            self.logger.warning(f"可用性チェック失敗: {e}")
            return False
    
    def get_capabilities(self) -> Dict[str, bool]:
        """機能取得 - 追加"""
        return {
            'streaming': True,
            'chat': True,
            'embeddings': False,
            'function_calling': False,
            'vision': False,
            'async': False
        }
    
    def get_limits(self) -> Dict[str, Any]:
        """制限情報取得 - 追加"""
        return {
            'max_tokens': 4096,
            'rate_limit': 60,
            'context_window': 4096
        }
    
    def generate_code(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        priority: str = "balanced",
        **kwargs
    ) -> Dict[str, Any]:
        """
        コード生成（スマートモデル選択付き）
        
        Args:
            prompt: 入力プロンプト
            task_type: タスクタイプ
            priority: 優先度 ("speed", "quality", "balanced")
            **kwargs: 追加パラメータ
            
        Returns:
            生成結果辞書
        """
        start_time = time.time()
        self.performance_stats['total_requests'] += 1
        
        try:
            # スマートモデル選択
            selected_model = self.model_selector.select_model(
                task_type=task_type,
                priority=priority,
                context_length=len(prompt)
            )
            # 現在のモデルを更新
            self.current_model = selected_model

            logger.info(f"選択されたモデル: {selected_model} (タスク: {task_type.value}, 優先度: {priority})")
            
            # モデル使用統計更新
            if selected_model not in self.performance_stats['model_usage']:
                self.performance_stats['model_usage'][selected_model] = 0
            self.performance_stats['model_usage'][selected_model] += 1
            
            # LLM呼び出し
            response = self.ollama_client.generate(
                model=selected_model,
                prompt=prompt,
                **kwargs
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.get('success', False):
                self.performance_stats['successful_requests'] += 1
                self.performance_stats['total_response_time'] += response_time
                
                logger.info(f"生成成功 ({response_time:.1f}s): {len(response.get('response', ''))}文字")
                
                return {
                    'success': True,
                    'response': response.get('response', ''),
                    'model': selected_model,
                    'response_time': response_time,
                    'task_type': task_type.value,
                    'priority': priority
                }
            else:
                self.performance_stats['failed_requests'] += 1
                error_msg = response.get('error', 'Unknown error')
                
                # エラー統計更新
                if error_msg not in self.performance_stats['error_counts']:
                    self.performance_stats['error_counts'][error_msg] = 0
                self.performance_stats['error_counts'][error_msg] += 1
                
                logger.error(f"生成失敗: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'model': selected_model,
                    'response_time': response_time
                }
                
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            
            self.performance_stats['failed_requests'] += 1
            error_msg = str(e)
            
            if error_msg not in self.performance_stats['error_counts']:
                self.performance_stats['error_counts'][error_msg] = 0
            self.performance_stats['error_counts'][error_msg] += 1
            
            logger.error(f"生成例外: {e}")
            
            return {
                'success': False,
                'error': error_msg,
                'response_time': response_time
            }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """性能レポート取得"""
        total_requests = self.performance_stats['total_requests']
        
        if total_requests == 0:
            return {
                'total_requests': 0,
                'success_rate': 0.0,
                'avg_response_time': 0.0,
                'model_usage': {},
                'error_summary': {}
            }
        
        success_rate = self.performance_stats['successful_requests'] / total_requests
        avg_response_time = (
            self.performance_stats['total_response_time'] / 
            max(self.performance_stats['successful_requests'], 1)
        )
        
        return {
            'total_requests': total_requests,
            'successful_requests': self.performance_stats['successful_requests'],
            'failed_requests': self.performance_stats['failed_requests'],
            'success_rate': f"{success_rate:.1%}",
            'avg_response_time': f"{avg_response_time:.1f}s",
            'model_usage': self.performance_stats['model_usage'],
            'error_summary': self.performance_stats['error_counts']
        }
    
    def reset_performance_stats(self):
        """性能統計リセット"""
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'model_usage': {},
            'error_counts': {}
        }
        logger.info("性能統計をリセットしました")
    
    def get_available_models(self) -> List[str]:
        """利用可能なモデル一覧取得"""
        try:
            if self.model_selector:
                return self.model_selector.get_available_models()
            else:
                # フォールバック: Ollamaクライアントから直接取得
                models = self.ollama_client.list_models()
                return [model.get('name', '') for model in models]
        except Exception as e:
            self.logger.error(f"モデル一覧取得エラー: {e}")
            # 最終フォールバック: デフォルトモデルリスト
            return ["starcoder:7b", "codellama:7b", "phi4:14b"]
        
    def get_model_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """モデル情報取得"""
        try:
            if model_name is None:
                model_name = self.current_model or "default"
            
            # 基本情報
            info = {
                'model': model_name,
                'provider': self.client_type,
                'status': 'available' if self.is_available() else 'unavailable',
                'capabilities': self.get_capabilities(),
                'limits': self.get_limits()
            }
            
            return info
            
        except Exception as e:
            self.logger.error(f"モデル情報取得エラー: {e}")
            return {
                'model': model_name or 'unknown',
                'provider': self.client_type,
                'status': 'error',
                'error': str(e)
            }
            
        except Exception as e:
            self.logger.error(f"モデル情報取得エラー: {e}")
            return {
                'model': model_name or 'unknown',
                'provider': self.client_type,
                'status': 'error',
                'error': str(e)
            }
    def validate_connection(self) -> bool:
        print("-----------接続確認-------------------")
        """
        接続確認
        
        Returns:
            接続可能かどうか
        """
        try:
            self.logger.info(f"models_endpoint: {self.models_endpoint}")
            response = requests.get(self.models_endpoint, timeout=100)
            self.logger.info(f"status_code: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"接続確認エラー: {e}")
            return False

def shutdown(self):
        """クライアント終了処理"""
        try:
            if hasattr(self.ollama_client, 'shutdown'):
                self.ollama_client.shutdown()
            self.logger.info("LLMクライアントを終了しました")
        except Exception as e:
            self.logger.error(f"クライアント終了エラー: {e}")
logger = get_logger(__name__)



# エクスポート
__all__ = [
    'EnhancedLLMClient', 'LLMRequest', 'LLMResponse', 'ClientType'
]
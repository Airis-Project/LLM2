# src/llm/openai_client.py
"""
OpenAI APIクライアントモジュール
OpenAI GPTモデルとの通信を管理
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
import aiohttp
import openai
from openai import AsyncOpenAI

from .base_llm import BaseLLM, LLMMessage, LLMResponse, LLMConfig, LLMStatus, LLMRole
from ..core.logger import get_logger
#from ..core.config_manager import get_config
from ..utils.validation_utils import ValidationUtils

def get_config(*args, **kwargs):
    from ..core.config_manager import get_config
    return get_config(*args, **kwargs)

logger = get_logger(__name__)

class OpenAIClient(BaseLLM):
    """OpenAI APIクライアントクラス"""
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None):
        """
        初期化
        
        Args:
            api_key: OpenAI APIキー
            config: LLM設定
        """
        super().__init__(config)
        
        # APIキーを設定
        self.api_key = api_key or self._get_api_key()
        if not self.api_key:
            raise ValueError("OpenAI APIキーが設定されていません")
        
        # OpenAIクライアントを初期化
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # デフォルト設定
        if not self.config.model:
            self.config.model = "gpt-3.5-turbo"
        
        # 利用可能なモデル一覧
        self.available_models = [
            "gpt-4",
            "gpt-4-32k",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo-instruct"
        ]
        
        # バリデーター
        self.validation_utils = ValidationUtils()
        
        self.logger.info(f"OpenAIクライアントを初期化しました (model: {self.config.model})")
    
    def _get_api_key(self) -> Optional[str]:
        """APIキーを取得"""
        try:
            # 設定ファイルから取得
            config = get_config()
            api_key = config.get('openai', {}).get('api_key')
            
            if api_key:
                return api_key
            
            # 環境変数から取得
            import os
            return os.getenv('OPENAI_API_KEY')
            
        except Exception as e:
            self.logger.error(f"APIキー取得エラー: {e}")
            return None
    
    async def generate_async(self, 
                           messages: List[LLMMessage], 
                           config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        非同期でテキストを生成
        
        Args:
            messages: メッセージリスト
            config: 生成設定
            
        Returns:
            LLMResponse: 生成結果
        """
        start_time = time.time()
        effective_config = config or self.config
        
        try:
            self._set_status(LLMStatus.PROCESSING)
            
            # メッセージを検証
            if not messages:
                raise ValueError("メッセージが空です")
            
            # OpenAI形式に変換
            openai_messages = self._convert_messages_to_openai(messages)
            
            # リクエストパラメータを構築
            request_params = self._build_request_params(effective_config)
            request_params['messages'] = openai_messages
            
            # API呼び出し
            response = await self._execute_with_retry(
                self._call_openai_api,
                request_params,
                config=effective_config
            )
            
            # レスポンスを処理
            llm_response = self._process_response(response, start_time)
            
            # メトリクスを記録
            usage = response.usage
            tokens = usage.total_tokens if usage else 0
            self._record_request(True, tokens, llm_response.response_time)
            
            self._set_status(LLMStatus.IDLE)
            return llm_response
            
        except Exception as e:
            self.logger.error(f"OpenAI生成エラー: {e}")
            self._record_request(False, 0, time.time() - start_time)
            self._set_status(LLMStatus.ERROR)
            raise
    
    async def generate_stream_async(self, 
                                  messages: List[LLMMessage], 
                                  config: Optional[LLMConfig] = None) -> AsyncGenerator[str, None]:
        """
        非同期でストリーミング生成
        
        Args:
            messages: メッセージリスト
            config: 生成設定
            
        Yields:
            str: 生成されたテキストの断片
        """
        start_time = time.time()
        effective_config = config or self.config
        
        try:
            self._set_status(LLMStatus.PROCESSING)
            
            # メッセージを検証
            if not messages:
                raise ValueError("メッセージが空です")
            
            # OpenAI形式に変換
            openai_messages = self._convert_messages_to_openai(messages)
            
            # リクエストパラメータを構築
            request_params = self._build_request_params(effective_config)
            request_params['messages'] = openai_messages
            request_params['stream'] = True
            
            # ストリーミング呼び出し
            total_tokens = 0
            async for chunk in self._stream_openai_api(request_params):
                if chunk:
                    yield chunk
                    total_tokens += 1  # 概算
            
            # メトリクスを記録
            self._record_request(True, total_tokens, time.time() - start_time)
            self._set_status(LLMStatus.IDLE)
            
        except Exception as e:
            self.logger.error(f"OpenAIストリーミング生成エラー: {e}")
            self._record_request(False, 0, time.time() - start_time)
            self._set_status(LLMStatus.ERROR)
            raise
    
    def is_available(self) -> bool:
        """
        OpenAI APIが利用可能かチェック
        
        Returns:
            bool: 利用可能フラグ
        """
        try:
            # APIキーの存在確認
            if not self.api_key:
                return False
            
            # 簡単なAPI呼び出しでテスト
            asyncio.run(self._test_api_connection())
            return True
            
        except Exception as e:
            self.logger.warning(f"OpenAI API利用不可: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        モデル情報を取得
        
        Returns:
            Dict[str, Any]: モデル情報
        """
        return {
            'provider': 'OpenAI',
            'model': self.config.model,
            'available_models': self.available_models,
            'supports_streaming': True,
            'supports_functions': True,
            'max_tokens': self._get_model_max_tokens(),
            'context_window': self._get_model_context_window()
        }
    
    def _convert_messages_to_openai(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """メッセージをOpenAI形式に変換"""
        openai_messages = []
        
        for message in messages:
            openai_message = {
                'role': message.role.value,
                'content': message.content
            }
            
            # メタデータがある場合は追加
            if message.metadata:
                # OpenAI APIでサポートされているメタデータのみ追加
                if 'name' in message.metadata:
                    openai_message['name'] = message.metadata['name']
            
            openai_messages.append(openai_message)
        
        return openai_messages
    
    def _build_request_params(self, config: LLMConfig) -> Dict[str, Any]:
        """リクエストパラメータを構築"""
        params = {
            'model': config.model,
            'temperature': config.temperature,
            'max_tokens': config.max_tokens,
            'top_p': config.top_p,
            'frequency_penalty': config.frequency_penalty,
            'presence_penalty': config.presence_penalty
        }
        
        # ストップシーケンスを追加
        if config.stop_sequences:
            params['stop'] = config.stop_sequences
        
        return params
    
    async def _call_openai_api(self, params: Dict[str, Any]):
        """OpenAI APIを呼び出し"""
        try:
            response = await self.client.chat.completions.create(**params)
            return response
            
        except openai.RateLimitError as e:
            self.logger.warning(f"OpenAI レート制限エラー: {e}")
            raise
        except openai.APIError as e:
            self.logger.error(f"OpenAI APIエラー: {e}")
            raise
        except Exception as e:
            self.logger.error(f"OpenAI API呼び出しエラー: {e}")
            raise
    
    async def _stream_openai_api(self, params: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """OpenAI APIをストリーミング呼び出し"""
        try:
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except openai.RateLimitError as e:
            self.logger.warning(f"OpenAI ストリーミングレート制限エラー: {e}")
            raise
        except openai.APIError as e:
            self.logger.error(f"OpenAI ストリーミングAPIエラー: {e}")
            raise
        except Exception as e:
            self.logger.error(f"OpenAI ストリーミング呼び出しエラー: {e}")
            raise
    
    def _process_response(self, response, start_time: float) -> LLMResponse:
        """レスポンスを処理"""
        try:
            choice = response.choices[0]
            content = choice.message.content
            
            # 使用量情報を取得
            usage = {}
            if response.usage:
                usage = {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            
            # レスポンスオブジェクトを作成
            llm_response = LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=choice.finish_reason,
                response_time=time.time() - start_time,
                metadata={
                    'response_id': response.id,
                    'created': response.created,
                    'system_fingerprint': getattr(response, 'system_fingerprint', None)
                }
            )
            
            return llm_response
            
        except Exception as e:
            self.logger.error(f"レスポンス処理エラー: {e}")
            raise
    
    async def _test_api_connection(self):
        """API接続をテスト"""
        try:
            test_messages = [
                {'role': 'user', 'content': 'Hello'}
            ]
            
            await self.client.chat.completions.create(
                model=self.config.model,
                messages=test_messages,
                max_tokens=1
            )
            
        except Exception as e:
            self.logger.error(f"API接続テストエラー: {e}")
            raise
    
    def _get_model_max_tokens(self) -> int:
        """モデルの最大トークン数を取得"""
        model_limits = {
            'gpt-4': 8192,
            'gpt-4-32k': 32768,
            'gpt-4-turbo-preview': 128000,
            'gpt-3.5-turbo': 4096,
            'gpt-3.5-turbo-16k': 16384,
            'gpt-3.5-turbo-instruct': 4096
        }
        
        return model_limits.get(self.config.model, 4096)
    
    def _get_model_context_window(self) -> int:
        """モデルのコンテキストウィンドウサイズを取得"""
        # 通常、コンテキストウィンドウは最大トークン数と同じ
        return self._get_model_max_tokens()
    
    async def get_available_models(self) -> List[str]:
        """
        利用可能なモデル一覧を取得
        
        Returns:
            List[str]: モデル名のリスト
        """
        try:
            models = await self.client.models.list()
            
            # チャット用モデルのみフィルタリング
            chat_models = []
            for model in models.data:
                if any(prefix in model.id for prefix in ['gpt-3.5', 'gpt-4']):
                    chat_models.append(model.id)
            
            return sorted(chat_models)
            
        except Exception as e:
            self.logger.error(f"モデル一覧取得エラー: {e}")
            return self.available_models
    
    def set_model(self, model: str):
        """
        使用モデルを設定
        
        Args:
            model: モデル名
        """
        if model not in self.available_models:
            self.logger.warning(f"未知のモデル: {model}")
        
        self.config.model = model
        self.logger.info(f"モデルを変更しました: {model}")
    
    def estimate_tokens(self, text: str) -> int:
        """
        テキストのトークン数を概算
        
        Args:
            text: テキスト
            
        Returns:
            int: 概算トークン数
        """
        try:
            # 簡易的な概算（実際のトークナイザーを使用することを推奨）
            # 英語: 約4文字で1トークン
            # 日本語: 約1文字で1トークン
            
            # 日本語文字数をカウント
            japanese_chars = sum(1 for char in text if ord(char) > 127)
            english_chars = len(text) - japanese_chars
            
            estimated_tokens = japanese_chars + (english_chars // 4)
            
            return max(estimated_tokens, 1)
            
        except Exception as e:
            self.logger.error(f"トークン数概算エラー: {e}")
            return len(text) // 4  # フォールバック
    
    def validate_input(self, messages: List[LLMMessage]) -> bool:
        """
        入力を検証
        
        Args:
            messages: メッセージリスト
            
        Returns:
            bool: 検証結果
        """
        try:
            if not messages:
                return False
            
            # 総トークン数をチェック
            total_tokens = 0
            for message in messages:
                total_tokens += self.estimate_tokens(message.content)
            
            max_context = self._get_model_context_window()
            if total_tokens > max_context * 0.8:  # 80%を超えたら警告
                self.logger.warning(f"コンテキストサイズが大きすぎます: {total_tokens}/{max_context}")
                return False
            
            # メッセージ形式をチェック
            for message in messages:
                if not message.content.strip():
                    return False
                
                if message.role not in [LLMRole.SYSTEM, LLMRole.USER, LLMRole.ASSISTANT]:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"入力検証エラー: {e}")
            return False
    
    async def get_usage_statistics(self) -> Dict[str, Any]:
        """
        使用統計を取得
        
        Returns:
            Dict[str, Any]: 使用統計
        """
        try:
            base_stats = self.get_metrics()
            
            # OpenAI固有の統計を追加
            openai_stats = {
                'api_key_valid': bool(self.api_key),
                'current_model': self.config.model,
                'estimated_cost': self._estimate_cost(base_stats.get('total_tokens', 0)),
                'rate_limit_status': await self._check_rate_limits()
            }
            
            base_stats.update(openai_stats)
            return base_stats
            
        except Exception as e:
            self.logger.error(f"使用統計取得エラー: {e}")
            return self.get_metrics()
    
    def _estimate_cost(self, total_tokens: int) -> float:
        """
        コストを概算
        
        Args:
            total_tokens: 総トークン数
            
        Returns:
            float: 概算コスト（USD）
        """
        try:
            # モデル別の料金（2024年時点の概算）
            pricing = {
                'gpt-4': 0.03 / 1000,  # $0.03 per 1K tokens
                'gpt-4-32k': 0.06 / 1000,
                'gpt-4-turbo-preview': 0.01 / 1000,
                'gpt-3.5-turbo': 0.002 / 1000,
                'gpt-3.5-turbo-16k': 0.004 / 1000,
                'gpt-3.5-turbo-instruct': 0.002 / 1000
            }
            
            rate = pricing.get(self.config.model, 0.002 / 1000)
            return total_tokens * rate
            
        except Exception as e:
            self.logger.error(f"コスト概算エラー: {e}")
            return 0.0
    
    async def _check_rate_limits(self) -> Dict[str, Any]:
        """レート制限状況をチェック"""
        try:
            # 実際のレート制限チェックは複雑なため、簡易版
            return {
                'requests_remaining': 'unknown',
                'tokens_remaining': 'unknown',
                'reset_time': 'unknown'
            }
            
        except Exception as e:
            self.logger.error(f"レート制限チェックエラー: {e}")
            return {}
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            # OpenAIクライアントのクリーンアップ
            if hasattr(self.client, 'close'):
                asyncio.create_task(self.client.close())
            
            self.logger.info("OpenAIクライアントをクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"OpenAIクライアントクリーンアップエラー: {e}")

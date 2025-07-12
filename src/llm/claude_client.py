# src/llm/claude_client.py
"""
Claude APIクライアントモジュール
Anthropic Claude APIとの通信を管理
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
import aiohttp
import anthropic
from anthropic import AsyncAnthropic

from src.llm.base_llm import BaseLLM, LLMMessage, LLMResponse, LLMConfig, LLMStatus, LLMRole
from src.core.logger import get_logger
#from ..core.config_manager import get_config
from src.utils.validation_utils import ValidationUtils

logger = get_logger(__name__)

def get_config(*args, **kwargs):
    from ..core.config_manager import get_config
    return get_config(*args, **kwargs)

class ClaudeClient(BaseLLM):
    """Claude APIクライアントクラス"""
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[LLMConfig] = None):
        """
        初期化
        
        Args:
            api_key: Anthropic APIキー
            config: LLM設定
        """
        super().__init__(config)
        
        # APIキーを設定
        self.api_key = api_key or self._get_api_key()
        if not self.api_key:
            raise ValueError("Anthropic APIキーが設定されていません")
        
        # Claudeクライアントを初期化
        self.client = AsyncAnthropic(api_key=self.api_key)
        
        # デフォルト設定
        if not self.config.model:
            self.config.model = "claude-3-sonnet-20240229"
        
        # 利用可能なモデル一覧
        self.available_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
        
        # モデル別の最大トークン数
        self.model_limits = {
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
            "claude-2.1": 200000,
            "claude-2.0": 100000,
            "claude-instant-1.2": 100000
        }
        
        # バリデーター
        self.validation_utils = ValidationUtils()
        
        self.logger.info(f"Claudeクライアントを初期化しました (model: {self.config.model})")
    
    def _get_api_key(self) -> Optional[str]:
        """APIキーを取得"""
        try:
            # 設定ファイルから取得
            config = get_config()
            api_key = config.get('anthropic', {}).get('api_key')
            
            if api_key:
                return api_key
            
            # 環境変数から取得
            import os
            return os.getenv('ANTHROPIC_API_KEY')
            
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
            
            # Claude形式に変換
            claude_messages, system_prompt = self._convert_messages_to_claude(messages)
            
            # リクエストパラメータを構築
            request_params = self._build_request_params(effective_config)
            request_params['messages'] = claude_messages
            
            if system_prompt:
                request_params['system'] = system_prompt
            
            # API呼び出し
            response = await self._execute_with_retry(
                self._call_claude_api,
                request_params,
                config=effective_config
            )
            
            # レスポンスを処理
            llm_response = self._process_response(response, start_time)
            
            # メトリクスを記録
            usage = getattr(response, 'usage', None)
            tokens = usage.output_tokens + usage.input_tokens if usage else 0
            self._record_request(True, tokens, llm_response.response_time)
            
            self._set_status(LLMStatus.IDLE)
            return llm_response
            
        except Exception as e:
            self.logger.error(f"Claude生成エラー: {e}")
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
            
            # Claude形式に変換
            claude_messages, system_prompt = self._convert_messages_to_claude(messages)
            
            # リクエストパラメータを構築
            request_params = self._build_request_params(effective_config)
            request_params['messages'] = claude_messages
            request_params['stream'] = True
            
            if system_prompt:
                request_params['system'] = system_prompt
            
            # ストリーミング呼び出し
            total_tokens = 0
            async for chunk in self._stream_claude_api(request_params):
                if chunk:
                    yield chunk
                    total_tokens += 1  # 概算
            
            # メトリクスを記録
            self._record_request(True, total_tokens, time.time() - start_time)
            self._set_status(LLMStatus.IDLE)
            
        except Exception as e:
            self.logger.error(f"Claudeストリーミング生成エラー: {e}")
            self._record_request(False, 0, time.time() - start_time)
            self._set_status(LLMStatus.ERROR)
            raise
    
    def is_available(self) -> bool:
        """
        Claude APIが利用可能かチェック
        
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
            self.logger.warning(f"Claude API利用不可: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        モデル情報を取得
        
        Returns:
            Dict[str, Any]: モデル情報
        """
        return {
            'provider': 'Anthropic',
            'model': self.config.model,
            'available_models': self.available_models,
            'supports_streaming': True,
            'supports_functions': False,  # Claude 3では限定的
            'max_tokens': self._get_model_max_tokens(),
            'context_window': self._get_model_context_window()
        }
    
    def _convert_messages_to_claude(self, messages: List[LLMMessage]) -> tuple[List[Dict[str, str]], Optional[str]]:
        """メッセージをClaude形式に変換"""
        claude_messages = []
        system_prompt = None
        
        for message in messages:
            if message.role == LLMRole.SYSTEM:
                # Claudeではシステムメッセージは別パラメータ
                if system_prompt:
                    system_prompt += "\n\n" + message.content
                else:
                    system_prompt = message.content
            else:
                claude_message = {
                    'role': 'user' if message.role == LLMRole.USER else 'assistant',
                    'content': message.content
                }
                claude_messages.append(claude_message)
        
        return claude_messages, system_prompt
    
    def _build_request_params(self, config: LLMConfig) -> Dict[str, Any]:
        """リクエストパラメータを構築"""
        params = {
            'model': config.model,
            'max_tokens': min(config.max_tokens, 4096),  # Claudeの制限
            'temperature': config.temperature
        }
        
        # Claude 3では一部パラメータが異なる
        if 'claude-3' in config.model:
            # top_pはClaude 3でサポート
            if config.top_p != 1.0:
                params['top_p'] = config.top_p
        
        # ストップシーケンスを追加
        if config.stop_sequences:
            params['stop_sequences'] = config.stop_sequences[:4]  # 最大4個
        
        return params
    
    async def _call_claude_api(self, params: Dict[str, Any]):
        """Claude APIを呼び出し"""
        try:
            response = await self.client.messages.create(**params)
            return response
            
        except anthropic.RateLimitError as e:
            self.logger.warning(f"Claude レート制限エラー: {e}")
            raise
        except anthropic.APIError as e:
            self.logger.error(f"Claude APIエラー: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Claude API呼び出しエラー: {e}")
            raise
    
    async def _stream_claude_api(self, params: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Claude APIをストリーミング呼び出し"""
        try:
            async with self.client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except anthropic.RateLimitError as e:
            self.logger.warning(f"Claude ストリーミングレート制限エラー: {e}")
            raise
        except anthropic.APIError as e:
            self.logger.error(f"Claude ストリーミングAPIエラー: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Claude ストリーミング呼び出しエラー: {e}")
            raise
    
    def _process_response(self, response, start_time: float) -> LLMResponse:
        """レスポンスを処理"""
        try:
            # Claudeのレスポンス形式に応じて処理
            content = ""
            if hasattr(response, 'content') and response.content:
                # Claude 3の場合
                for content_block in response.content:
                    if hasattr(content_block, 'text'):
                        content += content_block.text
            elif hasattr(response, 'completion'):
                # Claude 2の場合
                content = response.completion
            
            # 使用量情報を取得
            usage = {}
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    'input_tokens': response.usage.input_tokens,
                    'output_tokens': response.usage.output_tokens,
                    'total_tokens': response.usage.input_tokens + response.usage.output_tokens
                }
            
            # レスポンスオブジェクトを作成
            llm_response = LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=getattr(response, 'stop_reason', ''),
                response_time=time.time() - start_time,
                metadata={
                    'response_id': getattr(response, 'id', ''),
                    'type': getattr(response, 'type', ''),
                    'role': getattr(response, 'role', '')
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
            
            await self.client.messages.create(
                model=self.config.model,
                messages=test_messages,
                max_tokens=1
            )
            
        except Exception as e:
            self.logger.error(f"API接続テストエラー: {e}")
            raise
    
    def _get_model_max_tokens(self) -> int:
        """モデルの最大トークン数を取得"""
        return self.model_limits.get(self.config.model, 100000)
    
    def _get_model_context_window(self) -> int:
        """モデルのコンテキストウィンドウサイズを取得"""
        return self.model_limits.get(self.config.model, 100000)
    
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
            # Claudeのトークン計算は複雑なため簡易版
            # 英語: 約4文字で1トークン
            # 日本語: 約1.5文字で1トークン
            
            # 日本語文字数をカウント
            japanese_chars = sum(1 for char in text if ord(char) > 127)
            english_chars = len(text) - japanese_chars
            
            estimated_tokens = int(japanese_chars / 1.5) + (english_chars // 4)
            
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
            
            # Claudeの制約をチェック
            if not self._validate_claude_constraints(messages):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"入力検証エラー: {e}")
            return False
    
    def _validate_claude_constraints(self, messages: List[LLMMessage]) -> bool:
        """Claude固有の制約を検証"""
        try:
            # メッセージの順序をチェック（user/assistantの交互）
            non_system_messages = [msg for msg in messages if msg.role != LLMRole.SYSTEM]
            
            if not non_system_messages:
                return True
            
            # 最初のメッセージはuserである必要がある
            if non_system_messages[0].role != LLMRole.USER:
                self.logger.warning("最初のメッセージはユーザーメッセージである必要があります")
                return False
            
            # user/assistantが交互になっているかチェック
            for i in range(1, len(non_system_messages)):
                current_role = non_system_messages[i].role
                prev_role = non_system_messages[i-1].role
                
                if current_role == prev_role:
                    self.logger.warning("同じロールのメッセージが連続しています")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Claude制約検証エラー: {e}")
            return False
    
    async def get_usage_statistics(self) -> Dict[str, Any]:
        """
        使用統計を取得
        
        Returns:
            Dict[str, Any]: 使用統計
        """
        try:
            base_stats = self.get_metrics()
            
            # Claude固有の統計を追加
            claude_stats = {
                'api_key_valid': bool(self.api_key),
                'current_model': self.config.model,
                'estimated_cost': self._estimate_cost(base_stats.get('total_tokens', 0)),
                'model_family': self._get_model_family()
            }
            
            base_stats.update(claude_stats)
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
                'claude-3-opus-20240229': {
                    'input': 15.0 / 1000000,   # $15 per 1M input tokens
                    'output': 75.0 / 1000000   # $75 per 1M output tokens
                },
                'claude-3-sonnet-20240229': {
                    'input': 3.0 / 1000000,
                    'output': 15.0 / 1000000
                },
                'claude-3-haiku-20240307': {
                    'input': 0.25 / 1000000,
                    'output': 1.25 / 1000000
                },
                'claude-2.1': {
                    'input': 8.0 / 1000000,
                    'output': 24.0 / 1000000
                },
                'claude-2.0': {
                    'input': 8.0 / 1000000,
                    'output': 24.0 / 1000000
                },
                'claude-instant-1.2': {
                    'input': 0.8 / 1000000,
                    'output': 2.4 / 1000000
                }
            }
            
            model_pricing = pricing.get(self.config.model, {
                'input': 8.0 / 1000000,
                'output': 24.0 / 1000000
            })
            
            # 入力と出力の比率を仮定（入力:出力 = 3:1）
            input_tokens = int(total_tokens * 0.75)
            output_tokens = int(total_tokens * 0.25)
            
            cost = (input_tokens * model_pricing['input'] + 
                   output_tokens * model_pricing['output'])
            
            return cost
            
        except Exception as e:
            self.logger.error(f"コスト概算エラー: {e}")
            return 0.0
    
    def _get_model_family(self) -> str:
        """モデルファミリーを取得"""
        if 'claude-3-opus' in self.config.model:
            return 'Claude 3 Opus'
        elif 'claude-3-sonnet' in self.config.model:
            return 'Claude 3 Sonnet'
        elif 'claude-3-haiku' in self.config.model:
            return 'Claude 3 Haiku'
        elif 'claude-2.1' in self.config.model:
            return 'Claude 2.1'
        elif 'claude-2.0' in self.config.model:
            return 'Claude 2.0'
        elif 'claude-instant' in self.config.model:
            return 'Claude Instant'
        else:
            return 'Unknown'
    
    async def get_model_capabilities(self) -> Dict[str, Any]:
        """
        モデルの機能を取得
        
        Returns:
            Dict[str, Any]: モデル機能
        """
        try:
            capabilities = {
                'text_generation': True,
                'conversation': True,
                'code_generation': True,
                'analysis': True,
                'creative_writing': True,
                'math': True,
                'reasoning': True,
                'multilingual': True,
                'function_calling': False,
                'image_analysis': False,
                'document_analysis': False
            }
            
            # Claude 3の場合は追加機能
            if 'claude-3' in self.config.model:
                capabilities.update({
                    'image_analysis': True,
                    'document_analysis': True,
                    'advanced_reasoning': True
                })
            
            return capabilities
            
        except Exception as e:
            self.logger.error(f"モデル機能取得エラー: {e}")
            return {}
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            # Claudeクライアントのクリーンアップ
            if hasattr(self.client, 'close'):
                asyncio.create_task(self.client.close())
            
            self.logger.info("Claudeクライアントをクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"Claudeクライアントクリーンアップエラー: {e}")

# src/core/llm_interface.py
"""
LLMインターフェース - 複数のLLMプロバイダーとの統一インターフェース
"""

import logging
import json
import asyncio
from os import name
import time
from typing import List, Dict, Any, Optional, Tuple, Union, AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime
import hashlib
import openai
import anthropic
import requests
from pathlib import Path

class LLMProvider(Enum):
    """LLMプロバイダー"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"
    AZURE_OPENAI = "azure_openai"

class MessageRole(Enum):
    """メッセージの役割"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class LLMMessage:
    """LLMメッセージ"""
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            **self.metadata
        }

@dataclass
class LLMResponse:
    """LLM応答"""
    content: str
    provider: LLMProvider
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    response_time: float = 0.0
    finish_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "provider": self.provider.value,
            "model": self.model,
            "usage": self.usage,
            "metadata": self.metadata,
            "response_time": self.response_time,
            "finish_reason": self.finish_reason
        }

@dataclass
class LLMConfig:
    """LLM設定"""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0
    additional_params: Dict[str, Any] = field(default_factory=dict)

class LLMProviderInterface(ABC):
    """LLMプロバイダーの抽象基底クラス"""
    
    @abstractmethod
    async def generate_response(self, 
                              messages: List[LLMMessage], 
                              config: LLMConfig) -> LLMResponse:
        """レスポンスを生成"""
        pass
    
    @abstractmethod
    async def generate_stream_response(self, 
                                     messages: List[LLMMessage], 
                                     config: LLMConfig) -> AsyncGenerator[str, None]:
        """ストリーミングレスポンスを生成"""
        pass
    
    @abstractmethod
    def validate_config(self, config: LLMConfig) -> bool:
        """設定を検証"""
        pass

class OpenAIProvider(LLMProviderInterface):
    """OpenAIプロバイダー"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = None
    
    def _get_client(self, config: LLMConfig):
        """OpenAIクライアントを取得"""
        if config.provider == LLMProvider.AZURE_OPENAI:
            return openai.AzureOpenAI(
                api_key=config.api_key,
                api_version="2024-02-01",
                azure_endpoint=config.api_base
            )
        else:
            return openai.OpenAI(
                api_key=config.api_key,
                base_url=config.api_base
            )
    
    async def generate_response(self, 
                              messages: List[LLMMessage], 
                              config: LLMConfig) -> LLMResponse:
        """レスポンスを生成"""
        try:
            start_time = time.time()
            client = self._get_client(config)
            
            # メッセージを変換
            openai_messages = [msg.to_dict() for msg in messages]
            
            # API呼び出し
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=config.model,
                messages=openai_messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                timeout=config.timeout,
                **config.additional_params
            )
            
            response_time = time.time() - start_time
            
            # レスポンスを構築
            llm_response = LLMResponse(
                content=response.choices[0].message.content,
                provider=config.provider,
                model=config.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                response_time=response_time,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "response_id": response.id,
                    "created": response.created
                }
            )
            
            return llm_response
            
        except Exception as e:
            self.logger.error(f"OpenAI API呼び出しエラー: {e}")
            raise
    
    async def generate_stream_response(self, 
                                     messages: List[LLMMessage], 
                                     config: LLMConfig) -> AsyncGenerator[str, None]:
        """ストリーミングレスポンスを生成"""
        try:
            client = self._get_client(config)
            
            # メッセージを変換
            openai_messages = [msg.to_dict() for msg in messages]
            
            # ストリーミングAPI呼び出し
            stream = await asyncio.to_thread(
                client.chat.completions.create,
                model=config.model,
                messages=openai_messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                stream=True,
                **config.additional_params
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            self.logger.error(f"OpenAI ストリーミングエラー: {e}")
            raise
    
    def validate_config(self, config: LLMConfig) -> bool:
        """設定を検証"""
        if not config.api_key:
            return False
        
        if config.provider == LLMProvider.AZURE_OPENAI and not config.api_base:
            return False
        
        return True

class AnthropicProvider(LLMProviderInterface):
    """Anthropicプロバイダー"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _get_client(self, config: LLMConfig):
        """Anthropicクライアントを取得"""
        return anthropic.Anthropic(api_key=config.api_key)
    
    def _convert_messages(self, messages: List[LLMMessage]) -> Tuple[str, List[Dict]]:
        """メッセージをAnthropic形式に変換"""
        system_message = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        return system_message, anthropic_messages
    
    async def generate_response(self, 
                              messages: List[LLMMessage], 
                              config: LLMConfig) -> LLMResponse:
        """レスポンスを生成"""
        try:
            start_time = time.time()
            client = self._get_client(config)
            
            # メッセージを変換
            system_message, anthropic_messages = self._convert_messages(messages)
            
            # API呼び出し
            response = await asyncio.to_thread(
                client.messages.create,
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system=system_message,
                messages=anthropic_messages,
                **config.additional_params
            )
            
            response_time = time.time() - start_time
            
            # レスポンスを構築
            llm_response = LLMResponse(
                content=response.content[0].text,
                provider=config.provider,
                model=config.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                response_time=response_time,
                finish_reason=response.stop_reason,
                metadata={
                    "response_id": response.id,
                    "model": response.model
                }
            )
            
            return llm_response
            
        except Exception as e:
            self.logger.error(f"Anthropic API呼び出しエラー: {e}")
            raise
    
    async def generate_stream_response(self, 
                                     messages: List[LLMMessage], 
                                     config: LLMConfig) -> AsyncGenerator[str, None]:
        """ストリーミングレスポンスを生成"""
        try:
            client = self._get_client(config)
            
            # メッセージを変換
            system_message, anthropic_messages = self._convert_messages(messages)
            
            # ストリーミングAPI呼び出し
            stream = await asyncio.to_thread(
                client.messages.create,
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                system=system_message,
                messages=anthropic_messages,
                stream=True,
                **config.additional_params
            )
            
            async for chunk in stream:
                if chunk.type == "content_block_delta":
                    yield chunk.delta.text
                    
        except Exception as e:
            self.logger.error(f"Anthropic ストリーミングエラー: {e}")
            raise
    
    def validate_config(self, config: LLMConfig) -> bool:
        """設定を検証"""
        return bool(config.api_key)

class LocalLLMProvider(LLMProviderInterface):
    """ローカルLLMプロバイダー（Ollama等）"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def generate_response(self, 
                              messages: List[LLMMessage], 
                              config: LLMConfig) -> LLMResponse:
        """レスポンスを生成"""
        try:
            start_time = time.time()
            
            # ローカルAPI呼び出し
            payload = {
                "model": config.model,
                "messages": [msg.to_dict() for msg in messages],
                "options": {
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                    "num_predict": config.max_tokens
                }
            }
            
            response = await asyncio.to_thread(
                requests.post,
                f"{config.api_base}/api/chat",
                json=payload,
                timeout=config.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            response_time = time.time() - start_time
            
            # レスポンスを構築
            llm_response = LLMResponse(
                content=result.get("message", {}).get("content", ""),
                provider=config.provider,
                model=config.model,
                usage={
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                },
                response_time=response_time,
                finish_reason=result.get("done_reason", "stop"),
                metadata={
                    "total_duration": result.get("total_duration", 0),
                    "load_duration": result.get("load_duration", 0),
                    "eval_duration": result.get("eval_duration", 0)
                }
            )
            
            return llm_response
            
        except Exception as e:
            self.logger.error(f"ローカルLLM API呼び出しエラー: {e}")
            raise
    
    async def generate_stream_response(self, 
                                     messages: List[LLMMessage], 
                                     config: LLMConfig) -> AsyncGenerator[str, None]:
        """ストリーミングレスポンスを生成"""
        try:
            payload = {
                "model": config.model,
                "messages": [msg.to_dict() for msg in messages],
                "stream": True,
                "options": {
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                    "num_predict": config.max_tokens
                }
            }
            
            response = await asyncio.to_thread(
                requests.post,
                f"{config.api_base}/api/chat",
                json=payload,
                stream=True,
                timeout=config.timeout
            )
            
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            self.logger.error(f"ローカルLLM ストリーミングエラー: {e}")
            raise
    
    def validate_config(self, config: LLMConfig) -> bool:
        """設定を検証"""
        return bool(config.api_base)

class LLMInterface:
    """
    LLMインターフェースメインクラス
    複数のプロバイダーを統一的に管理
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # プロバイダーマッピング
        self.providers = {
            LLMProvider.OPENAI: OpenAIProvider(),
            LLMProvider.ANTHROPIC: AnthropicProvider(),
            LLMProvider.LOCAL: LocalLLMProvider(),
            LLMProvider.AZURE_OPENAI: OpenAIProvider()
        }
        
        # デフォルト設定
        self.default_configs = {
            LLMProvider.OPENAI: LLMConfig(
                provider=LLMProvider.OPENAI,
                model="gpt-3.5-turbo",
                max_tokens=4000,
                temperature=0.7
            ),
            LLMProvider.ANTHROPIC: LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.7
            ),
            LLMProvider.LOCAL: LLMConfig(
                provider=LLMProvider.LOCAL,
                model="llama2",
                api_base="http://localhost:11434",
                max_tokens=4000,
                temperature=0.7
            )
        }
        
        # レスポンスキャッシュ
        self.response_cache = {}
        self.cache_enabled = True
        self.cache_max_size = 1000
        
        # 統計情報
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "provider_usage": {}
        }
        
        self.logger.info("LLMInterface初期化完了")
    
    async def generate_response(self, 
        messages: List[LLMMessage], 
        config: LLMConfig = None,
        use_cache: bool = True) -> LLMResponse:
        """
        レスポンスを生成
        
        Args:
            messages: メッセージリスト
            config: LLM設定
            use_cache: キャッシュを使用するか
            
        Returns:
            LLMレスポンス
        """
        try:
            # 設定の準備
            if config is None:
                config = self.default_configs[LLMProvider.OPENAI]
            
            # 統計更新
            self.stats["total_requests"] += 1
            provider_name = config.provider.value
            if provider_name not in self.stats["provider_usage"]:
                self.stats["provider_usage"][provider_name] = 0
            self.stats["provider_usage"][provider_name] += 1
            
            # キャッシュチェック
            if use_cache and self.cache_enabled:
                cache_key = self._generate_cache_key(messages, config)
                if cache_key in self.response_cache:
                    self.stats["cache_hits"] += 1
                    self.logger.debug("キャッシュからレスポンスを返却")
                    return self.response_cache[cache_key]
            
            # プロバイダー取得
            provider = self.providers.get(config.provider)
            if not provider:
                raise ValueError(f"サポートされていないプロバイダー: {config.provider}")
            
            # 設定検証
            if not provider.validate_config(config):
                raise ValueError("無効な設定")
            
            # リトライ機能付きでレスポンス生成
            response = await self._generate_with_retry(provider, messages, config)
            
            # キャッシュに保存
            if use_cache and self.cache_enabled:
                self._add_to_cache(cache_key, response)
            
            # 統計更新
            self.stats["successful_requests"] += 1
            self.stats["total_tokens"] += response.usage.get("total_tokens", 0)
            self.stats["total_cost"] += self._calculate_cost(response)
            
            return response
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"レスポンス生成エラー: {e}")
            raise
    
    async def generate_stream_response(self,
        messages: List[LLMMessage],
        config: LLMConfig = None) -> AsyncGenerator[str, None]:
        """
        ストリーミングレスポンスを生成
        
        Args:
            messages: メッセージリスト
            config: LLM設定
            
        Yields:
            レスポンスチャンク
        """
        try:
            # 設定の準備
            if config is None:
                config = self.default_configs[LLMProvider.OPENAI]
            
            # プロバイダー取得
            provider = self.providers.get(config.provider)
            if not provider:
                raise ValueError(f"サポートされていないプロバイダー: {config.provider}")
            
            # 設定検証
            if not provider.validate_config(config):
                raise ValueError("無効な設定")
            
            # ストリーミングレスポンス生成
            async for chunk in provider.generate_stream_response(messages, config):
                yield chunk
                
        except Exception as e:
            self.logger.error(f"ストリーミングレスポンス生成エラー: {e}")
            raise
    
    async def _generate_with_retry(self, 
                                 provider: LLMProviderInterface, 
                                 messages: List[LLMMessage], 
                                 config: LLMConfig) -> LLMResponse:
        """リトライ機能付きでレスポンスを生成"""
        last_exception = None
        
        for attempt in range(config.retry_attempts):
            try:
                return await provider.generate_response(messages, config)
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"API呼び出し失敗 (試行 {attempt + 1}/{config.retry_attempts}): {e}")
                
                if attempt < config.retry_attempts - 1:
                    await asyncio.sleep(config.retry_delay * (2 ** attempt))  # 指数バックオフ
        
        raise last_exception
    
    def _generate_cache_key(self, messages: List[LLMMessage], config: LLMConfig) -> str:
        """キャッシュキーを生成"""
        content = json.dumps([msg.to_dict() for msg in messages], sort_keys=True)
        config_content = json.dumps({
            "provider": config.provider.value,
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }, sort_keys=True)
        
        combined = content + config_content
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _add_to_cache(self, key: str, response: LLMResponse):
        """レスポンスをキャッシュに追加"""
        if len(self.response_cache) >= self.cache_max_size:
            # 最も古いエントリを削除
            oldest_key = next(iter(self.response_cache))
            del self.response_cache[oldest_key]
        
        self.response_cache[key] = response
    
    def _calculate_cost(self, response: LLMResponse) -> float:
        """レスポンスのコストを計算"""
        # 簡易的なコスト計算（実際の料金は各プロバイダーの料金体系に基づく）
        cost_per_1k_tokens = {
            LLMProvider.OPENAI: 0.002,  # GPT-3.5-turbo概算
            LLMProvider.ANTHROPIC: 0.008,  # Claude概算
            LLMProvider.LOCAL: 0.0  # ローカルは無料
        }
        
        rate = cost_per_1k_tokens.get(response.provider, 0.0)
        total_tokens = response.usage.get("total_tokens", 0)
        
        return (total_tokens / 1000) * rate
    
    def create_message(self, role: MessageRole, content: str, **metadata) -> LLMMessage:
        """LLMメッセージを作成"""
        return LLMMessage(role=role, content=content, metadata=metadata)
    
    def create_config(self, 
                     provider: LLMProvider,
                     model: str = None,
                     **kwargs) -> LLMConfig:
        """LLM設定を作成"""
        base_config = self.default_configs.get(provider)
        if base_config:
            config_dict = {
                "provider": provider,
                "model": model or base_config.model,
                "api_key": kwargs.get("api_key", base_config.api_key),
                "api_base": kwargs.get("api_base", base_config.api_base),
                "max_tokens": kwargs.get("max_tokens", base_config.max_tokens),
                "temperature": kwargs.get("temperature", base_config.temperature),
                "top_p": kwargs.get("top_p", base_config.top_p),
                "frequency_penalty": kwargs.get("frequency_penalty", base_config.frequency_penalty),
                "presence_penalty": kwargs.get("presence_penalty", base_config.presence_penalty),
                "timeout": kwargs.get("timeout", base_config.timeout),
                "retry_attempts": kwargs.get("retry_attempts", base_config.retry_attempts),
                "retry_delay": kwargs.get("retry_delay", base_config.retry_delay),
                "additional_params": kwargs.get("additional_params", base_config.additional_params)
            }
        else:
            config_dict = {
                "provider": provider,
                "model": model or "default",
                **kwargs
            }
        
        return LLMConfig(**config_dict)
    
    def set_api_key(self, provider: LLMProvider, api_key: str):
        """APIキーを設定"""
        if provider in self.default_configs:
            self.default_configs[provider].api_key = api_key
    
    def get_available_models(self, provider: LLMProvider) -> List[str]:
        """利用可能なモデル一覧を取得"""
        model_lists = {
            LLMProvider.OPENAI: [
                "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", 
                "gpt-3.5-turbo-16k", "gpt-4-32k"
            ],
            LLMProvider.ANTHROPIC: [
                "claude-3-opus-20240229", "claude-3-sonnet-20240229", 
                "claude-3-haiku-20240307", "claude-2.1", "claude-2.0"
            ],
            LLMProvider.LOCAL: [
                "llama2", "llama2:13b", "llama2:70b",
                "codellama", "mistral", "neural-chat"
            ]
        }
        
        return model_lists.get(provider, [])
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self.response_cache.clear()
        self.logger.info("レスポンスキャッシュをクリアしました")
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            **self.stats,
            "cache_size": len(self.response_cache),
            "cache_hit_rate": (self.stats["cache_hits"] / max(self.stats["total_requests"], 1)) * 100,
            "success_rate": (self.stats["successful_requests"] / max(self.stats["total_requests"], 1)) * 100,
            "average_cost_per_request": self.stats["total_cost"] / max(self.stats["successful_requests"], 1)
        }
    
    def export_conversation(self, 
                          messages: List[LLMMessage], 
                          responses: List[LLMResponse],
                          export_path: str) -> bool:
        """会話をエクスポート"""
        try:
            export_data = {
                "messages": [msg.to_dict() for msg in messages],
                "responses": [resp.to_dict() for resp in responses],
                "exported_at": datetime.now().isoformat(),
                "statistics": self.get_statistics()
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"会話をエクスポートしました: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"会話エクスポートエラー: {e}")
            return False


# 使用例とテスト関数
async def example_usage():
    """LLMInterfaceの使用例"""
    
    # LLMInterfaceの初期化
    llm = LLMInterface()
    
    # APIキーの設定（実際の使用時は環境変数等から取得）
    # llm.set_api_key(LLMProvider.OPENAI, "your-openai-api-key")
    # llm.set_api_key(LLMProvider.ANTHROPIC, "your-anthropic-api-key")
    
    # メッセージの作成
    print("=== メッセージ作成 ===")
    messages = [
        llm.create_message(MessageRole.SYSTEM, "あなたはPythonプログラミングの専門家です。"),
        llm.create_message(MessageRole.USER, "フィボナッチ数列を計算するPython関数を作ってください。")
    ]
    
    for msg in messages:
        print(f"{msg.role.value}: {msg.content}")
    
    # 設定の作成
    print("\n=== 設定作成 ===")
    openai_config = llm.create_config(
        provider=LLMProvider.OPENAI,
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=1000
    )
    print(f"OpenAI設定: {openai_config.model}, temp={openai_config.temperature}")
    
    # ローカルLLM設定
    local_config = llm.create_config(
        provider=LLMProvider.LOCAL,
        model="llama2",
        api_base="http://localhost:11434",
        temperature=0.5,
        max_tokens=1500
    )
    print(f"ローカル設定: {local_config.model}, base={local_config.api_base}")
    
    # 利用可能なモデル一覧
    print("\n=== 利用可能なモデル ===")
    for provider in [LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.LOCAL]:
        models = llm.get_available_models(provider)
        print(f"{provider.value}: {', '.join(models[:3])}...")
    
    # レスポンス生成のシミュレーション（実際のAPI呼び出しなし）
    print("\n=== レスポンス生成シミュレーション ===")
    
    # モックレスポンスの作成
    mock_response = LLMResponse(
        content="""フィボナッチ数列を計算するPython関数をいくつかの方法で実装できます：

    ```python
    def fibonacci_recursive(n):
        \"\"\"再帰版フィボナッチ\"\"\"
        if n <= 1:
            return n
        return fibonacci_recursive(n-1) + fibonacci_recursive(n-2)

    def fibonacci_iterative(n):
        \"\"\"反復版フィボナッチ\"\"\"
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    def fibonacci_memoized(n, memo={}):
        \"\"\"メモ化版フィボナッチ\"\"\"
        if n in memo:
            return memo[n]
        if n <= 1:
            return n
        memo[n] = fibonacci_memoized(n-1, memo) + fibonacci_memoized(n-2, memo)
        return memo[n]
    再帰版は理解しやすいですが効率が悪く、反復版は効率的、メモ化版は再帰の利点を保ちつつ効率も良いです。""",
    provider=LLMProvider.OPENAI,
    model="gpt-3.5-turbo",
    usage={
    "prompt_tokens": 50,
    "completion_tokens": 200,
    "total_tokens": 250
    },
    response_time=1.5,
    finish_reason="stop"
    )
    print(f"レスポンス内容: {mock_response.content[:100]}...")
    print(f"使用トークン: {mock_response.usage}")
    print(f"応答時間: {mock_response.response_time}秒")

    # 統計情報の更新（シミュレーション）
    llm.stats["total_requests"] += 1
    llm.stats["successful_requests"] += 1
    llm.stats["total_tokens"] += mock_response.usage["total_tokens"]
    llm.stats["total_cost"] += llm._calculate_cost(mock_response)

    # キャッシュのテスト
    print("\n=== キャッシュテスト ===")
    cache_key = llm._generate_cache_key(messages, openai_config)
    print(f"キャッシュキー: {cache_key[:16]}...")

    llm._add_to_cache(cache_key, mock_response)
    print(f"キャッシュサイズ: {len(llm.response_cache)}")

    # 統計情報の表示
    print("\n=== 統計情報 ===")
    stats = llm.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")

    # 会話エクスポートのシミュレーション
    print("\n=== エクスポートテスト ===")
    export_success = llm.export_conversation(
        messages=[messages[1]],  # ユーザーメッセージのみ
        responses=[mock_response],
        export_path="conversation_export.json"
    )
    print(f"エクスポート成功: {export_success}")

    # 実際のAPI呼び出し例（コメントアウト）
    """
    try:
        print("\n=== 実際のAPI呼び出し（要APIキー） ===")
        response = await llm.generate_response(messages, openai_config)
        print(f"実際のレスポンス: {response.content[:100]}...")
        
        # ストリーミングレスポンス例
        print("\n=== ストリーミングレスポンス ===")
        async for chunk in llm.generate_stream_response(messages, openai_config):
            print(chunk, end="", flush=True)
        print("\n")
        
    except Exception as e:
        print(f"API呼び出しエラー（APIキーが設定されていない可能性）: {e}")
    """
class LLMResponseProcessor:
    """LLMレスポンス後処理クラス"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_code_blocks(self, response: LLMResponse) -> List[Dict[str, str]]:
        """レスポンスからコードブロックを抽出"""
        import re
        
        code_blocks = []
        content = response.content
        
        # ```で囲まれたコードブロックを抽出
        pattern = r'```(\w+)?\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for i, (language, code) in enumerate(matches):
            code_blocks.append({
                'id': f"code_block_{i}",
                'language': language or 'text',
                'code': code.strip(),
                'line_count': len(code.strip().split('\n'))
            })
        
        return code_blocks

    def extract_functions(self, response: LLMResponse) -> List[Dict[str, str]]:
        """レスポンスから関数定義を抽出"""
        import re
        
        functions = []
        code_blocks = self.extract_code_blocks(response)
        
        for block in code_blocks:
            if block['language'] in ['python', 'py']:
                # Python関数を抽出
                func_pattern = r'def\s+(\w+)\s*\([^)]*\):\s*\n((?:\s{4}.*\n?)*)'
                matches = re.findall(func_pattern, block['code'])
                
                for func_name, func_body in matches:
                    functions.append({
                        'name': func_name,
                        'language': 'python',
                        'code': f"def {func_name}({func_body}",
                        'docstring': self._extract_docstring(func_body)
                    })
        
        return functions

    def _extract_docstring(self, func_body: str) -> str:
        """関数本体からdocstringを抽出"""
        import re
        
        docstring_pattern = r'^\s*"""(.*?)"""'
        match = re.search(docstring_pattern, func_body, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        return ""

    def format_for_display(self, response: LLMResponse, include_metadata: bool = False) -> str:
        """表示用にレスポンスをフォーマット"""
        formatted_parts = []
        
        # ヘッダー情報
        formatted_parts.append(f"=== {response.provider.value.upper()} Response ===")
        formatted_parts.append(f"Model: {response.model}")
        formatted_parts.append(f"Tokens: {response.usage.get('total_tokens', 'N/A')}")
        formatted_parts.append(f"Time: {response.response_time:.2f}s")
        formatted_parts.append("")
        
        # メイン内容
        formatted_parts.append("--- Content ---")
        formatted_parts.append(response.content)
        
        # メタデータ
        if include_metadata and response.metadata:
            formatted_parts.append("")
            formatted_parts.append("--- Metadata ---")
            for key, value in response.metadata.items():
                formatted_parts.append(f"{key}: {value}")
        
        return "\n".join(formatted_parts)

    def validate_response(self, response: LLMResponse) -> Dict[str, Any]:
        """レスポンスを検証"""
        validation_result = {
            'is_valid': True,
            'issues': [],
            'quality_score': 0.0,
            'metrics': {}
        }
        
        # 基本検証
        if not response.content or not response.content.strip():
            validation_result['is_valid'] = False
            validation_result['issues'].append("Empty response content")
        
        # 内容の品質評価
        content = response.content
        
        # 長さチェック
        content_length = len(content)
        validation_result['metrics']['content_length'] = content_length
        
        if content_length < 10:
            validation_result['issues'].append("Response too short")
        elif content_length > 10000:
            validation_result['issues'].append("Response very long")
        
        # コードブロックの存在チェック
        code_blocks = self.extract_code_blocks(response)
        validation_result['metrics']['code_blocks_count'] = len(code_blocks)
        
        # 品質スコア計算
        score = 1.0
        
        # 長さによる減点
        if content_length < 50:
            score -= 0.3
        elif content_length > 5000:
            score -= 0.1
        
        # 問題による減点
        score -= len(validation_result['issues']) * 0.2
        
        # コードブロックによる加点
        if code_blocks:
            score += 0.1
        
        validation_result['quality_score'] = max(0.0, min(1.0, score))
        
        return validation_result

class LLMConversationManager:
    """LLM会話管理クラス"""
    def __init__(self, llm_interface: LLMInterface):
        self.llm = llm_interface
        self.logger = logging.getLogger(__name__)
        self.processor = LLMResponseProcessor()
        
        # 会話履歴
        self.conversations = {}
        self.current_conversation_id = None

    def start_conversation(self, 
                        conversation_id: str = None,
                        system_message: str = None) -> str:
        """新しい会話を開始"""
        if conversation_id is None:
            conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        conversation = {
            'id': conversation_id,
            'messages': [],
            'responses': [],
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'metadata': {}
        }
        
        # システムメッセージを追加
        if system_message:
            conversation['messages'].append(
                self.llm.create_message(MessageRole.SYSTEM, system_message)
            )
        
        self.conversations[conversation_id] = conversation
        self.current_conversation_id = conversation_id
        
        self.logger.info(f"新しい会話を開始: {conversation_id}")
        return conversation_id

    async def send_message(self, 
                        content: str,
                        conversation_id: str = None,
                        config: LLMConfig = None,
                        stream: bool = False) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """メッセージを送信"""
        if conversation_id is None:
            conversation_id = self.current_conversation_id
        
        if conversation_id not in self.conversations:
            raise ValueError(f"会話が見つかりません: {conversation_id}")
        
        conversation = self.conversations[conversation_id]
        
        # ユーザーメッセージを追加
        user_message = self.llm.create_message(MessageRole.USER, content)
        conversation['messages'].append(user_message)
        
        # レスポンスを生成
        if stream:
            return self.llm.generate_stream_response(conversation['messages'], config)
        else:
            response = await self.llm.generate_response(conversation['messages'], config)
            
            # アシスタントメッセージを追加
            assistant_message = self.llm.create_message(MessageRole.ASSISTANT, response.content)
            conversation['messages'].append(assistant_message)
            conversation['responses'].append(response)
            conversation['updated_at'] = datetime.now()
            
            return response

    def get_conversation_history(self, conversation_id: str = None) -> List[LLMMessage]:
        """会話履歴を取得"""
        if conversation_id is None:
            conversation_id = self.current_conversation_id
        
        if conversation_id not in self.conversations:
            return []
        
        return self.conversations[conversation_id]['messages']

    def get_conversation_summary(self, conversation_id: str = None) -> Dict[str, Any]:
        """会話サマリーを取得"""
        if conversation_id is None:
            conversation_id = self.current_conversation_id
        
        if conversation_id not in self.conversations:
            return {}
        
        conversation = self.conversations[conversation_id]
        messages = conversation['messages']
        responses = conversation['responses']
        
        # 統計計算
        user_messages = [msg for msg in messages if msg.role == MessageRole.USER]
        assistant_messages = [msg for msg in messages if msg.role == MessageRole.ASSISTANT]
        
        total_tokens = sum(resp.usage.get('total_tokens', 0) for resp in responses)
        total_cost = sum(self.llm._calculate_cost(resp) for resp in responses)
        
        return {
            'conversation_id': conversation_id,
            'created_at': conversation['created_at'].isoformat(),
            'updated_at': conversation['updated_at'].isoformat(),
            'total_messages': len(messages),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'total_tokens': total_tokens,
            'total_cost': total_cost,
            'average_response_time': sum(resp.response_time for resp in responses) / len(responses) if responses else 0
        }


if name == "main":
    asyncio.run(example_usage())

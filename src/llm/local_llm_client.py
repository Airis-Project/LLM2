# src/llm/local_llm_client.py
"""
ローカルLLMクライアントモジュール
Ollama、llama.cpp等のローカル実行LLMとの統合
"""

import requests
import json
import aiohttp
import asyncio
from typing import Iterator, Dict, Any, Optional, List, AsyncIterator
from .base_llm import BaseLLM, LLMConfig, LLMRole
from ..core.logger import get_logger

class LocalLLMClient(BaseLLM):
    """ローカルLLMクライアント（Ollama対応）"""
    
    def __init__(self, config: LLMConfig):
        """
        初期化
        
        Args:
            config: LLM設定
        """
        super().__init__(config)
        self.logger = get_logger(self.__class__.__name__)
        
        # 設定から値を取得
        self.model_name = config.model
        self.backend = getattr(config, 'backend', 'ollama')
        self.base_url = getattr(config, 'base_url', 'http://localhost:11434')
        
        # APIエンドポイントの設定
        if self.backend == 'ollama':
            self.api_url = f"{self.base_url}/api"
            self.generate_endpoint = f"{self.api_url}/generate"
            self.chat_endpoint = f"{self.api_url}/chat"
            self.models_endpoint = f"{self.api_url}/tags"
        else:
            # 他のバックエンド（llama.cpp等）の場合
            self.api_url = self.base_url
            self.generate_endpoint = f"{self.api_url}/completion"
            self.chat_endpoint = f"{self.api_url}/v1/chat/completions"
            self.models_endpoint = f"{self.api_url}/v1/models"
        
        self.logger.info(f"ローカルLLMクライアントを初期化: {self.backend} @ {self.base_url}")
    
    def generate(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        テキスト生成（同期版）
        
        Args:
            messages: メッセージリスト
            **kwargs: 追加パラメータ
            
        Returns:
            生成されたテキスト
        """
        try:
            if self.backend == 'ollama':
                return self._generate_ollama(messages, **kwargs)
            else:
                return self._generate_llamacpp(messages, **kwargs)
        except Exception as e:
            self.logger.error(f"テキスト生成エラー: {e}")
            raise
    
    def _generate_ollama(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Ollama用のテキスト生成"""
        # 最後のメッセージをプロンプトとして使用
        prompt = messages[-1].get('content', '') if messages else ''
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "top_p": kwargs.get('top_p', getattr(self.config, 'top_p', 0.9)),
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        response = requests.post(
            self.generate_endpoint,
            json=payload,
            timeout=kwargs.get('timeout', 60)
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', '')
    
    def _generate_llamacpp(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """llama.cpp用のテキスト生成"""
        prompt = messages[-1].get('content', '') if messages else ''
        
        payload = {
            "prompt": prompt,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "stop": kwargs.get('stop', [])
        }
        
        response = requests.post(
            self.generate_endpoint,
            json=payload,
            timeout=kwargs.get('timeout', 60)
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('content', '')
    
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
    
    async def _generate_ollama_async(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Ollama用の非同期テキスト生成"""
        prompt = messages[-1].get('content', '') if messages else ''
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "top_p": kwargs.get('top_p', getattr(self.config, 'top_p', 0.9)),
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=kwargs.get('timeout', 60))
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.generate_endpoint, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                return result.get('response', '')
    
    async def _generate_llamacpp_async(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """llama.cpp用の非同期テキスト生成"""
        prompt = messages[-1].get('content', '') if messages else ''
        
        payload = {
            "prompt": prompt,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "stop": kwargs.get('stop', [])
        }
        
        timeout = aiohttp.ClientTimeout(total=kwargs.get('timeout', 60))
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.generate_endpoint, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                return result.get('content', '')
    
    def generate_stream(self, messages: List[Dict[str, Any]], **kwargs) -> Iterator[str]:
        """
        ストリーミングテキスト生成（同期版）
        
        Args:
            messages: メッセージリスト
            **kwargs: 追加パラメータ
            
        Yields:
            生成されたテキストの断片
        """
        try:
            if self.backend == 'ollama':
                yield from self._generate_stream_ollama(messages, **kwargs)
            else:
                yield from self._generate_stream_llamacpp(messages, **kwargs)
        except Exception as e:
            self.logger.error(f"ストリーミング生成エラー: {e}")
            raise
    
    def _generate_stream_ollama(self, messages: List[Dict[str, Any]], **kwargs) -> Iterator[str]:
        """Ollama用のストリーミング生成"""
        prompt = messages[-1].get('content', '') if messages else ''
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "top_p": kwargs.get('top_p', getattr(self.config, 'top_p', 0.9)),
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        response = requests.post(
            self.generate_endpoint,
            json=payload,
            stream=True,
            timeout=kwargs.get('timeout', 60)
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    if 'response' in data:
                        yield data['response']
                    if data.get('done', False):
                        break
                except json.JSONDecodeError:
                    continue
    
    def _generate_stream_llamacpp(self, messages: List[Dict[str, Any]], **kwargs) -> Iterator[str]:
        """llama.cpp用のストリーミング生成"""
        prompt = messages[-1].get('content', '') if messages else ''
        
        payload = {
            "prompt": prompt,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "stream": True,
            "stop": kwargs.get('stop', [])
        }
        
        response = requests.post(
            self.generate_endpoint,
            json=payload,
            stream=True,
            timeout=kwargs.get('timeout', 60)
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if 'content' in data:
                            yield data['content']
                    except json.JSONDecodeError:
                        continue
    
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
    
    async def _generate_stream_ollama_async(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[str]:
        """Ollama用の非同期ストリーミング生成"""
        prompt = messages[-1].get('content', '') if messages else ''
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "top_p": kwargs.get('top_p', getattr(self.config, 'top_p', 0.9)),
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=kwargs.get('timeout', 60))
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.generate_endpoint, json=payload) as response:
                response.raise_for_status()
                async for line in response.content:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if 'response' in data:
                            yield data['response']
                        if data.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
    
    async def _generate_stream_llamacpp_async(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[str]:
        """llama.cpp用の非同期ストリーミング生成"""
        prompt = messages[-1].get('content', '') if messages else ''
        
        payload = {
            "prompt": prompt,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "stream": True,
            "stop": kwargs.get('stop', [])
        }
        
        timeout = aiohttp.ClientTimeout(total=kwargs.get('timeout', 60))
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.generate_endpoint, json=payload) as response:
                response.raise_for_status()
                async for line in response.content:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            if 'content' in data:
                                yield data['content']
                        except json.JSONDecodeError:
                            continue
    
    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        チャット形式での対話
        
        Args:
            messages: メッセージ履歴
            **kwargs: 追加パラメータ
            
        Returns:
            応答テキスト
        """
        try:
            if self.backend == 'ollama':
                return self._chat_ollama(messages, **kwargs)
            else:
                return self._chat_llamacpp(messages, **kwargs)
        except Exception as e:
            self.logger.error(f"チャットエラー: {e}")
            raise
    
    def _chat_ollama(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Ollama用のチャット"""
        # Ollamaのチャット形式に変換
        ollama_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            ollama_messages.append({"role": role, "content": content})
        
        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "top_p": kwargs.get('top_p', getattr(self.config, 'top_p', 0.9)),
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        response = requests.post(
            self.chat_endpoint,
            json=payload,
            timeout=kwargs.get('timeout', 60)
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('message', {}).get('content', '')
    
    def _chat_llamacpp(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """llama.cpp用のチャット"""
        payload = {
            "messages": messages,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "stop": kwargs.get('stop', [])
        }
        
        response = requests.post(
            self.chat_endpoint,
            json=payload,
            timeout=kwargs.get('timeout', 60)
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', '')
    
    def get_available_models(self) -> List[str]:
        """
        利用可能なモデル一覧を取得
        
        Returns:
            モデル名のリスト
        """
        try:
            response = requests.get(self.models_endpoint, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if self.backend == 'ollama':
                # Ollamaの場合
                models = result.get('models', [])
                return [model.get('name', '') for model in models if model.get('name')]
            else:
                # llama.cppの場合
                data = result.get('data', [])
                return [model.get('id', '') for model in data if model.get('id')]
                
        except Exception as e:
            self.logger.error(f"モデル一覧取得エラー: {e}")
            return []
    
    def validate_connection(self) -> bool:
        """
        接続確認
        
        Returns:
            接続可能かどうか
        """
        try:
            response = requests.get(self.models_endpoint, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"接続確認エラー: {e}")
            return False

# src/llm/local_llm_client.py
"""
ローカルLLMクライアントモジュール
Ollama、llama.cpp、Transformersなどのローカルモデルとの通信を管理
"""

import asyncio
import json
import time
import subprocess
import requests
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
from pathlib import Path
import aiohttp
import psutil

from .base_llm import BaseLLM, LLMMessage, LLMResponse, LLMConfig, LLMStatus, LLMRole
from ..core.logger import get_logger
from ..core.config_manager import get_config
from ..utils.validation_utils import ValidationUtils
from ..utils.file_utils import FileUtils

logger = get_logger(__name__)

class LocalLLMClient(BaseLLM):
    """ローカルLLMクライアントクラス"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初期化
        
        Args:
            config: LLM設定
        """
        super().__init__(config)
        
        # デフォルト設定
        if not self.config.model:
            self.config.model = "llama2:7b"
        
        # ローカルLLMの設定を取得
        self.local_config = self._get_local_config()
        
        # 利用可能なバックエンド
        self.available_backends = ['ollama', 'llama_cpp', 'transformers']
        self.backend = self.local_config.get('backend', 'ollama')
        
        # バックエンド固有の設定
        self.ollama_url = self.local_config.get('ollama_url', 'http://localhost:11434')
        self.llama_cpp_path = self.local_config.get('llama_cpp_path', '')
        self.model_path = self.local_config.get('model_path', '')
        
        # 利用可能なモデル一覧
        self.available_models = []
        
        # バリデーター
        self.validation_utils = ValidationUtils()
        self.file_utils = FileUtils()
        
        # セッション
        self.session = None
        
        self.logger.info(f"ローカルLLMクライアントを初期化しました (backend: {self.backend}, model: {self.config.model})")
    
    def _get_local_config(self) -> Dict[str, Any]:
        """ローカルLLM設定を取得"""
        try:
            config = get_config()
            return config.get('local_llm', {})
        except Exception as e:
            self.logger.error(f"ローカルLLM設定取得エラー: {e}")
            return {}
    
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
            
            # バックエンドに応じて処理
            if self.backend == 'ollama':
                response = await self._generate_with_ollama(messages, effective_config)
            elif self.backend == 'llama_cpp':
                response = await self._generate_with_llama_cpp(messages, effective_config)
            elif self.backend == 'transformers':
                response = await self._generate_with_transformers(messages, effective_config)
            else:
                raise ValueError(f"サポートされていないバックエンド: {self.backend}")
            
            # レスポンスを処理
            llm_response = self._process_response(response, start_time)
            
            # メトリクスを記録
            tokens = len(llm_response.content.split())  # 簡易的なトークン数
            self._record_request(True, tokens, llm_response.response_time)
            
            self._set_status(LLMStatus.IDLE)
            return llm_response
            
        except Exception as e:
            self.logger.error(f"ローカルLLM生成エラー: {e}")
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
            
            # バックエンドに応じてストリーミング処理
            total_tokens = 0
            if self.backend == 'ollama':
                async for chunk in self._stream_with_ollama(messages, effective_config):
                    if chunk:
                        yield chunk
                        total_tokens += 1
            elif self.backend == 'llama_cpp':
                async for chunk in self._stream_with_llama_cpp(messages, effective_config):
                    if chunk:
                        yield chunk
                        total_tokens += 1
            else:
                # ストリーミング非対応の場合は一括生成
                response = await self.generate_async(messages, effective_config)
                yield response.content
                total_tokens = len(response.content.split())
            
            # メトリクスを記録
            self._record_request(True, total_tokens, time.time() - start_time)
            self._set_status(LLMStatus.IDLE)
            
        except Exception as e:
            self.logger.error(f"ローカルLLMストリーミング生成エラー: {e}")
            self._record_request(False, 0, time.time() - start_time)
            self._set_status(LLMStatus.ERROR)
            raise
    
    async def _generate_with_ollama(self, messages: List[LLMMessage], config: LLMConfig) -> Dict[str, Any]:
        """Ollamaを使用して生成"""
        try:
            # Ollamaのサービス状態をチェック
            if not await self._check_ollama_service():
                raise RuntimeError("Ollamaサービスが利用できません")
            
            # プロンプトを構築
            prompt = self._build_prompt_for_ollama(messages)
            
            # リクエストデータを構築
            request_data = {
                'model': config.model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': config.temperature,
                    'top_p': config.top_p,
                    'num_predict': config.max_tokens
                }
            }
            
            # Ollama APIを呼び出し
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Ollama APIエラー: {response.status}")
                    
                    result = await response.json()
                    return result
                    
        except Exception as e:
            self.logger.error(f"Ollama生成エラー: {e}")
            raise
    
    async def _stream_with_ollama(self, messages: List[LLMMessage], config: LLMConfig) -> AsyncGenerator[str, None]:
        """Ollamaを使用してストリーミング生成"""
        try:
            # Ollamaのサービス状態をチェック
            if not await self._check_ollama_service():
                raise RuntimeError("Ollamaサービスが利用できません")
            
            # プロンプトを構築
            prompt = self._build_prompt_for_ollama(messages)
            
            # リクエストデータを構築
            request_data = {
                'model': config.model,
                'prompt': prompt,
                'stream': True,
                'options': {
                    'temperature': config.temperature,
                    'top_p': config.top_p,
                    'num_predict': config.max_tokens
                }
            }
            
            # Ollama APIをストリーミング呼び出し
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Ollama APIエラー: {response.status}")
                    
                    async for line in response.content:
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8'))
                                if 'response' in data:
                                    yield data['response']
                            except json.JSONDecodeError:
                                continue
                            
        except Exception as e:
            self.logger.error(f"Ollamaストリーミング生成エラー: {e}")
            raise
    
    async def _generate_with_llama_cpp(self, messages: List[LLMMessage], config: LLMConfig) -> Dict[str, Any]:
        """llama.cppを使用して生成"""
        try:
            if not self.llama_cpp_path or not Path(self.llama_cpp_path).exists():
                raise RuntimeError("llama.cppのパスが設定されていないか、ファイルが存在しません")
            
            if not self.model_path or not Path(self.model_path).exists():
                raise RuntimeError("モデルファイルのパスが設定されていないか、ファイルが存在しません")
            
            # プロンプトを構築
            prompt = self._build_prompt_for_llama_cpp(messages)
            
            # llama.cppのコマンドを構築
            cmd = [
                self.llama_cpp_path,
                '-m', self.model_path,
                '-p', prompt,
                '-n', str(config.max_tokens),
                '--temp', str(config.temperature),
                '--top-p', str(config.top_p),
                '--no-display-prompt'
            ]
            
            # 非同期でプロセスを実行
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"llama.cpp実行エラー: {stderr.decode()}")
            
            response_text = stdout.decode().strip()
            
            return {
                'response': response_text,
                'model': config.model,
                'done': True
            }
            
        except Exception as e:
            self.logger.error(f"llama.cpp生成エラー: {e}")
            raise
    
    async def _stream_with_llama_cpp(self, messages: List[LLMMessage], config: LLMConfig) -> AsyncGenerator[str, None]:
        """llama.cppを使用してストリーミング生成"""
        try:
            if not self.llama_cpp_path or not Path(self.llama_cpp_path).exists():
                raise RuntimeError("llama.cppのパスが設定されていないか、ファイルが存在しません")
            
            if not self.model_path or not Path(self.model_path).exists():
                raise RuntimeError("モデルファイルのパスが設定されていないか、ファイルが存在しません")
            
            # プロンプトを構築
            prompt = self._build_prompt_for_llama_cpp(messages)
            
            # llama.cppのコマンドを構築
            cmd = [
                self.llama_cpp_path,
                '-m', self.model_path,
                '-p', prompt,
                '-n', str(config.max_tokens),
                '--temp', str(config.temperature),
                '--top-p', str(config.top_p),
                '--no-display-prompt'
            ]
            
            # 非同期でプロセスを実行
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # ストリーミング出力を処理
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                text = line.decode().strip()
                if text:
                    yield text
            
            await process.wait()
            
        except Exception as e:
            self.logger.error(f"llama.cppストリーミング生成エラー: {e}")
            raise
    
    async def _generate_with_transformers(self, messages: List[LLMMessage], config: LLMConfig) -> Dict[str, Any]:
        """Transformersを使用して生成"""
        try:
            # Transformersライブラリの動的インポート
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM
                import torch
            except ImportError:
                raise RuntimeError("transformersライブラリがインストールされていません")
            
            # モデルとトークナイザーを読み込み
            if not hasattr(self, '_transformers_model') or not hasattr(self, '_transformers_tokenizer'):
                self._load_transformers_model()
            
            # プロンプトを構築
            prompt = self._build_prompt_for_transformers(messages)
            
            # トークン化
            inputs = self._transformers_tokenizer.encode(prompt, return_tensors='pt')
            
            # 生成設定
            generation_config = {
                'max_new_tokens': config.max_tokens,
                'temperature': config.temperature,
                'top_p': config.top_p,
                'do_sample': True,
                'pad_token_id': self._transformers_tokenizer.eos_token_id
            }
            
            # 生成実行
            with torch.no_grad():
                outputs = self._transformers_model.generate(inputs, **generation_config)
            
            # デコード
            generated_text = self._transformers_tokenizer.decode(
                outputs[0][inputs.shape[1]:], 
                skip_special_tokens=True
            )
            
            return {
                'response': generated_text,
                'model': config.model,
                'done': True
            }
            
        except Exception as e:
            self.logger.error(f"Transformers生成エラー: {e}")
            raise
    
    def _load_transformers_model(self):
        """Transformersモデルを読み込み"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            model_name = self.config.model
            if not model_name or model_name.startswith('llama'):
                model_name = "microsoft/DialoGPT-medium"  # デフォルトモデル
            
            self.logger.info(f"Transformersモデルを読み込み中: {model_name}")
            
            self._transformers_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._transformers_model = AutoModelForCausalLM.from_pretrained(model_name)
            
            # パディングトークンを設定
            if self._transformers_tokenizer.pad_token is None:
                self._transformers_tokenizer.pad_token = self._transformers_tokenizer.eos_token
            
            self.logger.info("Transformersモデルの読み込みが完了しました")
            
        except Exception as e:
            self.logger.error(f"Transformersモデル読み込みエラー: {e}")
            raise
    
    def _build_prompt_for_ollama(self, messages: List[LLMMessage]) -> str:
        """Ollama用のプロンプトを構築"""
        prompt_parts = []
        
        for message in messages:
            if message.role == LLMRole.SYSTEM:
                prompt_parts.append(f"System: {message.content}")
            elif message.role == LLMRole.USER:
                prompt_parts.append(f"User: {message.content}")
            elif message.role == LLMRole.ASSISTANT:
                prompt_parts.append(f"Assistant: {message.content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
    
    def _build_prompt_for_llama_cpp(self, messages: List[LLMMessage]) -> str:
        """llama.cpp用のプロンプトを構築"""
        # Llama2形式のプロンプト
        system_message = ""
        conversation = []
        
        for message in messages:
            if message.role == LLMRole.SYSTEM:
                system_message = message.content
            else:
                conversation.append({
                    'role': message.role.value,
                    'content': message.content
                })
        
        # Llama2のプロンプト形式
        prompt = f"<s>[INST] <<SYS>>\n{system_message}\n<</SYS>>\n\n"
        
        for i, msg in enumerate(conversation):
            if msg['role'] == 'user':
                if i == len(conversation) - 1:
                    prompt += f"{msg['content']} [/INST]"
                else:
                    prompt += f"{msg['content']} [/INST] "
            elif msg['role'] == 'assistant':
                prompt += f"{msg['content']} </s><s>[INST] "
        
        return prompt
    
    def _build_prompt_for_transformers(self, messages: List[LLMMessage]) -> str:
        """Transformers用のプロンプトを構築"""
        prompt_parts = []
        
        for message in messages:
            role_prefix = {
                LLMRole.SYSTEM: "System",
                LLMRole.USER: "Human",
                LLMRole.ASSISTANT: "Assistant"
            }.get(message.role, "Unknown")
            
            prompt_parts.append(f"{role_prefix}: {message.content}")
        
        prompt_parts.append("Assistant:")
        return "\n".join(prompt_parts)
    
    async def _check_ollama_service(self) -> bool:
        """Ollamaサービスの状態をチェック"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ollama_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception:
            return False
    
    def _process_response(self, response: Dict[str, Any], start_time: float) -> LLMResponse:
        """レスポンスを処理"""
        try:
            content = response.get('response', '')
            
            # 使用量情報を構築（簡易版）
            usage = {
                'total_tokens': len(content.split()),
                'completion_tokens': len(content.split()),
                'prompt_tokens': 0
            }
            
            # レスポンスオブジェクトを作成
            llm_response = LLMResponse(
                content=content,
                model=response.get('model', self.config.model),
                usage=usage,
                finish_reason='stop' if response.get('done', False) else 'length',
                response_time=time.time() - start_time,
                metadata={
                    'backend': self.backend,
                    'local': True
                }
            )
            
            return llm_response
            
        except Exception as e:
            self.logger.error(f"レスポンス処理エラー: {e}")
            raise
    
    def is_available(self) -> bool:
        """
        ローカルLLMが利用可能かチェック
        
        Returns:
            bool: 利用可能フラグ
        """
        try:
            if self.backend == 'ollama':
                return asyncio.run(self._check_ollama_service())
            elif self.backend == 'llama_cpp':
                return (Path(self.llama_cpp_path).exists() if self.llama_cpp_path else False)
            elif self.backend == 'transformers':
                try:
                    import transformers
                    return True
                except ImportError:
                    return False
            
            return False
            
        except Exception as e:
            self.logger.warning(f"ローカルLLM利用可能性チェックエラー: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        モデル情報を取得
        
        Returns:
            Dict[str, Any]: モデル情報
        """
        return {
            'provider': 'Local',
            'backend': self.backend,
            'model': self.config.model,
            'available_models': self.available_models,
            'supports_streaming': self.backend in ['ollama', 'llama_cpp'],
            'supports_functions': False,
            'max_tokens': self.config.max_tokens,
            'context_window': self._get_model_context_window(),
            'local': True
        }
    
    async def get_available_models(self) -> List[str]:
        """
        利用可能なモデル一覧を取得
        
        Returns:
            List[str]: モデル名のリスト
        """
        try:
            if self.backend == 'ollama':
                return await self._get_ollama_models()
            elif self.backend == 'llama_cpp':
                return self._get_llama_cpp_models()
            elif self.backend == 'transformers':
                return self._get_transformers_models()
            
            return []
            
        except Exception as e:
            self.logger.error(f"モデル一覧取得エラー: {e}")
            return []
    
    async def _get_ollama_models(self) -> List[str]:
        """Ollamaの利用可能モデルを取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            self.logger.error(f"Ollamaモデル一覧取得エラー: {e}")
            return []
    
    def _get_llama_cpp_models(self) -> List[str]:
        """llama.cppの利用可能モデルを取得"""
        try:
            # モデルディレクトリからGGMLファイルを検索
            model_dir = Path(self.model_path).parent if self.model_path else Path.cwd()
            models = []
            
            for file_path in model_dir.glob("*.ggml"):
                models.append(file_path.name)
            
            for file_path in model_dir.glob("*.gguf"):
                models.append(file_path.name)
            
            return models
            
        except Exception as e:
            self.logger.error(f"llama.cppモデル一覧取得エラー: {e}")
            return []
    
    def _get_transformers_models(self) -> List[str]:
        """Transformersの推奨モデル一覧を取得"""
        return [
            "microsoft/DialoGPT-medium",
            "microsoft/DialoGPT-large",
            "gpt2",
            "gpt2-medium",
            "gpt2-large",
            "facebook/blenderbot-400M-distill",
            "facebook/blenderbot-1B-distill"
        ]
    
    def _get_model_context_window(self) -> int:
        """モデルのコンテキストウィンドウサイズを取得"""
        # モデル名からコンテキストサイズを推定
        model_name = self.config.model.lower()
        
        if '7b' in model_name:
            return 4096
        elif '13b' in model_name:
            return 4096
        elif '30b' in model_name or '33b' in model_name:
            return 2048
        elif '65b' in model_name or '70b' in model_name:
            return 2048
        else:
            return 2048  # デフォルト
    
    def estimate_tokens(self, text: str) -> int:
        """
        テキストのトークン数を概算
        
        Args:
            text: テキスト
            
        Returns:
            int: 概算トークン数
        """
        try:
            # 簡易的な概算
            # 英語: 約4文字で1トークン
            # 日本語: 約1文字で1トークン
            
            japanese_chars = sum(1 for char in text if ord(char) > 127)
            english_chars = len(text) - japanese_chars
            
            estimated_tokens = japanese_chars + (english_chars // 4)
            
            return max(estimated_tokens, 1)
            
        except Exception as e:
            self.logger.error(f"トークン数概算エラー: {e}")
            return len(text.split())  # フォールバック
    
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
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        システム情報を取得
        
        Returns:
            Dict[str, Any]: システム情報
        """
        try:
            system_info = {
                'backend': self.backend,
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available,
                'disk_usage': psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else 0
            }
            
            # GPU情報を追加（可能な場合）
            try:
                import torch
                if torch.cuda.is_available():
                    system_info.update({
                        'gpu_available': True,
                        'gpu_count': torch.cuda.device_count(),
                        'gpu_memory': torch.cuda.get_device_properties(0).total_memory if torch.cuda.device_count() > 0 else 0
                    })
                else:
                    system_info['gpu_available'] = False
            except ImportError:
                system_info['gpu_available'] = False
            
            return system_info
            
        except Exception as e:
            self.logger.error(f"システム情報取得エラー: {e}")
            return {}
    
    def set_backend(self, backend: str):
        """
        バックエンドを設定
        
        Args:
            backend: バックエンド名
        """
        if backend not in self.available_backends:
            raise ValueError(f"サポートされていないバックエンド: {backend}")
        
        self.backend = backend
        self.logger.info(f"バックエンドを変更しました: {backend}")
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            # Transformersモデルをクリーンアップ
            if hasattr(self, '_transformers_model'):
                del self._transformers_model
            
            if hasattr(self, '_transformers_tokenizer'):
                del self._transformers_tokenizer
            
            # セッションをクリーンアップ
            if self.session and not self.session.closed:
                asyncio.create_task(self.session.close())
            
            # GPUメモリをクリア（PyTorchが利用可能な場合）
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            
            self.logger.info("ローカルLLMクライアントをクリーンアップしました")
            
        except Exception as e:
            self.logger.error(f"ローカルLLMクライアントクリーンアップエラー: {e}")
    
    async def download_model(self, model_name: str, progress_callback=None) -> bool:
        """
        モデルをダウンロード
        
        Args:
            model_name: モデル名
            progress_callback: 進捗コールバック関数
            
        Returns:
            bool: ダウンロード成功フラグ
        """
        try:
            if self.backend == 'ollama':
                return await self._download_ollama_model(model_name, progress_callback)
            elif self.backend == 'transformers':
                return await self._download_transformers_model(model_name, progress_callback)
            else:
                self.logger.warning(f"バックエンド {self.backend} はモデルダウンロードをサポートしていません")
                return False
                
        except Exception as e:
            self.logger.error(f"モデルダウンロードエラー: {e}")
            return False
    
    async def _download_ollama_model(self, model_name: str, progress_callback=None) -> bool:
        """Ollamaモデルをダウンロード"""
        try:
            request_data = {'name': model_name}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/pull",
                    json=request_data
                ) as response:
                    if response.status != 200:
                        return False
                    
                    async for line in response.content:
                        if line and progress_callback:
                            try:
                                data = json.loads(line.decode('utf-8'))
                                if 'completed' in data and 'total' in data:
                                    progress = data['completed'] / data['total'] * 100
                                    progress_callback(progress)
                            except json.JSONDecodeError:
                                continue
                    
                    return True
                    
        except Exception as e:
            self.logger.error(f"Ollamaモデルダウンロードエラー: {e}")
            return False
    
    async def _download_transformers_model(self, model_name: str, progress_callback=None) -> bool:
        """Transformersモデルをダウンロード"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            
            if progress_callback:
                progress_callback(10)
            
            # トークナイザーをダウンロード
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            if progress_callback:
                progress_callback(50)
            
            # モデルをダウンロード
            model = AutoModelForCausalLM.from_pretrained(model_name)
            
            if progress_callback:
                progress_callback(100)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Transformersモデルダウンロードエラー: {e}")
            return False
    
    async def get_model_status(self, model_name: str) -> Dict[str, Any]:
        """
        モデルの状態を取得
        
        Args:
            model_name: モデル名
            
        Returns:
            Dict[str, Any]: モデル状態
        """
        try:
            if self.backend == 'ollama':
                return await self._get_ollama_model_status(model_name)
            elif self.backend == 'transformers':
                return self._get_transformers_model_status(model_name)
            else:
                return {'status': 'unknown', 'available': False}
                
        except Exception as e:
            self.logger.error(f"モデル状態取得エラー: {e}")
            return {'status': 'error', 'available': False}
    
    async def _get_ollama_model_status(self, model_name: str) -> Dict[str, Any]:
        """Ollamaモデルの状態を取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get('models', [])
                        
                        for model in models:
                            if model['name'] == model_name:
                                return {
                                    'status': 'ready',
                                    'available': True,
                                    'size': model.get('size', 0),
                                    'modified': model.get('modified_at', ''),
                                    'digest': model.get('digest', '')
                                }
                        
                        return {'status': 'not_found', 'available': False}
                    
                    return {'status': 'service_unavailable', 'available': False}
                    
        except Exception as e:
            self.logger.error(f"Ollamaモデル状態取得エラー: {e}")
            return {'status': 'error', 'available': False}
    
    def _get_transformers_model_status(self, model_name: str) -> Dict[str, Any]:
        """Transformersモデルの状態を取得"""
        try:
            from transformers import AutoTokenizer
            from huggingface_hub import model_info
            
            # HuggingFace Hubからモデル情報を取得
            info = model_info(model_name)
            
            return {
                'status': 'available',
                'available': True,
                'downloads': getattr(info, 'downloads', 0),
                'likes': getattr(info, 'likes', 0),
                'library_name': getattr(info, 'library_name', ''),
                'pipeline_tag': getattr(info, 'pipeline_tag', '')
            }
            
        except Exception as e:
            self.logger.error(f"Transformersモデル状態取得エラー: {e}")
            return {'status': 'error', 'available': False}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        パフォーマンスメトリクスを取得
        
        Returns:
            Dict[str, Any]: パフォーマンス情報
        """
        try:
            base_metrics = self.get_metrics()
            
            # ローカルLLM固有のメトリクス
            local_metrics = {
                'backend': self.backend,
                'model_loaded': hasattr(self, '_transformers_model'),
                'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024,  # MB
                'cpu_percent': psutil.Process().cpu_percent(),
                'system_memory_percent': psutil.virtual_memory().percent
            }
            
            # GPU使用率（利用可能な場合）
            try:
                import torch
                if torch.cuda.is_available():
                    local_metrics.update({
                        'gpu_memory_allocated': torch.cuda.memory_allocated() / 1024 / 1024,  # MB
                        'gpu_memory_cached': torch.cuda.memory_reserved() / 1024 / 1024,  # MB
                        'gpu_utilization': self._get_gpu_utilization()
                    })
            except ImportError:
                pass
            
            base_metrics.update(local_metrics)
            return base_metrics
            
        except Exception as e:
            self.logger.error(f"パフォーマンスメトリクス取得エラー: {e}")
            return self.get_metrics()
    
    def _get_gpu_utilization(self) -> float:
        """GPU使用率を取得"""
        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return float(result.stdout.strip().split('\n')[0])
            
            return 0.0
            
        except Exception:
            return 0.0
    
    async def optimize_model(self) -> bool:
        """
        モデルを最適化
        
        Returns:
            bool: 最適化成功フラグ
        """
        try:
            if self.backend == 'transformers' and hasattr(self, '_transformers_model'):
                # PyTorchモデルの最適化
                try:
                    import torch
                    
                    # モデルを評価モードに設定
                    self._transformers_model.eval()
                    
                    # 可能であればJITコンパイル
                    if hasattr(torch, 'jit'):
                        # サンプル入力でトレース
                        sample_input = torch.randint(0, 1000, (1, 10))
                        self._transformers_model = torch.jit.trace(
                            self._transformers_model, 
                            sample_input
                        )
                    
                    # GPU利用可能な場合はGPUに移動
                    if torch.cuda.is_available():
                        self._transformers_model = self._transformers_model.cuda()
                    
                    self.logger.info("モデルの最適化が完了しました")
                    return True
                    
                except Exception as e:
                    self.logger.warning(f"モデル最適化エラー: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"モデル最適化エラー: {e}")
            return False
    
    def set_model_path(self, model_path: str):
        """
        モデルパスを設定
        
        Args:
            model_path: モデルファイルのパス
        """
        if not Path(model_path).exists():
            raise FileNotFoundError(f"モデルファイルが見つかりません: {model_path}")
        
        self.model_path = model_path
        self.logger.info(f"モデルパスを設定しました: {model_path}")
    
    def set_llama_cpp_path(self, llama_cpp_path: str):
        """
        llama.cppの実行ファイルパスを設定
        
        Args:
            llama_cpp_path: llama.cpp実行ファイルのパス
        """
        if not Path(llama_cpp_path).exists():
            raise FileNotFoundError(f"llama.cpp実行ファイルが見つかりません: {llama_cpp_path}")
        
        self.llama_cpp_path = llama_cpp_path
        self.logger.info(f"llama.cppパスを設定しました: {llama_cpp_path}")
    
    def set_ollama_url(self, ollama_url: str):
        """
        Ollama APIのURLを設定
        
        Args:
            ollama_url: Ollama APIのURL
        """
        self.ollama_url = ollama_url
        self.logger.info(f"Ollama URLを設定しました: {ollama_url}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        ヘルスチェックを実行
        
        Returns:
            Dict[str, Any]: ヘルスチェック結果
        """
        try:
            health_status = {
                'backend': self.backend,
                'status': 'unknown',
                'details': {}
            }
            
            if self.backend == 'ollama':
                # Ollamaサービスの確認
                service_available = await self._check_ollama_service()
                health_status.update({
                    'status': 'healthy' if service_available else 'unhealthy',
                    'details': {
                        'service_available': service_available,
                        'url': self.ollama_url
                    }
                })
                
            elif self.backend == 'llama_cpp':
                # llama.cpp実行ファイルの確認
                executable_exists = Path(self.llama_cpp_path).exists() if self.llama_cpp_path else False
                model_exists = Path(self.model_path).exists() if self.model_path else False
                
                health_status.update({
                    'status': 'healthy' if (executable_exists and model_exists) else 'unhealthy',
                    'details': {
                        'executable_exists': executable_exists,
                        'model_exists': model_exists,
                        'executable_path': self.llama_cpp_path,
                        'model_path': self.model_path
                    }
                })
                
            elif self.backend == 'transformers':
                # Transformersライブラリの確認
                try:
                    import transformers
                    import torch
                    
                    health_status.update({
                        'status': 'healthy',
                        'details': {
                            'transformers_version': transformers.__version__,
                            'torch_version': torch.__version__,
                            'cuda_available': torch.cuda.is_available(),
                            'model_loaded': hasattr(self, '_transformers_model')
                        }
                    })
                    
                except ImportError as e:
                    health_status.update({
                        'status': 'unhealthy',
                        'details': {
                            'error': f"必要なライブラリが見つかりません: {e}"
                        }
                    })
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"ヘルスチェックエラー: {e}")
            return {
                'backend': self.backend,
                'status': 'error',
                'details': {'error': str(e)}
            }


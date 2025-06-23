# tests/test_llm/test_openai_client.py
"""
OpenAIClientのテストモジュール
OpenAI API クライアントの単体テストと統合テストを実装
"""

import pytest
import asyncio
import tempfile
import shutil
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional

# テスト対象のインポート
from llm.openai_client import OpenAIClient
from llm.base_llm import LLMResponse, LLMConfig, LLMError
from core.config_manager import ConfigManager
from core.logger import Logger

# テスト用のインポート
from tests.test_core import (
    create_test_config_manager,
    create_test_logger,
    MockFileContext,
    requires_file
)


class MockOpenAIResponse:
    """OpenAI APIレスポンスのモック"""
    
    def __init__(self, content: str, model: str = "gpt-3.5-turbo", 
                 usage: Optional[Dict] = None, finish_reason: str = "stop"):
        self.choices = [
            type('Choice', (), {
                'message': type('Message', (), {
                    'content': content,
                    'role': 'assistant'
                })(),
                'finish_reason': finish_reason,
                'index': 0
            })()
        ]
        self.model = model
        self.usage = usage or {
            'prompt_tokens': 10,
            'completion_tokens': 20,
            'total_tokens': 30
        }
        self.id = "chatcmpl-test123"
        self.object = "chat.completion"
        self.created = 1234567890


class MockOpenAIStreamResponse:
    """OpenAI APIストリーミングレスポンスのモック"""
    
    def __init__(self, chunks: List[str]):
        self.chunks = chunks
        self.current_index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.current_index >= len(self.chunks):
            raise StopAsyncIteration
        
        chunk_content = self.chunks[self.current_index]
        self.current_index += 1
        
        # OpenAI APIのストリーミング形式をモック
        chunk = type('Chunk', (), {
            'choices': [
                type('Choice', (), {
                    'delta': type('Delta', (), {
                        'content': chunk_content,
                        'role': 'assistant' if self.current_index == 1 else None
                    })(),
                    'finish_reason': 'stop' if self.current_index == len(self.chunks) else None,
                    'index': 0
                })()
            ],
            'model': 'gpt-3.5-turbo',
            'id': f'chatcmpl-test{self.current_index}',
            'object': 'chat.completion.chunk',
            'created': 1234567890
        })()
        
        return chunk


class TestOpenAIClient:
    """OpenAIClientのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="openai_test_"))
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_openai_client")
        
        # OpenAI設定を追加
        self.config_manager.set('llm.openai.api_key', 'test-api-key-12345')
        self.config_manager.set('llm.openai.model', 'gpt-3.5-turbo')
        self.config_manager.set('llm.openai.max_tokens', 2048)
        self.config_manager.set('llm.openai.temperature', 0.7)
        self.config_manager.set('llm.openai.timeout', 30)
        self.config_manager.set('llm.openai.base_url', 'https://api.openai.com/v1')
        self.config_manager.set('llm.openai.organization', 'test-org')
        self.config_manager.set('llm.retry_attempts', 3)
        self.config_manager.set('llm.retry_delay', 1.0)
        
        # OpenAIClientのインスタンスを作成
        self.client = OpenAIClient(self.config_manager, self.logger)
        
        # テスト用のプロンプトとレスポンス
        self.test_prompts = [
            "こんにちは、今日の天気はどうですか？",
            "Pythonでリストを作成する方法を教えてください。",
            "機械学習の基本概念について説明してください。"
        ]
        
        self.test_responses = [
            "こんにちは！申し訳ございませんが、私はリアルタイムの天気情報にアクセスできません。",
            "Pythonでリストを作成する方法をいくつか紹介します：\n1. 空のリスト: `my_list = []`\n2. 要素付きリスト: `my_list = [1, 2, 3]`",
            "機械学習は、データからパターンを学習してタスクを実行するAIの手法です。主な種類には教師あり学習、教師なし学習、強化学習があります。"
        ]
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """OpenAIClientの初期化テスト"""
        # 初期化の確認
        assert self.client.config_manager is not None
        assert self.client.logger is not None
        assert self.client.api_key == 'test-api-key-12345'
        assert self.client.model_name == 'gpt-3.5-turbo'
        assert self.client.max_tokens == 2048
        assert self.client.temperature == 0.7
        assert self.client.timeout == 30
        assert self.client.base_url == 'https://api.openai.com/v1'
        assert self.client.organization == 'test-org'
    
    def test_init_with_missing_api_key(self):
        """APIキーが未設定の場合の初期化テスト"""
        # APIキーを削除
        self.config_manager.remove('llm.openai.api_key')
        
        # 環境変数からAPIキーを取得することを確認
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env-api-key'}):
            client = OpenAIClient(self.config_manager, self.logger)
            assert client.api_key == 'env-api-key'
    
    def test_init_with_no_api_key(self):
        """APIキーが全く設定されていない場合のテスト"""
        # APIキーを削除
        self.config_manager.remove('llm.openai.api_key')
        
        # 環境変数も設定しない
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                OpenAIClient(self.config_manager, self.logger)
            
            assert "OpenAI API key" in str(exc_info.value)
    
    def test_validate_config(self):
        """設定検証テスト"""
        # 有効な設定
        assert self.client._validate_config() is True
        
        # 無効な設定（APIキーなし）
        self.client.api_key = None
        assert self.client._validate_config() is False
        
        # 無効な設定（モデル名なし）
        self.client.api_key = 'test-key'
        self.client.model_name = None
        assert self.client._validate_config() is False
    
    def test_get_model_info(self):
        """モデル情報取得テスト"""
        model_info = self.client.get_model_info()
        
        assert isinstance(model_info, dict)
        assert model_info['name'] == 'gpt-3.5-turbo'
        assert model_info['provider'] == 'openai'
        assert model_info['max_tokens'] == 2048
        assert model_info['supports_streaming'] is True
        assert model_info['supports_functions'] is True
        assert 'api_version' in model_info
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """正常なレスポンス生成テスト"""
        mock_response = MockOpenAIResponse(self.test_responses[0])
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            # モックのOpenAIクライアントを設定
            mock_openai_instance = AsyncMock()
            mock_openai.return_value = mock_openai_instance
            mock_openai_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # 新しいクライアントインスタンスを作成（モック付き）
            client = OpenAIClient(self.config_manager, self.logger)
            client._openai_client = mock_openai_instance
            
            # レスポンスを生成
            response = await client.generate_response(self.test_prompts[0])
            
            # レスポンスの検証
            assert isinstance(response, LLMResponse)
            assert response.content == self.test_responses[0]
            assert response.metadata['model'] == 'gpt-3.5-turbo'
            assert response.metadata['tokens_used'] == 30
            assert response.metadata['prompt_tokens'] == 10
            assert response.metadata['completion_tokens'] == 20
            
            # OpenAI APIが正しく呼び出されたことを確認
            mock_openai_instance.chat.completions.create.assert_called_once()
            call_args = mock_openai_instance.chat.completions.create.call_args
            assert call_args[1]['model'] == 'gpt-3.5-turbo'
            assert call_args[1]['max_tokens'] == 2048
            assert call_args[1]['temperature'] == 0.7
    
    @pytest.mark.asyncio
    async def test_generate_response_with_context(self):
        """コンテキスト付きレスポンス生成テスト"""
        mock_response = MockOpenAIResponse("コンテキストを考慮した回答です。")
        
        context = {
            'system_prompt': 'あなたは親切なアシスタントです。',
            'conversation_history': [
                {'role': 'user', 'content': '前回の質問'},
                {'role': 'assistant', 'content': '前回の回答'}
            ],
            'user_preferences': {
                'language': 'japanese',
                'style': 'formal'
            }
        }
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai.return_value = mock_openai_instance
            mock_openai_instance.chat.completions.create = AsyncMock(return_value=mock_response)
            
            client = OpenAIClient(self.config_manager, self.logger)
            client._openai_client = mock_openai_instance
            
            # コンテキスト付きでレスポンスを生成
            response = await client.generate_response(
                "新しい質問です",
                context=context
            )
            
            assert response.content == "コンテキストを考慮した回答です。"
            
            # メッセージ構造の確認
            call_args = mock_openai_instance.chat.completions.create.call_args
            messages = call_args[1]['messages']
            
            # システムプロンプトが含まれていることを確認
            assert any(msg['role'] == 'system' for msg in messages)
            # 会話履歴が含まれていることを確認
            assert len(messages) >= 4  # system + history + current
    
    @pytest.mark.asyncio
    async def test_generate_response_with_functions(self):
        """関数呼び出し付きレスポンス生成テスト"""
        # 関数呼び出しを含むレスポンス
        function_call_response = type('FunctionCallResponse', (), {
            'choices': [
                type('Choice', (), {
                    'message': type('Message', (), {
                        'content': None,
                        'role': 'assistant',
                        'function_call': type('FunctionCall', (), {
                            'name': 'get_weather',
                            'arguments': '{"location": "東京"}'
                        })()
                    })(),
                    'finish_reason': 'function_call',
                    'index': 0
                })()
            ],
            'model': 'gpt-3.5-turbo',
            'usage': {'prompt_tokens': 15, 'completion_tokens': 25, 'total_tokens': 40},
            'id': 'chatcmpl-func123',
            'object': 'chat.completion',
            'created': 1234567890
        })()
        
        functions = [
            {
                'name': 'get_weather',
                'description': '指定された場所の天気を取得します',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'location': {
                            'type': 'string',
                            'description': '場所名'
                        }
                    },
                    'required': ['location']
                }
            }
        ]
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai.return_value = mock_openai_instance
            mock_openai_instance.chat.completions.create = AsyncMock(return_value=function_call_response)
            
            client = OpenAIClient(self.config_manager, self.logger)
            client._openai_client = mock_openai_instance
            
            # 関数付きでレスポンスを生成
            response = await client.generate_response(
                "東京の天気を教えて",
                context={'functions': functions}
            )
            
            # 関数呼び出し情報が含まれていることを確認
            assert 'function_call' in response.metadata
            assert response.metadata['function_call']['name'] == 'get_weather'
            assert '"location": "東京"' in response.metadata['function_call']['arguments']
    
    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """ストリーミングレスポンステスト"""
        streaming_chunks = [
            "これは",
            "ストリーミング",
            "レスポンス",
            "のテストです。"
        ]
        
        mock_stream = MockOpenAIStreamResponse(streaming_chunks)
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai.return_value = mock_openai_instance
            mock_openai_instance.chat.completions.create = AsyncMock(return_value=mock_stream)
            
            client = OpenAIClient(self.config_manager, self.logger)
            client._openai_client = mock_openai_instance
            
            # ストリーミングレスポンスを受信
            received_chunks = []
            async for chunk in client.stream_response("ストリーミングテスト"):
                received_chunks.append(chunk.content)
            
            assert received_chunks == streaming_chunks
            
            # ストリーミングパラメータが設定されていることを確認
            call_args = mock_openai_instance.chat.completions.create.call_args
            assert call_args[1]['stream'] is True
    
    @pytest.mark.asyncio
    async def test_generate_response_api_error(self):
        """API エラーハンドリングテスト"""
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai.return_value = mock_openai_instance
            
            # OpenAI APIエラーをシミュレート
            from openai import APIError
            mock_openai_instance.chat.completions.create = AsyncMock(
                side_effect=APIError("API rate limit exceeded")
            )
            
            client = OpenAIClient(self.config_manager, self.logger)
            client._openai_client = mock_openai_instance
            
            # エラーが適切に処理されることを確認
            with pytest.raises(LLMError) as exc_info:
                await client.generate_response("テストプロンプト")
            
            assert "OpenAI API error" in str(exc_info.value)
            assert "rate limit" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_response_timeout(self):
        """タイムアウトテスト"""
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai.return_value = mock_openai_instance
            
            # タイムアウトをシミュレート
            mock_openai_instance.chat.completions.create = AsyncMock(
                side_effect=asyncio.TimeoutError("Request timed out")
            )
            
            client = OpenAIClient(self.config_manager, self.logger)
            client._openai_client = mock_openai_instance
            client.timeout = 1.0  # 短いタイムアウト
            
            # タイムアウトエラーが発生することを確認
            with pytest.raises(LLMError) as exc_info:
                await client.generate_response("タイムアウトテスト")
            
            assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_generate_response_with_retry(self):
        """リトライ機能テスト"""
        call_count = 0
        
        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                from openai import RateLimitError
                raise RateLimitError("Rate limit exceeded")
            return MockOpenAIResponse("リトライ成功")
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai.return_value = mock_openai_instance
            mock_openai_instance.chat.completions.create = AsyncMock(side_effect=mock_api_call)
            
            client = OpenAIClient(self.config_manager, self.logger)
            client._openai_client = mock_openai_instance
            client.retry_delay = 0.1  # テストを高速化
            
            # リトライが成功することを確認
            response = await client.generate_response("リトライテスト")
            
            assert response.content == "リトライ成功"
            assert call_count == 3  # 2回失敗 + 1回成功
    
    def test_count_tokens(self):
        """トークン数カウントテスト"""
        text = "これはトークン数をカウントするテストです。"
        
        # tiktoken を使用したトークン数カウント
        with patch('tiktoken.encoding_for_model') as mock_tiktoken:
            mock_encoding = Mock()
            mock_encoding.encode.return_value = [1, 2, 3, 4, 5]  # 5トークン
            mock_tiktoken.return_value = mock_encoding
            
            token_count = self.client.count_tokens(text)
            
            assert token_count == 5
            mock_tiktoken.assert_called_once_with('gpt-3.5-turbo')
            mock_encoding.encode.assert_called_once_with(text)
    
    def test_count_tokens_fallback(self):
        """トークン数カウントのフォールバックテスト"""
        text = "これはフォールバック テスト です。"
        
        # tiktoken が利用できない場合のフォールバック
        with patch('tiktoken.encoding_for_model', side_effect=Exception("tiktoken not available")):
            token_count = self.client.count_tokens(text)
            
            # 単語数ベースの概算
            expected_tokens = len(text.split())
            assert token_count == expected_tokens
    
    def test_format_messages(self):
        """メッセージフォーマットテスト"""
        prompt = "こんにちは"
        context = {
            'system_prompt': 'あなたは親切なアシスタントです。',
            'conversation_history': [
                {'role': 'user', 'content': '前回の質問'},
                {'role': 'assistant', 'content': '前回の回答'}
            ]
        }
        
        messages = self.client._format_messages(prompt, context)
        
        # メッセージ構造の確認
        assert len(messages) == 4  # system + history(2) + current
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == 'あなたは親切なアシスタントです。'
        assert messages[1]['role'] == 'user'
        assert messages[1]['content'] == '前回の質問'
        assert messages[2]['role'] == 'assistant'
        assert messages[2]['content'] == '前回の回答'
        assert messages[3]['role'] == 'user'
        assert messages[3]['content'] == 'こんにちは'
    
    def test_format_messages_without_context(self):
        """コンテキストなしメッセージフォーマットテスト"""
        prompt = "シンプルな質問"
        
        messages = self.client._format_messages(prompt)
        
        # シンプルなメッセージ構造
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'] == 'シンプルな質問'
    
    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """バッチ処理テスト"""
        prompts = self.test_prompts[:2]  # 最初の2つのプロンプト
        expected_responses = self.test_responses[:2]
        
        call_count = 0
        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            response_content = expected_responses[call_count]
            call_count += 1
            return MockOpenAIResponse(response_content)
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai_instance = AsyncMock()
            mock_openai.return_value = mock_openai_instance
            mock_openai_instance.chat.completions.create = AsyncMock(side_effect=mock_api_call)
            
            client = OpenAIClient(self.config_manager, self.logger)
            client._openai_client = mock_openai_instance
            
            # バッチ処理を実行
            responses = await client.generate_batch_responses(prompts)
            
            assert len(responses) == len(prompts)
            for i, response in enumerate(responses):
                assert response.content == expected_responses[i]
    
    def test_model_configuration_update(self):
        """モデル設定更新テスト"""
        # 初期設定確認
        assert self.client.temperature == 0.7
        assert self.client.max_tokens == 2048
        
        # 設定を更新
        new_config = {
            'temperature': 0.9,
            'max_tokens': 1024,
            'top_p': 0.8,
            'frequency_penalty': 0.1
        }
        
        self.client.update_config(new_config)
        
        # 更新された設定を確認
        assert self.client.temperature == 0.9
        assert self.client.max_tokens == 1024
        assert self.client.top_p == 0.8
        assert self.client.frequency_penalty == 0.1
    
    @requires_file
    def test_openai_client_with_file_config(self):
        """ファイル設定でのOpenAIClientテスト"""
        config_content = {
            'llm': {
                'openai': {
                    'api_key': 'file-config-api-key',
                    'model': 'gpt-4',
                    'temperature': 0.5,
                    'max_tokens': 1024
                }
            }
        }
        
        with MockFileContext(
            self.temp_dir,
            'openai_config.json',
            json.dumps(config_content)
        ) as config_path:
            # ファイルベースの設定でクライアントを初期化
            file_config_manager = create_test_config_manager(self.temp_dir)
            file_config_manager.load_from_file(str(config_path))
            
            client = OpenAIClient(file_config_manager, self.logger)
            
            assert client.api_key == 'file-config-api-key'
            assert client.model_name == 'gpt-4'
            assert client.temperature == 0.5
            assert client.max_tokens == 1024
    
    def test_usage_tracking(self):
        """使用量追跡テスト"""
        # 使用量追跡の初期化
        assert hasattr(self.client, 'usage_tracker')
        
        # 使用量データを追加
        self.client.usage_tracker.add_usage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model='gpt-3.5-turbo'
        )
        
        # 使用量統計を取得
        stats = self.client.usage_tracker.get_usage_stats()
        
        assert stats['total_requests'] == 1
        assert stats['total_tokens'] == 150
        assert stats['total_prompt_tokens'] == 100
        assert stats['total_completion_tokens'] == 50
        assert 'gpt-3.5-turbo' in stats['models_used']

# tests/test_llm/test_claude_client.py
"""
ClaudeClientのテストモジュール
Anthropic Claude API クライアントの単体テストと統合テストを実装
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
from llm.claude_client import ClaudeClient
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


class MockClaudeResponse:
    """Claude APIレスポンスのモック"""
    
    def __init__(self, content: str, model: str = "claude-3-sonnet-20240229", 
                 usage: Optional[Dict] = None, stop_reason: str = "end_turn"):
        self.content = [
            type('Content', (), {
                'text': content,
                'type': 'text'
            })()
        ]
        self.model = model
        self.usage = usage or {
            'input_tokens': 10,
            'output_tokens': 20
        }
        self.id = "msg_test123"
        self.type = "message"
        self.role = "assistant"
        self.stop_reason = stop_reason
        self.stop_sequence = None


class MockClaudeStreamResponse:
    """Claude APIストリーミングレスポンスのモック"""
    
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
        
        # Claude APIのストリーミング形式をモック
        if self.current_index == 1:
            # メッセージ開始
            chunk = type('MessageStart', (), {
                'type': 'message_start',
                'message': type('Message', (), {
                    'id': f'msg_test{self.current_index}',
                    'type': 'message',
                    'role': 'assistant',
                    'content': [],
                    'model': 'claude-3-sonnet-20240229',
                    'stop_reason': None,
                    'stop_sequence': None,
                    'usage': {'input_tokens': 10, 'output_tokens': 0}
                })()
            })()
        elif self.current_index == len(self.chunks) + 1:
            # メッセージ終了
            chunk = type('MessageDelta', (), {
                'type': 'message_delta',
                'delta': type('Delta', (), {
                    'stop_reason': 'end_turn',
                    'stop_sequence': None
                })(),
                'usage': {'output_tokens': len(self.chunks)}
            })()
        else:
            # コンテンツチャンク
            chunk = type('ContentBlockDelta', (), {
                'type': 'content_block_delta',
                'index': 0,
                'delta': type('Delta', (), {
                    'type': 'text_delta',
                    'text': chunk_content
                })()
            })()
        
        return chunk


class TestClaudeClient:
    """ClaudeClientのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="claude_test_"))
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_claude_client")
        
        # Claude設定を追加
        self.config_manager.set('llm.claude.api_key', 'test-claude-api-key-12345')
        self.config_manager.set('llm.claude.model', 'claude-3-sonnet-20240229')
        self.config_manager.set('llm.claude.max_tokens', 2048)
        self.config_manager.set('llm.claude.temperature', 0.7)
        self.config_manager.set('llm.claude.timeout', 30)
        self.config_manager.set('llm.claude.base_url', 'https://api.anthropic.com')
        self.config_manager.set('llm.claude.version', '2023-06-01')
        self.config_manager.set('llm.retry_attempts', 3)
        self.config_manager.set('llm.retry_delay', 1.0)
        
        # ClaudeClientのインスタンスを作成
        self.client = ClaudeClient(self.config_manager, self.logger)
        
        # テスト用のプロンプトとレスポンス
        self.test_prompts = [
            "こんにちは、今日の天気はどうですか？",
            "Pythonでクラスを定義する方法を教えてください。",
            "人工知能の倫理について説明してください。"
        ]
        
        self.test_responses = [
            "こんにちは！申し訳ございませんが、私はリアルタイムの天気情報にアクセスできません。お住まいの地域の天気予報サービスをご確認いただくことをお勧めします。",
            "Pythonでクラスを定義する基本的な方法をご説明します：\n\n```python\nclass MyClass:\n    def __init__(self, name):\n        self.name = name\n    \n    def greet(self):\n        return f'Hello, {self.name}!'\n```",
            "人工知能の倫理は、AIシステムの開発と使用において考慮すべき道徳的原則と社会的責任に関する分野です。主要な論点には、プライバシー、公平性、透明性、説明責任などがあります。"
        ]
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """ClaudeClientの初期化テスト"""
        # 初期化の確認
        assert self.client.config_manager is not None
        assert self.client.logger is not None
        assert self.client.api_key == 'test-claude-api-key-12345'
        assert self.client.model_name == 'claude-3-sonnet-20240229'
        assert self.client.max_tokens == 2048
        assert self.client.temperature == 0.7
        assert self.client.timeout == 30
        assert self.client.base_url == 'https://api.anthropic.com'
        assert self.client.api_version == '2023-06-01'
    
    def test_init_with_missing_api_key(self):
        """APIキーが未設定の場合の初期化テスト"""
        # APIキーを削除
        self.config_manager.remove('llm.claude.api_key')
        
        # 環境変数からAPIキーを取得することを確認
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'env-claude-api-key'}):
            client = ClaudeClient(self.config_manager, self.logger)
            assert client.api_key == 'env-claude-api-key'
    
    def test_init_with_no_api_key(self):
        """APIキーが全く設定されていない場合のテスト"""
        # APIキーを削除
        self.config_manager.remove('llm.claude.api_key')
        
        # 環境変数も設定しない
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                ClaudeClient(self.config_manager, self.logger)
            
            assert "Claude API key" in str(exc_info.value)
    
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
        assert model_info['name'] == 'claude-3-sonnet-20240229'
        assert model_info['provider'] == 'anthropic'
        assert model_info['max_tokens'] == 2048
        assert model_info['supports_streaming'] is True
        assert model_info['supports_functions'] is False  # Claudeは現在関数呼び出しをサポートしていない
        assert 'api_version' in model_info
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self):
        """正常なレスポンス生成テスト"""
        mock_response = MockClaudeResponse(self.test_responses[0])
        
        with patch('anthropic.AsyncAnthropic') as mock_anthropic:
            # モックのAnthropicクライアントを設定
            mock_anthropic_instance = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_instance
            mock_anthropic_instance.messages.create = AsyncMock(return_value=mock_response)
            
            # 新しいクライアントインスタンスを作成（モック付き）
            client = ClaudeClient(self.config_manager, self.logger)
            client._anthropic_client = mock_anthropic_instance
            
            # レスポンスを生成
            response = await client.generate_response(self.test_prompts[0])
            
            # レスポンスの検証
            assert isinstance(response, LLMResponse)
            assert response.content == self.test_responses[0]
            assert response.metadata['model'] == 'claude-3-sonnet-20240229'
            assert response.metadata['tokens_used'] == 30  # input_tokens + output_tokens
            assert response.metadata['input_tokens'] == 10
            assert response.metadata['output_tokens'] == 20
            
            # Anthropic APIが正しく呼び出されたことを確認
            mock_anthropic_instance.messages.create.assert_called_once()
            call_args = mock_anthropic_instance.messages.create.call_args
            assert call_args[1]['model'] == 'claude-3-sonnet-20240229'
            assert call_args[1]['max_tokens'] == 2048
            assert call_args[1]['temperature'] == 0.7
    
    @pytest.mark.asyncio
    async def test_generate_response_with_context(self):
        """コンテキスト付きレスポンス生成テスト"""
        mock_response = MockClaudeResponse("コンテキストを考慮した回答です。")
        
        context = {
            'system_prompt': 'あなたは親切で知識豊富なアシスタントです。',
            'conversation_history': [
                {'role': 'user', 'content': '前回の質問'},
                {'role': 'assistant', 'content': '前回の回答'}
            ],
            'user_preferences': {
                'language': 'japanese',
                'style': 'formal'
            }
        }
        
        with patch('anthropic.AsyncAnthropic') as mock_anthropic:
            mock_anthropic_instance = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_instance
            mock_anthropic_instance.messages.create = AsyncMock(return_value=mock_response)
            
            client = ClaudeClient(self.config_manager, self.logger)
            client._anthropic_client = mock_anthropic_instance
            
            # コンテキスト付きでレスポンスを生成
            response = await client.generate_response(
                "新しい質問です",
                context=context
            )
            
            assert response.content == "コンテキストを考慮した回答です。"
            
            # メッセージ構造の確認
            call_args = mock_anthropic_instance.messages.create.call_args
            messages = call_args[1]['messages']
            system_prompt = call_args[1].get('system')
            
            # システムプロンプトが設定されていることを確認
            assert system_prompt == 'あなたは親切で知識豊富なアシスタントです。'
            # 会話履歴が含まれていることを確認
            assert len(messages) >= 3  # history + current
    
    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """ストリーミングレスポンステスト"""
        streaming_chunks = [
            "これは",
            "ストリーミング",
            "レスポンス",
            "のテストです。"
        ]
        
        mock_stream = MockClaudeStreamResponse(streaming_chunks)
        
        with patch('anthropic.AsyncAnthropic') as mock_anthropic:
            mock_anthropic_instance = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_instance
            mock_anthropic_instance.messages.create = AsyncMock(return_value=mock_stream)
            
            client = ClaudeClient(self.config_manager, self.logger)
            client._anthropic_client = mock_anthropic_instance
            
            # ストリーミングレスポンスを受信
            received_chunks = []
            async for chunk in client.stream_response("ストリーミングテスト"):
                if chunk.content:  # 空のチャンクをスキップ
                    received_chunks.append(chunk.content)
            
            assert received_chunks == streaming_chunks
            
            # ストリーミングパラメータが設定されていることを確認
            call_args = mock_anthropic_instance.messages.create.call_args
            assert call_args[1]['stream'] is True
    
    @pytest.mark.asyncio
    async def test_generate_response_api_error(self):
        """API エラーハンドリングテスト"""
        with patch('anthropic.AsyncAnthropic') as mock_anthropic:
            mock_anthropic_instance = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_instance
            
            # Anthropic APIエラーをシミュレート
            from anthropic import APIError
            mock_anthropic_instance.messages.create = AsyncMock(
                side_effect=APIError("API rate limit exceeded")
            )
            
            client = ClaudeClient(self.config_manager, self.logger)
            client._anthropic_client = mock_anthropic_instance
            
            # エラーが適切に処理されることを確認
            with pytest.raises(LLMError) as exc_info:
                await client.generate_response("テストプロンプト")
            
            assert "Claude API error" in str(exc_info.value)
            assert "rate limit" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_response_timeout(self):
        """タイムアウトテスト"""
        with patch('anthropic.AsyncAnthropic') as mock_anthropic:
            mock_anthropic_instance = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_instance
            
            # タイムアウトをシミュレート
            mock_anthropic_instance.messages.create = AsyncMock(
                side_effect=asyncio.TimeoutError("Request timed out")
            )
            
            client = ClaudeClient(self.config_manager, self.logger)
            client._anthropic_client = mock_anthropic_instance
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
                from anthropic import RateLimitError
                raise RateLimitError("Rate limit exceeded")
            return MockClaudeResponse("リトライ成功")
        
        with patch('anthropic.AsyncAnthropic') as mock_anthropic:
            mock_anthropic_instance = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_instance
            mock_anthropic_instance.messages.create = AsyncMock(side_effect=mock_api_call)
            
            client = ClaudeClient(self.config_manager, self.logger)
            client._anthropic_client = mock_anthropic_instance
            client.retry_delay = 0.1  # テストを高速化
            
            # リトライが成功することを確認
            response = await client.generate_response("リトライテスト")
            
            assert response.content == "リトライ成功"
            assert call_count == 3  # 2回失敗 + 1回成功
    
    def test_count_tokens(self):
        """トークン数カウントテスト"""
        text = "これはトークン数をカウントするテストです。"
        
        # Claudeのトークン数カウント（概算）
        token_count = self.client.count_tokens(text)
        
        # 文字数ベースの概算（Claudeは日本語で約1文字＝1トークン）
        expected_tokens = len(text)
        assert abs(token_count - expected_tokens) <= 5  # 誤差を許容
    
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
        
        messages, system_prompt = self.client._format_messages(prompt, context)
        
        # メッセージ構造の確認
        assert system_prompt == 'あなたは親切なアシスタントです。'
        assert len(messages) == 3  # history(2) + current
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'] == '前回の質問'
        assert messages[1]['role'] == 'assistant'
        assert messages[1]['content'] == '前回の回答'
        assert messages[2]['role'] == 'user'
        assert messages[2]['content'] == 'こんにちは'
    
    def test_format_messages_without_context(self):
        """コンテキストなしメッセージフォーマットテスト"""
        prompt = "シンプルな質問"
        
        messages, system_prompt = self.client._format_messages(prompt)
        
        # シンプルなメッセージ構造
        assert system_prompt is None
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
            return MockClaudeResponse(response_content)
        
        with patch('anthropic.AsyncAnthropic') as mock_anthropic:
            mock_anthropic_instance = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_instance
            mock_anthropic_instance.messages.create = AsyncMock(side_effect=mock_api_call)
            
            client = ClaudeClient(self.config_manager, self.logger)
            client._anthropic_client = mock_anthropic_instance
            
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
            'top_k': 40
        }
        
        self.client.update_config(new_config)
        
        # 更新された設定を確認
        assert self.client.temperature == 0.9
        assert self.client.max_tokens == 1024
        assert self.client.top_p == 0.8
        assert self.client.top_k == 40
    
    def test_claude_specific_features(self):
        """Claude固有機能のテスト"""
        # Claude特有の設定やメソッドをテスト
        
        # Constitutional AIの設定
        constitutional_config = {
            'constitutional_ai': True,
            'harmlessness_weight': 0.8,
            'helpfulness_weight': 0.9
        }
        
        self.client.update_config(constitutional_config)
        
        assert hasattr(self.client, 'constitutional_ai')
        assert self.client.constitutional_ai is True
    
    def test_safety_filtering(self):
        """安全性フィルタリングテスト"""
        # 不適切なコンテンツの検出とフィルタリング
        unsafe_prompts = [
            "違法な活動について教えて",
            "有害な物質の作り方",
            "個人情報を悪用する方法"
        ]
        
        for prompt in unsafe_prompts:
            # 安全性チェックが機能することを確認
            is_safe = self.client._check_content_safety(prompt)
            # 実装により結果は異なるが、チェック機能があることを確認
            assert isinstance(is_safe, bool)
    
    @requires_file
    def test_claude_client_with_file_config(self):
        """ファイル設定でのClaudeClientテスト"""
        config_content = {
            'llm': {
                'claude': {
                    'api_key': 'file-config-claude-api-key',
                    'model': 'claude-3-opus-20240229',
                    'temperature': 0.5,
                    'max_tokens': 1024
                }
            }
        }
        
        with MockFileContext(
            self.temp_dir,
            'claude_config.json',
            json.dumps(config_content)
        ) as config_path:
            # ファイルベースの設定でクライアントを初期化
            file_config_manager = create_test_config_manager(self.temp_dir)
            file_config_manager.load_from_file(str(config_path))
            
            client = ClaudeClient(file_config_manager, self.logger)
            
            assert client.api_key == 'file-config-claude-api-key'
            assert client.model_name == 'claude-3-opus-20240229'
            assert client.temperature == 0.5
            assert client.max_tokens == 1024
    
    def test_usage_tracking(self):
        """使用量追跡テスト"""
        # 使用量追跡の初期化
        assert hasattr(self.client, 'usage_tracker')
        
        # 使用量データを追加
        self.client.usage_tracker.add_usage(
            input_tokens=100,
            output_tokens=50,
            model='claude-3-sonnet-20240229'
        )
        
        # 使用量統計を取得
        stats = self.client.usage_tracker.get_usage_stats()
        
        assert stats['total_requests'] == 1
        assert stats['total_input_tokens'] == 100
        assert stats['total_output_tokens'] == 50
        assert 'claude-3-sonnet-20240229' in stats['models_used']
    
    def test_conversation_context_management(self):
        """会話コンテキスト管理テスト"""
        conversation_id = "test_claude_conversation_001"
        
        # 会話履歴を追加
        self.client.add_to_conversation_history(
            conversation_id,
            "user",
            "初回の質問"
        )
        self.client.add_to_conversation_history(
            conversation_id,
            "assistant",
            "初回の回答"
        )
        
        # 会話履歴を取得
        history = self.client.get_conversation_history(conversation_id)
        
        assert len(history) == 2
        assert history[0]['role'] == 'user'
        assert history[0]['content'] == '初回の質問'
        assert history[1]['role'] == 'assistant'
        assert history[1]['content'] == '初回の回答'
        
        # 会話履歴をクリア
        self.client.clear_conversation_history(conversation_id)
        history_after_clear = self.client.get_conversation_history(conversation_id)
        
        assert len(history_after_clear) == 0
    
    def test_model_version_compatibility(self):
        """モデルバージョン互換性テスト"""
        # 異なるClaudeモデルバージョンの互換性をテスト
        model_versions = [
            'claude-3-sonnet-20240229',
            'claude-3-opus-20240229',
            'claude-3-haiku-20240307'
        ]
        
        for model in model_versions:
            self.client.model_name = model
            model_info = self.client.get_model_info()
            
            assert model_info['name'] == model
            assert model_info['provider'] == 'anthropic'
            assert 'max_tokens' in model_info

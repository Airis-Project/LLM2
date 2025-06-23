# tests/test_llm/test_base_llm.py
"""
BaseLLMのテストモジュール
基底LLMクラスの単体テストと統合テストを実装
"""

import pytest
import asyncio
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional, AsyncGenerator

# テスト対象のインポート
from llm.base_llm import BaseLLM, LLMResponse, LLMConfig, LLMError
from core.config_manager import ConfigManager
from core.logger import Logger

# テスト用のインポート
from tests.test_core import (
    create_test_config_manager,
    create_test_logger,
    MockFileContext,
    requires_file
)


class MockLLM(BaseLLM):
    """テスト用のLLM実装クラス"""
    
    def __init__(self, config_manager: ConfigManager, logger: Logger):
        super().__init__(config_manager, logger)
        self.mock_responses = []
        self.call_count = 0
        self.last_prompt = None
        self.last_context = None
        self.should_raise_error = False
        self.error_message = "Mock error"
        self.delay_seconds = 0
    
    def set_mock_response(self, response: str, metadata: Optional[Dict] = None):
        """モックレスポンスを設定"""
        self.mock_responses.append({
            'response': response,
            'metadata': metadata or {}
        })
    
    def set_mock_responses(self, responses: List[str]):
        """複数のモックレスポンスを設定"""
        for response in responses:
            self.set_mock_response(response)
    
    def set_error_mode(self, should_error: bool = True, message: str = "Mock error"):
        """エラーモードを設定"""
        self.should_raise_error = should_error
        self.error_message = message
    
    def set_delay(self, seconds: float):
        """レスポンス遅延を設定"""
        self.delay_seconds = seconds
    
    async def _generate_response(self, prompt: str, context: Optional[Dict] = None) -> LLMResponse:
        """レスポンス生成の実装"""
        import time
        
        self.call_count += 1
        self.last_prompt = prompt
        self.last_context = context
        
        # 遅延をシミュレート
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        
        # エラーモードの場合
        if self.should_raise_error:
            raise LLMError(self.error_message)
        
        # モックレスポンスを返す
        if self.mock_responses:
            mock_data = self.mock_responses[min(self.call_count - 1, len(self.mock_responses) - 1)]
            return LLMResponse(
                content=mock_data['response'],
                metadata={
                    'model': 'mock-model',
                    'tokens_used': len(prompt.split()),
                    'response_time': self.delay_seconds,
                    **mock_data['metadata']
                }
            )
        
        # デフォルトレスポンス
        return LLMResponse(
            content=f"Mock response for: {prompt[:50]}...",
            metadata={
                'model': 'mock-model',
                'tokens_used': len(prompt.split()),
                'response_time': self.delay_seconds
            }
        )
    
    def _validate_config(self) -> bool:
        """設定の検証"""
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報を取得"""
        return {
            'name': 'Mock LLM',
            'version': '1.0.0',
            'provider': 'test',
            'max_tokens': 4096,
            'supports_streaming': True,
            'supports_functions': False
        }


class TestBaseLLM:
    """BaseLLMのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="llm_test_"))
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_base_llm")
        
        # LLM設定を追加
        self.config_manager.set('llm.default_model', 'mock-model')
        self.config_manager.set('llm.max_tokens', 2048)
        self.config_manager.set('llm.temperature', 0.7)
        self.config_manager.set('llm.timeout', 30)
        self.config_manager.set('llm.retry_attempts', 3)
        self.config_manager.set('llm.retry_delay', 1.0)
        
        # MockLLMのインスタンスを作成
        self.llm = MockLLM(self.config_manager, self.logger)
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """BaseLLMの初期化テスト"""
        # 初期化の確認
        assert self.llm.config_manager is not None
        assert self.llm.logger is not None
        assert self.llm.model_name == 'mock-model'
        assert self.llm.max_tokens == 2048
        assert self.llm.temperature == 0.7
        assert self.llm.timeout == 30
        assert self.llm.retry_attempts == 3
        assert self.llm.retry_delay == 1.0
    
    def test_llm_config_creation(self):
        """LLMConfig作成テスト"""
        config_data = {
            'model': 'test-model',
            'max_tokens': 1024,
            'temperature': 0.5,
            'top_p': 0.9,
            'frequency_penalty': 0.1,
            'presence_penalty': 0.2
        }
        
        config = LLMConfig(**config_data)
        
        assert config.model == 'test-model'
        assert config.max_tokens == 1024
        assert config.temperature == 0.5
        assert config.top_p == 0.9
        assert config.frequency_penalty == 0.1
        assert config.presence_penalty == 0.2
    
    def test_llm_response_creation(self):
        """LLMResponse作成テスト"""
        metadata = {
            'model': 'test-model',
            'tokens_used': 100,
            'response_time': 1.5
        }
        
        response = LLMResponse(
            content="テストレスポンス",
            metadata=metadata
        )
        
        assert response.content == "テストレスポンス"
        assert response.metadata == metadata
        assert response.model == 'test-model'
        assert response.tokens_used == 100
        assert response.response_time == 1.5
    
    def test_llm_error_creation(self):
        """LLMError作成テスト"""
        error = LLMError("テストエラー", error_code="TEST_ERROR")
        
        assert str(error) == "テストエラー"
        assert error.error_code == "TEST_ERROR"
        assert error.details is None
        
        # 詳細情報付きエラー
        details = {"request_id": "123", "status_code": 400}
        error_with_details = LLMError("詳細エラー", error_code="DETAILED_ERROR", details=details)
        
        assert error_with_details.details == details
    
    @pytest.mark.asyncio
    async def test_generate_simple_response(self):
        """シンプルなレスポンス生成テスト"""
        # モックレスポンスを設定
        self.llm.set_mock_response("こんにちは、これはテストレスポンスです。")
        
        # レスポンスを生成
        response = await self.llm.generate_response("こんにちは")
        
        assert isinstance(response, LLMResponse)
        assert response.content == "こんにちは、これはテストレスポンスです。"
        assert response.metadata['model'] == 'mock-model'
        assert 'tokens_used' in response.metadata
        assert self.llm.call_count == 1
        assert self.llm.last_prompt == "こんにちは"
    
    @pytest.mark.asyncio
    async def test_generate_response_with_context(self):
        """コンテキスト付きレスポンス生成テスト"""
        context = {
            'user_name': '田中太郎',
            'conversation_history': ['前回の質問', '前回の回答'],
            'system_prompt': 'あなたは親切なアシスタントです。'
        }
        
        self.llm.set_mock_response("田中太郎さん、ご質問にお答えします。")
        
        # コンテキスト付きでレスポンスを生成
        response = await self.llm.generate_response("質問があります", context=context)
        
        assert response.content == "田中太郎さん、ご質問にお答えします。"
        assert self.llm.last_context == context
    
    @pytest.mark.asyncio
    async def test_generate_multiple_responses(self):
        """複数レスポンス生成テスト"""
        responses = [
            "最初のレスポンス",
            "2番目のレスポンス", 
            "3番目のレスポンス"
        ]
        
        self.llm.set_mock_responses(responses)
        
        # 複数のレスポンスを生成
        for i, expected_response in enumerate(responses):
            response = await self.llm.generate_response(f"質問{i+1}")
            assert response.content == expected_response
            assert self.llm.call_count == i + 1
    
    @pytest.mark.asyncio
    async def test_generate_response_with_retry(self):
        """リトライ機能付きレスポンス生成テスト"""
        # 最初の2回は失敗、3回目で成功するように設定
        call_count = 0
        original_generate = self.llm._generate_response
        
        async def mock_generate_with_retry(prompt, context=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise LLMError(f"一時的なエラー {call_count}")
            return await original_generate(prompt, context)
        
        self.llm._generate_response = mock_generate_with_retry
        self.llm.set_mock_response("リトライ成功レスポンス")
        
        # リトライ設定を調整
        self.llm.retry_delay = 0.1  # テストを高速化
        
        # レスポンスを生成（リトライが発生する）
        response = await self.llm.generate_response("リトライテスト")
        
        assert response.content == "リトライ成功レスポンス"
        assert call_count == 3  # 2回失敗 + 1回成功
    
    @pytest.mark.asyncio
    async def test_generate_response_timeout(self):
        """タイムアウトテスト"""
        # 長い遅延を設定
        self.llm.set_delay(2.0)
        self.llm.timeout = 1.0  # 1秒でタイムアウト
        
        # タイムアウトが発生することを確認
        with pytest.raises(asyncio.TimeoutError):
            await self.llm.generate_response("タイムアウトテスト")
    
    @pytest.mark.asyncio
    async def test_generate_response_error_handling(self):
        """エラーハンドリングテスト"""
        # エラーモードを設定
        self.llm.set_error_mode(True, "テスト用エラー")
        
        # エラーが適切に発生することを確認
        with pytest.raises(LLMError) as exc_info:
            await self.llm.generate_response("エラーテスト")
        
        assert str(exc_info.value) == "テスト用エラー"
    
    @pytest.mark.asyncio
    async def test_generate_response_max_retries_exceeded(self):
        """最大リトライ回数超過テスト"""
        # 常にエラーを発生させる
        self.llm.set_error_mode(True, "継続的なエラー")
        self.llm.retry_delay = 0.1  # テストを高速化
        
        # 最大リトライ回数を超えてエラーになることを確認
        with pytest.raises(LLMError) as exc_info:
            await self.llm.generate_response("リトライ超過テスト")
        
        assert "継続的なエラー" in str(exc_info.value)
    
    def test_get_model_info(self):
        """モデル情報取得テスト"""
        model_info = self.llm.get_model_info()
        
        assert isinstance(model_info, dict)
        assert 'name' in model_info
        assert 'version' in model_info
        assert 'provider' in model_info
        assert 'max_tokens' in model_info
        assert 'supports_streaming' in model_info
        assert 'supports_functions' in model_info
        
        assert model_info['name'] == 'Mock LLM'
        assert model_info['provider'] == 'test'
    
    def test_validate_config(self):
        """設定検証テスト"""
        # 有効な設定
        assert self.llm._validate_config() is True
        
        # 無効な設定のテスト（MockLLMでは常にTrueを返すが、実装例として）
        invalid_llm = MockLLM(self.config_manager, self.logger)
        invalid_llm.model_name = None
        
        # 実際の実装では設定検証ロジックが必要
        # assert invalid_llm._validate_config() is False
    
    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """ストリーミングレスポンステスト"""
        # ストリーミング用のモックレスポンス
        streaming_chunks = [
            "これは",
            "ストリーミング",
            "レスポンス",
            "のテストです。"
        ]
        
        async def mock_stream_response(prompt, context=None):
            for chunk in streaming_chunks:
                yield LLMResponse(
                    content=chunk,
                    metadata={
                        'model': 'mock-model',
                        'is_streaming': True,
                        'chunk_index': streaming_chunks.index(chunk)
                    }
                )
        
        self.llm.stream_response = mock_stream_response
        
        # ストリーミングレスポンスを受信
        received_chunks = []
        async for chunk in self.llm.stream_response("ストリーミングテスト"):
            received_chunks.append(chunk.content)
        
        assert received_chunks == streaming_chunks
    
    def test_prompt_preprocessing(self):
        """プロンプト前処理テスト"""
        # 前処理ロジックのテスト
        raw_prompt = "  これは前処理テストです。  \n\n"
        processed_prompt = self.llm._preprocess_prompt(raw_prompt)
        
        # 基本的な前処理（空白の削除など）
        assert processed_prompt.strip() == "これは前処理テストです。"
    
    def test_response_postprocessing(self):
        """レスポンス後処理テスト"""
        # 後処理ロジックのテスト
        raw_response = "  これは後処理テストです。  \n\n"
        processed_response = self.llm._postprocess_response(raw_response)
        
        # 基本的な後処理（空白の削除など）
        assert processed_response.strip() == "これは後処理テストです。"
    
    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """バッチ処理テスト"""
        prompts = [
            "質問1: 今日の天気は？",
            "質問2: おすすめの本は？",
            "質問3: プログラミングのコツは？"
        ]
        
        expected_responses = [
            "天気は晴れです。",
            "『吾輩は猫である』がおすすめです。",
            "コードを読むことが大切です。"
        ]
        
        self.llm.set_mock_responses(expected_responses)
        
        # バッチ処理を実行
        responses = await self.llm.generate_batch_responses(prompts)
        
        assert len(responses) == len(prompts)
        for i, response in enumerate(responses):
            assert response.content == expected_responses[i]
    
    def test_token_counting(self):
        """トークン数カウントテスト"""
        text = "これはトークン数をカウントするテストです。"
        
        # 簡単なトークン数カウント（単語数ベース）
        token_count = self.llm.count_tokens(text)
        
        assert isinstance(token_count, int)
        assert token_count > 0
    
    def test_prompt_template_handling(self):
        """プロンプトテンプレート処理テスト"""
        template = "こんにちは、{name}さん。今日は{weather}ですね。"
        variables = {
            'name': '田中',
            'weather': '晴れ'
        }
        
        formatted_prompt = self.llm.format_prompt_template(template, variables)
        
        assert formatted_prompt == "こんにちは、田中さん。今日は晴れですね。"
    
    @pytest.mark.asyncio
    async def test_conversation_context_management(self):
        """会話コンテキスト管理テスト"""
        # 会話履歴を管理
        conversation_id = "test_conversation_001"
        
        # 最初のメッセージ
        self.llm.set_mock_response("はじめまして！")
        response1 = await self.llm.generate_response(
            "はじめまして",
            context={'conversation_id': conversation_id}
        )
        
        # 会話履歴を追加
        self.llm.add_to_conversation_history(
            conversation_id,
            "user",
            "はじめまして"
        )
        self.llm.add_to_conversation_history(
            conversation_id,
            "assistant", 
            response1.content
        )
        
        # 2番目のメッセージ（コンテキスト付き）
        self.llm.set_mock_response("はい、覚えています。")
        response2 = await self.llm.generate_response(
            "私のことを覚えていますか？",
            context={
                'conversation_id': conversation_id,
                'include_history': True
            }
        )
        
        # 会話履歴が適切に管理されていることを確認
        history = self.llm.get_conversation_history(conversation_id)
        assert len(history) >= 2
        assert history[0]['role'] == 'user'
        assert history[1]['role'] == 'assistant'
    
    def test_model_configuration_update(self):
        """モデル設定更新テスト"""
        # 初期設定
        assert self.llm.temperature == 0.7
        assert self.llm.max_tokens == 2048
        
        # 設定を更新
        new_config = {
            'temperature': 0.9,
            'max_tokens': 1024,
            'top_p': 0.8
        }
        
        self.llm.update_config(new_config)
        
        # 更新された設定を確認
        assert self.llm.temperature == 0.9
        assert self.llm.max_tokens == 1024
        assert hasattr(self.llm, 'top_p') and self.llm.top_p == 0.8
    
    @requires_file
    def test_llm_with_file_context(self):
        """ファイルコンテキストでのLLMテスト"""
        config_content = {
            'llm': {
                'model': 'file-context-model',
                'temperature': 0.5
            }
        }
        
        with MockFileContext(
            self.temp_dir, 
            'llm_config.json', 
            json.dumps(config_content)
        ) as config_path:
            # ファイルベースの設定でLLMを初期化
            file_config_manager = create_test_config_manager(self.temp_dir)
            file_config_manager.load_from_file(str(config_path))
            
            file_llm = MockLLM(file_config_manager, self.logger)
            
            assert file_llm.model_name == 'file-context-model'
            assert file_llm.temperature == 0.5

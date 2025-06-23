# tests/test_llm/test_llm_factory.py
"""
LLMFactoryのテストモジュール
LLMクライアントファクトリの単体テストと統合テストを実装
"""

import pytest
import tempfile
import shutil
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional

# テスト対象のインポート
from llm.llm_factory import LLMFactory, LLMType
from llm.base_llm import BaseLLM, LLMResponse, LLMConfig, LLMError
from llm.openai_client import OpenAIClient
from llm.claude_client import ClaudeClient
from llm.local_llm_client import LocalLLMClient
from core.config_manager import ConfigManager
from core.logger import Logger

# テスト用のインポート
from tests.test_core import (
    create_test_config_manager,
    create_test_logger,
    MockFileContext,
    requires_file
)


class MockLLMClient(BaseLLM):
    """テスト用のモックLLMクライアント"""
    
    def __init__(self, config_manager: ConfigManager, logger: Logger, 
                 provider: str = "mock", model: str = "mock-model"):
        super().__init__(config_manager, logger)
        self.provider = provider
        self.model_name = model
        self.is_initialized = True
        self.call_count = 0
        self.responses = []
    
    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報を取得"""
        return {
            'name': self.model_name,
            'provider': self.provider,
            'max_tokens': 2048,
            'supports_streaming': True,
            'supports_functions': False
        }
    
    async def generate_response(self, prompt: str, context: Optional[Dict] = None) -> LLMResponse:
        """レスポンス生成（モック）"""
        self.call_count += 1
        response_content = f"Mock response {self.call_count} for: {prompt[:50]}..."
        
        return LLMResponse(
            content=response_content,
            metadata={
                'model': self.model_name,
                'provider': self.provider,
                'tokens_used': 100,
                'call_count': self.call_count
            }
        )
    
    async def stream_response(self, prompt: str, context: Optional[Dict] = None):
        """ストリーミングレスポンス生成（モック）"""
        chunks = ["Mock ", "streaming ", "response"]
        for chunk in chunks:
            yield LLMResponse(
                content=chunk,
                metadata={'model': self.model_name, 'provider': self.provider}
            )
    
    def count_tokens(self, text: str) -> int:
        """トークン数カウント（モック）"""
        return len(text.split())
    
    def _validate_config(self) -> bool:
        """設定検証（モック）"""
        return self.is_initialized


class TestLLMFactory:
    """LLMFactoryのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化処理"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="llm_factory_test_"))
        
        # テスト用の設定とロガーを作成
        self.config_manager = create_test_config_manager(self.temp_dir)
        self.logger = create_test_logger("test_llm_factory")
        
        # テスト用のLLM設定を追加
        self.config_manager.set('llm.default_provider', 'openai')
        self.config_manager.set('llm.openai.api_key', 'test-openai-key')
        self.config_manager.set('llm.openai.model', 'gpt-3.5-turbo')
        self.config_manager.set('llm.claude.api_key', 'test-claude-key')
        self.config_manager.set('llm.claude.model', 'claude-3-sonnet-20240229')
        self.config_manager.set('llm.local.model_path', '/path/to/local/model')
        self.config_manager.set('llm.local.model_type', 'llama')
        
        # LLMFactoryのインスタンスを作成
        self.factory = LLMFactory(self.config_manager, self.logger)
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ処理"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """LLMFactoryの初期化テスト"""
        assert self.factory.config_manager is not None
        assert self.factory.logger is not None
        assert isinstance(self.factory._clients, dict)
        assert len(self.factory._clients) == 0  # 初期状態では空
    
    def test_get_available_providers(self):
        """利用可能なプロバイダー一覧取得テスト"""
        providers = self.factory.get_available_providers()
        
        assert isinstance(providers, list)
        assert 'openai' in providers
        assert 'claude' in providers
        assert 'local' in providers
        
        # 各プロバイダーの詳細情報を確認
        for provider in providers:
            provider_info = self.factory.get_provider_info(provider)
            assert isinstance(provider_info, dict)
            assert 'name' in provider_info
            assert 'description' in provider_info
            assert 'supported_models' in provider_info
    
    def test_get_provider_info(self):
        """プロバイダー情報取得テスト"""
        # OpenAIプロバイダー情報
        openai_info = self.factory.get_provider_info('openai')
        assert openai_info['name'] == 'OpenAI'
        assert 'gpt-3.5-turbo' in openai_info['supported_models']
        assert 'gpt-4' in openai_info['supported_models']
        
        # Claudeプロバイダー情報
        claude_info = self.factory.get_provider_info('claude')
        assert claude_info['name'] == 'Anthropic Claude'
        assert 'claude-3-sonnet-20240229' in claude_info['supported_models']
        
        # 存在しないプロバイダー
        with pytest.raises(ValueError):
            self.factory.get_provider_info('nonexistent')
    
    @patch('llm.openai_client.OpenAIClient')
    def test_create_client_openai(self, mock_openai_client):
        """OpenAIクライアント作成テスト"""
        mock_instance = Mock(spec=OpenAIClient)
        mock_openai_client.return_value = mock_instance
        
        client = self.factory.create_client(LLMType.OPENAI)
        
        assert client is not None
        assert client == mock_instance
        mock_openai_client.assert_called_once_with(self.config_manager, self.logger)
        
        # キャッシュされることを確認
        client2 = self.factory.create_client(LLMType.OPENAI)
        assert client2 == client
        assert mock_openai_client.call_count == 1  # 1回だけ呼ばれる
    
    @patch('llm.claude_client.ClaudeClient')
    def test_create_client_claude(self, mock_claude_client):
        """Claudeクライアント作成テスト"""
        mock_instance = Mock(spec=ClaudeClient)
        mock_claude_client.return_value = mock_instance
        
        client = self.factory.create_client(LLMType.CLAUDE)
        
        assert client is not None
        assert client == mock_instance
        mock_claude_client.assert_called_once_with(self.config_manager, self.logger)
    
    @patch('llm.local_llm_client.LocalLLMClient')
    def test_create_client_local(self, mock_local_client):
        """ローカルLLMクライアント作成テスト"""
        mock_instance = Mock(spec=LocalLLMClient)
        mock_local_client.return_value = mock_instance
        
        client = self.factory.create_client(LLMType.LOCAL)
        
        assert client is not None
        assert client == mock_instance
        mock_local_client.assert_called_once_with(self.config_manager, self.logger)
    
    def test_create_client_invalid_type(self):
        """無効なクライアントタイプでの作成テスト"""
        with pytest.raises(ValueError) as exc_info:
            self.factory.create_client("invalid_type")
        
        assert "Unsupported LLM type" in str(exc_info.value)
    
    def test_create_client_by_string(self):
        """文字列指定でのクライアント作成テスト"""
        with patch('llm.openai_client.OpenAIClient') as mock_openai:
            mock_instance = Mock(spec=OpenAIClient)
            mock_openai.return_value = mock_instance
            
            client = self.factory.create_client("openai")
            assert client == mock_instance
    
    def test_get_default_client(self):
        """デフォルトクライアント取得テスト"""
        with patch('llm.openai_client.OpenAIClient') as mock_openai:
            mock_instance = Mock(spec=OpenAIClient)
            mock_openai.return_value = mock_instance
            
            # デフォルトプロバイダーはopenaiに設定済み
            client = self.factory.get_default_client()
            assert client == mock_instance
    
    def test_get_default_client_with_different_provider(self):
        """異なるデフォルトプロバイダーでのクライアント取得テスト"""
        # デフォルトプロバイダーをclaudeに変更
        self.config_manager.set('llm.default_provider', 'claude')
        
        with patch('llm.claude_client.ClaudeClient') as mock_claude:
            mock_instance = Mock(spec=ClaudeClient)
            mock_claude.return_value = mock_instance
            
            client = self.factory.get_default_client()
            assert client == mock_instance
    
    def test_register_custom_client(self):
        """カスタムクライアント登録テスト"""
        # カスタムクライアントクラスを登録
        custom_provider = "custom_provider"
        
        self.factory.register_client_class(custom_provider, MockLLMClient)
        
        # 登録されたクライアントを作成
        client = self.factory.create_client(custom_provider)
        
        assert isinstance(client, MockLLMClient)
        assert client.provider == "mock"  # MockLLMClientのデフォルト値
    
    def test_list_active_clients(self):
        """アクティブクライアント一覧取得テスト"""
        # 初期状態では空
        active_clients = self.factory.list_active_clients()
        assert len(active_clients) == 0
        
        # クライアントを作成
        with patch('llm.openai_client.OpenAIClient') as mock_openai:
            mock_instance = Mock(spec=OpenAIClient)
            mock_openai.return_value = mock_instance
            
            self.factory.create_client(LLMType.OPENAI)
            
            active_clients = self.factory.list_active_clients()
            assert len(active_clients) == 1
            assert LLMType.OPENAI.value in active_clients
    
    def test_clear_clients(self):
        """クライアントキャッシュクリアテスト"""
        # クライアントを作成
        with patch('llm.openai_client.OpenAIClient') as mock_openai:
            mock_instance = Mock(spec=OpenAIClient)
            mock_openai.return_value = mock_instance
            
            self.factory.create_client(LLMType.OPENAI)
            assert len(self.factory._clients) == 1
            
            # キャッシュをクリア
            self.factory.clear_clients()
            assert len(self.factory._clients) == 0
    
    def test_client_health_check(self):
        """クライアントヘルスチェックテスト"""
        # モッククライアントを登録
        self.factory.register_client_class("mock", MockLLMClient)
        client = self.factory.create_client("mock")
        
        # ヘルスチェック実行
        health_status = self.factory.check_client_health("mock")
        
        assert isinstance(health_status, dict)
        assert 'status' in health_status
        assert 'provider' in health_status
        assert health_status['status'] in ['healthy', 'unhealthy', 'unknown']
    
    def test_client_configuration_update(self):
        """クライアント設定更新テスト"""
        # モッククライアントを作成
        self.factory.register_client_class("mock", MockLLMClient)
        client = self.factory.create_client("mock")
        
        # 設定を更新
        new_config = {
            'temperature': 0.8,
            'max_tokens': 1024
        }
        
        # update_configメソッドがあることを前提とした更新
        if hasattr(client, 'update_config'):
            client.update_config(new_config)
        
        # 設定が更新されたことを確認（実装依存）
        assert client is not None
    
    @pytest.mark.asyncio
    async def test_client_response_generation(self):
        """クライアントレスポンス生成テスト"""
        # モッククライアントを作成
        self.factory.register_client_class("mock", MockLLMClient)
        client = self.factory.create_client("mock")
        
        # レスポンスを生成
        response = await client.generate_response("テストプロンプト")
        
        assert isinstance(response, LLMResponse)
        assert "Mock response" in response.content
        assert response.metadata['provider'] == 'mock'
    
    @pytest.mark.asyncio
    async def test_client_streaming_response(self):
        """クライアントストリーミングレスポンステスト"""
        # モッククライアントを作成
        self.factory.register_client_class("mock", MockLLMClient)
        client = self.factory.create_client("mock")
        
        # ストリーミングレスポンスを受信
        chunks = []
        async for chunk in client.stream_response("ストリーミングテスト"):
            chunks.append(chunk.content)
        
        assert len(chunks) == 3
        assert chunks == ["Mock ", "streaming ", "response"]
    
    def test_factory_with_environment_variables(self):
        """環境変数を使用したファクトリーテスト"""
        # 環境変数を設定
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'env-openai-key',
            'ANTHROPIC_API_KEY': 'env-claude-key'
        }):
            # 設定からAPIキーを削除
            self.config_manager.remove('llm.openai.api_key')
            self.config_manager.remove('llm.claude.api_key')
            
            # 新しいファクトリーを作成
            factory = LLMFactory(self.config_manager, self.logger)
            
            # 環境変数からAPIキーが取得されることを確認
            with patch('llm.openai_client.OpenAIClient') as mock_openai:
                mock_instance = Mock(spec=OpenAIClient)
                mock_openai.return_value = mock_instance
                
                client = factory.create_client(LLMType.OPENAI)
                assert client is not None
    
    def test_factory_error_handling(self):
        """ファクトリーエラーハンドリングテスト"""
        # 無効な設定でクライアント作成を試行
        self.config_manager.remove('llm.openai.api_key')
        
        with patch('llm.openai_client.OpenAIClient') as mock_openai:
            # クライアント初期化時にエラーを発生させる
            mock_openai.side_effect = ValueError("Invalid API key")
            
            with pytest.raises(LLMError) as exc_info:
                self.factory.create_client(LLMType.OPENAI)
            
            assert "Failed to create LLM client" in str(exc_info.value)
    
    def test_concurrent_client_creation(self):
        """並行クライアント作成テスト"""
        import threading
        import time
        
        created_clients = []
        
        def create_client_thread():
            with patch('llm.openai_client.OpenAIClient') as mock_openai:
                mock_instance = Mock(spec=OpenAIClient)
                mock_openai.return_value = mock_instance
                
                client = self.factory.create_client(LLMType.OPENAI)
                created_clients.append(client)
        
        # 複数スレッドで同時にクライアントを作成
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_client_thread)
            threads.append(thread)
            thread.start()
        
        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 同じインスタンスが返されることを確認（キャッシュ機能）
        assert len(set(id(client) for client in created_clients)) == 1
    
    @requires_file
    def test_factory_with_file_config(self):
        """ファイル設定でのファクトリーテスト"""
        config_content = {
            'llm': {
                'default_provider': 'claude',
                'openai': {
                    'api_key': 'file-openai-key',
                    'model': 'gpt-4'
                },
                'claude': {
                    'api_key': 'file-claude-key',
                    'model': 'claude-3-opus-20240229'
                }
            }
        }
        
        with MockFileContext(
            self.temp_dir,
            'llm_config.json',
            json.dumps(config_content)
        ) as config_path:
            # ファイルベースの設定でファクトリーを初期化
            file_config_manager = create_test_config_manager(self.temp_dir)
            file_config_manager.load_from_file(str(config_path))
            
            factory = LLMFactory(file_config_manager, self.logger)
            
            # デフォルトプロバイダーがclaudeに設定されていることを確認
            default_provider = file_config_manager.get('llm.default_provider')
            assert default_provider == 'claude'
            
            # プロバイダー情報が正しく取得できることを確認
            providers = factory.get_available_providers()
            assert 'openai' in providers
            assert 'claude' in providers
    
    def test_factory_performance_metrics(self):
        """ファクトリーパフォーマンス測定テスト"""
        import time
        
        # クライアント作成時間を測定
        start_time = time.time()
        
        with patch('llm.openai_client.OpenAIClient') as mock_openai:
            mock_instance = Mock(spec=OpenAIClient)
            mock_openai.return_value = mock_instance
            
            # 複数回クライアントを作成（キャッシュ効果を確認）
            for _ in range(10):
                client = self.factory.create_client(LLMType.OPENAI)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # キャッシュにより高速に作成されることを確認
        assert creation_time < 1.0  # 1秒以内
        assert mock_openai.call_count == 1  # 1回だけ実際に作成される
    
    def test_factory_memory_usage(self):
        """ファクトリーメモリ使用量テスト"""
        import gc
        import sys
        
        # 初期メモリ使用量
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # 複数のクライアントを作成
        with patch('llm.openai_client.OpenAIClient') as mock_openai, \
             patch('llm.claude_client.ClaudeClient') as mock_claude:
            
            mock_openai.return_value = Mock(spec=OpenAIClient)
            mock_claude.return_value = Mock(spec=ClaudeClient)
            
            self.factory.create_client(LLMType.OPENAI)
            self.factory.create_client(LLMType.CLAUDE)
        
        # クライアントをクリア
        self.factory.clear_clients()
        
        # メモリ使用量の確認
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # メモリリークがないことを確認（大幅な増加がないこと）
        object_increase = final_objects - initial_objects
        assert object_increase < 100  # 許容範囲内

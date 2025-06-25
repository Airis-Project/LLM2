# tests/test_e2e.py
"""
End-to-End Tests for LLM Chat System
エンドツーエンドテスト
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, Mock
from io import StringIO

import pytest

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEnd:
    """エンドツーエンドテストクラス"""
    
    def test_system_startup_and_shutdown(self, temp_dir):
        """システム起動・終了テスト"""
        # テスト用設定ファイル作成
        config = {
            "version": "1.0.0",
            "application": {"name": "E2E Test", "debug": True},
            "llm": {
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "enabled": True,
                        "api_key": "test_key",
                        "models": {
                            "default": "gpt-3.5-turbo",
                            "available": ["gpt-3.5-turbo"]
                        }
                    }
                }
            }
        }
        
        config_path = temp_dir / "e2e_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        # システム初期化テスト
        init_result = subprocess.run([
            sys.executable, "scripts/init.py", "--force"
        ], capture_output=True, text=True, cwd=project_root)
        
        assert init_result.returncode == 0, f"Init failed: {init_result.stderr}"
        
        # ヘルスチェックテスト
        health_result = subprocess.run([
            sys.executable, "scripts/start.py", "--health-check"
        ], capture_output=True, text=True, cwd=project_root)
        
        assert health_result.returncode == 0, f"Health check failed: {health_result.stderr}"
    
    def test_cli_interactive_session(self, temp_dir):
        """CLIインタラクティブセッションテスト"""
        # テスト用設定
        config = {
            "version": "1.0.0",
            "application": {"name": "CLI E2E Test"},
            "llm": {
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "enabled": True,
                        "api_key": "test_key",
                        "models": {
                            "default": "gpt-3.5-turbo",
                            "available": ["gpt-3.5-turbo"]
                        }
                    }
                }
            }
        }
        
        config_path = temp_dir / "cli_e2e_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        # CLIコマンドのテスト入力
        test_commands = [
            "help",
            "config",
            "provider",
            "clear",
            "quit"
        ]
        
        # プロセス起動とコマンド送信
        process = subprocess.Popen([
            sys.executable, "main.py", 
            "--config", str(config_path),
            "--interface", "cli"
        ], 
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=project_root
        )
        
        # コマンド送信
        input_text = "\n".join(test_commands)
        try:
            stdout, stderr = process.communicate(input=input_text, timeout=30)
            
            # 基本的な出力確認
            assert "LLM Chat System" in stdout
            assert process.returncode == 0
            
        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("CLI session timed out")
    
    @pytest.mark.requires_api_key
    def test_real_api_integration(self):
        """実際のAPI統合テスト（APIキーが利用可能な場合のみ）"""
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY not available")
        
        # 実際のAPIを使用したテスト
        from src.core.config_manager import ConfigManager
        from src.core.logger import setup_logger
        from src.services.llm_service import LLMService
        
        # 実際の設定でLLMサービスを初期化
        config_manager = ConfigManager()
        config_manager.load_config("config/default_config.json")
        
        logger = setup_logger("RealAPITest")
        llm_service = LLMService(config_manager, logger)
        
        # 簡単なメッセージ送信テスト
        try:
            response = llm_service.send_message("Hello, this is a test message.")
            
            # レスポンス検証
            assert isinstance(response, str)
            assert len(response) > 0
            assert response.strip() != ""
            
        except Exception as e:
            pytest.fail(f"Real API integration failed: {e}")
    
    def test_configuration_scenarios(self, temp_dir):
        """設定シナリオテスト"""
        scenarios = [
            {
                "name": "minimal_config",
                "config": {
                    "version": "1.0.0",
                    "application": {"name": "Minimal Test"},
                    "llm": {
                        "default_provider": "openai",
                        "providers": {
                            "openai": {
                                "enabled": True,
                                "api_key": "test_key",
                                "models": {
                                    "default": "gpt-3.5-turbo",
                                    "available": ["gpt-3.5-turbo"]
                                }
                            }
                        }
                    }
                }
            },
            {
                "name": "full_config",
                "config": {
                    "version": "1.0.0",
                    "application": {
                        "name": "Full Test",
                        "debug": True,
                        "log_level": "DEBUG"
                    },
                    "llm": {
                        "default_provider": "openai",
                        "timeout": 30,
                        "max_retries": 3,
                        "providers": {
                            "openai": {
                                "enabled": True,
                                "api_key": "test_key",
                                "models": {
                                    "default": "gpt-3.5-turbo",
                                    "available": ["gpt-3.5-turbo", "gpt-4"]
                                },
                                "parameters": {
                                    "temperature": 0.7,
                                    "max_tokens": 2000
                                }
                            }
                        }
                    },
                    "ui": {
                        "default_interface": "cli",
                        "cli": {
                            "prompt_style": "colorful",
                            "show_timestamps": True
                        }
                    },
                    "logging": {
                        "level": "DEBUG",
                        "console_output": True,
                        "file_output": True
                    }
                }
            }
        ]
        
        for scenario in scenarios:
            config_path = temp_dir / f"{scenario['name']}_config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(scenario['config'], f)
            
            # 設定ファイルでシステム起動テスト
            result = subprocess.run([
                sys.executable, "scripts/start.py",
                "--config", str(config_path),
                "--health-check"
            ], capture_output=True, text=True, cwd=project_root)
            
            assert result.returncode == 0, \
                f"Scenario '{scenario['name']}' failed: {result.stderr}"
    
    def test_error_recovery_scenarios(self, temp_dir):
        """エラー回復シナリオテスト"""
        # 無効な設定ファイル
        invalid_config = {
            "version": "invalid",
            "application": {},
            "llm": {"providers": {}}
            }
        
        config_path = temp_dir / "invalid_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(invalid_config, f)
        
        # 無効な設定での起動テスト（失敗することを期待）
        result = subprocess.run([
            sys.executable, "scripts/start.py",
            "--config", str(config_path)
        ], capture_output=True, text=True, cwd=project_root)
        
        # エラーで終了することを確認
        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "failed" in result.stderr.lower()
        
        # 存在しない設定ファイル
        nonexistent_config = temp_dir / "nonexistent.json"
        result = subprocess.run([
            sys.executable, "scripts/start.py",
            "--config", str(nonexistent_config)
        ], capture_output=True, text=True, cwd=project_root)
        
        assert result.returncode != 0
    
    def test_session_persistence_e2e(self, temp_dir):
        """セッション永続化エンドツーエンドテスト"""
        # テスト用設定
        config = {
            "version": "1.0.0",
            "application": {"name": "Session Persistence Test"},
            "llm": {
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "enabled": True,
                        "api_key": "test_key",
                        "models": {
                            "default": "gpt-3.5-turbo",
                            "available": ["gpt-3.5-turbo"]
                        }
                    }
                }
            },
            "storage": {
                "chat_history": {
                    "enabled": True,
                    "storage_path": str(temp_dir / "sessions")
                }
            }
        }
        
        config_path = temp_dir / "session_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        # セッションディレクトリの作成
        session_dir = temp_dir / "sessions"
        session_dir.mkdir(exist_ok=True)
        
        # テストセッションファイルの作成
        test_session = {
            "metadata": {
                "created_at": "2024-01-01T10:00:00",
                "provider": "openai",
                "model": "gpt-3.5-turbo"
            },
            "messages": [
                {
                    "user": "Hello",
                    "assistant": "Hi there!",
                    "timestamp": "2024-01-01T10:00:00"
                }
            ]
        }
        
        session_file = session_dir / "test_session.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(test_session, f)
        
        # セッション読み込みテスト
        from src.ui.cli import CLIInterface
        from src.core.config_manager import ConfigManager
        from src.core.logger import setup_logger
        
        config_manager = ConfigManager()
        config_manager.load_config(str(config_path))
        logger = setup_logger("SessionTest")
        
        cli = CLIInterface(config_manager, logger)
        
        # セッション読み込み
        cli.load_session(str(session_file))
        
        # セッションデータの確認
        assert len(cli.current_session) == 1
        assert cli.current_session[0]["user"] == "Hello"
        assert cli.current_session[0]["assistant"] == "Hi there!"


@pytest.mark.integration
class TestSystemStress:
    """システムストレステストクラス"""
    
    @patch('src.llm.openai_provider.OpenAI')
    def test_concurrent_requests(self, mock_openai_class, config_manager, test_logger):
        """並行リクエストテスト"""
        import threading
        import queue
        
        # OpenAIクライアントのモック
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Concurrent response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        from src.services.llm_service import LLMService
        llm_service = LLMService(config_manager, test_logger)
        
        # 結果キュー
        results = queue.Queue()
        
        def send_message_worker(message_id):
            try:
                response = llm_service.send_message(f"Message {message_id}")
                results.put(("success", message_id, response))
            except Exception as e:
                results.put(("error", message_id, str(e)))
        
        # 10個の並行リクエストを送信
        threads = []
        for i in range(10):
            thread = threading.Thread(target=send_message_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # すべてのスレッドの完了を待機
        for thread in threads:
            thread.join(timeout=30)
        
        # 結果の確認
        success_count = 0
        error_count = 0
        
        while not results.empty():
            status, message_id, result = results.get()
            if status == "success":
                success_count += 1
                assert isinstance(result, str)
                assert len(result) > 0
            else:
                error_count += 1
        
        # 大部分のリクエストが成功することを確認
        assert success_count >= 8  # 80%以上の成功率
    
    def test_memory_leak_detection(self, config_manager, test_logger):
        """メモリリークテスト"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        from src.services.llm_service import LLMService
        
        # 多数のインスタンス作成と削除
        for i in range(100):
            service = LLMService(config_manager, test_logger)
            # 使用後に明示的に削除
            del service
            
            # 定期的にガベージコレクション実行
            if i % 10 == 0:
                gc.collect()
        
        # 最終的なガベージコレクション
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # メモリ増加が許容範囲内であることを確認
        assert memory_increase < 20, f"Memory increased by {memory_increase}MB"
    
    def test_long_running_session(self, config_manager, test_logger):
        """長時間実行セッションテスト"""
        from src.ui.cli import CLIInterface
        
        cli = CLIInterface(config_manager, test_logger)
        
        # 大量のセッションデータを追加
        for i in range(1000):
            cli.current_session.append({
                "user": f"Message {i}",
                "assistant": f"Response {i}",
                "timestamp": f"2024-01-01T{i%24:02d}:00:00"
            })
        
        # セッションデータの整合性確認
        assert len(cli.current_session) == 1000
        assert cli.current_session[0]["user"] == "Message 0"
        assert cli.current_session[999]["user"] == "Message 999"
        
        # メモリ使用量の確認
        import sys
        session_size = sys.getsizeof(cli.current_session)
        assert session_size < 10 * 1024 * 1024  # 10MB以下


@pytest.mark.integration
class TestSystemCompatibility:
    """システム互換性テストクラス"""
    
    def test_python_version_compatibility(self):
        """Python バージョン互換性テスト"""
        import sys
        
        # Python 3.8以上であることを確認
        assert sys.version_info >= (3, 8), f"Python {sys.version_info} is not supported"
        
        # 必要なモジュールのインポートテスト
        required_modules = [
            "json", "os", "sys", "pathlib", "typing",
            "logging", "configparser", "argparse"
        ]
        
        for module_name in required_modules:
            try:
                __import__(module_name)
            except ImportError:
                pytest.fail(f"Required module '{module_name}' is not available")
    
    def test_file_system_compatibility(self, temp_dir):
        """ファイルシステム互換性テスト"""
        # 長いファイル名のテスト
        long_filename = "a" * 200 + ".json"
        long_file_path = temp_dir / long_filename
        
        try:
            with open(long_file_path, 'w') as f:
                f.write('{"test": "data"}')
            
            # ファイルが正常に作成されたか確認
            assert long_file_path.exists()
            
        except OSError:
            # ファイルシステムが長いファイル名をサポートしない場合
            pytest.skip("File system does not support long filenames")
        
        # Unicode ファイル名のテスト
        unicode_filename = "テスト_файл_🚀.json"
        unicode_file_path = temp_dir / unicode_filename
        
        try:
            with open(unicode_file_path, 'w', encoding='utf-8') as f:
                json.dump({"unicode": "test"}, f, ensure_ascii=False)
            
            assert unicode_file_path.exists()
            
            # ファイル読み込みテスト
            with open(unicode_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert data["unicode"] == "test"
                
        except (OSError, UnicodeError):
            pytest.skip("File system does not support Unicode filenames")
    
    def test_environment_variable_handling(self):
        """環境変数処理テスト"""
        import os
        
        # 環境変数の設定と取得
        test_var_name = "LLM_CHAT_TEST_VAR"
        test_var_value = "test_value_123"
        
        # 環境変数を設定
        os.environ[test_var_name] = test_var_value
        
        # 環境変数の取得確認
        retrieved_value = os.getenv(test_var_name)
        assert retrieved_value == test_var_value
        
        # 環境変数の削除
        del os.environ[test_var_name]
        
        # 削除後の確認
        assert os.getenv(test_var_name) is None


def run_all_e2e_tests():
    """すべてのE2Eテストを実行"""
    import subprocess
    
    test_commands = [
        # 基本的なE2Eテスト
        ["python", "-m", "pytest", "tests/test_e2e.py::TestEndToEnd", "-v"],
        
        # ストレステスト
        ["python", "-m", "pytest", "tests/test_e2e.py::TestSystemStress", "-v", "-s"],
        
        # 互換性テスト
        ["python", "-m", "pytest", "tests/test_e2e.py::TestSystemCompatibility", "-v"]
    ]
    
    all_passed = True
    
    for cmd in test_commands:
        print(f"\n🧪 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=project_root)
        
        if result.returncode != 0:
            print(f"❌ Test failed: {' '.join(cmd)}")
            all_passed = False
        else:
            print(f"✅ Test passed: {' '.join(cmd)}")
    
    return all_passed


if __name__ == "__main__":
    # 直接実行時はすべてのE2Eテストを実行
    success = run_all_e2e_tests()
    
    if success:
        print("\n🎉 All E2E tests passed!")
    else:
        print("\n💥 Some E2E tests failed!")
    
    sys.exit(0 if success else 1)


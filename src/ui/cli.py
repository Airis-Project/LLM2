# src/ui/cli.py
"""
CLI Interface for LLM Chat System
コマンドライン インターフェース
"""

import os
import sys
from typing import Optional, Dict, Any
import json
from pathlib import Path

from src.core.logger import Logger
#from src.core.config_manager import ConfigManager
from src.core.exceptions import LLMChatError
from src.services.llm_service import LLMService

def get_config_manager():
    from src.core.config_manager import ConfigManager
    return ConfigManager()

class CLIInterface:
    """コマンドライン インターフェース"""
    
    def __init__(self, config_manager: get_config_manager, logger: Logger):
        self.config_manager = config_manager
        self.logger = logger
        self.llm_service = None
        self.current_session = []
        
    def run(self):
        """CLIインターフェースを実行"""
        self.logger.info("Starting CLI interface")
        self.print_welcome()
        
        try:
            # LLMサービスの初期化
            self.initialize_llm_service()
            
            # メインループ
            self.main_loop()
            
        except Exception as e:
            self.logger.error(f"CLI interface error: {e}")
            print(f"Error: {e}")
    
    def print_welcome(self):
        """ウェルカムメッセージを表示"""
        print("\n" + "="*60)
        print("🤖 LLM Chat System v1.0.0")
        print("="*60)
        print("Multi-provider LLM chat interface")
        print("Type 'help' for commands, 'quit' to exit")
        print("="*60 + "\n")
    
    def initialize_llm_service(self):
        """LLMサービスを初期化"""
        try:
            self.llm_service = LLMService(self.config_manager, self.logger)
            print("✅ LLM service initialized successfully")
            
            # 利用可能なプロバイダーを表示
            providers = self.llm_service.get_available_providers()
            if providers:
                print(f"📡 Available providers: {', '.join(providers)}")
            else:
                print("⚠️  No providers configured. Please check your configuration.")
                
        except Exception as e:
            print(f"❌ Failed to initialize LLM service: {e}")
            raise
    
    def main_loop(self):
        """メインループ"""
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                
                if not user_input:
                    continue
                
                # コマンド処理
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.handle_quit()
                    break
                elif user_input.lower() in ['help', 'h']:
                    self.show_help()
                elif user_input.lower().startswith('config'):
                    self.handle_config_command(user_input)
                elif user_input.lower().startswith('provider'):
                    self.handle_provider_command(user_input)
                elif user_input.lower() in ['clear', 'cls']:
                    self.clear_session()
                elif user_input.lower() == 'history':
                    self.show_history()
                elif user_input.lower().startswith('save'):
                    self.handle_save_command(user_input)
                else:
                    # 通常のチャット処理
                    self.handle_chat(user_input)
                    
            except KeyboardInterrupt:
                print("\n\nUse 'quit' to exit gracefully.")
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                print(f"❌ Error: {e}")
    
    def handle_chat(self, message: str):
        """チャットメッセージを処理"""
        if not self.llm_service:
            print("❌ LLM service not available")
            return
        
        try:
            print("🤔 Thinking...")
            
            # LLMに送信
            response = self.llm_service.send_message(message)
            
            # セッション履歴に追加
            self.current_session.append({
                "user": message,
                "assistant": response,
                "timestamp": self.get_timestamp()
            })
            
            # レスポンス表示
            print(f"\n🤖 Assistant: {response}")
            
        except Exception as e:
            self.logger.error(f"Chat error: {e}")
            print(f"❌ Chat error: {e}")
    
    def handle_config_command(self, command: str):
        """設定コマンドを処理"""
        parts = command.split()
        
        if len(parts) == 1:
            # 現在の設定を表示
            self.show_current_config()
        elif len(parts) == 2 and parts[1] == 'reload':
            # 設定をリロード
            self.reload_config()
        else:
            print("Usage: config [reload]")
    
    def handle_provider_command(self, command: str):
        """プロバイダーコマンドを処理"""
        parts = command.split()
        
        if len(parts) == 1:
            # 利用可能なプロバイダーを表示
            self.show_providers()
        elif len(parts) == 2:
            # プロバイダーを切り替え
            provider_name = parts[1]
            self.switch_provider(provider_name)
        else:
            print("Usage: provider [provider_name]")
    
    def handle_save_command(self, command: str):
        """保存コマンドを処理"""
        parts = command.split()
        
        if len(parts) == 1:
            # デフォルトファイル名で保存
            filename = f"chat_session_{self.get_timestamp()}.json"
        else:
            filename = parts[1]
        
        self.save_session(filename)
    
    def show_help(self):
        """ヘルプを表示"""
        help_text = """
📖 Available Commands:
─────────────────────
• help, h           - Show this help message
• quit, exit, q     - Exit the application
• clear, cls        - Clear current session
• history           - Show current session history
• config            - Show current configuration
• config reload     - Reload configuration
• provider          - Show available providers
• provider <name>   - Switch to specified provider
• save [filename]   - Save current session
─────────────────────
Just type your message to start chatting!
        """
        print(help_text)
    
    def show_current_config(self):
        """現在の設定を表示"""
        try:
            config = self.config_manager.get_all_config()
            print("\n📋 Current Configuration:")
            print("─" * 30)
            
            # 重要な設定のみ表示（APIキーは隠す）
            display_config = {}
            for key, value in config.items():
                if isinstance(value, dict):
                    display_config[key] = {}
                    for sub_key, sub_value in value.items():
                        if 'key' in sub_key.lower() or 'token' in sub_key.lower():
                            display_config[key][sub_key] = "***hidden***"
                        else:
                            display_config[key][sub_key] = sub_value
                else:
                    display_config[key] = value
            
            print(json.dumps(display_config, indent=2))
            
        except Exception as e:
            print(f"❌ Failed to show configuration: {e}")
    
    def show_providers(self):
        """利用可能なプロバイダーを表示"""
        if not self.llm_service:
            print("❌ LLM service not available")
            return
        
        try:
            providers = self.llm_service.get_available_providers()
            current = self.llm_service.get_current_provider()
            
            print("\n📡 Available Providers:")
            print("─" * 25)
            
            for provider in providers:
                status = "✅ (current)" if provider == current else "⚪"
                print(f"{status} {provider}")
                
        except Exception as e:
            print(f"❌ Failed to show providers: {e}")
    
    def switch_provider(self, provider_name: str):
        """プロバイダーを切り替え"""
        if not self.llm_service:
            print("❌ LLM service not available")
            return
        
        try:
            self.llm_service.switch_provider(provider_name)
            print(f"✅ Switched to provider: {provider_name}")
            
        except Exception as e:
            print(f"❌ Failed to switch provider: {e}")
    
    def clear_session(self):
        """セッションをクリア"""
        self.current_session.clear()
        print("✅ Session cleared")
    
    def show_history(self):
        """履歴を表示"""
        if not self.current_session:
            print("📝 No chat history in current session")
            return
        
        print(f"\n📝 Chat History ({len(self.current_session)} messages):")
        print("─" * 50)
        
        for i, entry in enumerate(self.current_session, 1):
            print(f"\n[{i}] {entry['timestamp']}")
            print(f"💬 You: {entry['user']}")
            print(f"🤖 Assistant: {entry['assistant']}")
    
    def save_session(self, filename: str):
        """セッションを保存"""
        try:
            if not self.current_session:
                print("📝 No session data to save")
                return
            
            # ファイルパスの準備
            save_dir = Path("logs")
            save_dir.mkdir(exist_ok=True)
            filepath = save_dir / filename
            
            # セッションデータの保存
            session_data = {
                "timestamp": self.get_timestamp(),
                "total_messages": len(self.current_session),
                "messages": self.current_session
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Session saved to: {filepath}")
            
        except Exception as e:
            print(f"❌ Failed to save session: {e}")
    
    def reload_config(self):
        """設定をリロード"""
        try:
            self.config_manager.reload_config()
            
            # LLMサービスを再初期化
            self.llm_service = LLMService(self.config_manager, self.logger)
            
            print("✅ Configuration reloaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to reload configuration: {e}")
    
    def handle_quit(self):
        """終了処理"""
        print("\n👋 Thank you for using LLM Chat System!")
        
        if self.current_session:
            save_choice = input("💾 Save current session? (y/n): ").lower()
            if save_choice in ['y', 'yes']:
                filename = f"chat_session_{self.get_timestamp()}.json"
                self.save_session(filename)
        
        print("Goodbye! 🚀")
    
    def get_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    """CLI単体実行用のメイン関数"""
    from ..core.logger import setup_logger
    from ..core.config_manager import ConfigManager
    
    try:
        logger = setup_logger()
        config_manager = ConfigManager()
        
        cli = CLIInterface(config_manager, logger)
        cli.run()
        
    except Exception as e:
        print(f"CLI startup error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

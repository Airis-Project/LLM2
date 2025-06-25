# test_integration.py
"""
メイン統合テスト
LLM機能がUIに正しく統合されているかテスト
"""

import sys
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """インポートテスト"""
    print("=== インポートテスト ===")
    
    try:
        # メインパッケージ
        import src
        print(f"✓ srcパッケージ: v{src.__version__}")
        
        # LLMクライアント
        from src.llm_client_v2 import EnhancedLLMClient
        print("✓ EnhancedLLMClient")
        
        # UIコンポーネント
        from src.ui.main_window import MainWindow
        from src.ui.llm_chat_panel import LLMChatPanel
        from src.ui.code_editor import CodeEditor
        print("✓ UIコンポーネント")
        
        # サービス
        from src.services.llm_service import LLMService
        print("✓ LLMService")
        
        # 設定
        from config import load_default_settings
        print("✓ 設定システム")
        
        return True
        
    except ImportError as e:
        print(f"✗ インポートエラー: {e}")
        return False

def test_llm_client():
    """LLMクライアントテスト"""
    print("\n=== LLMクライアントテスト ===")
    
    try:
        from src.llm_client_v2 import EnhancedLLMClient
        
        client = EnhancedLLMClient()
        print(f"✓ クライアント初期化完了")
        
        # 可用性チェック
        is_available = client.is_available()
        print(f"✓ 可用性: {'利用可能' if is_available else '利用不可'}")
        
        # モデルリスト
        models = client.list_available_models()
        print(f"✓ 利用可能モデル: {len(models)}個")
        for model in models[:3]:  # 最初の3つを表示
            print(f"  - {model}")
        
        # 簡単なテスト（利用可能な場合のみ）
        if is_available and models:
            print("\n簡単な生成テスト実行中...")
            result = client.generate_code(
                prompt="Create a simple hello world function in Python",
                task_type="code_generation",
                priority="speed"
            )
            
            if result.get('success'):
                print("✓ 生成テスト成功")
                print(f"  モデル: {result.get('model', 'Unknown')}")
                print(f"  実行時間: {result.get('duration', 0):.2f}秒")
                response = result.get('response', '')[:100]
                print(f"  レスポンス: {response}...")
            else:
                print(f"✗ 生成テスト失敗: {result.get('error', 'Unknown error')}")
        
        return True
        
    except Exception as e:
        print(f"✗ LLMクライアントテストエラー: {e}")
        return False

def test_ui_components():
    """UIコンポーネントテスト"""
    print("\n=== UIコンポーネントテスト ===")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from src.llm_client_v2 import EnhancedLLMClient
        from src.ui.llm_chat_panel import LLMChatPanel
        from src.ui.code_editor import CodeEditor
        
        # QApplication作成（必要な場合）
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # LLMクライアント
        llm_client = EnhancedLLMClient()
        
        # チャットパネル
        chat_panel = LLMChatPanel(llm_client)
        print("✓ LLMChatPanel初期化完了")
        
        # コードエディタ
        code_editor = CodeEditor()
        code_editor.set_llm_client(llm_client)
        print("✓ CodeEditor初期化完了")
        
        # ウィジェット表示テスト
        chat_panel.show()
        code_editor.show()
        print("✓ ウィジェット表示テスト完了")
        
        # クリーンアップ
        chat_panel.close()
        code_editor.close()
        
        return True
        
    except Exception as e:
        print(f"✗ UIコンポーネントテストエラー: {e}")
        return False

def test_main_integration():
    """メイン統合テスト"""
    print("\n=== メイン統合テスト ===")
    
    try:
        from src.main import initialize_application
        
        # アプリケーション初期化
        components = initialize_application()
        print("✓ アプリケーション初期化完了")
        
        # コンポーネント確認
        required_components = ['config_manager', 'event_bus', 'plugin_manager', 'llm_client']
        for component in required_components:
            if component in components:
                print(f"✓ {component}: 利用可能")
            else:
                print(f"✗ {component}: 見つかりません")
        
        # LLMクライアント特別チェック
        llm_client = components.get('llm_client')
        if llm_client:
            print(f"✓ LLMクライアント可用性: {'利用可能' if llm_client.is_available() else '利用不可'}")
        
        return True
        
    except Exception as e:
        print(f"✗ メイン統合テストエラー: {e}")
        return False

def test_configuration():
    """設定テスト"""
    print("\n=== 設定テスト ===")
    
    try:
        from config import load_default_settings, load_logging_config
        
        # デフォルト設定
        settings = load_default_settings()
        print(f"✓ デフォルト設定読み込み: {len(settings)}セクション")
        
        # LLM設定確認
        llm_config = settings.get('llm', {})
        if llm_config:
            providers = llm_config.get('providers', {})
            print(f"✓ LLMプロバイダー設定: {len(providers)}個")
            
            for provider, config in providers.items():
                enabled = config.get('enabled', False)
                status = "有効" if enabled else "無効"
                print(f"  - {provider}: {status}")
        
        # ログ設定
        log_config = load_logging_config()
        print(f"✓ ログ設定読み込み: バージョン{log_config.get('version', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"✗ 設定テストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 LLM Code Assistant 統合テスト開始\n")
    
    tests = [
        ("インポート", test_imports),
        ("LLMクライアント", test_llm_client),
        ("UIコンポーネント", test_ui_components),
        ("メイン統合", test_main_integration),
        ("設定", test_configuration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name}テスト中に予期しないエラー: {e}")
            results.append((test_name, False))
    
    # 結果サマリー
    print("\n" + "="*50)
    print("📊 テスト結果サマリー")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 総合結果: {passed}/{total} テスト成功")
    
    if passed == total:
        print("🎉 すべてのテストが成功しました！")
        print("✨ LLM機能がメインアプリケーションに正常に統合されています。")
    else:
        print("⚠️  一部のテストが失敗しました。")
        print("🔧 エラーを確認して修正してください。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# run_app.py
"""
LLM Code Assistant 起動スクリプト
統合されたアプリケーションの起動
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_requirements():
    """必要な依存関係をチェック"""
    print("📋 依存関係チェック中...")
    
    required_packages = [
        'PyQt6', 'requests', 'json', 'yaml', 
        'pathlib', 'logging', 'threading', 'queue'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} (未インストール)")
    
    if missing_packages:
        print(f"\n❌ 不足パッケージ: {', '.join(missing_packages)}")
        print("pip install で必要なパッケージをインストールしてください。")
        return False
    
    print("✅ すべての依存関係が満たされています。")
    return True

def check_llm_availability():
    """LLM可用性チェック"""
    print("\n🤖 LLM可用性チェック中...")
    
    try:
        from src.llm_client_v2 import EnhancedLLMClient
        
        client = EnhancedLLMClient()
        
        if client.get_model_info():
            models = client.get_available_models()
            print(f"✅ LLMサービス利用可能 ({len(models)}個のモデル)")
            
            # 推奨モデルの確認
            recommended_models = ['wizardcoder:33b', 'starcoder:7b']
            available_recommended = [m for m in recommended_models if m in models]
            
            if available_recommended:
                print(f"✨ 推奨モデル利用可能: {', '.join(available_recommended)}")
            else:
                print("⚠️  推奨モデルが見つかりません。基本機能は利用できますが、パフォーマンスが制限される可能性があります。")
            
            return True
        else:
            print("⚠️  LLMサービスが利用できません。")
            print("   - Ollamaサービスが起動しているか確認してください")
            print("   - 必要なモデルがダウンロードされているか確認してください")
            return False
            
    except Exception as e:
        print(f"❌ LLMチェックエラー: {e}")
        return False

def run_integration_test():
    """統合テスト実行"""
    print("\n🧪 統合テスト実行中...")
    
    try:
        from test_integration import main as run_tests
        
        # テスト実行
        success = run_tests()
        
        if success:
            print("✅ 統合テスト成功")
            return True
        else:
            print("❌ 統合テスト失敗")
            return False
            
    except Exception as e:
        print(f"❌ 統合テストエラー: {e}")
        return False

def main():
    """メイン起動処理"""
    print("🚀 LLM Code Assistant 起動中...")
    print("="*50)
    
    # 1. 依存関係チェック
    if not check_requirements():
        print("\n❌ 起動を中止します。")
        return False
    
    # 2. LLM可用性チェック
    llm_available = check_llm_availability()
    
    # 3. 統合テスト（オプション）
    if "--test" in sys.argv:
        if not run_integration_test():
            print("\n❌ テスト失敗のため起動を中止します。")
            return False
    
    # 4. アプリケーション起動
    print("\n🎯 アプリケーション起動中...")
    
    try:
        from src.main import main as app_main
        
        if not llm_available:
            print("⚠️  LLM機能は制限されますが、アプリケーションを起動します。")
        
        print("✨ LLM Code Assistant を起動します...")
        app_main()
        
        return True
        
    except KeyboardInterrupt:
        print("\n👋 ユーザーによって中断されました。")
        return True
        
    except Exception as e:
        print(f"\n❌ 起動エラー: {e}")
        
        # エラー詳細をログファイルに保存
        import traceback
        error_log = project_root / "logs" / "startup_error.log"
        error_log.parent.mkdir(exist_ok=True)
        
        with open(error_log, "w", encoding="utf-8") as f:
            f.write(f"起動エラー: {e}\n")
            f.write(traceback.format_exc())
        
        print(f"詳細なエラー情報は {error_log} に保存されました。")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 LLM Code Assistant - AI支援コード生成ツール")
    print("=" * 60)
    
    success = main()
    
    if success:
        print("\n👋 アプリケーションが正常に終了しました。")
    else:
        print("\n❌ エラーが発生しました。")
        print("🔧 ログファイルを確認して問題を解決してください。")
    
    sys.exit(0 if success else 1)

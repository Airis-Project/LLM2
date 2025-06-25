# test_basic_functionality.py
"""
基本機能テストスクリプト
各コアモジュールの基本的な読み込みと初期化をテスト
"""
import sys
import os
import traceback

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """基本的なimportテスト"""
    print("--- Import テスト ---")
    
    tests = [
        ("src.core.config_manager", "ConfigManager"),
        ("src.core.logger", "get_logger"),
        ("src.core.error_handler", "ErrorHandler"),
        ("src.core.event_system", "EventSystem"),
        ("src.database.database_manager", "DatabaseManager"),
        ("src.llm.llm_factory", "LLMFactory"),
        ("src.llm.base_llm", "BaseLLM"),
        ("src.utils.file_utils", "FileUtils"),
        ("src.utils.validation_utils", "ValidationUtils"),
    ]
    
    passed = 0
    for module_name, class_name in tests:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
            passed += 1
        except Exception as e:
            print(f"❌ {module_name}.{class_name}: {e}")
    
    print(f"Import テスト結果: {passed}/{len(tests)}")
    return passed == len(tests)

def test_config_manager():
    """設定管理のテスト"""
    print("\n--- ConfigManager テスト ---")
    try:
        from src.core.config_manager import ConfigManager
        config = ConfigManager()
        print("✅ ConfigManager: 初期化成功")
        
        # 基本的な設定取得テスト
        app_config = config.get_config('app', {})
        print(f"✅ 設定取得: app config keys = {list(app_config.keys())}")
        return True
    except Exception as e:
        print(f"❌ ConfigManager: {e}")
        traceback.print_exc()
        return False

def test_logger():
    """ログ機能のテスト"""
    print("\n--- Logger テスト ---")
    try:
        from src.core.logger import get_logger
        logger = get_logger("test")
        logger.info("テストログメッセージ")
        print("✅ Logger: 正常動作")
        return True
    except Exception as e:
        print(f"❌ Logger: {e}")
        traceback.print_exc()
        return False

def test_error_handler():
    """エラーハンドラーのテスト"""
    print("\n--- ErrorHandler テスト ---")
    try:
        from src.core.error_handler import ErrorHandler
        error_handler = ErrorHandler()
        print("✅ ErrorHandler: 初期化成功")
        return True
    except Exception as e:
        print(f"❌ ErrorHandler: {e}")
        traceback.print_exc()
        return False

def test_database():
    """データベースのテスト"""
    print("\n--- DatabaseManager テスト ---")
    try:
        from src.database.database_manager import DatabaseManager
        db = DatabaseManager()
        print("✅ DatabaseManager: 初期化成功")
        return True
    except Exception as e:
        print(f"❌ DatabaseManager: {e}")
        traceback.print_exc()
        return False

def test_llm_factory():
    """LLMファクトリーのテスト"""
    print("\n--- LLMFactory テスト ---")
    try:
        from src.llm.llm_factory import LLMFactory
        factory = LLMFactory()
        print("✅ LLMFactory: 初期化成功")
        
        # 利用可能なプロバイダーの確認
        providers = factory.get_available_providers()
        if isinstance(providers, dict):
            print(f"✅ 利用可能プロバイダー: {list(providers.keys())}")
        elif isinstance(providers, list):
            print(f"✅ 利用可能プロバイダー: {providers}")
        else:
            print(f"✅ 利用可能プロバイダー: {providers}")
        return True
    except Exception as e:
        print(f"❌ LLMFactory: {e}")
        traceback.print_exc()
        return False

def test_utilities():
    """ユーティリティのテスト"""
    print("\n--- Utilities テスト ---")
    try:
        from src.utils.file_utils import FileUtils
        from src.utils.validation_utils import ValidationUtils
        
        file_utils = FileUtils()
        validation_utils = ValidationUtils()
        
        print("✅ FileUtils: 初期化成功")
        print("✅ ValidationUtils: 初期化成功")
        return True
    except Exception as e:
        print(f"❌ Utilities: {e}")
        traceback.print_exc()
        return False

def main():
    """メインテスト実行"""
    print("=" * 50)
    print("🚀 LLM Code Assistant 基本機能テスト開始")
    print("=" * 50)
    
    # テスト関数のリスト
    tests = [
        ("Import", test_imports),
        ("ConfigManager", test_config_manager),
        ("Logger", test_logger),
        ("ErrorHandler", test_error_handler),
        ("DatabaseManager", test_database),
        ("LLMFactory", test_llm_factory),
        ("Utilities", test_utilities),
    ]
    
    passed = 0
    total = len(tests)
    failed_tests = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name} テスト実行中...")
        try:
            if test_func():
                passed += 1
            else:
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} テストでエラー: {e}")
            failed_tests.append(test_name)
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("📊 テスト結果サマリー")
    print("=" * 50)
    print(f"✅ 成功: {passed}/{total}")
    print(f"❌ 失敗: {len(failed_tests)}/{total}")
    
    if failed_tests:
        print(f"失敗したテスト: {', '.join(failed_tests)}")
    
    if passed == total:
        print("\n🎉 すべてのテストが成功しました！")
        print("次のステップ: UI テストまたはアプリケーション起動テスト")
    else:
        print("\n⚠️ 一部のテストが失敗しました。")
        print("失敗したモジュールを確認・修正してください。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# test_local_llm.py
from src.llm.llm_factory import LLMFactory
from src.core.config_manager import ConfigManager

def test_local_llm_integration():
    """ローカルLLM統合テスト"""
    print("🔧 LLMFactory + Ollama 統合テスト")
    
    try:
        # 設定確認
        config = ConfigManager()
        llm_config = config.get('llm', {})
        print(f"設定確認: {llm_config}")
        
        # LLMFactory初期化
        factory = LLMFactory()
        
        # ローカルプロバイダー取得
        local_llm = factory.get_provider('local')
        print(f"✅ ローカルLLM取得成功: {type(local_llm)}")
        
        # 簡単なテスト
        response = local_llm.generate("def hello():")
        print(f"✅ コード生成テスト成功: {response[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 統合テスト失敗: {e}")
        return False

if __name__ == "__main__":
    test_local_llm_integration()

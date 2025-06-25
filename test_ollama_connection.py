import requests
import json
import time
from src.core.logger import get_logger

logger = get_logger(__name__)

def test_ollama_connection():
    """Ollama + CodeLlama:70B 接続テスト"""
    print("🦙 Ollama + CodeLlama:70B 接続テスト開始")
    
    # 1. Ollamaサーバー確認
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json()
            print("✅ Ollamaサーバー接続成功")
            available_models = [m['name'] for m in models.get('models', [])]
            print(f"📋 利用可能モデル: {available_models}")
        else:
            print("❌ Ollamaサーバー応答エラー")
            return False
    except Exception as e:
        print(f"❌ Ollama接続失敗: {e}")
        return False
    
    # 2. CodeLlama:70B テスト
    print("\n🔍 CodeLlama:70B テスト実行中...")
    
    test_cases = [
        {
            "name": "Python関数生成",
            "prompt": "Write a Python function to calculate the factorial of a number:",
            "expected_keywords": ["def", "factorial", "return"]
        },
        {
            "name": "JavaScript関数生成", 
            "prompt": "Write a JavaScript function to reverse a string:",
            "expected_keywords": ["function", "reverse", "return"]
        },
        {
            "name": "コード説明",
            "prompt": "Explain this Python code: def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
            "expected_keywords": ["fibonacci", "recursive", "function"]
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📝 テスト {i}: {test['name']}")
        
        try:
            start_time = time.time()
            
            test_prompt = {
                "model": "codellama:70b",
                "prompt": test["prompt"],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 300
                }
            }
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=test_prompt,
                timeout=120
            )
            
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')
                
                print(f"✅ 応答成功 (応答時間: {end_time - start_time:.1f}秒)")
                print(f"📄 生成内容 ({len(generated_text)} 文字):")
                print("-" * 60)
                print(generated_text[:400] + ("..." if len(generated_text) > 400 else ""))
                print("-" * 60)
                
                # キーワード確認
                keywords_found = [kw for kw in test["expected_keywords"] 
                                if kw.lower() in generated_text.lower()]
                print(f"🔍 期待キーワード確認: {keywords_found}/{test['expected_keywords']}")
                
            else:
                print(f"❌ 応答エラー: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ テスト失敗: {e}")
            return False
    
    # 3. 代替モデルのクイックテスト
    print(f"\n🚀 軽量モデル (starcoder:7b) クイックテスト")
    
    try:
        quick_test = {
            "model": "starcoder:7b",
            "prompt": "def hello_world():",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 100
            }
        }
        
        start_time = time.time()
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=quick_test,
            timeout=30
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 軽量モデル応答成功 (応答時間: {end_time - start_time:.1f}秒)")
            print(f"📄 生成内容: {result.get('response', '')[:150]}...")
        else:
            print(f"⚠️ 軽量モデル応答エラー: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ 軽量モデルテスト失敗: {e}")
    
    return True

if __name__ == "__main__":
    success = test_ollama_connection()
    if success:
        print("\n🎉 Ollama + CodeLlama:70B セットアップ完了！")
        print("💡 次のステップ: python test_basic_functionality.py")
    else:
        print("\n❌ セットアップに問題があります")
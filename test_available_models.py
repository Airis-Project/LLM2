# 軽量モデル動作確認
import requests
import json
import time

def test_available_models():
    """利用可能な軽量モデルをテスト"""
    print("🚀 利用可能モデル動作確認")
    
    # メモリ使用量順（軽量→重量）
    models_to_test = [
        ("codellama:7b", "3.8GB"), 
        ("starcoder:7b", "4.3GB"),
        ("phi4:14b", "9.1GB"),
        ("wizardcoder:33b", "18GB")
    ]
    
    working_models = []
    
    for model, size in models_to_test:
        print(f"\n📝 {model} ({size}) テスト:")
        
        try:
            payload = {
                "model": model,
                "prompt": "def fibonacci(n):",
                "stream": False,
                "options": {
                    "num_predict": 100,
                    "temperature": 0.1
                }
            }
            
            start_time = time.time()
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=120
            )
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                print(f"✅ {model} 成功! (応答時間: {end_time - start_time:.1f}秒)")
                print(f"📄 応答: {response_text[:150]}...")
                working_models.append({
                    'model': model,
                    'size': size,
                    'response_time': end_time - start_time,
                    'response_length': len(response_text)
                })
            else:
                print(f"❌ {model} エラー: {response.status_code}")
                if response.text:
                    error_detail = response.text[:200]
                    print(f"詳細: {error_detail}")
                
        except requests.exceptions.Timeout:
            print(f"⏱️ {model} タイムアウト (120秒)")
        except Exception as e:
            print(f"❌ {model} 例外: {e}")
        
        # モデル間で少し待機
        time.sleep(2)
    
    return working_models

if __name__ == "__main__":
    print("🔍 システムメモリ制限により、軽量モデルをテストします")
    working_models = test_available_models()
    
    if working_models:
        print(f"\n🎉 動作確認済みモデル ({len(working_models)}個):")
        for model_info in working_models:
            print(f"  ✅ {model_info['model']} ({model_info['size']}) - {model_info['response_time']:.1f}秒")
        
        # 最適なモデルを推奨
        fastest_model = min(working_models, key=lambda x: x['response_time'])
        print(f"\n💡 推奨モデル: {fastest_model['model']} (最速応答: {fastest_model['response_time']:.1f}秒)")
        
    else:
        print("\n❌ 動作するモデルが見つかりませんでした")

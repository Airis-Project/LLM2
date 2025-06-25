# 実際のLLM呼び出しテスト
# テスト実行
# python test_llm_real.py

# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm_client_v2 import EnhancedLLMClient
from src.model_selector import TaskType
import time

def test_real_llm_calls():
    """実際のLLM呼び出しテスト"""
    print("🧪 実際のLLM呼び出しテスト開始")
    
    try:
        client = EnhancedLLMClient()
        
        # 利用可能なモデル確認
        available_models = client.get_available_models()
        print(f"📋 利用可能なモデル: {len(available_models)}個")
        for model in available_models[:5]:  # 最初の5個だけ表示
            print(f"   • {model}")
        
        # テストケース（短時間で完了するもの）
        test_cases = [
            {
                "name": "高速コード補完",
                "task": TaskType.QUICK_RESPONSE,
                "priority": "speed",
                "prompt": "def fibonacci(n):",
                "max_tokens": 150
            },
            {
                "name": "簡単なコード説明",
                "task": TaskType.CODE_EXPLANATION,
                "priority": "quality",
                "prompt": "Explain this code: x = [i**2 for i in range(5)]",
                "max_tokens": 200
            },
            {
                "name": "コードデバッグ",
                "task": TaskType.DEBUGGING,
                "priority": "balanced",
                "prompt": "Fix this code: def add(a, b) return a + b",
                "max_tokens": 100
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 テスト {i}: {test_case['name']}")
            print(f"   プロンプト: {test_case['prompt']}")
            
            start_time = time.time()
            
            try:
                result = client.generate_code(
                    prompt=test_case['prompt'],
                    task_type=test_case['task'],
                    priority=test_case['priority'],
                    num_predict=test_case['max_tokens']
                )
                
                end_time = time.time()
                actual_time = end_time - start_time
                
                if result['success']:
                    response_text = result['response'].strip()
                    print(f"   ✅ 成功 ({actual_time:.1f}s)")
                    print(f"   🤖 使用モデル: {result['model']}")
                    print(f"   📝 応答: {response_text[:150]}...")
                    
                    results.append({
                        "test": test_case['name'],
                        "success": True,
                        "time": actual_time,
                        "model": result['model'],
                        "response_length": len(response_text)
                    })
                else:
                    print(f"   ❌ 失敗: {result.get('error', 'Unknown error')}")
                    results.append({
                        "test": test_case['name'],
                        "success": False,
                        "time": actual_time,
                        "error": result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                end_time = time.time()
                actual_time = end_time - start_time
                print(f"   💥 例外 ({actual_time:.1f}s): {e}")
                results.append({
                    "test": test_case['name'],
                    "success": False,
                    "time": actual_time,
                    "error": str(e)
                })
        
        # 結果サマリー
        print(f"\n📊 テスト結果サマリー:")
        successful_tests = sum(1 for r in results if r['success'])
        total_time = sum(r['time'] for r in results)
        
        print(f"   成功率: {successful_tests}/{len(results)} ({successful_tests/len(results):.1%})")
        print(f"   総実行時間: {total_time:.1f}秒")
        
        for result in results:
            status = "✅" if result['success'] else "❌"
            if result['success']:
                print(f"   {status} {result['test']}: {result['time']:.1f}s ({result['model']})")
            else:
                print(f"   {status} {result['test']}: {result.get('error', 'Failed')}")
        
        # 性能レポート
        print(f"\n📈 性能レポート:")
        try:
            perf_report = client.get_performance_report()
            print(f"   総リクエスト: {perf_report['total_requests']}")
            print(f"   成功率: {perf_report['success_rate']}")
            print(f"   平均応答時間: {perf_report['avg_response_time']}")
            
            print(f"   モデル使用状況:")
            for model, count in perf_report.get('model_usage', {}).items():
                print(f"     • {model}: {count}回")
                
            if perf_report.get('error_summary'):
                print(f"   エラーサマリー:")
                for error, count in perf_report['error_summary'].items():
                    print(f"     • {error}: {count}回")
                    
        except Exception as e:
            print(f"   性能レポート生成エラー: {e}")
            
    except Exception as e:
        print(f"❌ テスト初期化エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_llm_calls()
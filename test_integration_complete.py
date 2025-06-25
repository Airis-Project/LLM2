# 包括的統合テストを作成
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 実行権限付与
#chmod +x test_integration_complete.py

# 包括的テスト実行
#python test_integration_complete.py

"""
完全統合テスト - 全機能テスト
"""

import sys
import time
import asyncio
from pathlib import Path

# パス設定
sys.path.insert(0, str(Path(__file__).parent))

from src.llm_client_v2 import EnhancedLLMClient
from src.model_selector import TaskType

def print_section(title: str):
    """セクション表示"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print('='*60)

def print_test(name: str, prompt: str):
    """テスト開始表示"""
    print(f"\n📝 テスト: {name}")
    print(f"   プロンプト: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")

async def run_comprehensive_tests():
    """包括的テスト実行"""
    
    print_section("LLM Code Assistant 完全統合テスト")
    
    # クライアント初期化
    client = EnhancedLLMClient()
    
    print(f"📋 利用可能なモデル: {len(client.get_available_models())}個")
    for model in client.get_available_models()[:5]:
        print(f"   • {model}")
    
    # テストケース定義
    test_cases = [
        # 基本機能テスト
        {
            "name": "Python関数生成",
            "prompt": "Create a Python function to calculate factorial",
            "task_type": TaskType.CODE_GENERATION,
            "priority": "quality"
        },
        {
            "name": "JavaScript関数生成", 
            "prompt": "Write a JavaScript function to validate email",
            "task_type": TaskType.CODE_GENERATION,
            "priority": "balanced"
        },
        {
            "name": "SQL クエリ生成",
            "prompt": "Write SQL to find top 5 customers by purchase amount",
            "task_type": TaskType.CODE_GENERATION,
            "priority": "quality"
        },
        
        # コード説明テスト
        {
            "name": "複雑なコード説明",
            "prompt": "Explain this code: def quicksort(arr): if len(arr) <= 1: return arr; pivot = arr[len(arr)//2]; left = [x for x in arr if x < pivot]; middle = [x for x in arr if x == pivot]; right = [x for x in arr if x > pivot]; return quicksort(left) + middle + quicksort(right)",
            "task_type": TaskType.CODE_EXPLANATION,
            "priority": "quality"
        },
        {
            "name": "正規表現説明",
            "prompt": "Explain this regex: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
            "task_type": TaskType.CODE_EXPLANATION,
            "priority": "balanced"
        },
        
        # デバッグテスト
        {
            "name": "Python構文エラー修正",
            "prompt": "Fix this Python code: for i in range(10) print(i)",
            "task_type": TaskType.DEBUGGING,
            "priority": "speed"
        },
        {
            "name": "論理エラー修正",
            "prompt": "Fix this code: def is_even(n): return n % 2 == 1",
            "task_type": TaskType.DEBUGGING,
            "priority": "balanced"
        },
        {
            "name": "JavaScript エラー修正",
            "prompt": "Fix this JS: function add(a, b) { return a + b; } console.log(add(1));",
            "task_type": TaskType.DEBUGGING,
            "priority": "balanced"
        },
        
        # リファクタリングテスト
        {
            "name": "コード最適化",
            "prompt": "Refactor this code for better performance: def find_max(arr): max_val = arr[0]; for i in range(1, len(arr)): if arr[i] > max_val: max_val = arr[i]; return max_val",
            "task_type": TaskType.REFACTORING,
            "priority": "quality"
        },
        {
            "name": "可読性向上",
            "prompt": "Make this code more readable: x=[i for i in range(100) if i%2==0 and i%3==0 and i>10]",
            "task_type": TaskType.REFACTORING,
            "priority": "balanced"
        },
        
        # 高速レスポンステスト
        {
            "name": "クイック補完1",
            "prompt": "Complete: def hello_world():",
            "task_type": TaskType.QUICK_RESPONSE,
            "priority": "speed"
        },
        {
            "name": "クイック補完2", 
            "prompt": "Complete: import pandas as pd; df = pd.read_csv('data.csv'); df.",
            "task_type": TaskType.QUICK_RESPONSE,
            "priority": "speed"
        },
        
        # 複雑分析テスト
        {
            "name": "アルゴリズム分析",
            "prompt": "Analyze the time and space complexity of merge sort algorithm",
            "task_type": TaskType.COMPLEX_ANALYSIS,
            "priority": "quality"
        },
        {
            "name": "設計パターン説明",
            "prompt": "Explain the Singleton design pattern with Python example",
            "task_type": TaskType.COMPLEX_ANALYSIS,
            "priority": "quality"
        }
    ]
    
    # テスト実行
    results = []
    total_start_time = time.time()
    
    for i, test_case in enumerate(test_cases, 1):
        print_test(f"{i}. {test_case['name']}", test_case['prompt'])
        
        start_time = time.time()
        try:
            response = await client.generate_async(
                prompt=test_case['prompt'],
                task_type=test_case['task_type'],
                priority=test_case['priority']
            )
            
            duration = time.time() - start_time
            
            if response['success']:
                print(f"   ✅ 成功 ({duration:.1f}s)")
                print(f"   🤖 使用モデル: {response['model']}")
                print(f"   📝 応答: {response['content'][:100]}{'...' if len(response['content']) > 100 else ''}")
                
                results.append({
                    'name': test_case['name'],
                    'success': True,
                    'duration': duration,
                    'model': response['model'],
                    'task_type': test_case['task_type'].value,
                    'priority': test_case['priority']
                })
            else:
                print(f"   ❌ 失敗: {response['error']}")
                results.append({
                    'name': test_case['name'],
                    'success': False,
                    'duration': duration,
                    'error': response['error'],
                    'task_type': test_case['task_type'].value,
                    'priority': test_case['priority']
                })
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"   ❌ 例外: {e}")
            results.append({
                'name': test_case['name'],
                'success': False,
                'duration': duration,
                'error': str(e),
                'task_type': test_case['task_type'].value,
                'priority': test_case['priority']
            })
    
    # 結果分析
    total_duration = time.time() - total_start_time
    successful_tests = [r for r in results if r['success']]
    failed_tests = [r for r in results if not r['success']]
    
    print_section("完全統合テスト結果")
    
    print(f"📊 総合結果:")
    print(f"   成功率: {len(successful_tests)}/{len(results)} ({len(successful_tests)/len(results)*100:.1f}%)")
    print(f"   総実行時間: {total_duration:.1f}秒")
    print(f"   平均応答時間: {sum(r['duration'] for r in successful_tests)/len(successful_tests):.1f}秒" if successful_tests else "   平均応答時間: N/A")
    
    # 成功テスト詳細
    if successful_tests:
        print(f"\n✅ 成功したテスト ({len(successful_tests)}個):")
        for result in successful_tests:
            print(f"   • {result['name']}: {result['duration']:.1f}s ({result['model']})")
    
    # 失敗テスト詳細
    if failed_tests:
        print(f"\n❌ 失敗したテスト ({len(failed_tests)}個):")
        for result in failed_tests:
            print(f"   • {result['name']}: {result.get('error', 'Unknown error')}")
    
    # タスクタイプ別分析
    print(f"\n📈 タスクタイプ別成功率:")
    task_types = {}
    for result in results:
        task_type = result['task_type']
        if task_type not in task_types:
            task_types[task_type] = {'total': 0, 'success': 0}
        task_types[task_type]['total'] += 1
        if result['success']:
            task_types[task_type]['success'] += 1
    
    for task_type, stats in task_types.items():
        success_rate = stats['success'] / stats['total'] * 100
        print(f"   • {task_type}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
    
    # 優先度別分析
    print(f"\n⚡ 優先度別平均応答時間:")
    priorities = {}
    for result in successful_tests:
        priority = result['priority']
        if priority not in priorities:
            priorities[priority] = []
        priorities[priority].append(result['duration'])
    
    for priority, durations in priorities.items():
        avg_duration = sum(durations) / len(durations)
        print(f"   • {priority}: {avg_duration:.1f}秒 (サンプル数: {len(durations)})")
    
    # モデル使用統計
    print(f"\n🤖 モデル使用統計:")
    model_usage = {}
    for result in successful_tests:
        model = result['model']
        model_usage[model] = model_usage.get(model, 0) + 1
    
    for model, count in sorted(model_usage.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {model}: {count}回")
    
    print_section("統合テスト完了")
    
    return {
        'total_tests': len(results),
        'successful_tests': len(successful_tests),
        'success_rate': len(successful_tests) / len(results) * 100,
        'total_duration': total_duration,
        'results': results
    }

if __name__ == "__main__":
    # 非同期実行
    asyncio.run(run_comprehensive_tests())


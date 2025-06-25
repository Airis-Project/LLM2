# 最終版テスト実行
#python test_integration_final.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完全統合テスト - 最終修正版（generate_code使用）
"""

import sys
import time
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

def run_comprehensive_tests():
    """包括的テスト実行（generate_code使用）"""
    
    print_section("LLM Code Assistant 完全統合テスト（最終版）")
    
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
            "prompt": "Create a simple Python function to calculate factorial",
            "task_type": TaskType.CODE_GENERATION,
            "priority": "balanced"
        },
        {
            "name": "JavaScript関数生成", 
            "prompt": "Write a simple JavaScript function to validate email",
            "task_type": TaskType.CODE_GENERATION,
            "priority": "balanced"
        },
        {
            "name": "SQL クエリ生成",
            "prompt": "Write SQL to select top 5 users",
            "task_type": TaskType.CODE_GENERATION,
            "priority": "balanced"
        },
        
        # コード説明テスト
        {
            "name": "リスト内包表記説明",
            "prompt": "Explain this code: squares = [x**2 for x in range(10)]",
            "task_type": TaskType.CODE_EXPLANATION,
            "priority": "balanced"
        },
        {
            "name": "関数説明",
            "prompt": "Explain this function: def greet(name): return f'Hello, {name}!'",
            "task_type": TaskType.CODE_EXPLANATION,
            "priority": "balanced"
        },
        
        # デバッグテスト
        {
            "name": "Python構文エラー修正",
            "prompt": "Fix this Python code: for i in range(5) print(i)",
            "task_type": TaskType.DEBUGGING,
            "priority": "speed"
        },
        {
            "name": "論理エラー修正",
            "prompt": "Fix this code: def is_odd(n): return n % 2 == 0",
            "task_type": TaskType.DEBUGGING,
            "priority": "balanced"
        },
        
        # リファクタリングテスト
        {
            "name": "コード最適化",
            "prompt": "Improve this code: def sum_list(lst): total = 0; for item in lst: total += item; return total",
            "task_type": TaskType.REFACTORING,
            "priority": "balanced"
        },
        
        # 高速レスポンステスト
        {
            "name": "クイック補完1",
            "prompt": "Complete: def hello():",
            "task_type": TaskType.QUICK_RESPONSE,
            "priority": "speed"
        },
        {
            "name": "クイック補完2", 
            "prompt": "Complete: import os; path = os.path.",
            "task_type": TaskType.QUICK_RESPONSE,
            "priority": "speed"
        },
        
        # 複雑分析テスト
        {
            "name": "アルゴリズム分析",
            "prompt": "Analyze bubble sort time complexity",
            "task_type": TaskType.COMPLEX_ANALYSIS,
            "priority": "quality"
        },
        {
            "name": "設計パターン説明",
            "prompt": "Explain Factory pattern briefly",
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
            # 正しいメソッド名：generate_code を使用
            response = client.generate_code(
                prompt=test_case['prompt'],
                task_type=test_case['task_type'],
                priority=test_case['priority']
            )
            
            duration = time.time() - start_time
            
            if response['success']:
                print(f"   ✅ 成功 ({duration:.1f}s)")
                print(f"   🤖 使用モデル: {response['model']}")
                print(f"   📝 応答: {response['response'][:100]}{'...' if len(response['response']) > 100 else ''}")
                
                results.append({
                    'name': test_case['name'],
                    'success': True,
                    'duration': duration,
                    'model': response['model'],
                    'task_type': test_case['task_type'].value,
                    'priority': test_case['priority'],
                    'content_length': len(response['response']),
                    'response_time': response.get('response_time', duration)
                })
            else:
                print(f"   ❌ 失敗: {response['error']}")
                results.append({
                    'name': test_case['name'],
                    'success': False,
                    'duration': duration,
                    'error': response['error'],
                    'task_type': test_case['task_type'].value,
                    'priority': test_case['priority'],
                    'model': response.get('model', 'unknown')
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
    
    if successful_tests:
        avg_duration = sum(r['duration'] for r in successful_tests) / len(successful_tests)
        avg_content_length = sum(r['content_length'] for r in successful_tests) / len(successful_tests)
        avg_response_time = sum(r['response_time'] for r in successful_tests) / len(successful_tests)
        print(f"   平均応答時間: {avg_duration:.1f}秒")
        print(f"   平均LLM応答時間: {avg_response_time:.1f}秒")
        print(f"   平均応答長: {avg_content_length:.0f}文字")
    else:
        print("   平均応答時間: N/A")
    
    # 成功テスト詳細
    if successful_tests:
        print(f"\n✅ 成功したテスト ({len(successful_tests)}個):")
        for result in successful_tests:
            print(f"   • {result['name']}: {result['duration']:.1f}s ({result['model']}) - {result['content_length']}文字")
    
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
            task_types[task_type] = {'total': 0, 'success': 0, 'avg_time': []}
        task_types[task_type]['total'] += 1
        if result['success']:
            task_types[task_type]['success'] += 1
            task_types[task_type]['avg_time'].append(result['duration'])
    
    for task_type, stats in task_types.items():
        success_rate = stats['success'] / stats['total'] * 100
        avg_time = sum(stats['avg_time']) / len(stats['avg_time']) if stats['avg_time'] else 0
        print(f"   • {task_type}: {stats['success']}/{stats['total']} ({success_rate:.1f}%) - 平均{avg_time:.1f}s")
    
    # 優先度別分析
    print(f"\n⚡ 優先度別平均応答時間:")
    priorities = {}
    for result in successful_tests:
        priority = result['priority']
        if priority not in priorities:
            priorities[priority] = []
        priorities[priority].append(result['duration'])
    
    for priority, durations in priorities.items():
        if durations:
            avg_duration = sum(durations) / len(durations)
            print(f"   • {priority}: {avg_duration:.1f}秒 (サンプル数: {len(durations)})")
    
    # モデル使用統計
    print(f"\n🤖 モデル使用統計:")
    model_usage = {}
    total_chars = {}
    for result in successful_tests:
        model = result['model']
        model_usage[model] = model_usage.get(model, 0) + 1
        total_chars[model] = total_chars.get(model, 0) + result['content_length']
    
    for model, count in sorted(model_usage.items(), key=lambda x: x[1], reverse=True):
        avg_chars = total_chars[model] / count if count > 0 else 0
        print(f"   • {model}: {count}回 (平均{avg_chars:.0f}文字/回)")
    
    # 性能評価
    print(f"\n🏆 性能評価:")
    if successful_tests:
        fastest_test = min(successful_tests, key=lambda x: x['duration'])
        slowest_test = max(successful_tests, key=lambda x: x['duration'])
        longest_response = max(successful_tests, key=lambda x: x['content_length'])
        
        print(f"   • 最速テスト: {fastest_test['name']} ({fastest_test['duration']:.1f}s)")
        print(f"   • 最遅テスト: {slowest_test['name']} ({slowest_test['duration']:.1f}s)")
        print(f"   • 最長応答: {longest_response['name']} ({longest_response['content_length']}文字)")
    
    # クライアントの性能レポート
    print(f"\n📊 クライアント性能レポート:")
    perf_report = client.get_performance_report()
    for key, value in perf_report.items():
        print(f"   • {key}: {value}")
    
    print_section("統合テスト完了")
    
    return {
        'total_tests': len(results),
        'successful_tests': len(successful_tests),
        'success_rate': len(successful_tests) / len(results) * 100,
        'total_duration': total_duration,
        'results': results,
        'performance_report': perf_report
    }

if __name__ == "__main__":
    # 実行
    final_results = run_comprehensive_tests()
    
    # 最終サマリー
    print(f"\n🎯 最終結果サマリー:")
    print(f"   • 総テスト数: {final_results['total_tests']}")
    print(f"   • 成功数: {final_results['successful_tests']}")
    print(f"   • 成功率: {final_results['success_rate']:.1f}%")
    print(f"   • 総実行時間: {final_results['total_duration']:.1f}秒")


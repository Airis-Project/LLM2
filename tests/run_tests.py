# tests/run_tests.py
"""
Test Runner Script
テスト実行スクリプト
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Any

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """テスト実行クラス"""
    
    def __init__(self):
        self.project_root = project_root
        self.test_results = {}
        
    def run_unit_tests(self, coverage: bool = False) -> bool:
        """ユニットテストを実行"""
        print("\n🧪 Running Unit Tests...")
        print("=" * 50)
        
        cmd = ["python", "-m", "pytest", "tests/", "-v"]
        
        # 統合テストとE2Eテストを除外
        cmd.extend(["-m", "not integration and not slow"])
        
        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-report=xml"
            ])
        
        result = subprocess.run(cmd, cwd=self.project_root)
        success = result.returncode == 0
        
        self.test_results["unit_tests"] = {
            "success": success,
            "command": " ".join(cmd),
            "timestamp": time.time()
        }
        
        if success:
            print("✅ Unit tests passed!")
        else:
            print("❌ Unit tests failed!")
        
        return success
    
    def run_integration_tests(self) -> bool:
        """統合テストを実行"""
        print("\n🔗 Running Integration Tests...")
        print("=" * 50)
        
        cmd = [
            "python", "-m", "pytest", 
            "tests/test_integration.py", 
            "-v", "-m", "integration"
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root)
        success = result.returncode == 0
        
        self.test_results["integration_tests"] = {
            "success": success,
            "command": " ".join(cmd),
            "timestamp": time.time()
        }
        
        if success:
            print("✅ Integration tests passed!")
        else:
            print("❌ Integration tests failed!")
        
        return success
    
    def run_e2e_tests(self) -> bool:
        """E2Eテストを実行"""
        print("\n🎯 Running End-to-End Tests...")
        print("=" * 50)
        
        cmd = [
            "python", "-m", "pytest", 
            "tests/test_e2e.py", 
            "-v", "-s"
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root)
        success = result.returncode == 0
        
        self.test_results["e2e_tests"] = {
            "success": success,
            "command": " ".join(cmd),
            "timestamp": time.time()
        }
        
        if success:
            print("✅ E2E tests passed!")
        else:
            print("❌ E2E tests failed!")
        
        return success
    
    def run_performance_tests(self) -> bool:
        """パフォーマンステストを実行"""
        print("\n⚡ Running Performance Tests...")
        print("=" * 50)
        
        cmd = [
            "python", "-m", "pytest", 
            "tests/", "-v", "-m", "slow"
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root)
        success = result.returncode == 0
        
        self.test_results["performance_tests"] = {
            "success": success,
            "command": " ".join(cmd),
            "timestamp": time.time()
        }
        
        if success:
            print("✅ Performance tests passed!")
        else:
            print("❌ Performance tests failed!")
        
        return success
    
    def run_api_tests(self) -> bool:
        """APIテストを実行（APIキーが利用可能な場合のみ）"""
        if not os.getenv('OPENAI_API_KEY'):
            print("\n🔑 Skipping API Tests (No API key available)")
            self.test_results["api_tests"] = {
                "success": True,
                "skipped": True,
                "reason": "No API key available"
            }
            return True
        
        print("\n🌐 Running API Tests...")
        print("=" * 50)
        
        cmd = [
            "python", "-m", "pytest", 
            "tests/", "-v", "-m", "requires_api_key"
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root)
        success = result.returncode == 0
        
        self.test_results["api_tests"] = {
            "success": success,
            "command": " ".join(cmd),
            "timestamp": time.time()
        }
        
        if success:
            print("✅ API tests passed!")
        else:
            print("❌ API tests failed!")
        
        return success
    
    def run_linting(self) -> bool:
        """リンティングを実行"""
        print("\n🔍 Running Code Quality Checks...")
        print("=" * 50)
        
        # Flake8
        print("Running Flake8...")
        flake8_result = subprocess.run([
            "python", "-m", "flake8", "src/", "tests/", "scripts/",
            "--max-line-length=88",
            "--extend-ignore=E203,W503"
        ], cwd=self.project_root)
        
        # Black check
        print("Running Black check...")
        black_result = subprocess.run([
            "python", "-m", "black", "--check", "src/", "tests/", "scripts/"
        ], cwd=self.project_root)
        
        success = flake8_result.returncode == 0 and black_result.returncode == 0
        
        self.test_results["linting"] = {
            "success": success,
            "flake8_success": flake8_result.returncode == 0,
            "black_success": black_result.returncode == 0,
            "timestamp": time.time()
        }
        
        if success:
            print("✅ Code quality checks passed!")
        else:
            print("❌ Code quality checks failed!")
        
        return success
    
    def run_security_tests(self) -> bool:
        """セキュリティテストを実行"""
        print("\n🔒 Running Security Tests...")
        print("=" * 50)
        
        # Bandit (セキュリティ脆弱性チェック)
        try:
            result = subprocess.run([
                "python", "-m", "bandit", "-r", "src/", "-f", "json"
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ No security issues found!")
                success = True
            else:
                print("⚠️  Security issues detected!")
                print(result.stdout)
                success = False
                
        except FileNotFoundError:
            print("⚠️  Bandit not installed, skipping security tests")
            success = True  # Banditがない場合はスキップ
        
        self.test_results["security_tests"] = {
            "success": success,
            "timestamp": time.time()
        }
        
        return success
    
    def generate_test_report(self) -> Dict[str, Any]:
        """テストレポートを生成"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() 
                          if result.get("success", False))
        
        report = {
            "summary": {
                "total_test_suites": total_tests,
                "passed_test_suites": passed_tests,
                "failed_test_suites": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "timestamp": time.time()
            },
            "details": self.test_results
        }
        
        return report
    
    def save_test_report(self, filepath: str):
        """テストレポートをファイルに保存"""
        report = self.generate_test_report()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 Test report saved to: {filepath}")
    
    def print_summary(self):
        """テスト結果のサマリーを表示"""
        print("\n" + "="*60)
        print("🎯 TEST EXECUTION SUMMARY")
        print("="*60)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            
            if result.get("skipped"):
                status = "⏭️  SKIP"
            
            print(f"{status} {test_name.replace('_', ' ').title()}")
            
            if "reason" in result:
                print(f"      Reason: {result['reason']}")
        
        report = self.generate_test_report()
        summary = report["summary"]
        
        print(f"\nOverall Success Rate: {summary['success_rate']:.1f}%")
        print(f"Passed: {summary['passed_test_suites']}/{summary['total_test_suites']}")
        
        if summary['success_rate'] == 100:
            print("\n🎉 All tests passed! System is ready for deployment.")
        else:
            print("\n⚠️  Some tests failed. Please review the results above.")
    
    def run_all_tests(self, coverage: bool = False, include_slow: bool = False) -> bool:
        """すべてのテストを実行"""
        print("\n🚀 Starting Complete Test Suite")
        print("="*60)
        
        start_time = time.time()
        
        # テスト実行順序
        test_sequence = [
            ("Linting", self.run_linting),
            ("Unit Tests", lambda: self.run_unit_tests(coverage=coverage)),
            ("Integration Tests", self.run_integration_tests),
            ("Security Tests", self.run_security_tests),
            ("API Tests", self.run_api_tests),
        ]
        
        if include_slow:
            test_sequence.extend([
                ("Performance Tests", self.run_performance_tests),
                ("E2E Tests", self.run_e2e_tests),
            ])
        
        # テスト実行
        all_passed = True
        for test_name, test_func in test_sequence:
            print(f"\n⏳ Starting {test_name}...")
            success = test_func()
            if not success:
                all_passed = False
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 結果サマリー
        self.print_summary()
        print(f"\n⏱️  Total execution time: {execution_time:.2f} seconds")
        
        # レポート保存
        report_path = self.project_root / "test_report.json"
        self.save_test_report(str(report_path))
        
        return all_passed


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM Chat System Test Runner")
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run tests with coverage reporting"
    )
    parser.add_argument(
        "--unit-only", "-u",
        action="store_true",
        help="Run unit tests only"
    )
    parser.add_argument(
        "--integration-only", "-i",
        action="store_true",
        help="Run integration tests only"
    )
    parser.add_argument(
        "--e2e-only", "-e",
        action="store_true",
        help="Run E2E tests only"
    )
    parser.add_argument(
        "--include-slow", "-s",
        action="store_true",
        help="Include slow tests (performance and E2E)"
    )
    parser.add_argument(
        "--lint-only", "-l",
        action="store_true",
        help="Run linting only"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # 個別テスト実行
    if args.unit_only:
        success = runner.run_unit_tests(coverage=args.coverage)
    elif args.integration_only:
        success = runner.run_integration_tests()
    elif args.e2e_only:
        success = runner.run_e2e_tests()
    elif args.lint_only:
        success = runner.run_linting()
    else:
        # 全テスト実行
        success = runner.run_all_tests(
            coverage=args.coverage,
            include_slow=args.include_slow
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

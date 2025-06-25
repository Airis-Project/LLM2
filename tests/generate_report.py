# tests/generate_report.py
"""
Test Report Generator
テストレポート生成スクリプト
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestReportGenerator:
    """テストレポート生成クラス"""
    
    def __init__(self):
        self.project_root = project_root
        self.report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "project_name": "LLM Chat System",
                "version": "1.0.0"
            },
            "system_info": {},
            "test_results": {},
            "coverage_info": {},
            "quality_metrics": {},
            "recommendations": []
        }
    
    def collect_system_info(self):
        """システム情報を収集"""
        import platform
        import sys
        
        self.report_data["system_info"] = {
            "platform": platform.platform(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "working_directory": str(self.project_root),
            "environment_variables": {
                "OPENAI_API_KEY": "SET" if os.getenv("OPENAI_API_KEY") else "NOT_SET",
                "ANTHROPIC_API_KEY": "SET" if os.getenv("ANTHROPIC_API_KEY") else "NOT_SET"
            }
        }
    
    def run_comprehensive_tests(self):
        """包括的なテストを実行"""
        print("🧪 Running comprehensive test suite...")
        
        # テストコマンドの定義
        test_commands = {
            "unit_tests": {
                "command": ["python", "-m", "pytest", "tests/", "-v", 
                           "-m", "not integration and not slow", 
                           "--cov=src", "--cov-report=json"],
                "description": "Unit tests with coverage"
            },
            "integration_tests": {
                "command": ["python", "-m", "pytest", "tests/test_integration.py", 
                           "-v", "-m", "integration"],
                "description": "Integration tests"
            },
            "linting": {
                "command": ["python", "-m", "flake8", "src/", "tests/", "scripts/",
                           "--max-line-length=88", "--extend-ignore=E203,W503"],
                "description": "Code style checking"
            },
            "security": {
                "command": ["python", "-m", "bandit", "-r", "src/", "-f", "json"],
                "description": "Security vulnerability scanning"
            }
        }
        
        # 各テストを実行
        for test_name, test_config in test_commands.items():
            print(f"\n📋 Running {test_config['description']}...")
            
            start_time = time.time()
            result = subprocess.run(
                test_config["command"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            end_time = time.time()
            
            self.report_data["test_results"][test_name] = {
                "success": result.returncode == 0,
                "execution_time": end_time - start_time,
                "command": " ".join(test_config["command"]),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            
            status = "✅ PASS" if result.returncode == 0 else "❌ FAIL"
            print(f"{status} {test_name} ({end_time - start_time:.2f}s)")
    
    def collect_coverage_info(self):
        """カバレッジ情報を収集"""
        coverage_file = self.project_root / "coverage.json"
        
        if coverage_file.exists():
            try:
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                
                self.report_data["coverage_info"] = {
                    "total_coverage": coverage_data.get("totals", {}).get("percent_covered", 0),
                    "files": coverage_data.get("files", {}),
                    "summary": coverage_data.get("totals", {})
                }
            except Exception as e:
                self.report_data["coverage_info"] = {
                    "error": f"Failed to parse coverage data: {e}"
                }
        else:
            self.report_data["coverage_info"] = {
                "message": "Coverage data not available"
            }
    
    def analyze_code_quality(self):
        """コード品質を分析"""
        # ファイル数とコード行数の計算
        src_files = list((self.project_root / "src").rglob("*.py"))
        test_files = list((self.project_root / "tests").rglob("*.py"))
        
        total_lines = 0
        total_files = len(src_files)
        
        for file_path in src_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    total_lines += lines
            except Exception:
                continue
        
        self.report_data["quality_metrics"] = {
            "source_files": total_files,
            "total_lines_of_code": total_lines,
            "test_files": len(test_files),
            "average_lines_per_file": total_lines / total_files if total_files > 0 else 0,
            "test_to_source_ratio": len(test_files) / total_files if total_files > 0 else 0
        }
    
    def generate_recommendations(self):
        """推奨事項を生成"""
        recommendations = []
        
        # テスト結果に基づく推奨事項
        test_results = self.report_data["test_results"]
        
        if not test_results.get("unit_tests", {}).get("success", False):
            recommendations.append({
                "type": "critical",
                "title": "Unit Tests Failing",
                "description": "Unit tests are failing. Fix failing tests before deployment.",
                "priority": "high"
            })
        
        if not test_results.get("integration_tests", {}).get("success", False):
            recommendations.append({
                "type": "warning",
                "title": "Integration Tests Failing",
                "description": "Integration tests are failing. Check system integration.",
                "priority": "medium"
            })
        
        # カバレッジに基づく推奨事項
        coverage_info = self.report_data["coverage_info"]
        if isinstance(coverage_info.get("total_coverage"), (int, float)):
            coverage = coverage_info["total_coverage"]
            if coverage < 80:
                recommendations.append({
                    "type": "improvement",
                    "title": "Low Test Coverage",
                    "description": f"Test coverage is {coverage:.1f}%. Aim for at least 80%.",
                    "priority": "medium"
                })
            elif coverage >= 90:
                recommendations.append({
                    "type": "success",
                    "title": "Excellent Test Coverage",
                    "description": f"Test coverage is {coverage:.1f}%. Great job!",
                    "priority": "low"
                })
        
        # コード品質に基づく推奨事項
        quality_metrics = self.report_data["quality_metrics"]
        avg_lines = quality_metrics.get("average_lines_per_file", 0)
        
        if avg_lines > 300:
            recommendations.append({
                "type": "improvement",
                "title": "Large Files Detected",
                "description": f"Average file size is {avg_lines:.0f} lines. Consider breaking down large files.",
                "priority": "low"
            })
        
        test_ratio = quality_metrics.get("test_to_source_ratio", 0)
        if test_ratio < 0.5:
            recommendations.append({
                "type": "improvement",
                "title": "Low Test File Ratio",
                "description": f"Test-to-source file ratio is {test_ratio:.2f}. Consider adding more test files.",
                "priority": "medium"
            })
        
        # 環境に基づく推奨事項
        env_vars = self.report_data["system_info"]["environment_variables"]
        if env_vars.get("OPENAI_API_KEY") == "NOT_SET":
            recommendations.append({
                "type": "warning",
                "title": "Missing API Key",
                "description": "OPENAI_API_KEY is not set. Some features may not work.",
                "priority": "medium"
            })
        
        self.report_data["recommendations"] = recommendations
    
    def generate_html_report(self, output_path: str):
        """HTMLレポートを生成"""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Chat System - Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .success { background-color: #d4edda; border-color: #c3e6cb; }
        .warning { background-color: #fff3cd; border-color: #ffeaa7; }
        .error { background-color: #f8d7da; border-color: #f5c6cb; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #f8f9fa; border-radius: 3px; }
        .recommendation { margin: 10px 0; padding: 10px; border-left: 4px solid #007bff; background: #f8f9fa; }
        .critical { border-left-color: #dc3545; }
        .warning-rec { border-left-color: #ffc107; }
        .improvement { border-left-color: #17a2b8; }
        .success-rec { border-left-color: #28a745; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .status-pass { color: #28a745; font-weight: bold; }
        .status-fail { color: #dc3545; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 LLM Chat System - Test Report</h1>
        <p>Generated on: {generated_at}</p>
        <p>Project Version: {version}</p>
    </div>

    <div class="section">
        <h2>📊 Test Results Summary</h2>
        <div class="metric">
            <strong>Total Test Suites:</strong> {total_suites}
        </div>
        <div class="metric">
            <strong>Passed:</strong> <span class="status-pass">{passed_suites}</span>
        </div>
        <div class="metric">
            <strong>Failed:</strong> <span class="status-fail">{failed_suites}</span>
        </div>
        <div class="metric">
            <strong>Success Rate:</strong> {success_rate:.1f}%
        </div>
    </div>

    <div class="section">
        <h2>🧪 Detailed Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Suite</th>
                    <th>Status</th>
                    <th>Execution Time</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                {test_rows}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>📈 Coverage Information</h2>
        {coverage_section}
    </div>

    <div class="section">
        <h2>📏 Quality Metrics</h2>
        <div class="metric">
            <strong>Source Files:</strong> {source_files}
        </div>
        <div class="metric">
            <strong>Test Files:</strong> {test_files}
        </div>
        <div class="metric">
            <strong>Lines of Code:</strong> {total_lines}
        </div>
        <div class="metric">
            <strong>Test Coverage:</strong> {coverage_percent}%
        </div>
    </div>

    <div class="section">
        <h2>💡 Recommendations</h2>
        {recommendations_section}
    </div>

    <div class="section">
        <h2>🖥️ System Information</h2>
        <p><strong>Platform:</strong> {platform}</p>
        <p><strong>Python Version:</strong> {python_version}</p>
        <p><strong>Working Directory:</strong> {working_directory}</p>
    </div>
</body>
</html>
        """
        
        # データの準備
        test_results = self.report_data["test_results"]
        total_suites = len(test_results)
        passed_suites = sum(1 for result in test_results.values() if result.get("success", False))
        failed_suites = total_suites - passed_suites
        success_rate = (passed_suites / total_suites * 100) if total_suites > 0 else 0
        
        # テスト結果テーブルの生成
        test_rows = ""
        for test_name, result in test_results.items():
            status = "PASS" if result.get("success", False) else "FAIL"
            status_class = "status-pass" if result.get("success", False) else "status-fail"
            execution_time = f"{result.get('execution_time', 0):.2f}s"
            
            test_rows += f"""
                <tr>
                    <td>{test_name.replace('_', ' ').title()}</td>
                    <td><span class="{status_class}">{status}</span></td>
                    <td>{execution_time}</td>
                    <td>Return Code: {result.get('return_code', 'N/A')}</td>
                </tr>
            """
        
        # カバレッジセクションの生成
        coverage_info = self.report_data["coverage_info"]
        if "total_coverage" in coverage_info:
            coverage_section = f"""
                <div class="metric">
                    <strong>Total Coverage:</strong> {coverage_info['total_coverage']:.1f}%
                </div>
            """
        else:
            coverage_section = "<p>Coverage information not available</p>"
        
        # 推奨事項セクションの生成
        recommendations_section = ""
        for rec in self.report_data["recommendations"]:
            rec_class = {
                "critical": "critical",
                "warning": "warning-rec",
                "improvement": "improvement",
                "success": "success-rec"
            }.get(rec["type"], "improvement")
            
            recommendations_section += f"""
                <div class="recommendation {rec_class}">
                    <h4>{rec['title']}</h4>
                    <p>{rec['description']}</p>
                    <small>Priority: {rec['priority']}</small>
                </div>
            """
        
        # HTMLの生成
        html_content = html_template.format(
            generated_at=self.report_data["metadata"]["generated_at"],
            version=self.report_data["metadata"]["version"],
            total_suites=total_suites,
            passed_suites=passed_suites,
            failed_suites=failed_suites,
            success_rate=success_rate,
            test_rows=test_rows,
            coverage_section=coverage_section,
            coverage_percent=coverage_info.get("total_coverage", 0),
            source_files=self.report_data["quality_metrics"].get("source_files", 0),
            test_files=self.report_data["quality_metrics"].get("test_files", 0),
            total_lines=self.report_data["quality_metrics"].get("total_lines_of_code", 0),
            recommendations_section=recommendations_section,
            platform=self.report_data["system_info"]["platform"],
            python_version=self.report_data["system_info"]["python_version"],
            working_directory=self.report_data["system_info"]["working_directory"]
        )
        
        # ファイルに保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def generate_full_report(self):
        """完全なレポートを生成"""
        print("📊 Generating comprehensive test report...")
        
        # 1. システム情報収集
        self.collect_system_info()
        
        # 2. テスト実行
        self.run_comprehensive_tests()
        
        # 3. カバレッジ情報収集
        self.collect_coverage_info()
        
        # 4. コード品質分析
        self.analyze_code_quality()
        
        # 5. 推奨事項生成
        self.generate_recommendations()
        
        # 6. レポート保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON レポート
        json_path = self.project_root / f"test_report_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.report_data, f, indent=2, ensure_ascii=False)
        
        # HTML レポート
        html_path = self.project_root / f"test_report_{timestamp}.html"
        self.generate_html_report(str(html_path))
        
        print(f"✅ Reports generated:")
        print(f"   📄 JSON: {json_path}")
        print(f"   🌐 HTML: {html_path}")
        
        return self.report_data


def main():
    """メイン関数"""
    generator = TestReportGenerator()
    report_data = generator.generate_full_report()
    
    # 結果サマリー表示
    test_results = report_data["test_results"]
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result.get("success", False))
    
    print(f"\n🎯 Test Summary:")
    print(f"   Total Test Suites: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    # 推奨事項表示
    recommendations = report_data["recommendations"]
    if recommendations:
        print(f"\n💡 Key Recommendations:")
        for rec in recommendations[:3]:  # 上位3つを表示
            print(f"   • {rec['title']}: {rec['description']}")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

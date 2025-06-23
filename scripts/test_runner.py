#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/test_runner.py - テスト実行スクリプト

LLM Code Assistantアプリケーションのテストを自動化するスクリプト
"""

import os
import sys
import subprocess
import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

# プロジェクトルートディレクトリの設定
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

class TestError(Exception):
    """テストエラー"""
    pass

class TestRunner:
    """テストランナークラス"""
    
    def __init__(self, config: Dict):
        """
        初期化
        
        Args:
            config: テスト設定
        """
        self.config = config
        self.project_root = PROJECT_ROOT
        self.test_dir = self.project_root / "tests"
        self.reports_dir = self.project_root / "test_reports"
        
        # ログ設定
        self.setup_logging()
        
    def setup_logging(self):
        """ログ設定"""
        import logging
        
        # ログディレクトリの作成
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # ログファイル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"test_{timestamp}.log"
        
        # ロガーの設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def check_test_environment(self):
        """テスト環境のチェック"""
        self.logger.info("テスト環境をチェックしています...")
        
        # テストディレクトリの存在確認
        if not self.test_dir.exists():
            raise TestError("テストディレクトリが見つかりません")
            
        # 必要なツールの確認
        required_tools = ['python', 'pytest']
        if self.config.get('coverage', False):
            required_tools.append('coverage')
            
        for tool in required_tools:
            try:
                subprocess.run([tool, '--version'], 
                             capture_output=True, check=True)
                self.logger.debug(f"{tool}が利用可能です")
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise TestError(f"{tool}が見つかりません")
                
        self.logger.info("テスト環境のチェックが完了しました")
        
    def install_test_dependencies(self):
        """テスト依存関係のインストール"""
        self.logger.info("テスト依存関係をインストールしています...")
        
        test_requirements = [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-xdist>=3.0.0',
            'pytest-html>=3.0.0',
            'pytest-mock>=3.0.0',
            'coverage>=7.0.0'
        ]
        
        try:
            for requirement in test_requirements:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', requirement
                ], check=True, capture_output=True)
                
            self.logger.info("テスト依存関係のインストールが完了しました")
            
        except subprocess.CalledProcessError as e:
            raise TestError(f"テスト依存関係のインストールに失敗しました: {e}")
            
    def run_unit_tests(self) -> Tuple[bool, Dict]:
        """ユニットテストの実行"""
        self.logger.info("ユニットテストを実行しています...")
        
        # レポートディレクトリの作成
        self.reports_dir.mkdir(exist_ok=True)
        
        # pytestコマンドの構築
        pytest_args = [
            sys.executable, '-m', 'pytest',
            str(self.test_dir / "unit"),
            '-v',
            '--tb=short'
        ]
        
        # JUnitXMLレポートの設定
        junit_file = self.reports_dir / "junit_unit.xml"
        pytest_args.extend(['--junit-xml', str(junit_file)])
        
        # HTMLレポートの設定
        if self.config.get('html_report', True):
            html_file = self.reports_dir / "unit_report.html"
            pytest_args.extend(['--html', str(html_file), '--self-contained-html'])
            
        # カバレッジの設定
        if self.config.get('coverage', False):
            cov_file = self.reports_dir / "coverage_unit.xml"
            pytest_args.extend([
                '--cov=src',
                '--cov-report=xml:' + str(cov_file),
                '--cov-report=html:' + str(self.reports_dir / "coverage_unit_html"),
                '--cov-report=term'
            ])
            
        # 並列実行の設定
        if self.config.get('parallel', False):
            workers = self.config.get('workers', 'auto')
            pytest_args.extend(['-n', str(workers)])
            
        # テストの実行
        start_time = time.time()
        result = subprocess.run(pytest_args, cwd=self.project_root)
        end_time = time.time()
        
        # 結果の解析
        success = result.returncode == 0
        test_results = self._parse_junit_results(junit_file)
        test_results['duration'] = end_time - start_time
        test_results['type'] = 'unit'
        
        if success:
            self.logger.info(f"ユニットテストが成功しました (所要時間: {test_results['duration']:.2f}秒)")
        else:
            self.logger.error(f"ユニットテストが失敗しました (所要時間: {test_results['duration']:.2f}秒)")
            
        return success, test_results
        
    def run_integration_tests(self) -> Tuple[bool, Dict]:
        """統合テストの実行"""
        integration_dir = self.test_dir / "integration"
        if not integration_dir.exists():
            self.logger.info("統合テストディレクトリが見つかりません。スキップします。")
            return True, {'type': 'integration', 'skipped': True}
            
        self.logger.info("統合テストを実行しています...")
        
        # pytestコマンドの構築
        pytest_args = [
            sys.executable, '-m', 'pytest',
            str(integration_dir),
            '-v',
            '--tb=short'
        ]
        
        # JUnitXMLレポートの設定
        junit_file = self.reports_dir / "junit_integration.xml"
        pytest_args.extend(['--junit-xml', str(junit_file)])
        
        # HTMLレポートの設定
        if self.config.get('html_report', True):
            html_file = self.reports_dir / "integration_report.html"
            pytest_args.extend(['--html', str(html_file), '--self-contained-html'])
            
        # テストの実行
        start_time = time.time()
        result = subprocess.run(pytest_args, cwd=self.project_root)
        end_time = time.time()
        
        # 結果の解析
        success = result.returncode == 0
        test_results = self._parse_junit_results(junit_file)
        test_results['duration'] = end_time - start_time
        test_results['type'] = 'integration'
        
        if success:
            self.logger.info(f"統合テストが成功しました (所要時間: {test_results['duration']:.2f}秒)")
        else:
            self.logger.error(f"統合テストが失敗しました (所要時間: {test_results['duration']:.2f}秒)")
            
        return success, test_results
        
    def run_performance_tests(self) -> Tuple[bool, Dict]:
        """パフォーマンステストの実行"""
        performance_dir = self.test_dir / "performance"
        if not performance_dir.exists():
            self.logger.info("パフォーマンステストディレクトリが見つかりません。スキップします。")
            return True, {'type': 'performance', 'skipped': True}
            
        self.logger.info("パフォーマンステストを実行しています...")
        
        # pytestコマンドの構築
        pytest_args = [
            sys.executable, '-m', 'pytest',
            str(performance_dir),
            '-v',
            '--tb=short',
            '--benchmark-only'
        ]
        
        # ベンチマークレポートの設定
        benchmark_file = self.reports_dir / "benchmark.json"
        pytest_args.extend(['--benchmark-json', str(benchmark_file)])
        
        # JUnitXMLレポートの設定
        junit_file = self.reports_dir / "junit_performance.xml"
        pytest_args.extend(['--junit-xml', str(junit_file)])
        
        # テストの実行
        start_time = time.time()
        result = subprocess.run(pytest_args, cwd=self.project_root)
        end_time = time.time()
        
        # 結果の解析
        success = result.returncode == 0
        test_results = self._parse_junit_results(junit_file)
        test_results['duration'] = end_time - start_time
        test_results['type'] = 'performance'
        
        # ベンチマーク結果の追加
        if benchmark_file.exists():
            try:
                with open(benchmark_file, 'r', encoding='utf-8') as f:
                    benchmark_data = json.load(f)
                    test_results['benchmarks'] = benchmark_data
            except Exception as e:
                self.logger.warning(f"ベンチマーク結果の読み込みに失敗しました: {e}")
                
        if success:
            self.logger.info(f"パフォーマンステストが成功しました (所要時間: {test_results['duration']:.2f}秒)")
        else:
            self.logger.error(f"パフォーマンステストが失敗しました (所要時間: {test_results['duration']:.2f}秒)")
            
        return success, test_results
        
    def run_linting(self) -> Tuple[bool, Dict]:
        """リンティングの実行"""
        if not self.config.get('linting', True):
            self.logger.info("リンティングをスキップします")
            return True, {'type': 'linting', 'skipped': True}
            
        self.logger.info("リンティングを実行しています...")
        
        results = {}
        overall_success = True
        
        # flake8の実行
        if self.config.get('flake8', True):
            success, result = self._run_flake8()
            results['flake8'] = result
            overall_success &= success
            
        # pylintの実行
        if self.config.get('pylint', True):
            success, result = self._run_pylint()
            results['pylint'] = result
            overall_success &= success
            
        # mypyの実行
        if self.config.get('mypy', True):
            success, result = self._run_mypy()
            results['mypy'] = result
            overall_success &= success
            
        return overall_success, {'type': 'linting', 'results': results}
        
    def _run_flake8(self) -> Tuple[bool, Dict]:
        """flake8の実行"""
        self.logger.info("flake8を実行しています...")
        
        output_file = self.reports_dir / "flake8.txt"
        
        try:
            result = subprocess.run([
                'flake8', 'src', '--output-file', str(output_file)
            ], cwd=self.project_root, capture_output=True, text=True)
            
            success = result.returncode == 0
            
            return success, {
                'success': success,
                'output_file': str(output_file),
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except FileNotFoundError:
            self.logger.warning("flake8が見つかりません。スキップします。")
            return True, {'skipped': True}
            
    def _run_pylint(self) -> Tuple[bool, Dict]:
        """pylintの実行"""
        self.logger.info("pylintを実行しています...")
        
        output_file = self.reports_dir / "pylint.txt"
        
        try:
            result = subprocess.run([
                'pylint', 'src', '--output', str(output_file)
            ], cwd=self.project_root, capture_output=True, text=True)
            
            # pylintは警告があっても0以外を返すため、より柔軟に判定
            success = result.returncode < 4  # fatal error以外は成功とみなす
            
            return success, {
                'success': success,
                'output_file': str(output_file),
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
            
        except FileNotFoundError:
            self.logger.warning("pylintが見つかりません。スキップします。")
            return True, {'skipped': True}
            
    def _run_mypy(self) -> Tuple[bool, Dict]:
        """mypyの実行"""
        self.logger.info("mypyを実行しています...")
        
        output_file = self.reports_dir / "mypy.txt"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                result = subprocess.run([
                    'mypy', 'src'
                ], cwd=self.project_root, stdout=f, stderr=subprocess.STDOUT, text=True)
                
            success = result.returncode == 0
            
            return success, {
                'success': success,
                'output_file': str(output_file),
                'return_code': result.returncode
            }
            
        except FileNotFoundError:
            self.logger.warning("mypyが見つかりません。スキップします。")
            return True, {'skipped': True}
            
    def _parse_junit_results(self, junit_file: Path) -> Dict:
        """JUnitXML結果の解析"""
        if not junit_file.exists():
            return {'error': 'JUnitXMLファイルが見つかりません'}
            
        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            # テストスイート情報の取得
            testsuite = root.find('testsuite') or root
            
            return {
                'tests': int(testsuite.get('tests', 0)),
                'failures': int(testsuite.get('failures', 0)),
                'errors': int(testsuite.get('errors', 0)),
                'skipped': int(testsuite.get('skipped', 0)),
                'time': float(testsuite.get('time', 0.0))
            }
            
        except Exception as e:
            self.logger.error(f"JUnitXML解析エラー: {e}")
            return {'error': str(e)}
            
    def generate_summary_report(self, results: List[Tuple[bool, Dict]]):
        """サマリーレポートの生成"""
        self.logger.info("サマリーレポートを生成しています...")
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'overall_success': all(success for success, _ in results),
            'total_duration': sum(
                result.get('duration', 0) 
                for _, result in results 
                if 'duration' in result
            ),
            'results': [result for _, result in results]
        }
        
        # JSONレポートの作成
        json_report = self.reports_dir / "test_summary.json"
        with open(json_report, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
            
        # テキストレポートの作成
        text_report = self.reports_dir / "test_summary.txt"
        with open(text_report, 'w', encoding='utf-8') as f:
            f.write("=== LLM Code Assistant テスト結果サマリー ===\n\n")
            f.write(f"実行日時: {summary['timestamp']}\n")
            f.write(f"総合結果: {'成功' if summary['overall_success'] else '失敗'}\n")
            f.write(f"総実行時間: {summary['total_duration']:.2f}秒\n\n")
            
            for result in summary['results']:
                test_type = result.get('type', 'unknown')
                f.write(f"=== {test_type.upper()} ===\n")
                
                if result.get('skipped'):
                    f.write("スキップされました\n\n")
                    continue
                    
                if 'tests' in result:
                    f.write(f"テスト数: {result['tests']}\n")
                    f.write(f"失敗: {result['failures']}\n")
                    f.write(f"エラー: {result['errors']}\n")
                    f.write(f"スキップ: {result['skipped']}\n")
                    f.write(f"実行時間: {result.get('duration', 0):.2f}秒\n")
                    
                f.write("\n")
                
        self.logger.info(f"サマリーレポートを作成しました: {json_report}, {text_report}")
        
    def run_all_tests(self):
        """すべてのテストの実行"""
        try:
            self.logger.info("テスト実行を開始します...")
            start_time = datetime.now()
            
            # 環境チェック
            self.check_test_environment()
            
            if self.config.get('install_deps', True):
                self.install_test_dependencies()
                
            # テストの実行
            results = []
            
            # ユニットテスト
            if self.config.get('unit_tests', True):
                success, result = self.run_unit_tests()
                results.append((success, result))
                
            # 統合テスト
            if self.config.get('integration_tests', True):
                success, result = self.run_integration_tests()
                results.append((success, result))
                
            # パフォーマンステスト
            if self.config.get('performance_tests', False):
                success, result = self.run_performance_tests()
                results.append((success, result))
                
            # リンティング
            success, result = self.run_linting()
            results.append((success, result))
            
            # サマリーレポートの生成
            self.generate_summary_report(results)
            
            # 結果の判定
            overall_success = all(success for success, _ in results)
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            if overall_success:
                self.logger.info(f"すべてのテストが成功しました (所要時間: {duration})")
            else:
                self.logger.error(f"一部のテストが失敗しました (所要時間: {duration})")
                sys.exit(1)
                
        except TestError as e:
            self.logger.error(f"テストエラー: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}")
            sys.exit(1)

def load_config(config_file: Optional[str] = None) -> Dict:
    """設定ファイルの読み込み"""
    if config_file and Path(config_file).exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # デフォルト設定
    return {
        'install_deps': True,
        'unit_tests': True,
        'integration_tests': True,
        'performance_tests': False,
        'linting': True,
        'flake8': True,
        'pylint': True,
        'mypy': True,
        'coverage': True,
        'html_report': True,
        'parallel': False,
        'workers': 'auto'
    }

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='LLM Code Assistant テストスクリプト')
    parser.add_argument('--config', '-c', help='設定ファイルのパス')
    parser.add_argument('--unit-only', action='store_true', 
                       help='ユニットテストのみ実行')
    parser.add_argument('--integration-only', action='store_true',
                       help='統合テストのみ実行')
    parser.add_argument('--performance-only', action='store_true',
                       help='パフォーマンステストのみ実行')
    parser.add_argument('--no-linting', action='store_true',
                       help='リンティングをスキップ')
    parser.add_argument('--no-coverage', action='store_true',
                       help='カバレッジをスキップ')
    parser.add_argument('--parallel', '-p', action='store_true',
                       help='並列実行を有効化')
    parser.add_argument('--workers', '-w', type=str, default='auto',
                       help='並列実行時のワーカー数')
    
    args = parser.parse_args()
    
    # 設定の読み込み
    config = load_config(args.config)
    
    # コマンドライン引数による設定の上書き
    if args.unit_only:
        config.update({
            'unit_tests': True,
            'integration_tests': False,
            'performance_tests': False,
            'linting': False
        })
    elif args.integration_only:
        config.update({
            'unit_tests': False,
            'integration_tests': True,
            'performance_tests': False,
            'linting': False
        })
    elif args.performance_only:
        config.update({
            'unit_tests': False,
            'integration_tests': False,
            'performance_tests': True,
            'linting': False
        })
        
    if args.no_linting:
        config['linting'] = False
    if args.no_coverage:
        config['coverage'] = False
    if args.parallel:
        config['parallel'] = True
        config['workers'] = args.workers
        
    # テストの実行
    runner = TestRunner(config)
    runner.run_all_tests()

if __name__ == '__main__':
    main()

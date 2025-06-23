#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build.py - ビルドスクリプト

LLM Code Assistantアプリケーションのビルドを自動化するスクリプト
"""

import os
import sys
import shutil
import subprocess
import argparse
import json
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# プロジェクトルートディレクトリの設定
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

class BuildError(Exception):
    """ビルドエラー"""
    pass

class Builder:
    """ビルダークラス"""
    
    def __init__(self, config: Dict):
        """
        初期化
        
        Args:
            config: ビルド設定
        """
        self.config = config
        self.project_root = PROJECT_ROOT
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.temp_dir = self.project_root / "temp"
        
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
        log_file = log_dir / f"build_{timestamp}.log"
        
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
        
    def clean(self):
        """クリーンアップ"""
        self.logger.info("クリーンアップを開始します...")
        
        # 既存のビルドディレクトリを削除
        for directory in [self.build_dir, self.dist_dir, self.temp_dir]:
            if directory.exists():
                self.logger.info(f"ディレクトリを削除: {directory}")
                shutil.rmtree(directory)
        
        # __pycache__ディレクトリを削除
        self._remove_pycache()
        
        self.logger.info("クリーンアップが完了しました")
        
    def _remove_pycache(self):
        """__pycache__ディレクトリを削除"""
        for root, dirs, files in os.walk(self.project_root):
            if '__pycache__' in dirs:
                pycache_path = Path(root) / '__pycache__'
                self.logger.debug(f"__pycache__を削除: {pycache_path}")
                shutil.rmtree(pycache_path)
                dirs.remove('__pycache__')
                
    def check_dependencies(self):
        """依存関係のチェック"""
        self.logger.info("依存関係をチェックしています...")
        
        # requirements.txtの存在確認
        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            raise BuildError("requirements.txtが見つかりません")
            
        # 必要なツールの確認
        required_tools = ['pip', 'python']
        if self.config.get('build_type') == 'executable':
            required_tools.append('pyinstaller')
            
        for tool in required_tools:
            try:
                subprocess.run([tool, '--version'], 
                             capture_output=True, check=True)
                self.logger.debug(f"{tool}が利用可能です")
            except (subprocess.CalledProcessError, FileNotFoundError):
                raise BuildError(f"{tool}が見つかりません")
                
        self.logger.info("依存関係のチェックが完了しました")
        
    def install_dependencies(self):
        """依存関係のインストール"""
        self.logger.info("依存関係をインストールしています...")
        
        requirements_file = self.project_root / "requirements.txt"
        
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 
                str(requirements_file)
            ], check=True)
            
            self.logger.info("依存関係のインストールが完了しました")
            
        except subprocess.CalledProcessError as e:
            raise BuildError(f"依存関係のインストールに失敗しました: {e}")
            
    def run_tests(self):
        """テストの実行"""
        if not self.config.get('run_tests', True):
            self.logger.info("テストをスキップします")
            return
            
        self.logger.info("テストを実行しています...")
        
        test_dir = self.project_root / "tests"
        if not test_dir.exists():
            self.logger.warning("テストディレクトリが見つかりません")
            return
            
        try:
            # pytestを使用してテストを実行
            subprocess.run([
                sys.executable, '-m', 'pytest', 
                str(test_dir), '-v'
            ], check=True, cwd=self.project_root)
            
            self.logger.info("すべてのテストが成功しました")
            
        except subprocess.CalledProcessError as e:
            if self.config.get('fail_on_test_error', True):
                raise BuildError(f"テストが失敗しました: {e}")
            else:
                self.logger.warning(f"テストが失敗しましたが、ビルドを続行します: {e}")
                
    def build_application(self):
        """アプリケーションのビルド"""
        self.logger.info("アプリケーションをビルドしています...")
        
        # ビルドディレクトリの作成
        self.build_dir.mkdir(exist_ok=True)
        
        build_type = self.config.get('build_type', 'source')
        
        if build_type == 'source':
            self._build_source_distribution()
        elif build_type == 'executable':
            self._build_executable()
        elif build_type == 'wheel':
            self._build_wheel()
        else:
            raise BuildError(f"不明なビルドタイプ: {build_type}")
            
        self.logger.info("アプリケーションのビルドが完了しました")
        
    def _build_source_distribution(self):
        """ソース配布版のビルド"""
        self.logger.info("ソース配布版をビルドしています...")
        
        # 配布用ディレクトリの作成
        dist_name = f"llm-code-assistant-{self.config.get('version', '1.0.0')}"
        dist_path = self.build_dir / dist_name
        dist_path.mkdir(exist_ok=True)
        
        # ファイルのコピー
        self._copy_source_files(dist_path)
        
        # ZIPファイルの作成
        zip_path = self.dist_dir / f"{dist_name}.zip"
        self.dist_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(dist_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(self.build_dir)
                    zipf.write(file_path, arcname)
                    
        self.logger.info(f"ソース配布版を作成しました: {zip_path}")
        
    def _build_executable(self):
        """実行可能ファイルのビルド"""
        self.logger.info("実行可能ファイルをビルドしています...")
        
        main_script = self.project_root / "src" / "main.py"
        if not main_script.exists():
            raise BuildError("メインスクリプトが見つかりません")
            
        # PyInstallerの設定
        pyinstaller_args = [
            'pyinstaller',
            '--onefile',
            '--windowed' if self.config.get('windowed', True) else '--console',
            '--name', self.config.get('app_name', 'LLMCodeAssistant'),
            '--distpath', str(self.dist_dir),
            '--workpath', str(self.temp_dir),
            '--specpath', str(self.build_dir),
        ]
        
        # アイコンの設定
        icon_path = self.project_root / "assets" / "icons" / "app_icon.ico"
        if icon_path.exists():
            pyinstaller_args.extend(['--icon', str(icon_path)])
            
        # 追加データの設定
        data_dirs = [
            ('assets', 'assets'),
            ('config', 'config'),
            ('data/templates', 'data/templates'),
        ]
        
        for src, dst in data_dirs:
            src_path = self.project_root / src
            if src_path.exists():
                pyinstaller_args.extend(['--add-data', f'{src_path}{os.pathsep}{dst}'])
                
        pyinstaller_args.append(str(main_script))
        
        try:
            subprocess.run(pyinstaller_args, check=True, cwd=self.project_root)
            self.logger.info("実行可能ファイルのビルドが完了しました")
            
        except subprocess.CalledProcessError as e:
            raise BuildError(f"実行可能ファイルのビルドに失敗しました: {e}")
            
    def _build_wheel(self):
        """Wheelパッケージのビルド"""
        self.logger.info("Wheelパッケージをビルドしています...")
        
        try:
            subprocess.run([
                sys.executable, 'setup.py', 'bdist_wheel'
            ], check=True, cwd=self.project_root)
            
            self.logger.info("Wheelパッケージのビルドが完了しました")
            
        except subprocess.CalledProcessError as e:
            raise BuildError(f"Wheelパッケージのビルドに失敗しました: {e}")
            
    def _copy_source_files(self, dest_dir: Path):
        """ソースファイルのコピー"""
        # コピー対象のディレクトリとファイル
        copy_items = [
            'src',
            'config',
            'data',
            'assets',
            'requirements.txt',
            'README.md',
            'setup.py',
            '.env.example'
        ]
        
        # 除外パターン
        exclude_patterns = [
            '__pycache__',
            '*.pyc',
            '*.pyo',
            '.git',
            '.pytest_cache',
            'build',
            'dist',
            'temp',
            'logs'
        ]
        
        for item in copy_items:
            src_path = self.project_root / item
            if src_path.exists():
                if src_path.is_dir():
                    dest_item = dest_dir / item
                    shutil.copytree(src_path, dest_item, 
                                  ignore=shutil.ignore_patterns(*exclude_patterns))
                else:
                    shutil.copy2(src_path, dest_dir / item)
                    
    def generate_checksums(self):
        """チェックサムの生成"""
        self.logger.info("チェックサムを生成しています...")
        
        if not self.dist_dir.exists():
            self.logger.warning("配布ディレクトリが見つかりません")
            return
            
        checksums = {}
        
        for file_path in self.dist_dir.glob('*'):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    content = f.read()
                    sha256_hash = hashlib.sha256(content).hexdigest()
                    checksums[file_path.name] = sha256_hash
                    
        # チェックサムファイルの作成
        checksum_file = self.dist_dir / "checksums.txt"
        with open(checksum_file, 'w', encoding='utf-8') as f:
            for filename, checksum in checksums.items():
                f.write(f"{checksum}  {filename}\n")
                
        self.logger.info(f"チェックサムファイルを作成しました: {checksum_file}")
        
    def create_build_info(self):
        """ビルド情報の作成"""
        self.logger.info("ビルド情報を作成しています...")
        
        build_info = {
            'version': self.config.get('version', '1.0.0'),
            'build_type': self.config.get('build_type', 'source'),
            'build_date': datetime.now().isoformat(),
            'python_version': sys.version,
            'platform': sys.platform,
            'config': self.config
        }
        
        # ビルド情報ファイルの作成
        build_info_file = self.dist_dir / "build_info.json"
        self.dist_dir.mkdir(exist_ok=True)
        
        with open(build_info_file, 'w', encoding='utf-8') as f:
            json.dump(build_info, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"ビルド情報ファイルを作成しました: {build_info_file}")
        
    def build(self):
        """ビルドの実行"""
        try:
            self.logger.info("ビルドを開始します...")
            start_time = datetime.now()
            
            # ビルドステップの実行
            if self.config.get('clean', True):
                self.clean()
                
            self.check_dependencies()
            
            if self.config.get('install_deps', True):
                self.install_dependencies()
                
            self.run_tests()
            self.build_application()
            self.generate_checksums()
            self.create_build_info()
            
            # ビルド完了
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.logger.info(f"ビルドが完了しました (所要時間: {duration})")
            
        except BuildError as e:
            self.logger.error(f"ビルドエラー: {e}")
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
        'version': '1.0.0',
        'app_name': 'LLMCodeAssistant',
        'build_type': 'source',
        'clean': True,
        'install_deps': True,
        'run_tests': True,
        'fail_on_test_error': True,
        'windowed': True
    }

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='LLM Code Assistant ビルドスクリプト')
    parser.add_argument('--config', '-c', help='設定ファイルのパス')
    parser.add_argument('--build-type', '-t', 
                       choices=['source', 'executable', 'wheel'],
                       help='ビルドタイプ')
    parser.add_argument('--version', '-v', help='バージョン番号')
    parser.add_argument('--no-tests', action='store_true', 
                       help='テストをスキップ')
    parser.add_argument('--no-clean', action='store_true', 
                       help='クリーンアップをスキップ')
    parser.add_argument('--console', action='store_true',
                       help='コンソールアプリケーションとしてビルド')
    
    args = parser.parse_args()
    
    # 設定の読み込み
    config = load_config(args.config)
    
    # コマンドライン引数による設定の上書き
    if args.build_type:
        config['build_type'] = args.build_type
    if args.version:
        config['version'] = args.version
    if args.no_tests:
        config['run_tests'] = False
    if args.no_clean:
        config['clean'] = False
    if args.console:
        config['windowed'] = False
        
    # ビルドの実行
    builder = Builder(config)
    builder.build()

if __name__ == '__main__':
    main()

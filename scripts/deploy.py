#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/deploy.py - デプロイメントスクリプト

LLM Code Assistantアプリケーションのデプロイメントを自動化するスクリプト
"""

import os
import sys
import shutil
import subprocess
import argparse
import json
import zipfile
import tarfile
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import tempfile

# プロジェクトルートディレクトリの設定
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

class DeploymentError(Exception):
    """デプロイメントエラー"""
    pass

class Deployer:
    """デプロイメントクラス"""
    
    def __init__(self, config: Dict):
        """
        初期化
        
        Args:
            config: デプロイメント設定
        """
        self.config = config
        self.project_root = PROJECT_ROOT
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.temp_dir = None
        
        # プラットフォーム情報
        self.platform = platform.system().lower()
        self.architecture = platform.machine().lower()
        
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
        log_file = log_dir / f"deploy_{timestamp}.log"
        
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
        
    def check_deployment_requirements(self):
        """デプロイメント要件のチェック"""
        self.logger.info("デプロイメント要件をチェックしています...")
        
        # 必要なファイルの存在確認
        required_files = [
            self.project_root / "setup.py",
            self.project_root / "requirements.txt",
            self.project_root / "src" / "main.py"
        ]
        
        for file_path in required_files:
            if not file_path.exists():
                raise DeploymentError(f"必要なファイルが見つかりません: {file_path}")
                
        # 必要なツールの確認
        required_tools = ['python', 'pip']
        
        # デプロイメントタイプに応じた追加ツール
        deploy_type = self.config.get('type', 'source')
        if deploy_type == 'executable':
            required_tools.extend(['pyinstaller'])
        elif deploy_type == 'docker':
            required_tools.extend(['docker'])
        elif deploy_type == 'wheel':
            required_tools.extend(['wheel', 'twine'])
            
        for tool in required_tools:
            try:
                subprocess.run([tool, '--version'], 
                             capture_output=True, check=True)
                self.logger.debug(f"{tool}が利用可能です")
            except (subprocess.CalledProcessError, FileNotFoundError):
                if tool in ['pyinstaller', 'wheel', 'twine']:
                    self.logger.warning(f"{tool}が見つかりません。インストールを試行します...")
                    self._install_tool(tool)
                else:
                    raise DeploymentError(f"{tool}が見つかりません")
                    
        self.logger.info("デプロイメント要件のチェックが完了しました")
        
    def _install_tool(self, tool: str):
        """ツールのインストール"""
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', tool
            ], check=True, capture_output=True)
            self.logger.info(f"{tool}のインストールが完了しました")
        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"{tool}のインストールに失敗しました: {e}")
            
    def clean_build_directories(self):
        """ビルドディレクトリのクリーンアップ"""
        self.logger.info("ビルドディレクトリをクリーンアップしています...")
        
        directories_to_clean = [
            self.build_dir,
            self.dist_dir,
            self.project_root / "*.egg-info"
        ]
        
        for dir_pattern in directories_to_clean:
            if "*" in str(dir_pattern):
                # glob パターンの処理
                import glob
                for path in glob.glob(str(dir_pattern)):
                    path_obj = Path(path)
                    if path_obj.exists():
                        if path_obj.is_dir():
                            shutil.rmtree(path_obj)
                        else:
                            path_obj.unlink()
                        self.logger.debug(f"削除しました: {path_obj}")
            else:
                if dir_pattern.exists():
                    if dir_pattern.is_dir():
                        shutil.rmtree(dir_pattern)
                    else:
                        dir_pattern.unlink()
                    self.logger.debug(f"削除しました: {dir_pattern}")
                    
        self.logger.info("ビルドディレクトリのクリーンアップが完了しました")
        
    def create_version_info(self) -> str:
        """バージョン情報の作成"""
        version = self.config.get('version', '1.0.0')
        
        # setup.pyからバージョン情報を取得
        setup_py = self.project_root / "setup.py"
        if setup_py.exists():
            try:
                with open(setup_py, 'r', encoding='utf-8') as f:
                    content = f.read()
                    import re
                    version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                    if version_match:
                        version = version_match.group(1)
            except Exception as e:
                self.logger.warning(f"setup.pyからバージョン情報を取得できませんでした: {e}")
                
        # Git情報の取得
        git_info = self._get_git_info()
        
        version_info = {
            'version': version,
            'build_date': datetime.now().isoformat(),
            'platform': self.platform,
            'architecture': self.architecture,
            'git_commit': git_info.get('commit', 'unknown'),
            'git_branch': git_info.get('branch', 'unknown'),
            'python_version': sys.version
        }
        
        # バージョン情報ファイルの作成
        version_file = self.project_root / "src" / "version_info.py"
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(f'# -*- coding: utf-8 -*-\n')
            f.write(f'"""バージョン情報 - 自動生成ファイル"""\n\n')
            f.write(f'VERSION_INFO = {json.dumps(version_info, indent=4, ensure_ascii=False)}\n')
            f.write(f'VERSION = "{version}"\n')
            f.write(f'BUILD_DATE = "{version_info["build_date"]}"\n')
            
        self.logger.info(f"バージョン情報を作成しました: {version}")
        return version
        
    def _get_git_info(self) -> Dict:
        """Git情報の取得"""
        git_info = {}
        
        try:
            # コミットハッシュの取得
            result = subprocess.run([
                'git', 'rev-parse', 'HEAD'
            ], cwd=self.project_root, capture_output=True, text=True, check=True)
            git_info['commit'] = result.stdout.strip()
            
            # ブランチ名の取得
            result = subprocess.run([
                'git', 'rev-parse', '--abbrev-ref', 'HEAD'
            ], cwd=self.project_root, capture_output=True, text=True, check=True)
            git_info['branch'] = result.stdout.strip()
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("Git情報を取得できませんでした")
            
        return git_info
        
    def deploy_source_distribution(self) -> str:
        """ソース配布の作成"""
        self.logger.info("ソース配布を作成しています...")
        
        # 一時ディレクトリの作成
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # プロジェクトファイルのコピー
            project_name = self.config.get('name', 'llm-code-assistant')
            version = self.create_version_info()
            
            source_dir = temp_path / f"{project_name}-{version}"
            source_dir.mkdir()
            
            # コピーするディレクトリとファイル
            items_to_copy = [
                'src',
                'config',
                'data',
                'assets',
                'requirements.txt',
                'setup.py',
                'README.md',
                '.env.example'
            ]
            
            for item in items_to_copy:
                src_path = self.project_root / item
                if src_path.exists():
                    if src_path.is_dir():
                        shutil.copytree(src_path, source_dir / item)
                    else:
                        shutil.copy2(src_path, source_dir / item)
                        
            # アーカイブの作成
            self.dist_dir.mkdir(exist_ok=True)
            
            if self.config.get('format', 'zip') == 'zip':
                archive_path = self.dist_dir / f"{project_name}-{version}.zip"
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file_path in source_dir.rglob('*'):
                        if file_path.is_file():
                            arc_path = file_path.relative_to(temp_path)
                            zf.write(file_path, arc_path)
            else:
                archive_path = self.dist_dir / f"{project_name}-{version}.tar.gz"
                with tarfile.open(archive_path, 'w:gz') as tf:
                    tf.add(source_dir, arcname=f"{project_name}-{version}")
                    
        self.logger.info(f"ソース配布を作成しました: {archive_path}")
        return str(archive_path)
        
    def deploy_executable(self) -> str:
        """実行可能ファイルの作成"""
        self.logger.info("実行可能ファイルを作成しています...")
        
        version = self.create_version_info()
        
        # PyInstallerの設定
        spec_file = self.project_root / "main.spec"
        if not spec_file.exists():
            self._create_pyinstaller_spec()
            
        # PyInstallerの実行
        try:
            cmd = [
                'pyinstaller',
                '--clean',
                '--noconfirm',
                str(spec_file)
            ]
            
            subprocess.run(cmd, cwd=self.project_root, check=True)
            
            # 実行可能ファイルの場所
            exe_name = self.config.get('name', 'llm-code-assistant')
            if self.platform == 'windows':
                exe_name += '.exe'
                
            exe_path = self.dist_dir / exe_name
            
            if exe_path.exists():
                self.logger.info(f"実行可能ファイルを作成しました: {exe_path}")
                return str(exe_path)
            else:
                raise DeploymentError("実行可能ファイルが見つかりません")
                
        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"PyInstallerの実行に失敗しました: {e}")
            
    def _create_pyinstaller_spec(self):
        """PyInstaller specファイルの作成"""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('data', 'data'),
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'openai',
        'anthropic',
        'transformers',
        'torch',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{self.config.get('name', 'llm-code-assistant')}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{self.config.get('name', 'llm-code-assistant')}',
)
'''
        
        spec_file = self.project_root / "main.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
            
        self.logger.info("PyInstaller specファイルを作成しました")
        
    def deploy_wheel_package(self) -> str:
        """Wheelパッケージの作成"""
        self.logger.info("Wheelパッケージを作成しています...")
        
        self.create_version_info()
        
        try:
            # setup.py bdist_wheelの実行
            subprocess.run([
                sys.executable, 'setup.py', 'bdist_wheel'
            ], cwd=self.project_root, check=True)
            
            # 作成されたwheelファイルの検索
            wheel_files = list(self.dist_dir.glob('*.whl'))
            if wheel_files:
                wheel_path = wheel_files[0]  # 最新のwheelファイル
                self.logger.info(f"Wheelパッケージを作成しました: {wheel_path}")
                return str(wheel_path)
            else:
                raise DeploymentError("Wheelファイルが見つかりません")
                
        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Wheelパッケージの作成に失敗しました: {e}")
            
    def deploy_docker_image(self) -> str:
        """Dockerイメージの作成"""
        self.logger.info("Dockerイメージを作成しています...")
        
        # Dockerfileの作成
        dockerfile_path = self.project_root / "Dockerfile"
        if not dockerfile_path.exists():
            self._create_dockerfile()
            
        # .dockerignoreの作成
        dockerignore_path = self.project_root / ".dockerignore"
        if not dockerignore_path.exists():
            self._create_dockerignore()
            
        version = self.create_version_info()
        image_name = self.config.get('docker_image', 'llm-code-assistant')
        image_tag = f"{image_name}:{version}"
        
        try:
            # Dockerイメージのビルド
            subprocess.run([
                'docker', 'build',
                '-t', image_tag,
                '-t', f"{image_name}:latest",
                '.'
            ], cwd=self.project_root, check=True)
            
            self.logger.info(f"Dockerイメージを作成しました: {image_tag}")
            return image_tag
            
        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Dockerイメージの作成に失敗しました: {e}")
            
    def _create_dockerfile(self):
        """Dockerfileの作成"""
        dockerfile_content = '''FROM python:3.11.9-slim

WORKDIR /app

# システムパッケージの更新とインストール
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/
COPY assets/ ./assets/

# 環境変数の設定
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# ポートの公開
EXPOSE 8000

# アプリケーションの起動
CMD ["python", "src/main.py"]
'''
        
        dockerfile_path = self.project_root / "Dockerfile"
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
            
        self.logger.info("Dockerfileを作成しました")
        
    def _create_dockerignore(self):
        """.dockerignoreの作成"""
        dockerignore_content = '''# Git
.git
.gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Test
test_reports/
.coverage
.pytest_cache/

# Documentation
docs/_build/

# Temporary files
*.tmp
*.temp
'''
        
        dockerignore_path = self.project_root / ".dockerignore"
        with open(dockerignore_path, 'w', encoding='utf-8') as f:
            f.write(dockerignore_content)
            
        self.logger.info(".dockerignoreを作成しました")
        
    def create_deployment_manifest(self, deployed_files: List[str]):
        """デプロイメントマニフェストの作成"""
        self.logger.info("デプロイメントマニフェストを作成しています...")
        
        manifest = {
            'deployment_info': {
                'timestamp': datetime.now().isoformat(),
                'type': self.config.get('type', 'source'),
                'version': self.config.get('version', '1.0.0'),
                'platform': self.platform,
                'architecture': self.architecture
            },
            'files': deployed_files,
            'config': self.config
        }
        
        manifest_file = self.dist_dir / "deployment_manifest.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"デプロイメントマニフェストを作成しました: {manifest_file}")
        
    def deploy(self) -> List[str]:
        """デプロイメントの実行"""
        try:
            self.logger.info("デプロイメントを開始します...")
            start_time = datetime.now()
            
            # 要件チェック
            self.check_deployment_requirements()
            
            # ビルドディレクトリのクリーンアップ
            if self.config.get('clean', True):
                self.clean_build_directories()
                
            # デプロイメントタイプに応じた処理
            deployed_files = []
            deploy_type = self.config.get('type', 'source')
            
            if deploy_type == 'source':
                file_path = self.deploy_source_distribution()
                deployed_files.append(file_path)
            elif deploy_type == 'executable':
                file_path = self.deploy_executable()
                deployed_files.append(file_path)
            elif deploy_type == 'wheel':
                file_path = self.deploy_wheel_package()
                deployed_files.append(file_path)
            elif deploy_type == 'docker':
                image_tag = self.deploy_docker_image()
                deployed_files.append(image_tag)
            elif deploy_type == 'all':
                # すべてのタイプでデプロイ
                for dt in ['source', 'wheel', 'executable']:
                    temp_config = self.config.copy()
                    temp_config['type'] = dt
                    temp_deployer = Deployer(temp_config)
                    if dt == 'source':
                        file_path = temp_deployer.deploy_source_distribution()
                    elif dt == 'wheel':
                        file_path = temp_deployer.deploy_wheel_package()
                    elif dt == 'executable':
                        file_path = temp_deployer.deploy_executable()
                    deployed_files.append(file_path)
            else:
                raise DeploymentError(f"未知のデプロイメントタイプ: {deploy_type}")
                
            # マニフェストの作成
            self.create_deployment_manifest(deployed_files)
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.logger.info(f"デプロイメントが完了しました (所要時間: {duration})")
            self.logger.info(f"作成されたファイル: {deployed_files}")
            
            return deployed_files
            
        except DeploymentError as e:
            self.logger.error(f"デプロイメントエラー: {e}")
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
        'name': 'llm-code-assistant',
        'version': '1.0.0',
        'type': 'source',
        'format': 'zip',
        'clean': True,
        'docker_image': 'llm-code-assistant'
    }

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='LLM Code Assistant デプロイメントスクリプト')
    parser.add_argument('--config', '-c', help='設定ファイルのパス')
    parser.add_argument('--type', '-t', 
                       choices=['source', 'executable', 'wheel', 'docker', 'all'],
                       help='デプロイメントタイプ')
    parser.add_argument('--version', '-v', help='バージョン番号')
    parser.add_argument('--name', '-n', help='プロジェクト名')
    parser.add_argument('--format', '-f', choices=['zip', 'tar.gz'],
                       help='アーカイブ形式（sourceタイプの場合）')
    parser.add_argument('--no-clean', action='store_true',
                       help='ビルドディレクトリをクリーンアップしない')
    
    args = parser.parse_args()
    
    # 設定の読み込み
    config = load_config(args.config)
    
    # コマンドライン引数による設定の上書き
    if args.type:
        config['type'] = args.type
    if args.version:
        config['version'] = args.version
    if args.name:
        config['name'] = args.name
    if args.format:
        config['format'] = args.format
    if args.no_clean:
        config['clean'] = False
        
    # デプロイメントの実行
    deployer = Deployer(config)
    deployed_files = deployer.deploy()
    
    print("\n=== デプロイメント完了 ===")
    for file_path in deployed_files:
        print(f"作成されたファイル: {file_path}")

if __name__ == '__main__':
    main()

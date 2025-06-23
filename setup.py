#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup.py - LLM Code Assistant パッケージセットアップ

LLM Code Assistantプロジェクトのインストールとパッケージング設定
"""

import os
import sys
from pathlib import Path
from setuptools import setup, find_packages

# プロジェクトルートディレクトリ
PROJECT_ROOT = Path(__file__).parent

# バージョン情報の読み込み
def get_version():
    """バージョン情報を取得"""
    version_file = PROJECT_ROOT / "src" / "__init__.py"
    if version_file.exists():
        with open(version_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('__version__'):
                    return line.split('=')[1].strip().strip('"\'')
    return "0.1.0"

# README.mdの読み込み
def get_long_description():
    """長い説明文を取得"""
    readme_file = PROJECT_ROOT / "README.md"
    if readme_file.exists():
        with open(readme_file, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

# requirements.txtの読み込み
def get_requirements():
    """依存関係を取得"""
    requirements_file = PROJECT_ROOT / "requirements.txt"
    requirements = []
    
    if requirements_file.exists():
        with open(requirements_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # コメント行と空行をスキップ
                if line and not line.startswith('#'):
                    # 条件付き依存関係の処理
                    if ';' in line:
                        # プラットフォーム固有の依存関係を処理
                        package, condition = line.split(';', 1)
                        package = package.strip()
                        condition = condition.strip()
                        
                        # extra == "xxx" 形式の条件をスキップ
                        if 'extra ==' not in condition:
                            requirements.append(line)
                    else:
                        requirements.append(line)
    
    return requirements

# 開発用依存関係
def get_dev_requirements():
    """開発用依存関係を取得"""
    return [
        'pytest>=7.4.3,<8.0.0',
        'pytest-qt>=4.2.0,<5.0.0',
        'pytest-asyncio>=0.21.1,<1.0.0',
        'pytest-cov>=4.1.0,<5.0.0',
        'pytest-mock>=3.12.0,<4.0.0',
        'black>=23.11.0,<24.0.0',
        'flake8>=6.1.0,<7.0.0',
        'mypy>=1.7.0,<2.0.0',
        'isort>=5.12.0,<6.0.0',
        'pre-commit>=3.5.0,<4.0.0',
        'sphinx>=7.2.0,<8.0.0',
        'sphinx-rtd-theme>=1.3.0,<2.0.0',
    ]

# 追加機能の依存関係
def get_extras_require():
    """追加機能の依存関係を取得"""
    return {
        'gpu': [
            'torch-audio>=2.1.0,<3.0.0',
            'torchvision>=0.16.0,<1.0.0',
        ],
        'nlp': [
            'spacy>=3.7.0,<4.0.0',
            'nltk>=3.8.1,<4.0.0',
            'textblob>=0.17.1,<1.0.0',
        ],
        'export': [
            'openpyxl>=3.1.2,<4.0.0',
            'xlsxwriter>=3.1.9,<4.0.0',
            'reportlab>=4.0.7,<5.0.0',
        ],
        'web': [
            'fastapi>=0.104.0,<1.0.0',
            'uvicorn>=0.24.0,<1.0.0',
            'websockets>=12.0,<13.0',
        ],
        'dev': get_dev_requirements(),
        'all': [
            # GPU support
            'torch-audio>=2.1.0,<3.0.0',
            'torchvision>=0.16.0,<1.0.0',
            # NLP features
            'spacy>=3.7.0,<4.0.0',
            'nltk>=3.8.1,<4.0.0',
            'textblob>=0.17.1,<1.0.0',
            # Export features
            'openpyxl>=3.1.2,<4.0.0',
            'xlsxwriter>=3.1.9,<4.0.0',
            'reportlab>=4.0.7,<5.0.0',
            # Web interface
            'fastapi>=0.104.0,<1.0.0',
            'uvicorn>=0.24.0,<1.0.0',
            'websockets>=12.0,<13.0',
        ] + get_dev_requirements()
    }

# エントリーポイント
def get_entry_points():
    """エントリーポイントを取得"""
    return {
        'console_scripts': [
            'llm-code-assistant=src.main:main',
            'llm-assistant=src.main:main',
            'llm-setup=scripts.setup_dev:main',
        ],
        'gui_scripts': [
            'llm-code-assistant-gui=src.main:main',
        ],
    }

# データファイル
def get_package_data():
    """パッケージデータファイルを取得"""
    return {
        'src': [
            '../config/*.json',
            '../config/*.yaml',
            '../data/templates/*',
            '../data/examples/*',
            '../assets/icons/*',
            '../assets/icons/file_icons/*',
            '../assets/icons/toolbar_icons/*',
            '../assets/themes/*',
            '../assets/sounds/*',
        ],
    }

# データファイル（パッケージ外）
def get_data_files():
    """データファイル（パッケージ外）を取得"""
    data_files = []
    
    # 設定ファイル
    config_files = []
    config_dir = PROJECT_ROOT / "config"
    if config_dir.exists():
        for file_path in config_dir.glob("*"):
            if file_path.is_file():
                config_files.append(str(file_path))
    
    if config_files:
        data_files.append(('config', config_files))
    
    # アセットファイル
    assets_dir = PROJECT_ROOT / "assets"
    if assets_dir.exists():
        for subdir in assets_dir.iterdir():
            if subdir.is_dir():
                files = [str(f) for f in subdir.glob("*") if f.is_file()]
                if files:
                    data_files.append((f'assets/{subdir.name}', files))
    
    return data_files

# クラシファイア
def get_classifiers():
    """PyPIクラシファイアを取得"""
    return [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Text Processing :: Linguistic',
        'Environment :: X11 Applications :: Qt',
        'Environment :: Win32 (MS Windows)',
        'Environment :: MacOS X',
        'Framework :: AsyncIO',
        'Natural Language :: Japanese',
        'Natural Language :: English',
    ]

# キーワード
def get_keywords():
    """キーワードを取得"""
    return [
        'llm', 'ai', 'code-assistant', 'code-generation', 'openai', 'claude',
        'local-llm', 'transformers', 'pytorch', 'gui', 'pyqt5', 'development-tools',
        'programming', 'automation', 'natural-language-processing', 'machine-learning',
        'vector-database', 'embeddings', 'chat', 'assistant', 'japanese'
    ]

# プロジェクトURL
def get_project_urls():
    """プロジェクトURLを取得"""
    return {
        'Homepage': 'https://github.com/your-username/llm-code-assistant',
        'Bug Reports': 'https://github.com/your-username/llm-code-assistant/issues',
        'Source': 'https://github.com/your-username/llm-code-assistant',
        'Documentation': 'https://llm-code-assistant.readthedocs.io/',
        'Changelog': 'https://github.com/your-username/llm-code-assistant/blob/main/CHANGELOG.md',
    }

# メイン設定
def main():
    """セットアップの実行"""
    
    # Python バージョンチェック
    if sys.version_info < (3, 11):
        sys.exit('Python 3.11以上が必要です。')
    
    setup(
        # 基本情報
        name='llm-code-assistant',
        version=get_version(),
        description='高品質なローカルLLMを活用したコード生成・編集アシスタント',
        long_description=get_long_description(),
        long_description_content_type='text/markdown',
        
        # 作者情報
        author='LLM Code Assistant Team',
        author_email='contact@llm-code-assistant.com',
        maintainer='LLM Code Assistant Team',
        maintainer_email='contact@llm-code-assistant.com',
        
        # URL情報
        url='https://github.com/your-username/llm-code-assistant',
        project_urls=get_project_urls(),
        
        # ライセンス
        license='MIT',
        
        # パッケージ情報
        packages=find_packages(where='src'),
        package_dir={'': 'src'},
        package_data=get_package_data(),
        data_files=get_data_files(),
        include_package_data=True,
        
        # 依存関係
        python_requires='>=3.11.0,<3.12.0',
        install_requires=get_requirements(),
        extras_require=get_extras_require(),
        
        # エントリーポイント
        entry_points=get_entry_points(),
        
        # メタデータ
        classifiers=get_classifiers(),
        keywords=get_keywords(),
        
        # zipファイルでの実行を無効化
        zip_safe=False,
        
        # テストスイート
        test_suite='tests',
        tests_require=get_dev_requirements(),
        
        # setuptools設定
        setup_requires=[
            'setuptools>=69.0.0',
            'wheel>=0.42.0',
        ],
        
        # プラットフォーム固有の設定
        platforms=['any'],
        
        # 追加オプション
        options={
            'build_exe': {
                'packages': ['src'],
                'include_files': [
                    ('config/', 'config/'),
                    ('assets/', 'assets/'),
                    ('data/', 'data/'),
                ],
                'excludes': [
                    'tests',
                    'docs',
                    'scripts',
                ],
            },
            'bdist_wheel': {
                'universal': False,
            },
        },
        
        # コマンドクラス（カスタムコマンド用）
        cmdclass={},
    )

if __name__ == '__main__':
    main()

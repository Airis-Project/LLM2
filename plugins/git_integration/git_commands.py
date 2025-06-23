# src/plugins/git_integration/git_commands.py
"""
Git操作のコマンドクラス
実際のGit操作を実行する
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

try:
    import git
    from git import Repo, InvalidGitRepositoryError, GitCommandError
    GIT_PYTHON_AVAILABLE = True
except ImportError:
    GIT_PYTHON_AVAILABLE = False

from ...core.logger import get_logger


class GitCommandError(Exception):
    """Git操作エラー"""
    def __init__(self, message: str, command: str = None, exit_code: int = None):
        super().__init__(message)
        self.command = command
        self.exit_code = exit_code


class GitCommands:
    """Git操作を実行するクラス"""
    
    def __init__(self, repo_path: Union[str, Path]):
        self.repo_path = Path(repo_path)
        self.logger = get_logger(f"git_commands.{self.repo_path.name}")
        self._repo: Optional[Repo] = None
        
        # GitPythonが利用可能かチェック
        if not GIT_PYTHON_AVAILABLE:
            self.logger.warning("GitPython が利用できません。コマンドライン経由でGitを実行します。")
    
    @property
    def repo(self) -> Optional[Repo]:
        """Gitリポジトリオブジェクト"""
        if self._repo is None and GIT_PYTHON_AVAILABLE:
            try:
                self._repo = Repo(self.repo_path)
            except InvalidGitRepositoryError:
                self.logger.debug(f"Gitリポジトリではありません: {self.repo_path}")
                return None
        return self._repo
    
    def is_git_repository(self) -> bool:
        """Gitリポジトリかどうかを確認"""
        try:
            if GIT_PYTHON_AVAILABLE:
                return self.repo is not None
            else:
                # コマンドライン経由で確認
                result = self._run_git_command(['rev-parse', '--git-dir'])
                return result.returncode == 0
        except Exception:
            return False
    
    def _run_git_command(self, args: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
        """Gitコマンドを実行"""
        if cwd is None:
            cwd = self.repo_path
        
        cmd = ['git'] + args
        self.logger.debug(f"Git コマンド実行: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                self.logger.error(f"Git コマンドエラー: {result.stderr}")
            
            return result
            
        except FileNotFoundError:
            raise GitCommandError("Gitが見つかりません。Gitがインストールされているか確認してください。")
        except Exception as e:
            raise GitCommandError(f"Git コマンド実行エラー: {str(e)}")
    
    def init_repository(self, bare: bool = False) -> bool:
        """Gitリポジトリを初期化"""
        try:
            if GIT_PYTHON_AVAILABLE:
                Repo.init(self.repo_path, bare=bare)
                self._repo = None  # リセット
                self.logger.info(f"Gitリポジトリを初期化しました: {self.repo_path}")
                return True
            else:
                args = ['init']
                if bare:
                    args.append('--bare')
                result = self._run_git_command(args)
                if result.returncode == 0:
                    self.logger.info(f"Gitリポジトリを初期化しました: {self.repo_path}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"リポジトリ初期化エラー: {e}")
            return False
    
    def clone_repository(self, url: str, target_path: Path = None) -> bool:
        """リポジトリをクローン"""
        try:
            if target_path is None:
                target_path = self.repo_path
            
            if GIT_PYTHON_AVAILABLE:
                Repo.clone_from(url, target_path)
                self.repo_path = target_path
                self._repo = None  # リセット
                self.logger.info(f"リポジトリをクローンしました: {url} -> {target_path}")
                return True
            else:
                result = self._run_git_command(['clone', url, str(target_path)])
                if result.returncode == 0:
                    self.repo_path = target_path
                    self.logger.info(f"リポジトリをクローンしました: {url} -> {target_path}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"クローンエラー: {e}")
            return False
    
    def get_status(self) -> Dict[str, List[str]]:
        """リポジトリの状態を取得"""
        try:
            if not self.is_git_repository():
                return {}
            
            if GIT_PYTHON_AVAILABLE and self.repo:
                status = {
                    'modified': [item.a_path for item in self.repo.index.diff(None)],
                    'staged': [item.a_path for item in self.repo.index.diff('HEAD')],
                    'untracked': self.repo.untracked_files,
                    'deleted': []
                }
                
                # 削除されたファイルを検出
                for item in self.repo.index.diff(None):
                    if item.deleted_file:
                        status['deleted'].append(item.a_path)
                
                return status
            else:
                # コマンドライン経由で状態を取得
                result = self._run_git_command(['status', '--porcelain'])
                if result.returncode != 0:
                    return {}
                
                status = {
                    'modified': [],
                    'staged': [],
                    'untracked': [],
                    'deleted': []
                }
                
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    status_code = line[:2]
                    file_path = line[3:]
                    
                    if status_code[0] in ['M', 'A', 'D', 'R', 'C']:
                        status['staged'].append(file_path)
                    if status_code[1] == 'M':
                        status['modified'].append(file_path)
                    elif status_code[1] == 'D':
                        status['deleted'].append(file_path)
                    elif status_code == '??':
                        status['untracked'].append(file_path)
                
                return status
                
        except Exception as e:
            self.logger.error(f"状態取得エラー: {e}")
            return {}
    
    def add_files(self, files: Union[str, List[str]] = None) -> bool:
        """ファイルをステージングエリアに追加"""
        try:
            if not self.is_git_repository():
                return False
            
            if files is None:
                files = ['.']
            elif isinstance(files, str):
                files = [files]
            
            if GIT_PYTHON_AVAILABLE and self.repo:
                self.repo.index.add(files)
                self.logger.info(f"ファイルを追加しました: {files}")
                return True
            else:
                result = self._run_git_command(['add'] + files)
                if result.returncode == 0:
                    self.logger.info(f"ファイルを追加しました: {files}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"ファイル追加エラー: {e}")
            return False
    
    def commit(self, message: str, author_name: str = None, author_email: str = None) -> bool:
        """コミットを作成"""
        try:
            if not self.is_git_repository():
                return False
            
            if GIT_PYTHON_AVAILABLE and self.repo:
                # 作者情報を設定
                if author_name and author_email:
                    actor = git.Actor(author_name, author_email)
                    self.repo.index.commit(message, author=actor, committer=actor)
                else:
                    self.repo.index.commit(message)
                
                self.logger.info(f"コミットしました: {message}")
                return True
            else:
                # 作者情報を設定
                env = os.environ.copy()
                if author_name:
                    env['GIT_AUTHOR_NAME'] = author_name
                    env['GIT_COMMITTER_NAME'] = author_name
                if author_email:
                    env['GIT_AUTHOR_EMAIL'] = author_email
                    env['GIT_COMMITTER_EMAIL'] = author_email
                
                cmd = ['git', 'commit', '-m', message]
                result = subprocess.run(
                    cmd,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    env=env
                )
                
                if result.returncode == 0:
                    self.logger.info(f"コミットしました: {message}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"コミットエラー: {e}")
            return False
    
    def get_commit_history(self, max_count: int = 50) -> List[Dict[str, str]]:
        """コミット履歴を取得"""
        try:
            if not self.is_git_repository():
                return []
            
            if GIT_PYTHON_AVAILABLE and self.repo:
                commits = []
                for commit in self.repo.iter_commits(max_count=max_count):
                    commits.append({
                        'hash': commit.hexsha,
                        'short_hash': commit.hexsha[:8],
                        'message': commit.message.strip(),
                        'author': str(commit.author),
                        'date': commit.committed_datetime.isoformat(),
                        'files_changed': len(commit.stats.files)
                    })
                return commits
            else:
                result = self._run_git_command([
                    'log',
                    f'--max-count={max_count}',
                    '--pretty=format:%H|%h|%s|%an <%ae>|%ci|%n',
                    '--stat'
                ])
                
                if result.returncode != 0:
                    return []
                
                commits = []
                lines = result.stdout.strip().split('\n')
                
                for line in lines:
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 5:
                            commits.append({
                                'hash': parts[0],
                                'short_hash': parts[1],
                                'message': parts[2],
                                'author': parts[3],
                                'date': parts[4],
                                'files_changed': 0  # 簡易版では省略
                            })
                
                return commits
                
        except Exception as e:
            self.logger.error(f"履歴取得エラー: {e}")
            return []
    
    def create_branch(self, branch_name: str, checkout: bool = True) -> bool:
        """ブランチを作成"""
        try:
            if not self.is_git_repository():
                return False
            
            if GIT_PYTHON_AVAILABLE and self.repo:
                new_branch = self.repo.create_head(branch_name)
                if checkout:
                    new_branch.checkout()
                self.logger.info(f"ブランチを作成しました: {branch_name}")
                return True
            else:
                if checkout:
                    result = self._run_git_command(['checkout', '-b', branch_name])
                else:
                    result = self._run_git_command(['branch', branch_name])
                
                if result.returncode == 0:
                    self.logger.info(f"ブランチを作成しました: {branch_name}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"ブランチ作成エラー: {e}")
            return False
    
    def switch_branch(self, branch_name: str) -> bool:
        """ブランチを切り替え"""
        try:
            if not self.is_git_repository():
                return False
            
            if GIT_PYTHON_AVAILABLE and self.repo:
                self.repo.heads[branch_name].checkout()
                self.logger.info(f"ブランチを切り替えました: {branch_name}")
                return True
            else:
                result = self._run_git_command(['checkout', branch_name])
                if result.returncode == 0:
                    self.logger.info(f"ブランチを切り替えました: {branch_name}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"ブランチ切り替えエラー: {e}")
            return False
    
    def get_branches(self) -> Dict[str, List[str]]:
        """ブランチ一覧を取得"""
        try:
            if not self.is_git_repository():
                return {'local': [], 'remote': []}
            
            if GIT_PYTHON_AVAILABLE and self.repo:
                local_branches = [head.name for head in self.repo.heads]
                remote_branches = [ref.name for ref in self.repo.remote().refs]
                
                return {
                    'local': local_branches,
                    'remote': remote_branches
                }
            else:
                # ローカルブランチ
                result = self._run_git_command(['branch'])
                local_branches = []
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        branch = line.strip().lstrip('* ')
                        if branch:
                            local_branches.append(branch)
                
                # リモートブランチ
                result = self._run_git_command(['branch', '-r'])
                remote_branches = []
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        branch = line.strip()
                        if branch and not branch.startswith('origin/HEAD'):
                            remote_branches.append(branch)
                
                return {
                    'local': local_branches,
                    'remote': remote_branches
                }
                
        except Exception as e:
            self.logger.error(f"ブランチ取得エラー: {e}")
            return {'local': [], 'remote': []}
    
    def get_current_branch(self) -> Optional[str]:
        """現在のブランチ名を取得"""
        try:
            if not self.is_git_repository():
                return None
            
            if GIT_PYTHON_AVAILABLE and self.repo:
                return self.repo.active_branch.name
            else:
                result = self._run_git_command(['branch', '--show-current'])
                if result.returncode == 0:
                    return result.stdout.strip()
                return None
                
        except Exception as e:
            self.logger.error(f"現在ブランチ取得エラー: {e}")
            return None
    
    def pull(self, remote: str = 'origin', branch: str = None) -> bool:
        """リモートから変更を取得"""
        try:
            if not self.is_git_repository():
                return False
            
            if GIT_PYTHON_AVAILABLE and self.repo:
                origin = self.repo.remote(remote)
                if branch:
                    origin.pull(branch)
                else:
                    origin.pull()
                self.logger.info(f"プルしました: {remote}")
                return True
            else:
                args = ['pull', remote]
                if branch:
                    args.append(branch)
                
                result = self._run_git_command(args)
                if result.returncode == 0:
                    self.logger.info(f"プルしました: {remote}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"プルエラー: {e}")
            return False
    
    def push(self, remote: str = 'origin', branch: str = None) -> bool:
        """リモートに変更を送信"""
        try:
            if not self.is_git_repository():
                return False
            
            if GIT_PYTHON_AVAILABLE and self.repo:
                origin = self.repo.remote(remote)
                if branch:
                    origin.push(branch)
                else:
                    origin.push()
                self.logger.info(f"プッシュしました: {remote}")
                return True
            else:
                args = ['push', remote]
                if branch:
                    args.append(branch)
                
                result = self._run_git_command(args)
                if result.returncode == 0:
                    self.logger.info(f"プッシュしました: {remote}")
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"プッシュエラー: {e}")
            return False
    
    def get_diff(self, file_path: str = None, staged: bool = False) -> str:
        """差分を取得"""
        try:
            if not self.is_git_repository():
                return ""
            
            args = ['diff']
            if staged:
                args.append('--cached')
            if file_path:
                args.append(file_path)
            
            result = self._run_git_command(args)
            if result.returncode == 0:
                return result.stdout
            return ""
            
        except Exception as e:
            self.logger.error(f"差分取得エラー: {e}")
            return ""
    
    def reset_file(self, file_path: str, hard: bool = False) -> bool:
        """ファイルをリセット"""
        try:
            if not self.is_git_repository():
                return False
            
            if hard:
                result = self._run_git_command(['checkout', 'HEAD', '--', file_path])
            else:
                result = self._run_git_command(['reset', 'HEAD', '--', file_path])
            
            if result.returncode == 0:
                self.logger.info(f"ファイルをリセットしました: {file_path}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"リセットエラー: {e}")
            return False

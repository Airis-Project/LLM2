# src/plugins/git_integration/git_plugin.py
"""
Git Integration Plugin - Git統合プラグイン

このプラグインは、LLM Code AssistantにGit機能を統合し、
バージョン管理操作をGUIから実行できるようにします。
"""

import os
import subprocess
import threading
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QTextEdit, QLineEdit, QComboBox, QCheckBox,
    QGroupBox, QSplitter, QTabWidget, QMessageBox, QInputDialog,
    QProgressDialog, QMenu, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QAction

from ..base_plugin import BasePlugin
from .git_commands import GitCommands
from ...core.logger import get_logger
from ...ui.components.custom_widgets import LoadingSpinner, StatusBar

logger = get_logger(__name__)


class GitStatusThread(QThread):
    """
    Git状態取得スレッド
    
    UIをブロックすることなくGit状態を取得するためのワーカースレッド
    """
    
    status_updated = pyqtSignal(dict)  # Git状態更新シグナル
    error_occurred = pyqtSignal(str)   # エラー発生シグナル
    
    def __init__(self, git_commands: GitCommands, repo_path: str):
        """
        GitStatusThreadを初期化
        
        Args:
            git_commands: Gitコマンドインスタンス
            repo_path: リポジトリパス
        """
        super().__init__()
        self.git_commands = git_commands
        self.repo_path = repo_path
        self.running = True
        
        logger.debug(f"GitStatusThread initialized for: {repo_path}")
    
    def run(self) -> None:
        """スレッド実行"""
        try:
            while self.running:
                if os.path.exists(self.repo_path):
                    # Git状態を取得
                    status_info = self._get_git_status()
                    self.status_updated.emit(status_info)
                
                # 5秒間隔で更新
                self.msleep(5000)
                
        except Exception as e:
            logger.error(f"Git status thread error: {e}")
            self.error_occurred.emit(str(e))
    
    def stop(self) -> None:
        """スレッド停止"""
        self.running = False
        self.quit()
        self.wait()
    
    def _get_git_status(self) -> Dict[str, Any]:
        """Git状態を取得"""
        try:
            status_info = {
                'branch': self.git_commands.get_current_branch(self.repo_path),
                'status': self.git_commands.get_status(self.repo_path),
                'remote_status': self.git_commands.get_remote_status(self.repo_path),
                'last_commit': self.git_commands.get_last_commit(self.repo_path),
                'stash_count': len(self.git_commands.get_stash_list(self.repo_path))
            }
            return status_info
        except Exception as e:
            logger.error(f"Failed to get git status: {e}")
            return {}


class GitPlugin(BasePlugin):
    """
    Git統合プラグイン
    
    プロジェクトのGit操作を統合的に管理するプラグイン
    """
    
    # シグナル定義
    repository_changed = pyqtSignal(str)  # リポジトリ変更シグナル
    commit_created = pyqtSignal(str)      # コミット作成シグナル
    branch_changed = pyqtSignal(str)      # ブランチ変更シグナル
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        GitPluginを初期化
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.plugin_name = "Git Integration"
        self.plugin_version = "1.0.0"
        self.plugin_description = "Git バージョン管理システムとの統合"
        
        self.git_commands = GitCommands()
        self.current_repo_path = ""
        self.status_thread: Optional[GitStatusThread] = None
        
        self._setup_ui()
        self._setup_signals()
        
        logger.info("Git Plugin initialized")
    
    def _setup_ui(self) -> None:
        """UIのセットアップ"""
        layout = QVBoxLayout()
        
        # ツールバー
        toolbar_layout = QHBoxLayout()
        
        # リポジトリ選択
        self.repo_label = QLabel("リポジトリ:")
        toolbar_layout.addWidget(self.repo_label)
        
        self.repo_path_edit = QLineEdit()
        self.repo_path_edit.setPlaceholder("リポジトリパスを入力またはブラウズ...")
        toolbar_layout.addWidget(self.repo_path_edit)
        
        self.browse_button = QPushButton("参照")
        self.browse_button.clicked.connect(self._browse_repository)
        toolbar_layout.addWidget(self.browse_button)
        
        self.refresh_button = QPushButton("更新")
        self.refresh_button.clicked.connect(self._refresh_status)
        toolbar_layout.addWidget(self.refresh_button)
        
        layout.addLayout(toolbar_layout)
        
        # メインコンテンツ
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左パネル: ファイル状態
        left_panel = self._create_file_status_panel()
        main_splitter.addWidget(left_panel)
        
        # 右パネル: Git操作
        right_panel = self._create_git_operations_panel()
        main_splitter.addWidget(right_panel)
        
        main_splitter.setSizes([400, 300])
        layout.addWidget(main_splitter)
        
        # ステータスバー
        self.status_bar = StatusBar()
        layout.addWidget(self.status_bar)
        
        self.setLayout(layout)
    
    def _create_file_status_panel(self) -> QWidget:
        """ファイル状態パネルを作成"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # ヘッダー
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("ファイル状態"))
        
        # ブランチ情報
        self.branch_label = QLabel("ブランチ: -")
        self.branch_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        header_layout.addWidget(self.branch_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # ファイルツリー
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["ファイル", "状態"])
        self.file_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self._show_file_context_menu)
        layout.addWidget(self.file_tree)
        
        panel.setLayout(layout)
        return panel
    
    def _create_git_operations_panel(self) -> QWidget:
        """Git操作パネルを作成"""
        panel = QTabWidget()
        
        # コミットタブ
        commit_tab = self._create_commit_tab()
        panel.addTab(commit_tab, "コミット")
        
        # ブランチタブ
        branch_tab = self._create_branch_tab()
        panel.addTab(branch_tab, "ブランチ")
        
        # 履歴タブ
        history_tab = self._create_history_tab()
        panel.addTab(history_tab, "履歴")
        
        # リモートタブ
        remote_tab = self._create_remote_tab()
        panel.addTab(remote_tab, "リモート")
        
        return panel
    
    def _create_commit_tab(self) -> QWidget:
        """コミットタブを作成"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # コミットメッセージ
        commit_group = QGroupBox("コミット")
        commit_layout = QVBoxLayout()
        
        commit_layout.addWidget(QLabel("コミットメッセージ:"))
        self.commit_message_edit = QTextEdit()
        self.commit_message_edit.setMaximumHeight(100)
        self.commit_message_edit.setPlaceholderText("コミットメッセージを入力してください...")
        commit_layout.addWidget(self.commit_message_edit)
        
        # コミットオプション
        options_layout = QHBoxLayout()
        self.amend_checkbox = QCheckBox("前回のコミットを修正")
        options_layout.addWidget(self.amend_checkbox)
        
        self.sign_off_checkbox = QCheckBox("Sign-off を追加")
        options_layout.addWidget(self.sign_off_checkbox)
        
        options_layout.addStretch()
        commit_layout.addLayout(options_layout)
        
        # コミットボタン
        button_layout = QHBoxLayout()
        self.stage_all_button = QPushButton("すべてステージ")
        self.stage_all_button.clicked.connect(self._stage_all_files)
        button_layout.addWidget(self.stage_all_button)
        
        self.commit_button = QPushButton("コミット")
        self.commit_button.clicked.connect(self._commit_changes)
        button_layout.addWidget(self.commit_button)
        
        button_layout.addStretch()
        commit_layout.addLayout(button_layout)
        
        commit_group.setLayout(commit_layout)
        layout.addWidget(commit_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _create_branch_tab(self) -> QWidget:
        """ブランチタブを作成"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # ブランチ一覧
        branch_group = QGroupBox("ブランチ管理")
        branch_layout = QVBoxLayout()
        
        # 現在のブランチ
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("現在のブランチ:"))
        self.current_branch_label = QLabel("-")
        self.current_branch_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        current_layout.addWidget(self.current_branch_label)
        current_layout.addStretch()
        branch_layout.addLayout(current_layout)
        
        # ブランチリスト
        self.branch_combo = QComboBox()
        self.branch_combo.currentTextChanged.connect(self._on_branch_selected)
        branch_layout.addWidget(self.branch_combo)
        
        # ブランチ操作ボタン
        branch_button_layout = QHBoxLayout()
        
        self.create_branch_button = QPushButton("新規作成")
        self.create_branch_button.clicked.connect(self._create_branch)
        branch_button_layout.addWidget(self.create_branch_button)
        
        self.checkout_button = QPushButton("チェックアウト")
        self.checkout_button.clicked.connect(self._checkout_branch)
        branch_button_layout.addWidget(self.checkout_button)
        
        self.merge_button = QPushButton("マージ")
        self.merge_button.clicked.connect(self._merge_branch)
        branch_button_layout.addWidget(self.merge_button)
        
        self.delete_branch_button = QPushButton("削除")
        self.delete_branch_button.clicked.connect(self._delete_branch)
        branch_button_layout.addWidget(self.delete_branch_button)
        
        branch_layout.addLayout(branch_button_layout)
        
        branch_group.setLayout(branch_layout)
        layout.addWidget(branch_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _create_history_tab(self) -> QWidget:
        """履歴タブを作成"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # コミット履歴
        history_group = QGroupBox("コミット履歴")
        history_layout = QVBoxLayout()
        
        # 履歴ツリー
        self.history_tree = QTreeWidget()
        self.history_tree.setHeaderLabels(["コミット", "作成者", "日時", "メッセージ"])
        self.history_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.history_tree.itemClicked.connect(self._on_commit_selected)
        history_layout.addWidget(self.history_tree)
        
        # コミット詳細
        self.commit_detail_edit = QTextEdit()
        self.commit_detail_edit.setMaximumHeight(150)
        self.commit_detail_edit.setReadOnly(True)
        history_layout.addWidget(self.commit_detail_edit)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        tab.setLayout(layout)
        return tab
    
    def _create_remote_tab(self) -> QWidget:
        """リモートタブを作成"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # リモート操作
        remote_group = QGroupBox("リモート操作")
        remote_layout = QVBoxLayout()
        
        # プッシュ/プル
        sync_layout = QHBoxLayout()
        
        self.pull_button = QPushButton("プル")
        self.pull_button.clicked.connect(self._pull_changes)
        sync_layout.addWidget(self.pull_button)
        
        self.push_button = QPushButton("プッシュ")
        self.push_button.clicked.connect(self._push_changes)
        sync_layout.addWidget(self.push_button)
        
        self.fetch_button = QPushButton("フェッチ")
        self.fetch_button.clicked.connect(self._fetch_changes)
        sync_layout.addWidget(self.fetch_button)
        
        sync_layout.addStretch()
        remote_layout.addLayout(sync_layout)
        
        # リモート情報
        self.remote_info_edit = QTextEdit()
        self.remote_info_edit.setMaximumHeight(100)
        self.remote_info_edit.setReadOnly(True)
        remote_layout.addWidget(self.remote_info_edit)
        
        remote_group.setLayout(remote_layout)
        layout.addWidget(remote_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _setup_signals(self) -> None:
        """シグナルのセットアップ"""
        self.repo_path_edit.textChanged.connect(self._on_repo_path_changed)
    
    def _browse_repository(self) -> None:
        """リポジトリを参照"""
        from PyQt6.QtWidgets import QFileDialog
        
        repo_path = QFileDialog.getExistingDirectory(
            self, "リポジトリディレクトリを選択", self.current_repo_path
        )
        
        if repo_path:
            self.repo_path_edit.setText(repo_path)
    
    def _on_repo_path_changed(self, path: str) -> None:
        """リポジトリパス変更時の処理"""
        if path and os.path.exists(path):
            if self.git_commands.is_git_repository(path):
                self.current_repo_path = path
                self._start_status_monitoring()
                self._refresh_status()
                self.repository_changed.emit(path)
            else:
                self.status_bar.show_message("指定されたディレクトリはGitリポジトリではありません", 3000)
    
    def _start_status_monitoring(self) -> None:
        """Git状態監視を開始"""
        if self.status_thread:
            self.status_thread.stop()
        
        self.status_thread = GitStatusThread(self.git_commands, self.current_repo_path)
        self.status_thread.status_updated.connect(self._update_git_status)
        self.status_thread.error_occurred.connect(self._handle_git_error)
        self.status_thread.start()
    
    def _update_git_status(self, status_info: Dict[str, Any]) -> None:
        """Git状態を更新"""
        try:
            # ブランチ情報更新
            if 'branch' in status_info:
                self.branch_label.setText(f"ブランチ: {status_info['branch']}")
                self.current_branch_label.setText(status_info['branch'])
            
            # ファイル状態更新
            if 'status' in status_info:
                self._update_file_tree(status_info['status'])
            
            # ブランチリスト更新
            self._update_branch_list()
            
            # コミット履歴更新
            self._update_commit_history()
            
            # リモート情報更新
            if 'remote_status' in status_info:
                self._update_remote_info(status_info['remote_status'])
            
        except Exception as e:
            logger.error(f"Failed to update git status: {e}")
    
    def _update_file_tree(self, status_files: List[Tuple[str, str]]) -> None:
        """ファイルツリーを更新"""
        self.file_tree.clear()
        
        for file_path, status in status_files:
            item = QTreeWidgetItem([file_path, status])
            
            # 状態に応じて色を設定
            if status in ['A', 'M']:  # Added, Modified
                item.setForeground(0, QColor(0, 150, 0))
            elif status in ['D']:     # Deleted
                item.setForeground(0, QColor(150, 0, 0))
            elif status in ['?']:     # Untracked
                item.setForeground(0, QColor(150, 150, 0))
            
            self.file_tree.addTopLevelItem(item)
    
    def _update_branch_list(self) -> None:
        """ブランチリストを更新"""
        try:
            branches = self.git_commands.get_branches(self.current_repo_path)
            
            self.branch_combo.clear()
            for branch in branches:
                self.branch_combo.addItem(branch)
                
        except Exception as e:
            logger.error(f"Failed to update branch list: {e}")
    
    def _update_commit_history(self) -> None:
        """コミット履歴を更新"""
        try:
            commits = self.git_commands.get_commit_history(self.current_repo_path, limit=50)
            
            self.history_tree.clear()
            for commit in commits:
                item = QTreeWidgetItem([
                    commit['hash'][:8],
                    commit['author'],
                    commit['date'],
                    commit['message']
                ])
                item.setData(0, Qt.ItemDataRole.UserRole, commit)
                self.history_tree.addTopLevelItem(item)
                
        except Exception as e:
            logger.error(f"Failed to update commit history: {e}")
    
    def _update_remote_info(self, remote_status: Dict[str, Any]) -> None:
        """リモート情報を更新"""
        info_text = []
        
        if 'ahead' in remote_status:
            info_text.append(f"ローカルが {remote_status['ahead']} コミット先行")
        
        if 'behind' in remote_status:
            info_text.append(f"リモートが {remote_status['behind']} コミット先行")
        
        if not info_text:
            info_text.append("リモートと同期済み")
        
        self.remote_info_edit.setPlainText("\n".join(info_text))
    
    def _refresh_status(self) -> None:
        """状態を手動更新"""
        if self.current_repo_path:
            self.status_bar.show_message("Git状態を更新中...", 2000)
            # 状態監視スレッドが自動的に更新
    
    def _show_file_context_menu(self, position) -> None:
        """ファイルコンテキストメニューを表示"""
        item = self.file_tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        # ステージ/アンステージ
        stage_action = QAction("ステージ", self)
        stage_action.triggered.connect(lambda: self._stage_file(item.text(0)))
        menu.addAction(stage_action)
        
        unstage_action = QAction("アンステージ", self)
        unstage_action.triggered.connect(lambda: self._unstage_file(item.text(0)))
        menu.addAction(unstage_action)
        
        menu.addSeparator()
        
        # 差分表示
        diff_action = QAction("差分を表示", self)
        diff_action.triggered.connect(lambda: self._show_file_diff(item.text(0)))
        menu.addAction(diff_action)
        
        # 元に戻す
        revert_action = QAction("変更を元に戻す", self)
        revert_action.triggered.connect(lambda: self._revert_file(item.text(0)))
        menu.addAction(revert_action)
        
        menu.exec(self.file_tree.mapToGlobal(position))
    
    def _stage_file(self, file_path: str) -> None:
        """ファイルをステージ"""
        try:
            self.git_commands.stage_file(self.current_repo_path, file_path)
            self.status_bar.show_message(f"ステージしました: {file_path}", 2000)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"ステージに失敗しました: {e}")
    
    def _unstage_file(self, file_path: str) -> None:
        """ファイルをアンステージ"""
        try:
            self.git_commands.unstage_file(self.current_repo_path, file_path)
            self.status_bar.show_message(f"アンステージしました: {file_path}", 2000)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"アンステージに失敗しました: {e}")
    
    def _stage_all_files(self) -> None:
        """すべてのファイルをステージ"""
        try:
            self.git_commands.stage_all(self.current_repo_path)
            self.status_bar.show_message("すべてのファイルをステージしました", 2000)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"ステージに失敗しました: {e}")
    
    def _commit_changes(self) -> None:
        """変更をコミット"""
        message = self.commit_message_edit.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "警告", "コミットメッセージを入力してください")
            return
        
        try:
            options = {}
            if self.amend_checkbox.isChecked():
                options['amend'] = True
            if self.sign_off_checkbox.isChecked():
                options['signoff'] = True
            
            commit_hash = self.git_commands.commit(self.current_repo_path, message, **options)
            self.commit_message_edit.clear()
            self.status_bar.show_message(f"コミットしました: {commit_hash[:8]}", 3000)
            self.commit_created.emit(commit_hash)
            
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"コミットに失敗しました: {e}")
    
    def _create_branch(self) -> None:
        """新しいブランチを作成"""
        branch_name, ok = QInputDialog.getText(
            self, "新しいブランチ", "ブランチ名を入力してください:"
        )
        
        if ok and branch_name:
            try:
                self.git_commands.create_branch(self.current_repo_path, branch_name)
                self.status_bar.show_message(f"ブランチを作成しました: {branch_name}", 2000)
                self._update_branch_list()
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"ブランチ作成に失敗しました: {e}")
    
    def _checkout_branch(self) -> None:
        """ブランチをチェックアウト"""
        branch_name = self.branch_combo.currentText()
        if not branch_name:
            return
        
        try:
            self.git_commands.checkout_branch(self.current_repo_path, branch_name)
            self.status_bar.show_message(f"ブランチを切り替えました: {branch_name}", 2000)
            self.branch_changed.emit(branch_name)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"ブランチの切り替えに失敗しました: {e}")
    
    def _merge_branch(self) -> None:
        """ブランチをマージ"""
        branch_name = self.branch_combo.currentText()
        if not branch_name:
            return
        
        reply = QMessageBox.question(
            self, "確認", 
            f"ブランチ '{branch_name}' を現在のブランチにマージしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.git_commands.merge_branch(self.current_repo_path, branch_name)
                self.status_bar.show_message(f"ブランチをマージしました: {branch_name}", 2000)
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"マージに失敗しました: {e}")
    
    def _delete_branch(self) -> None:
        """ブランチを削除"""
        branch_name = self.branch_combo.currentText()
        if not branch_name:
            return
        
        reply = QMessageBox.question(
            self, "確認", 
            f"ブランチ '{branch_name}' を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.git_commands.delete_branch(self.current_repo_path, branch_name)
                self.status_bar.show_message(f"ブランチを削除しました: {branch_name}", 2000)
                self._update_branch_list()
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"ブランチ削除に失敗しました: {e}")
    
    def _pull_changes(self) -> None:
        """変更をプル"""
        try:
            self.git_commands.pull(self.current_repo_path)
            self.status_bar.show_message("プルしました", 2000)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"プルに失敗しました: {e}")
    
    def _push_changes(self) -> None:
        """変更をプッシュ"""
        try:
            self.git_commands.push(self.current_repo_path)
            self.status_bar.show_message("プッシュしました", 2000)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"プッシュに失敗しました: {e}")
    
    def _fetch_changes(self) -> None:
        """変更をフェッチ"""
        try:
            self.git_commands.fetch(self.current_repo_path)
            self.status_bar.show_message("フェッチしました", 2000)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"フェッチに失敗しました: {e}")
    
    def _on_branch_selected(self, branch_name: str) -> None:
        """ブランチ選択時の処理"""
        # 現在のブランチと異なる場合のみ処理
        current_branch = self.git_commands.get_current_branch(self.current_repo_path)
        if branch_name != current_branch:
            # チェックアウトボタンを有効化
            self.checkout_button.setEnabled(True)
        else:
            self.checkout_button.setEnabled(False)
    
    def _on_commit_selected(self, item: QTreeWidgetItem, column: int) -> None:
        """コミット選択時の処理"""
        commit_data = item.data(0, Qt.ItemDataRole.UserRole)
        if commit_data:
            try:
                # コミット詳細を取得
                commit_detail = self.git_commands.get_commit_detail(
                    self.current_repo_path, commit_data['hash']
                )
                
                # 詳細情報を表示
                detail_text = f"コミット: {commit_data['hash']}\n"
                detail_text += f"作成者: {commit_data['author']}\n"
                detail_text += f"日時: {commit_data['date']}\n"
                detail_text += f"メッセージ: {commit_data['message']}\n\n"
                detail_text += "変更ファイル:\n"
                detail_text += commit_detail.get('files', '情報なし')
                
                self.commit_detail_edit.setPlainText(detail_text)
                
            except Exception as e:
                logger.error(f"Failed to get commit detail: {e}")
                self.commit_detail_edit.setPlainText("コミット詳細の取得に失敗しました")
    
    def _show_file_diff(self, file_path: str) -> None:
        """ファイルの差分を表示"""
        try:
            diff = self.git_commands.get_file_diff(self.current_repo_path, file_path)
            
            # 差分表示ダイアログ
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"差分: {file_path}")
            dialog.setGeometry(100, 100, 800, 600)
            
            layout = QVBoxLayout()
            
            diff_text = QTextEdit()
            diff_text.setPlainText(diff)
            diff_text.setReadOnly(True)
            diff_text.setFont(QFont("Courier New", 10))
            layout.addWidget(diff_text)
            
            close_button = QPushButton("閉じる")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"差分の取得に失敗しました: {e}")
    
    def _revert_file(self, file_path: str) -> None:
        """ファイルの変更を元に戻す"""
        reply = QMessageBox.question(
            self, "確認", 
            f"ファイル '{file_path}' の変更を元に戻しますか？\n"
            "この操作は取り消せません。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.git_commands.revert_file(self.current_repo_path, file_path)
                self.status_bar.show_message(f"変更を元に戻しました: {file_path}", 2000)
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"変更の取り消しに失敗しました: {e}")
    
    def _handle_git_error(self, error_message: str) -> None:
        """Gitエラーの処理"""
        logger.error(f"Git error: {error_message}")
        self.status_bar.show_message(f"Gitエラー: {error_message}", 5000)
    
    # BasePluginの抽象メソッドの実装
    def activate(self) -> bool:
        """プラグインを有効化"""
        try:
            # Git コマンドの利用可能性をチェック
            if not self.git_commands.is_git_available():
                QMessageBox.warning(
                    self, "警告", 
                    "Gitコマンドが見つかりません。\n"
                    "Gitをインストールしてパスを通してください。"
                )
                return False
            
            self.setEnabled(True)
            logger.info("Git Plugin activated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate Git Plugin: {e}")
            return False
    
    def deactivate(self) -> None:
        """プラグインを無効化"""
        try:
            # 状態監視スレッドを停止
            if self.status_thread:
                self.status_thread.stop()
                self.status_thread = None
            
            self.setEnabled(False)
            logger.info("Git Plugin deactivated")
            
        except Exception as e:
            logger.error(f"Failed to deactivate Git Plugin: {e}")
    
    def get_settings(self) -> Dict[str, Any]:
        """プラグイン設定を取得"""
        return {
            'current_repo_path': self.current_repo_path,
            'auto_refresh_interval': 5000,
            'show_untracked_files': True,
            'commit_template': "",
            'default_branch': "main"
        }
    
    def set_settings(self, settings: Dict[str, Any]) -> None:
        """プラグイン設定を適用"""
        try:
            if 'current_repo_path' in settings:
                repo_path = settings['current_repo_path']
                if repo_path and os.path.exists(repo_path):
                    self.repo_path_edit.setText(repo_path)
            
            if 'commit_template' in settings:
                template = settings['commit_template']
                if template:
                    self.commit_message_edit.setPlaceholderText(template)
            
            logger.debug("Git Plugin settings applied")
            
        except Exception as e:
            logger.error(f"Failed to apply Git Plugin settings: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """プラグインの状態を取得"""
        return {
            'active': self.isEnabled(),
            'repository_path': self.current_repo_path,
            'git_available': self.git_commands.is_git_available(),
            'current_branch': (
                self.git_commands.get_current_branch(self.current_repo_path) 
                if self.current_repo_path else None
            ),
            'has_changes': bool(
                self.git_commands.get_status(self.current_repo_path)
                if self.current_repo_path else False
            )
        }
    
    def cleanup(self) -> None:
        """プラグインのクリーンアップ"""
        try:
            # 状態監視スレッドを停止
            if self.status_thread:
                self.status_thread.stop()
                self.status_thread = None
            
            # 一時ファイルのクリーンアップ
            # （必要に応じて実装）
            
            logger.info("Git Plugin cleanup completed")
            
        except Exception as e:
            logger.error(f"Failed to cleanup Git Plugin: {e}")
    
    def get_menu_actions(self) -> List[QAction]:
        """メニューアクションを取得"""
        actions = []
        
        # Git操作メニュー
        git_menu = QMenu("Git", self)
        
        # 基本操作
        status_action = QAction("状態を更新", self)
        status_action.triggered.connect(self._refresh_status)
        git_menu.addAction(status_action)
        
        git_menu.addSeparator()
        
        # コミット操作
        commit_action = QAction("コミット...", self)
        commit_action.triggered.connect(lambda: self.commit_message_edit.setFocus())
        git_menu.addAction(commit_action)
        
        # ブランチ操作
        branch_action = QAction("ブランチ管理...", self)
        branch_action.triggered.connect(lambda: self.setCurrentIndex(1))  # ブランチタブに切り替え
        git_menu.addAction(branch_action)
        
        git_menu.addSeparator()
        
        # 同期操作
        pull_action = QAction("プル", self)
        pull_action.triggered.connect(self._pull_changes)
        git_menu.addAction(pull_action)
        
        push_action = QAction("プッシュ", self)
        push_action.triggered.connect(self._push_changes)
        git_menu.addAction(push_action)
        
        return [git_menu.menuAction()]
    
    def get_toolbar_actions(self) -> List[QAction]:
        """ツールバーアクションを取得"""
        actions = []
        
        # 更新アクション
        refresh_action = QAction("Git更新", self)
        refresh_action.setToolTip("Git状態を更新")
        refresh_action.triggered.connect(self._refresh_status)
        actions.append(refresh_action)
        
        # コミットアクション
        commit_action = QAction("コミット", self)
        commit_action.setToolTip("変更をコミット")
        commit_action.triggered.connect(self._commit_changes)
        actions.append(commit_action)
        
        return actions
    
    def handle_file_changed(self, file_path: str) -> None:
        """ファイル変更の処理"""
        if self.current_repo_path and file_path.startswith(self.current_repo_path):
            # Git管理下のファイルが変更された場合、状態を更新
            QTimer.singleShot(1000, self._refresh_status)  # 1秒後に更新
    
    def handle_project_opened(self, project_path: str) -> None:
        """プロジェクト開始時の処理"""
        if self.git_commands.is_git_repository(project_path):
            self.repo_path_edit.setText(project_path)
            self.status_bar.show_message(f"Gitリポジトリを検出しました: {project_path}", 3000)
    
    def handle_project_closed(self) -> None:
        """プロジェクト終了時の処理"""
        if self.status_thread:
            self.status_thread.stop()
            self.status_thread = None
        
        self.current_repo_path = ""
        self.repo_path_edit.clear()
        self.file_tree.clear()
        self.branch_combo.clear()
        self.history_tree.clear()
        self.commit_detail_edit.clear()
        self.remote_info_edit.clear()


# プラグインのエクスポート関数
def create_plugin(parent: Optional[QWidget] = None) -> GitPlugin:
    """
    Gitプラグインのインスタンスを作成
    
    Args:
        parent: 親ウィジェット
        
    Returns:
        GitPluginインスタンス
    """
    return GitPlugin(parent)


def get_plugin_info() -> Dict[str, Any]:
    """
    プラグイン情報を取得
    
    Returns:
        プラグイン情報辞書
    """
    return {
        'name': 'Git Integration',
        'version': '1.0.0',
        'description': 'Git バージョン管理システムとの統合',
        'author': 'LLM Code Assistant Team',
        'category': 'Version Control',
        'dependencies': ['git'],
        'settings_schema': {
            'current_repo_path': {
                'type': 'string',
                'description': '現在のリポジトリパス',
                'default': ''
            },
            'auto_refresh_interval': {
                'type': 'integer',
                'description': '自動更新間隔（ミリ秒）',
                'default': 5000,
                'minimum': 1000
            },
            'show_untracked_files': {
                'type': 'boolean',
                'description': '未追跡ファイルを表示',
                'default': True
            },
            'commit_template': {
                'type': 'string',
                'description': 'コミットメッセージテンプレート',
                'default': ''
            },
            'default_branch': {
                'type': 'string',
                'description': 'デフォルトブランチ名',
                'default': 'main'
            }
        }
    }


if __name__ == "__main__":
    """テスト用のメイン関数"""
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Git Plugin Test")
            self.setGeometry(100, 100, 1200, 800)
            
            # Gitプラグインを作成
            self.git_plugin = GitPlugin()
            self.setCentralWidget(self.git_plugin)
            
            # プラグインを有効化
            self.git_plugin.activate()
    
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())

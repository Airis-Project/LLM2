# src/ui/components/theme_manager.py
"""
テーママネージャー
アプリケーションのテーマ管理を提供
"""

import json
import os
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal, QSettings
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication

from ...core.logger import get_logger
from ...core.config_manager import ConfigManager


class ThemeType(Enum):
    """テーマタイプ"""
    LIGHT = "light"
    DARK = "dark"
    CUSTOM = "custom"


@dataclass
class ColorScheme:
    """カラースキーム"""
    # 基本色
    background: str = "#ffffff"
    foreground: str = "#000000"
    
    # ウィンドウ色
    window: str = "#f0f0f0"
    window_text: str = "#000000"
    
    # ベース色
    base: str = "#ffffff"
    alternate_base: str = "#f5f5f5"
    
    # ボタン色
    button: str = "#e1e1e1"
    button_text: str = "#000000"
    
    # ハイライト色
    highlight: str = "#0078d4"
    highlighted_text: str = "#ffffff"
    
    # リンク色
    link: str = "#0066cc"
    link_visited: str = "#800080"
    
    # テキスト色
    text: str = "#000000"
    bright_text: str = "#ffffff"
    
    # ツールチップ色
    tooltip_base: str = "#ffffcc"
    tooltip_text: str = "#000000"
    
    # 無効化色
    disabled_text: str = "#808080"
    disabled_button_text: str = "#808080"
    
    # エラー・警告色
    error: str = "#ff0000"
    warning: str = "#ff8c00"
    success: str = "#008000"
    info: str = "#0078d4"
    
    # エディタ固有色
    editor_background: str = "#ffffff"
    editor_text: str = "#000000"
    editor_selection: str = "#0078d4"
    editor_selection_text: str = "#ffffff"
    editor_line_number: str = "#808080"
    editor_current_line: str = "#f0f0f0"
    
    # シンタックスハイライト色
    syntax_keyword: str = "#0000ff"
    syntax_string: str = "#a31515"
    syntax_comment: str = "#008000"
    syntax_number: str = "#000080"
    syntax_operator: str = "#000000"
    syntax_function: str = "#795e26"
    syntax_class: str = "#267f99"


@dataclass
class FontSettings:
    """フォント設定"""
    family: str = "Segoe UI"
    size: int = 10
    weight: str = "normal"  # normal, bold
    style: str = "normal"   # normal, italic
    
    # エディタ固有フォント
    editor_family: str = "Consolas"
    editor_size: int = 11
    editor_weight: str = "normal"
    editor_style: str = "normal"


@dataclass
class Theme:
    """テーマ定義"""
    name: str
    type: ThemeType
    colors: ColorScheme
    fonts: FontSettings
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ThemeManager(QObject):
    """テーママネージャー"""
    
    theme_changed = pyqtSignal(Theme)
    
    def __init__(self, config_manager: ConfigManager = None):
        super().__init__()
        self.logger = get_logger(__name__)
        self.config_manager = config_manager or ConfigManager()
        
        # 設定
        self.settings = QSettings()
        
        # テーマ辞書
        self.themes: Dict[str, Theme] = {}
        self.current_theme: Optional[Theme] = None
        
        # デフォルトテーマを初期化
        self._init_default_themes()
        
        # カスタムテーマを読み込み
        self._load_custom_themes()
        
        # 現在のテーマを設定
        self._load_current_theme()
    
    def _init_default_themes(self):
        """デフォルトテーマを初期化"""
        try:
            # ライトテーマ
            light_colors = ColorScheme(
                background="#ffffff",
                foreground="#000000",
                window="#f0f0f0",
                window_text="#000000",
                base="#ffffff",
                alternate_base="#f5f5f5",
                button="#e1e1e1",
                button_text="#000000",
                highlight="#0078d4",
                highlighted_text="#ffffff",
                link="#0066cc",
                link_visited="#800080",
                text="#000000",
                bright_text="#ffffff",
                tooltip_base="#ffffcc",
                tooltip_text="#000000",
                disabled_text="#808080",
                disabled_button_text="#808080",
                error="#dc3545",
                warning="#ffc107",
                success="#28a745",
                info="#17a2b8",
                editor_background="#ffffff",
                editor_text="#000000",
                editor_selection="#0078d4",
                editor_selection_text="#ffffff",
                editor_line_number="#808080",
                editor_current_line="#f0f8ff",
                syntax_keyword="#0000ff",
                syntax_string="#a31515",
                syntax_comment="#008000",
                syntax_number="#000080",
                syntax_operator="#000000",
                syntax_function="#795e26",
                syntax_class="#267f99"
            )
            
            light_fonts = FontSettings(
                family="Segoe UI",
                size=10,
                editor_family="Consolas",
                editor_size=11
            )
            
            light_theme = Theme(
                name="Light",
                type=ThemeType.LIGHT,
                colors=light_colors,
                fonts=light_fonts,
                metadata={"description": "明るいテーマ", "author": "System"}
            )
            
            self.themes["light"] = light_theme
            
            # ダークテーマ
            dark_colors = ColorScheme(
                background="#2b2b2b",
                foreground="#ffffff",
                window="#3c3c3c",
                window_text="#ffffff",
                base="#2b2b2b",
                alternate_base="#404040",
                button="#404040",
                button_text="#ffffff",
                highlight="#0078d4",
                highlighted_text="#ffffff",
                link="#4fc3f7",
                link_visited="#ba68c8",
                text="#ffffff",
                bright_text="#ffffff",
                tooltip_base="#484848",
                tooltip_text="#ffffff",
                disabled_text="#808080",
                disabled_button_text="#606060",
                error="#f44336",
                warning="#ff9800",
                success="#4caf50",
                info="#2196f3",
                editor_background="#1e1e1e",
                editor_text="#d4d4d4",
                editor_selection="#264f78",
                editor_selection_text="#ffffff",
                editor_line_number="#858585",
                editor_current_line="#2a2d2e",
                syntax_keyword="#569cd6",
                syntax_string="#ce9178",
                syntax_comment="#6a9955",
                syntax_number="#b5cea8",
                syntax_operator="#d4d4d4",
                syntax_function="#dcdcaa",
                syntax_class="#4ec9b0"
            )
            
            dark_fonts = FontSettings(
                family="Segoe UI",
                size=10,
                editor_family="Consolas",
                editor_size=11
            )
            
            dark_theme = Theme(
                name="Dark",
                type=ThemeType.DARK,
                colors=dark_colors,
                fonts=dark_fonts,
                metadata={"description": "暗いテーマ", "author": "System"}
            )
            
            self.themes["dark"] = dark_theme
            
        except Exception as e:
            self.logger.error(f"デフォルトテーマ初期化エラー: {e}")
    
    def _load_custom_themes(self):
        """カスタムテーマを読み込み"""
        try:
            themes_dir = os.path.join("assets", "themes")
            if not os.path.exists(themes_dir):
                return
            
            for filename in os.listdir(themes_dir):
                if filename.endswith('.json'):
                    theme_path = os.path.join(themes_dir, filename)
                    try:
                        with open(theme_path, 'r', encoding='utf-8') as f:
                            theme_data = json.load(f)
                        
                        theme = self._create_theme_from_data(theme_data)
                        if theme:
                            theme_id = filename.replace('.json', '')
                            self.themes[theme_id] = theme
                            
                    except Exception as e:
                        self.logger.error(f"テーマファイル読み込みエラー {filename}: {e}")
            
        except Exception as e:
            self.logger.error(f"カスタムテーマ読み込みエラー: {e}")
    
    def _create_theme_from_data(self, data: Dict[str, Any]) -> Optional[Theme]:
        """データからテーマを作成"""
        try:
            # 必須フィールドのチェック
            if 'name' not in data or 'colors' not in data:
                return None
            
            # カラースキーム作成
            color_data = data['colors']
            colors = ColorScheme(**color_data)
            
            # フォント設定作成
            font_data = data.get('fonts', {})
            fonts = FontSettings(**font_data)
            
            # テーマタイプ
            theme_type_str = data.get('type', 'custom')
            theme_type = ThemeType.CUSTOM
            if theme_type_str == 'light':
                theme_type = ThemeType.LIGHT
            elif theme_type_str == 'dark':
                theme_type = ThemeType.DARK
            
            # テーマ作成
            theme = Theme(
                name=data['name'],
                type=theme_type,
                colors=colors,
                fonts=fonts,
                metadata=data.get('metadata', {})
            )
            
            return theme
            
        except Exception as e:
            self.logger.error(f"テーマ作成エラー: {e}")
            return None
    
    def _load_current_theme(self):
        """現在のテーマを読み込み"""
        try:
            current_theme_id = self.settings.value("theme/current", "light")
            if current_theme_id in self.themes:
                self.set_theme(current_theme_id)
            else:
                self.set_theme("light")
                
        except Exception as e:
            self.logger.error(f"現在テーマ読み込みエラー: {e}")
            self.set_theme("light")
    
    def get_available_themes(self) -> List[str]:
        """利用可能なテーマ一覧を取得"""
        try:
            return list(self.themes.keys())
            
        except Exception as e:
            self.logger.error(f"テーマ一覧取得エラー: {e}")
            return []
    
    def get_theme(self, theme_id: str) -> Optional[Theme]:
        """テーマを取得"""
        try:
            return self.themes.get(theme_id)
            
        except Exception as e:
            self.logger.error(f"テーマ取得エラー: {e}")
            return None
    
    def get_current_theme(self) -> Optional[Theme]:
        """現在のテーマを取得"""
        return self.current_theme
    
    def set_theme(self, theme_id: str) -> bool:
        """テーマを設定"""
        try:
            if theme_id not in self.themes:
                self.logger.warning(f"テーマが見つかりません: {theme_id}")
                return False
            
            theme = self.themes[theme_id]
            self.current_theme = theme
            
            # アプリケーションにテーマを適用
            self._apply_theme(theme)
            
            # 設定を保存
            self.settings.setValue("theme/current", theme_id)
            
            # シグナル発信
            self.theme_changed.emit(theme)
            
            self.logger.info(f"テーマを変更しました: {theme.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"テーマ設定エラー: {e}")
            return False
    
    def _apply_theme(self, theme: Theme):
        """テーマをアプリケーションに適用"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            # パレットを作成
            palette = self._create_palette(theme.colors)
            app.setPalette(palette)
            
            # フォントを設定
            self._apply_fonts(theme.fonts)
            
        except Exception as e:
            self.logger.error(f"テーマ適用エラー: {e}")
    
    def _create_palette(self, colors: ColorScheme) -> QPalette:
        """カラースキームからパレットを作成"""
        try:
            palette = QPalette()
            
            # 基本色
            palette.setColor(QPalette.ColorRole.Window, QColor(colors.window))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(colors.window_text))
            palette.setColor(QPalette.ColorRole.Base, QColor(colors.base))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors.alternate_base))
            palette.setColor(QPalette.ColorRole.Text, QColor(colors.text))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(colors.bright_text))
            
            # ボタン色
            palette.setColor(QPalette.ColorRole.Button, QColor(colors.button))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors.button_text))
            
            # ハイライト色
            palette.setColor(QPalette.ColorRole.Highlight, QColor(colors.highlight))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors.highlighted_text))
            
            # リンク色
            palette.setColor(QPalette.ColorRole.Link, QColor(colors.link))
            palette.setColor(QPalette.ColorRole.LinkVisited, QColor(colors.link_visited))
            
            # ツールチップ色
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors.tooltip_base))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors.tooltip_text))
            
            # 無効化状態の色
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, 
                           QColor(colors.disabled_text))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, 
                           QColor(colors.disabled_button_text))
            
            return palette
            
        except Exception as e:
            self.logger.error(f"パレット作成エラー: {e}")
            return QPalette()
    
    def _apply_fonts(self, fonts: FontSettings):
        """フォントを適用"""
        try:
            app = QApplication.instance()
            if not app:
                return
            
            # アプリケーションフォント
            font = QFont(fonts.family, fonts.size)
            if fonts.weight == "bold":
                font.setBold(True)
            if fonts.style == "italic":
                font.setItalic(True)
            
            app.setFont(font)
            
        except Exception as e:
            self.logger.error(f"フォント適用エラー: {e}")
    
    def create_custom_theme(self, name: str, base_theme_id: str = "light") -> Optional[str]:
        """カスタムテーマを作成"""
        try:
            if base_theme_id not in self.themes:
                self.logger.error(f"ベーステーマが見つかりません: {base_theme_id}")
                return None
            
            base_theme = self.themes[base_theme_id]
            
            # カスタムテーマID生成
            custom_id = f"custom_{len([t for t in self.themes.values() if t.type == ThemeType.CUSTOM])}"
            
            # カスタムテーマ作成
            custom_theme = Theme(
                name=name,
                type=ThemeType.CUSTOM,
                colors=ColorScheme(**base_theme.colors.__dict__),
                fonts=FontSettings(**base_theme.fonts.__dict__),
                metadata={"description": f"カスタムテーマ: {name}", "author": "User"}
            )
            
            self.themes[custom_id] = custom_theme
            
            return custom_id
            
        except Exception as e:
            self.logger.error(f"カスタムテーマ作成エラー: {e}")
            return None
    
    def save_theme(self, theme_id: str) -> bool:
        """テーマをファイルに保存"""
        try:
            if theme_id not in self.themes:
                return False
            
            theme = self.themes[theme_id]
            
            # テーマディレクトリ作成
            themes_dir = os.path.join("assets", "themes")
            os.makedirs(themes_dir, exist_ok=True)
            
            # テーマデータ作成
            theme_data = {
                "name": theme.name,
                "type": theme.type.value,
                "colors": theme.colors.__dict__,
                "fonts": theme.fonts.__dict__,
                "metadata": theme.metadata
            }
            
            # ファイルに保存
            theme_path = os.path.join(themes_dir, f"{theme_id}.json")
            with open(theme_path, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"テーマを保存しました: {theme_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"テーマ保存エラー: {e}")
            return False
    
    def delete_theme(self, theme_id: str) -> bool:
        """テーマを削除"""
        try:
            if theme_id not in self.themes:
                return False
            
            theme = self.themes[theme_id]
            
            # システムテーマは削除不可
            if theme.type != ThemeType.CUSTOM:
                self.logger.warning(f"システムテーマは削除できません: {theme_id}")
                return False
            
            # 現在のテーマの場合はデフォルトに変更
            if self.current_theme and self.current_theme.name == theme.name:
                self.set_theme("light")
            
            # テーマを削除
            del self.themes[theme_id]
            
            # ファイルも削除
            themes_dir = os.path.join("assets", "themes")
            theme_path = os.path.join(themes_dir, f"{theme_id}.json")
            if os.path.exists(theme_path):
                os.remove(theme_path)
            
            self.logger.info(f"テーマを削除しました: {theme_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"テーマ削除エラー: {e}")
            return False
    
    def get_color(self, color_name: str) -> Optional[QColor]:
        """現在のテーマから色を取得"""
        try:
            if not self.current_theme:
                return None
            
            color_value = getattr(self.current_theme.colors, color_name, None)
            if color_value:
                return QColor(color_value)
            
            return None
            
        except Exception as e:
            self.logger.error(f"色取得エラー: {e}")
            return None
    
    def get_font(self, font_type: str = "default") -> Optional[QFont]:
        """現在のテーマからフォントを取得"""
        try:
            if not self.current_theme:
                return None
            
            fonts = self.current_theme.fonts
            
            if font_type == "editor":
                font = QFont(fonts.editor_family, fonts.editor_size)
                if fonts.editor_weight == "bold":
                    font.setBold(True)
                if fonts.editor_style == "italic":
                    font.setItalic(True)
            else:
                font = QFont(fonts.family, fonts.size)
                if fonts.weight == "bold":
                    font.setBold(True)
                if fonts.style == "italic":
                    font.setItalic(True)
            
            return font
            
        except Exception as e:
            self.logger.error(f"フォント取得エラー: {e}")
            return None
    
    def update_theme_colors(self, theme_id: str, color_updates: Dict[str, str]) -> bool:
        """テーマの色を更新"""
        try:
            if theme_id not in self.themes:
                return False
            
            theme = self.themes[theme_id]
            
            # 色を更新
            for color_name, color_value in color_updates.items():
                if hasattr(theme.colors, color_name):
                    setattr(theme.colors, color_name, color_value)
            
            # 現在のテーマの場合は再適用
            if self.current_theme and self.current_theme.name == theme.name:
                self._apply_theme(theme)
                self.theme_changed.emit(theme)
            
            return True
            
        except Exception as e:
            self.logger.error(f"テーマ色更新エラー: {e}")
            return False
    
    def update_theme_fonts(self, theme_id: str, font_updates: Dict[str, Any]) -> bool:
        """テーマのフォントを更新"""
        try:
            if theme_id not in self.themes:
                return False
            
            theme = self.themes[theme_id]
            
            # フォントを更新
            for font_attr, font_value in font_updates.items():
                if hasattr(theme.fonts, font_attr):
                    setattr(theme.fonts, font_attr, font_value)
            
            # 現在のテーマの場合は再適用
            if self.current_theme and self.current_theme.name == theme.name:
                self._apply_theme(theme)
                self.theme_changed.emit(theme)
            
            return True
            
        except Exception as e:
            self.logger.error(f"テーマフォント更新エラー: {e}")
            return False


# グローバルテーママネージャーインスタンス
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """グローバルテーママネージャーを取得"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def set_theme_manager(theme_manager: ThemeManager):
    """グローバルテーママネージャーを設定"""
    global _theme_manager
    _theme_manager = theme_manager

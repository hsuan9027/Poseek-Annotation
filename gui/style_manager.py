"""
Style management module for unified application styling
"""

from PySide6.QtWidgets import QMessageBox, QPushButton, QApplication

# Standard button style
STANDARD_BUTTON_STYLE = """
    QPushButton {
        background-color: #787878;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 2px 10px;
    }
    QPushButton:hover {
        background-color: #8C8C8C;
    }
    QPushButton:pressed {
        background-color: #646464;
    }
"""

# Primary button style for main actions
PRIMARY_BUTTON_STYLE = """
    QPushButton {
        background-color: #007BFF;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 2px 10px;
    }
    QPushButton:hover {
        background-color: #3399FF;
    }
    QPushButton:pressed {
        background-color: #0056b3;
    }
"""

# Circular help button style
HELP_BUTTON_STYLE = """
    QPushButton {
        border-radius: 10px;
        background-color: #787878;
        color: white;
        font-size: 18px;
        font-weight: bold;
        border: none;
    }
    QPushButton:hover {
        background-color: #8C8C8C;
    }
    QPushButton:pressed {
        background-color: #646464;
    }
"""

# Dialog button style
DIALOG_BUTTON_STYLE = """
    QPushButton {
        background-color: #4a86e8;
        color: white;
        padding: 8px 20px;
        border: none;
        border-radius: 4px;
        min-width: 80px;
    }
    QPushButton:hover {
        background-color: #5a96f8;
    }
"""

# Tab widget style
TAB_WIDGET_STYLE = """
    QTabWidget::pane {
        border: 1px solid #222222;
        background-color: #333333;
    }
    QTabBar::tab {
        background-color: #787878;
        color: white;
        padding: 2px 10px;
        margin-right: 2px;
        border: none;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
    }
    QTabBar::tab:selected {
        background-color: #007BFF;
    }
    QTabBar::tab:hover:!selected {
        background-color: #8C8C8C;
    }
    QTabBar::tab:!selected {
        margin-top: 2px;
    }
"""

# Background style
BACKGROUND_STYLE = """
    QWidget {
        background-color: #333333;
        color: white;
    }
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #444444;
        color: white;
        border: 1px solid #555555;
        border-radius: 3px;
        padding: 2px;
    }
    QTreeView, QListView, QTableView {
        background-color: #333333;
        color: white;
        border: 1px solid #555555;
    }
    QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {
        background-color: #555555;
    }
"""

# Global application style
GLOBAL_STYLE = BACKGROUND_STYLE

# Message box style
MESSAGE_BOX_STYLE = """
    QMessageBox {
        background-color: #333333;
        color: white;
    }
    QMessageBox QLabel {
        color: white;
    }
"""

# Scrollbar style
SCROLLBAR_STYLE = """
    QScrollBar:vertical {
        border: none;
        background: rgba(60, 60, 60, 150);
        width: 8px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: rgba(100, 100, 100, 150);
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        border: none;
        background: rgba(60, 60, 60, 150);
        height: 8px;
        margin: 0px;
    }
    QScrollBar::handle:horizontal {
        background: rgba(100, 100, 100, 150);
        min-width: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
"""

# Style application functions
def apply_standard_style(button):
    """Apply standard button style"""
    button.setStyleSheet(STANDARD_BUTTON_STYLE)

def apply_help_style(button):
    """Apply help button style"""
    button.setStyleSheet(HELP_BUTTON_STYLE)

def apply_primary_style(button):
    """Apply primary button style"""
    button.setStyleSheet(PRIMARY_BUTTON_STYLE)

def apply_dialog_style(dialog):
    """Apply dialog style"""
    dialog.setStyleSheet(BACKGROUND_STYLE)
    
    # Apply style to all buttons in dialog
    buttons = dialog.findChildren(QPushButton)
    for button in buttons:
        text = button.text().lower()
        if text in ["ok", "yes", "apply", "save"]:
            apply_primary_style(button)
        else:
            apply_standard_style(button)

def apply_tab_style(tab_widget):
    """Apply tab widget style"""
    tab_widget.setStyleSheet(TAB_WIDGET_STYLE)

def apply_global_style(app):
    """Apply global style to application"""
    app.setStyleSheet(GLOBAL_STYLE)

def apply_message_box_style(message_box):
    """Apply message box style"""
    message_box.setStyleSheet(MESSAGE_BOX_STYLE)
    
    # Apply standard style to all buttons
    buttons = message_box.findChildren(QPushButton)
    for button in buttons:
        text = button.text().lower()
        if text in ["ok", "yes", "apply", "save"]:
            apply_primary_style(button)
        else:
            apply_standard_style(button)

def create_styled_message_box(parent, title, text, icon=None, buttons=None, default_button=None, use_primary_buttons=True):
    """Create styled QMessageBox with consistent styling"""
    # Custom QMessageBox subclass for proper styling
    class StyledMessageBox(QMessageBox):
        def __init__(self, parent, title, text, icon, buttons, default_button, use_primary_buttons):
            super().__init__(parent)
            self.setWindowTitle(title)
            self.setText(text)
            
            if icon is not None:
                self.setIcon(icon)
            
            if buttons is not None:
                self.setStandardButtons(buttons)
            
            if default_button is not None:
                self.setDefaultButton(default_button)
            
            self.setStyleSheet(MESSAGE_BOX_STYLE)
            self.use_primary_buttons = use_primary_buttons
        
        def showEvent(self, event):
            """Apply button styles when dialog is shown"""
            buttons = self.findChildren(QPushButton)
            for button in buttons:
                std_button = self.standardButton(button)
                
                if std_button in [QMessageBox.Yes, QMessageBox.Ok, QMessageBox.Save, QMessageBox.Apply]:
                    apply_primary_style(button)
                else:
                    apply_standard_style(button)
            
            super().showEvent(event)
    
    return StyledMessageBox(parent, title, text, icon, buttons, default_button, use_primary_buttons)

class StyleManager:
    """Style manager for application styling"""
    
    @staticmethod
    def init_app_style(app):
        """Initialize application styles"""
        apply_global_style(app)
    
    @staticmethod
    def get_button_style(style_type="standard"):
        """Get button stylesheet"""
        if style_type == "primary":
            return PRIMARY_BUTTON_STYLE
        elif style_type == "help":
            return HELP_BUTTON_STYLE
        elif style_type == "dialog":
            return DIALOG_BUTTON_STYLE
        else:
            return STANDARD_BUTTON_STYLE
    
    @staticmethod
    def get_scrollbar_style():
        """Get scrollbar stylesheet"""
        return SCROLLBAR_STYLE
    
    @staticmethod
    def apply_style_to_widget(widget, style_type):
        """Apply style to widget"""
        if style_type == "standard_button":
            apply_standard_style(widget)
        elif style_type == "primary_button":
            apply_primary_style(widget)
        elif style_type == "help_button":
            apply_help_style(widget)
        elif style_type == "dialog":
            apply_dialog_style(widget)
        elif style_type == "tab":
            apply_tab_style(widget)
        elif style_type == "message_box":
            apply_message_box_style(widget)
        elif style_type == "global":
            apply_global_style(QApplication.instance())

# Global style manager instance
style_manager = StyleManager()

def get_style_manager():
    """Get global style manager instance"""
    return style_manager 
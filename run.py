#!/usr/bin/env python3
"""Main entry point for Poseek Annotation Tool."""

import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PySide6.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.tabs.annotation_tab import AnnotationTab
from gui.style_manager import apply_standard_style, apply_tab_style

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poseek Annotation Tool")
        self.setGeometry(100, 100, 1400, 900)
        
        self.setMinimumSize(800, 600)
        
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        apply_tab_style(self.tab_widget)
        
        self.annotation_tab = AnnotationTab()
        self.tab_widget.addTab(self.annotation_tab, "Pose Annotation")
        
        self.annotation_tab.annotation_dir_changed.connect(self.on_annotation_dir_changed)
        
        self.setWindowFlags(Qt.Window)
        
        self.apply_dark_theme()
    
    def apply_dark_theme(self):
        """Apply dark theme."""
        dark_stylesheet = """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #2b2b2b;
        }
        QTabWidget::tab-bar {
            alignment: center;
        }
        QTabBar::tab {
            background-color: #404040;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #0078d4;
        }
        QTabBar::tab:hover {
            background-color: #505050;
        }
        """
        self.setStyleSheet(dark_stylesheet)
    
    def on_annotation_dir_changed(self, directory):
        pass
    
    def closeEvent(self, event):
        """Handle close event."""
        if hasattr(self.annotation_tab, 'has_unsaved_changes') and self.annotation_tab.has_unsaved_changes:
            from gui.style_manager import create_styled_message_box
            from PySide6.QtWidgets import QMessageBox
            
            reply = create_styled_message_box(
                self, 
                "Unsaved Changes", 
                "You have unsaved changes. Do you want to save before closing?",
                QMessageBox.Question,
                buttons=QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            ).exec()
            
            if reply == QMessageBox.Save:
                if hasattr(self.annotation_tab, 'save_annotations'):
                    self.annotation_tab.save_annotations()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
                return
        
        event.accept()

def main():
    """Main entry point."""
    # Uncomment to suppress Qt warnings:
    # os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'
    
    app = QApplication(sys.argv)
    
    app.setApplicationName("Poseek Annotation Tool")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Poseek")
    
    app.setStyle('Fusion')
    
    try:
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
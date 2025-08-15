from PySide6.QtWidgets import (
    QLabel, QGraphicsView, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QDialog, QListWidget, QListWidgetItem, QLineEdit, QComboBox, QSizePolicy,
    QMessageBox, QTabWidget, QFrame, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
import os
import yaml
from gui.style_manager import apply_standard_style, apply_primary_style, apply_dialog_style, create_styled_message_box
from gui.utils import save_config
from PySide6.QtWidgets import QApplication


class GraphicsView(QGraphicsView):
    """Custom GraphicsView with mouse wheel zoom and drag support"""
    
    mouse_moved = Signal(float, float)  # Mouse position in scene coordinates
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Rendering settings
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Zoom settings
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        # Zoom parameters
        self._zoom_factor = 1.05
        self._panning = False
        self._last_pan_point = None
        self._min_scale = 0.5
        self._max_scale = 5.0
        self._current_scale = 1
        
        # View settings
        self.setAlignment(Qt.AlignCenter)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        self._extra_scene_size = 1000
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
    
    def setScene(self, scene):
        """Override setScene to expand scene rectangle"""
        super().setScene(scene)
        if scene:
            rect = scene.sceneRect()
            extended_rect = rect.adjusted(
                -self._extra_scene_size, 
                -self._extra_scene_size, 
                self._extra_scene_size, 
                self._extra_scene_size
            )
            scene.setSceneRect(extended_rect)
    
    def wheelEvent(self, event):
        """Handle mouse wheel zoom"""
        old_scale = self._current_scale
        
        if event.angleDelta().y() > 0:
            new_scale = old_scale * self._zoom_factor
        else:
            new_scale = old_scale / self._zoom_factor
        
        new_scale = max(self._min_scale, min(new_scale, self._max_scale))
        scale_factor = new_scale / old_scale
        
        if abs(scale_factor - 1.0) > 0.001:
            self.scale(scale_factor, scale_factor)
            self._current_scale = new_scale
        
        event.accept()
    
    def resetZoom(self):
        """Reset zoom to 1:1"""
        scale_factor = 1.0 / self._current_scale
        self.scale(scale_factor, scale_factor)
        self._current_scale = 1.0
    
    def get_current_scale(self):
        """Get current zoom scale"""
        return self._current_scale
    
    def set_scale(self, scale_value):
        """Set zoom scale"""
        if scale_value <= 0:
            return
        
        scale_value = max(self._min_scale, min(scale_value, self._max_scale))
        scale_factor = scale_value / self._current_scale
        
        if abs(scale_factor - 1.0) > 0.001:
            self.scale(scale_factor, scale_factor)
            self._current_scale = scale_value
    
    def get_view_center(self):
        """Get view center in scene coordinates"""
        view_rect = self.viewport().rect()
        return self.mapToScene(view_rect.center())
    
    def set_view_center(self, scene_point):
        """Center view on scene point"""
        if scene_point:
            self.centerOn(scene_point)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        scene_pos = self.mapToScene(event.pos())
        self.mouse_moved.emit(scene_pos.x(), scene_pos.y())
        super().mouseMoveEvent(event)


class ClickableLabel(QLabel):
    """Clickable label with right-click delete"""
    
    delete_requested = Signal(int)
    
    def __init__(self, text, index, parent=None):
        super().__init__(text, parent)
        self.index = index
        self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.delete_requested.emit(self.index)
        super().mousePressEvent(event)


class KeypointEditor:
    """Keypoint editor for managing keypoints and connections"""
    
    def __init__(self, parent, config, bodyparts, connections, keypoints_config_path):
        """Initialize keypoint editor"""
        self.parent = parent
        self.config = config
        self.bodyparts = bodyparts
        self.connections = connections
        self.keypoints_config_path = keypoints_config_path
        self.saved_configs = self.load_saved_configs()
    
    def load_saved_configs(self):
        """Load saved keypoint configurations"""
        try:
            with open(self.keypoints_config_path, 'r', encoding='utf-8') as f:
                configs = yaml.safe_load(f)
            return configs if isinstance(configs, dict) else {}
        except Exception as e:
            print(f"Error loading keypoints config {self.keypoints_config_path}: {e}")
            return {}
    
    def save_config_to_file(self):
        """Save configurations to keypoints_cfg.yaml"""
        try:
            save_config(self.keypoints_config_path, self.saved_configs)
            return True
        except Exception as e:
            print(f"Error saving keypoints config to {self.keypoints_config_path}: {e}")
            return False
    
    def open_editor(self):
        """Open keypoint editor dialog"""
        config_name_from_parent = self.config.get('keypoints', {}).get('name', "")
        self.saved_configs = self.load_saved_configs() 

        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Edit Keypoints")
        dialog.setMinimumWidth(650)
        dialog.setMinimumHeight(600) 

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        
        # Configuration selection group
        config_group = QGroupBox()
        config_group_layout = QVBoxLayout(config_group)
        
        config_selection_layout = QHBoxLayout()
        
        self.config_combo = QComboBox()
        config_selection_layout.addWidget(self.config_combo, 1) 
        
        delete_config_button = QPushButton("Delete")
        delete_config_button.clicked.connect(self.delete_selected_config)
        delete_config_button.setToolTip("Delete selected configuration")
        apply_standard_style(delete_config_button)
        delete_config_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        config_selection_layout.addWidget(delete_config_button)
        
        config_group_layout.addLayout(config_selection_layout)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Configuration Name:"))
        self.config_name_input = QLineEdit()
        self.config_name_input.setText(config_name_from_parent)
        self.config_name_input.setPlaceholderText("Enter name to save configuration")
        name_layout.addWidget(self.config_name_input)
        config_group_layout.addLayout(name_layout)

        layout.addWidget(config_group)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: rgba(100, 100, 100, 150);")
        layout.addWidget(separator)
        
        # Create tabs
        tab_widget = QTabWidget()
        apply_dialog_style(tab_widget)
        bodyparts_widget = self._create_bodyparts_tab()
        connections_widget = self._create_connections_tab()
        tab_widget.addTab(bodyparts_widget, "Body Parts")
        tab_widget.addTab(connections_widget, "Connections")
        layout.addWidget(tab_widget) 
        
        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch(1)
        save_button = QPushButton("Save") 
        save_button.clicked.connect(lambda: self._save_and_close(dialog))
        apply_primary_style(save_button) 
        save_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        save_layout.addWidget(save_button)
        layout.addLayout(save_layout)
        
        apply_dialog_style(dialog)
        
        # Setup config combo
        self.update_config_combo()
        current_config_index = self.config_combo.findText(config_name_from_parent)
        
        if current_config_index > 0:
            self.config_combo.setCurrentIndex(current_config_index)
        else:
            self.config_combo.setCurrentIndex(0)
            
        self.config_combo.currentIndexChanged.connect(self.on_config_selected) 

        dialog.exec_()
    
    def update_config_combo(self):
        """Update configuration combo box"""
        self.config_combo.clear()
        self.config_combo.addItem("-- Create New Configuration --")
        
        if self.saved_configs:
            sorted_config_names = sorted(self.saved_configs.keys())
            for config_name in sorted_config_names:
                self.config_combo.addItem(config_name)
    
    def on_config_selected(self, _):
        """Handle configuration selection"""
        selected_text = self.config_combo.currentText()

        if selected_text == "-- Create New Configuration --":
            self.config_name_input.clear()
            self.config_name_input.setPlaceholderText("Enter name for new configuration")
            self.keypoints_list.clear()
            self.connections_list.clear()
            self.update_connection_combos()

        elif selected_text in self.saved_configs:
            self.config_name_input.setText(selected_text)
            self.load_selected_config()

    def load_selected_config(self):
        """Load selected configuration into editor"""
        config_name = self.config_combo.currentText()
        if config_name.startswith("--") or config_name not in self.saved_configs:
            return
        
        selected_config = self.saved_configs[config_name]
        
        self.keypoints_list.clear()
        if 'bodyparts' in selected_config:
            for i, part in enumerate(selected_config['bodyparts'], 1):
                self.keypoints_list.addItem(f"{i}. {part}")
        
        self.connections_list.clear()
        if 'connections' in selected_config:
            self.update_connection_combos()
            
            temp_bodyparts = []
            for i in range(self.keypoints_list.count()):
                text = self.keypoints_list.item(i).text()
                if '. ' in text:
                    text = text.split('. ', 1)[1]
                temp_bodyparts.append(text)
            
            idx = 1
            for connection in selected_config['connections']:
                if len(connection) == 2 and connection[0] < len(temp_bodyparts) and connection[1] < len(temp_bodyparts):
                    item_text = f"{idx}. {temp_bodyparts[connection[0]]} ↔ {temp_bodyparts[connection[1]]}"
                    item = QListWidgetItem(item_text)
                    item.connection = connection
                    self.connections_list.addItem(item)
                    idx += 1
    
    def update_connection_combos(self):
        """Update connection combo boxes"""
        bodyparts = []
        for i in range(self.keypoints_list.count()):
            text = self.keypoints_list.item(i).text()
            if '. ' in text:
                text = text.split('. ', 1)[1]
            bodyparts.append(text)
        
        first_idx = self.first_point_combo.currentIndex()
        second_idx = self.second_point_combo.currentIndex()
        
        self.first_point_combo.clear()
        self.second_point_combo.clear()
        
        for part in bodyparts:
            self.first_point_combo.addItem(part)
            self.second_point_combo.addItem(part)
        
        if first_idx >= 0 and first_idx < len(bodyparts):
            self.first_point_combo.setCurrentIndex(first_idx)
        if second_idx >= 0 and second_idx < len(bodyparts):
            self.second_point_combo.setCurrentIndex(second_idx)
    
    
    def _create_bodyparts_tab(self):
        """Create body parts tab"""
        bodyparts_widget = QWidget()
        bodyparts_layout = QVBoxLayout(bodyparts_widget)
        
        # Create keypoints list
        keypoints_list = QListWidget()
        keypoints_list.setStyleSheet("""
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid rgba(100, 100, 100, 100);
            }
            QListWidget::item:selected {
                background-color: rgba(100, 100, 100, 150);
            }
            QListWidget::item:hover {
                background-color: rgba(80, 80, 80, 150);
            }
        """)
        
        # Enable drag and drop
        keypoints_list.setDragDropMode(QListWidget.InternalMove)
        keypoints_list.setDefaultDropAction(Qt.MoveAction)
        keypoints_list.setDragEnabled(True)
        keypoints_list.setAcceptDrops(True)
        keypoints_list.setDropIndicatorShown(True)
        keypoints_list.setSelectionMode(QListWidget.SingleSelection)
        
        bodyparts_layout.addWidget(QLabel("Add or delete bodyparts:"))
        
        for i, part in enumerate(self.bodyparts, 1):
            keypoints_list.addItem(f"{i}. {part}")
        
        keypoints_list.model().rowsMoved.connect(lambda: self._update_bodyparts_numbers(keypoints_list))
        
        bodyparts_layout.addWidget(keypoints_list)
        
        # Edit controls
        edit_layout = QHBoxLayout()
        new_keypoint_input = QLineEdit()
        new_keypoint_input.setPlaceholderText("Enter new keypoint name")
        edit_layout.addWidget(new_keypoint_input)
        
        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: self.add_keypoint(new_keypoint_input, keypoints_list))
        apply_standard_style(add_button)
        add_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        edit_layout.addWidget(add_button)
        
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda: self.delete_keypoint(keypoints_list))
        apply_standard_style(delete_button)
        delete_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        edit_layout.addWidget(delete_button)
        
        bodyparts_layout.addLayout(edit_layout)
        
        self.keypoints_list = keypoints_list
        self.bodyparts_widget = bodyparts_widget
        
        return bodyparts_widget
    
    def _update_bodyparts_numbers(self, list_widget):
        """Update bodyparts list numbering"""
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            original_text = item.text()
            if '. ' in original_text:
                original_text = original_text.split('. ', 1)[1]
            item.setText(f"{i+1}. {original_text}")
    
    def _create_connections_tab(self):
        """Create connections tab"""
        connections_widget = QWidget()
        connections_layout = QVBoxLayout(connections_widget)
        
        connections_layout.addWidget(QLabel("Define connections between keypoints:"))
        
        # Create connections list
        connections_list = QListWidget()
        connections_list.setStyleSheet("""
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid rgba(100, 100, 100, 100);
            }
            QListWidget::item:selected {
                background-color: rgba(100, 100, 100, 150);
            }
            QListWidget::item:hover {
                background-color: rgba(80, 80, 80, 150);
            }
        """)
        
        # Enable drag and drop
        connections_list.setDragDropMode(QListWidget.InternalMove)
        connections_list.setDefaultDropAction(Qt.MoveAction)
        connections_list.setDragEnabled(True)
        connections_list.setAcceptDrops(True)
        connections_list.setDropIndicatorShown(True)
        connections_list.setSelectionMode(QListWidget.SingleSelection)
        
        # Add existing connections
        idx = 1
        for connection in self.connections:
            if len(connection) == 2 and connection[0] < len(self.bodyparts) and connection[1] < len(self.bodyparts):
                item_text = f"{idx}. {self.bodyparts[connection[0]]} ↔ {self.bodyparts[connection[1]]}"
                item = QListWidgetItem(item_text)
                item.connection = connection
                connections_list.addItem(item)
                idx += 1
        
        connections_list.model().rowsMoved.connect(lambda: self._update_connections_numbers(connections_list))
        
        connections_layout.addWidget(connections_list)
        
        # Connection edit controls
        connection_edit_layout = QHBoxLayout()
        connection_edit_layout.setSpacing(10)
        
        first_point_combo = QComboBox()
        first_point_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(40, 40, 40, 200);
                color: white;
                border: 1px solid rgba(100, 100, 100, 150);
                border-radius: 4px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(dropdown-arrow.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(40, 40, 40, 200);
                color: white;
                selection-background-color: rgba(100, 100, 100, 150);
            }
        """)
        
        second_point_combo = QComboBox()
        second_point_combo.setStyleSheet(first_point_combo.styleSheet())
        
        first_point_combo.setMinimumWidth(200)
        second_point_combo.setMinimumWidth(200)
        
        first_point_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        second_point_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        
        for part in self.bodyparts:
            first_point_combo.addItem(part)
            second_point_combo.addItem(part)
        
        connection_edit_layout.addWidget(first_point_combo)
        connection_edit_layout.addSpacing(5)
        connection_edit_layout.addWidget(QLabel("↔"))
        connection_edit_layout.addSpacing(5)
        connection_edit_layout.addWidget(second_point_combo)
        
        add_connection_button = QPushButton("Add")
        add_connection_button.clicked.connect(lambda: self.add_connection(
            first_point_combo, second_point_combo, connections_list
        ))
        apply_standard_style(add_connection_button)
        add_connection_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        connection_edit_layout.addSpacing(10)
        connection_edit_layout.addWidget(add_connection_button)
        
        delete_connection_button = QPushButton("Delete")
        delete_connection_button.clicked.connect(lambda: self.delete_connection(connections_list))
        apply_standard_style(delete_connection_button)
        delete_connection_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        connection_edit_layout.addWidget(delete_connection_button)
        
        connections_layout.addLayout(connection_edit_layout)
        
        self.connections_list = connections_list
        self.first_point_combo = first_point_combo
        self.second_point_combo = second_point_combo
        self.connections_widget = connections_widget
        
        return connections_widget
    
    def _update_connections_numbers(self, list_widget):
        """Update connections list numbering"""
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            original_text = item.text()
            if '. ' in original_text:
                original_text = original_text.split('. ', 1)[1]
            item.setText(f"{i+1}. {original_text}")
    
    def add_keypoint(self, input_field, list_widget):
        """Add new keypoint"""
        new_keypoint = input_field.text().strip()
        
        existing_keypoints = []
        for i in range(list_widget.count()):
            text = list_widget.item(i).text()
            if '. ' in text:
                text = text.split('. ', 1)[1]
            existing_keypoints.append(text)
        
        if new_keypoint and new_keypoint not in existing_keypoints:
            new_index = list_widget.count() + 1
            list_widget.addItem(f"{new_index}. {new_keypoint}")
            input_field.clear()
            self.update_connection_combos()
    
    def delete_keypoint(self, list_widget):
        """Delete selected keypoint"""
        current_item = list_widget.currentItem()
        if current_item:
            list_widget.takeItem(list_widget.row(current_item))
            self._update_bodyparts_numbers(list_widget)
            self.update_connection_combos()
    
    def add_connection(self, first_combo, second_combo, connections_list):
        """Add connection between keypoints"""
        first_idx = first_combo.currentIndex()
        second_idx = second_combo.currentIndex()
        
        if first_idx == second_idx:
            create_styled_message_box(None, "Warning", "Cannot connect a point to itself.", QMessageBox.Warning, use_primary_buttons=False).exec()
            return
        
        temp_bodyparts = []
        for i in range(self.keypoints_list.count()):
            text = self.keypoints_list.item(i).text()
            if '. ' in text:
                text = text.split('. ', 1)[1]
            temp_bodyparts.append(text)
        
        connection = [first_idx, second_idx]
        reverse_connection = [second_idx, first_idx]
        
        for i in range(connections_list.count()):
            item = connections_list.item(i)
            if (item.connection == connection or 
                item.connection == reverse_connection):
                create_styled_message_box(None, "Warning", "This connection already exists.", QMessageBox.Warning, use_primary_buttons=False).exec()
                return
        
        new_index = connections_list.count() + 1
        item_text = f"{new_index}. {temp_bodyparts[first_idx]} ↔ {temp_bodyparts[second_idx]}"
        item = QListWidgetItem(item_text)
        item.connection = connection
        connections_list.addItem(item)
    
    def delete_connection(self, connections_list):
        """Delete selected connections"""
        selected_items = connections_list.selectedItems()
        for item in selected_items:
            connections_list.takeItem(connections_list.row(item))
        self._update_connections_numbers(connections_list)
    
    def _save_and_close(self, dialog):
        """Save changes and close dialog"""
        if self.save_keypoints_and_connections():
             dialog.accept()
    
    def save_keypoints_and_connections(self):
        """Save keypoints and connections configuration"""
        new_bodyparts = []
        for i in range(self.keypoints_list.count()):
            text = self.keypoints_list.item(i).text()
            if '. ' in text:
                text = text.split('. ', 1)[1]
            new_bodyparts.append(text)
        
        config_name = self.config_name_input.text().strip()
        
        if not config_name:
            create_styled_message_box(None, "Error", "Configuration name cannot be empty.", QMessageBox.Warning).exec()
            return False
        if config_name.startswith("--"):
            create_styled_message_box(None, "Error", f"Invalid configuration name: '{config_name}'", QMessageBox.Warning).exec()
            return False
        
        new_connections = []
        for i in range(self.connections_list.count()):
            item = self.connections_list.item(i)
            if hasattr(item, 'connection'):
                if (item.connection[0] < len(new_bodyparts) and 
                    item.connection[1] < len(new_bodyparts)):
                    new_connections.append(item.connection)
        
        self.saved_configs[config_name] = {
            'name': config_name,
            'bodyparts': new_bodyparts,
            'connections': new_connections
        }
        
        # Save to keypoints_cfg.yaml
        save_to_keypoints_ok = self.save_config_to_file()
        save_message = f"\n• Saved as '{config_name}' to keypoints_cfg.yaml" if save_to_keypoints_ok else f"\n• Failed to save '{config_name}' to keypoints_cfg.yaml"
        
        # Update main config
        self.config['keypoints']['name'] = config_name
        self.config['keypoints']['bodyparts'] = new_bodyparts
        self.config['keypoints']['connections'] = new_connections
        if 'model' in self.config and 'n_keypoints' in self.config['model']:
            self.config['model']['n_keypoints'] = len(new_bodyparts)
            
        # Save to train_cfg.yaml
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        train_config_path = os.path.join(project_root, 'train_cfg.yaml')
        save_to_train_ok = False
        try:
            save_config(train_config_path, self.config)
            save_to_train_ok = True
        except Exception as e:
            print(f"Error saving to train_cfg.yaml: {e}")
            save_message += f"\n• Failed to update train_cfg.yaml"
        
        # Update parent
        if hasattr(self.parent, 'config_manager'):
            self.parent.config_manager.set_bodyparts(new_bodyparts)
            self.parent.config_manager.set_connections(new_connections)
            if hasattr(self.parent.config_manager, 'keypoints_updated'):
                self.parent.config_manager.keypoints_updated.emit(new_bodyparts, new_connections)
        
        # Update combo box
        self.update_config_combo()
        index = self.config_combo.findText(config_name)
        if index >= 0:
            self.config_combo.setCurrentIndex(index)

        # Show result
        final_message = f"Configuration '{config_name}' processed:\n"
        final_message += f"• {len(new_bodyparts)} keypoints, {len(new_connections)} connections"
        if save_to_train_ok:
             final_message += f"\n• Updated train_cfg.yaml for the current project"
        final_message += save_message
        
        create_styled_message_box(None, "Save Result", 
            final_message,
            QMessageBox.Information,
            use_primary_buttons=True
        ).exec()
        
        return True
    
    def delete_selected_config(self):
        """Delete selected configuration"""
        config_name = self.config_combo.currentText()
        
        if config_name.startswith("--"):
            create_styled_message_box(None, "Warning", 
                "Please select a valid configuration to delete.", 
                QMessageBox.Warning, 
                use_primary_buttons=False
            ).exec()
            return
        
        confirm = create_styled_message_box(None, "Confirm Delete", 
            f"Are you sure you want to delete the '{config_name}' configuration?", 
            QMessageBox.Question, 
            use_primary_buttons=False,
            buttons=QMessageBox.Yes | QMessageBox.No
        ).exec()
        
        if confirm != QMessageBox.Yes:
            return
        
        if config_name in self.saved_configs:
            del self.saved_configs[config_name]
            
            if self.save_config_to_file():
                self.update_config_combo()
                self.config_combo.setCurrentIndex(0)
                
                create_styled_message_box(None, "Success", 
                    f"Configuration '{config_name}' deleted successfully", 
                    QMessageBox.Information, 
                    use_primary_buttons=True
                ).exec()


class CheckpointComboBox(QWidget):
    """Checkpoint selection combo box"""
    
    checkpointSelected = Signal(str)  # Signal: emitted when selection changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.ckpt_dir = os.path.join(self.project_root, 'ckpt')
        self.selected_checkpoint = None
        
        self.initUI()
        self.load_checkpoints()
    
    def initUI(self):
        """Initialize UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        self.combo_box = NativeComboBox()
        self.combo_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_box.setMinimumWidth(250)
        self.combo_box.currentIndexChanged.connect(self.on_selection_changed)
        layout.addWidget(self.combo_box)
        
        self.setLayout(layout)
    
    def load_checkpoints(self):
        """Load checkpoint files into combo box"""
        self.combo_box.clear()
        
        if not os.path.exists(self.ckpt_dir):
            try:
                os.makedirs(self.ckpt_dir, exist_ok=True)
                self.combo_box.addItem("No available checkpoints", None)
            except Exception as e:
                self.combo_box.addItem(f"Error creating directory: {str(e)}", None)
            return
        
        self.combo_box.addItem("Select a checkpoint", None)
        
        ckpt_files = []
        for root, _, files in os.walk(self.ckpt_dir):
            for file in files:
                if file.endswith('.ckpt'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.ckpt_dir)
                    ckpt_files.append((rel_path, file_path))
        
        if not ckpt_files:
            self.combo_box.addItem("No available checkpoints", None)
            return
        
        for rel_path, full_path in sorted(ckpt_files):
            self.combo_box.addItem(rel_path, full_path)
    
    def on_selection_changed(self, index):
        """Handle selection change"""
        if index > 0:  # Skip default selection
            self.selected_checkpoint = self.combo_box.itemData(index)
            self.checkpointSelected.emit(self.selected_checkpoint)
    
    def get_selected_checkpoint(self):
        """Get selected checkpoint path"""
        return self.selected_checkpoint
    
    def set_checkpoint(self, checkpoint_path):
        """Set current checkpoint selection"""
        if not checkpoint_path:
            self.combo_box.setCurrentIndex(0)
            return
            
        for i in range(self.combo_box.count()):
            if self.combo_box.itemData(i) == checkpoint_path:
                self.combo_box.setCurrentIndex(i)
                return
        
        self.load_checkpoints()
        for i in range(self.combo_box.count()):
            if self.combo_box.itemData(i) == checkpoint_path:
                self.combo_box.setCurrentIndex(i)
                return


class NativeComboBox(QComboBox):
    """Native-styled combo box with auto-refresh"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyle(QApplication.style())
    
    def showPopup(self):
        """Override to refresh content before showing popup"""
        parent = self.parent()
        if parent and isinstance(parent, CheckpointComboBox):
            current_data = None
            if self.currentIndex() >= 0:
                current_data = self.itemData(self.currentIndex())
            
            parent.load_checkpoints()
            
            if current_data:
                for i in range(self.count()):
                    if self.itemData(i) == current_data:
                        self.setCurrentIndex(i)
                        break
        
        super().showPopup()
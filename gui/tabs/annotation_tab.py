"""Main annotation tab controller."""

import os
from PySide6.QtWidgets import QWidget, QApplication, QMessageBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent

from .managers import (
    FileManager, AnnotationManager, GraphicsManager, 
    UIManager, ConfigManager, EventHandler
)
from gui.data_model import AnnotationDataModel


class AnnotationTab(QWidget):
    """Annotation tab controller."""
    
    annotation_dir_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        self._init_managers()
        self._connect_signals()
        self._init_ui()
        self._load_initial_config()
        self.setFocusPolicy(Qt.StrongFocus)
        self.has_unsaved_changes = False
    
    def _init_managers(self):
        """Initialize managers."""
        self.data_model = AnnotationDataModel(self)
        self.file_manager = FileManager(self)
        self.annotation_manager = AnnotationManager(self)
        self.graphics_manager = GraphicsManager(self)
        self.ui_manager = UIManager(self)
        self.config_manager = ConfigManager(self)
        self.event_handler = EventHandler(self)
    
    def _connect_signals(self):
        """Connect signals between managers."""
        # UI Manager signals
        self.ui_manager.folder_selected.connect(self.file_manager.select_directory)
        self.ui_manager.file_selected.connect(self.file_manager.on_file_selected)
        self.ui_manager.folder_input_changed.connect(self.file_manager.on_folder_input_changed)
        self.ui_manager.point_size_changed.connect(self._on_point_size_changed)
        self.ui_manager.edit_keypoints_clicked.connect(self.config_manager.edit_keypoints)
        self.ui_manager.bodypart_clicked.connect(self._on_bodypart_clicked)
        self.ui_manager.save_clicked.connect(self.annotation_manager.save_annotation)
        self.ui_manager.help_clicked.connect(self.event_handler.show_help)
        self.ui_manager.export_clicked.connect(self._handle_export_request)
        
        # File Manager signals
        self.file_manager.directory_changed.connect(self._on_directory_changed)
        self.file_manager.image_loaded.connect(self._on_image_loaded)
        
        # Annotation Manager signals
        self.annotation_manager.annotation_dir_changed.connect(self.annotation_dir_changed)
        self.annotation_manager.annotation_saved.connect(self._on_annotation_saved)
        self.annotation_manager.annotations_loaded.connect(self._on_annotations_loaded)
        
        # Graphics Manager signals
        self.graphics_manager.point_added.connect(self._on_point_added)
        self.graphics_manager.point_selected.connect(self._on_point_selected)
        self.graphics_manager.selection_changed.connect(self._on_selection_changed)
        self.graphics_manager.view_updated.connect(self._on_view_updated)
        
        # Config Manager signals
        self.config_manager.config_updated.connect(self._on_config_updated)
        self.config_manager.keypoints_updated.connect(self._on_keypoints_updated)
        
        # Event Handler signals
        self.event_handler.point_add_requested.connect(self._handle_add_point_request)
        self.event_handler.save_requested.connect(self.annotation_manager.save_annotation)
        self.event_handler.next_image_requested.connect(self.file_manager.load_next_image)
        self.event_handler.previous_image_requested.connect(self.file_manager.load_previous_image)
        self.event_handler.move_view_requested.connect(self.graphics_manager.move_image)
        self.event_handler.delete_points_requested.connect(self._handle_delete_points_request)
        self.event_handler.clear_selection_requested.connect(self.graphics_manager.clear_selection)
        self.event_handler.help_requested.connect(self.event_handler.show_help)
        self.event_handler.selection_click.connect(self._handle_selection_click)
        self.event_handler.rectangle_selection.connect(self._handle_rectangle_selection)
        
        # Data model signals
        self.data_model.points_changed.connect(self._on_data_points_changed)
        self.data_model.selection_changed.connect(self._on_data_selection_changed)
    
    def _init_ui(self):
        """Initialize UI."""
        self.ui_manager.init_ui(self)
        
        graphics_view, graphics_scene = self.ui_manager.get_graphics_components()
        file_model, tree_view = self.ui_manager.get_file_model_components()
        
        self.graphics_manager.set_ui_components(graphics_view, graphics_scene)
        self.event_handler.set_graphics_components(graphics_view, graphics_scene)
        
        if graphics_view:
            graphics_view.setFocusPolicy(Qt.StrongFocus)
        
        self.file_manager.set_ui_components(
            tree_view, file_model, self.ui_manager.selected_folder_input,
            self.ui_manager.stacked_widget, graphics_view, graphics_scene
        )
        
        self.annotation_manager.set_ui_components(graphics_scene, self.ui_manager.part_labels)
        
        self._setup_mouse_events()
        
        if graphics_view and hasattr(graphics_view, 'mouse_moved'):
            graphics_view.mouse_moved.connect(self.ui_manager.update_mouse_coordinates)
    
    def _setup_mouse_events(self):
        """Setup mouse event handlers."""
        graphics_view, _ = self.ui_manager.get_graphics_components()
        if graphics_view:
            if not hasattr(graphics_view, '_original_mousePressEvent'):
                graphics_view._original_mousePressEvent = graphics_view.mousePressEvent
                graphics_view._original_mouseMoveEvent = graphics_view.mouseMoveEvent
                graphics_view._original_mouseReleaseEvent = graphics_view.mouseReleaseEvent
            
            def mouse_press_event(event):
                if event.button() == Qt.LeftButton:
                    scene_pos = graphics_view.mapToScene(event.pos())
                    self.event_handler.handle_selection_click(scene_pos, event)
                else:
                    graphics_view._original_mousePressEvent(event)
            
            def mouse_move_event(event):
                if event.buttons() & Qt.LeftButton:
                    scene_pos = graphics_view.mapToScene(event.pos())
                    self.event_handler.handle_selection_move(scene_pos)
                else:
                    graphics_view._original_mouseMoveEvent(event)
            
            def mouse_release_event(event):
                if event.button() == Qt.LeftButton:
                    self.event_handler.handle_selection_release()
                else:
                    graphics_view._original_mouseReleaseEvent(event)
            
            graphics_view.mousePressEvent = mouse_press_event
            graphics_view.mouseMoveEvent = mouse_move_event
            graphics_view.mouseReleaseEvent = mouse_release_event
    
    def _load_initial_config(self):
        """Load initial configuration."""
        if self.config_manager.load_main_config():
            config = self.config_manager.get_config()
            config_name = config.get('keypoints', {}).get('name', '')
            self.ui_manager.update_keypoint_config_name(config_name)
    
    # Signal handlers
    
    def _on_point_size_changed(self, size):
        self.graphics_manager.set_point_size(size)
        self.graphics_manager.update_all_points()
    
    def _on_bodypart_clicked(self, bodypart_idx):
        self.graphics_manager.select_point(bodypart_idx)
        self.data_model.select_point(bodypart_idx)
    
    def _on_directory_changed(self, directory):
        self.ui_manager.update_directory_ui(directory)
    
    def _on_image_loaded(self, image_path):
        self.annotation_manager.set_current_image_path(image_path)
        
        self.annotation_manager.load_annotation(image_path)
        
        current_points = self.annotation_manager.get_all_points()
        self.data_model.set_points(current_points)
        
        current_index, total_count = self.file_manager.get_image_info()
        self.ui_manager.update_image_info(current_index, total_count)
        
        self.graphics_manager.clear_selection()
        first_unmarked = self.graphics_manager.get_next_bodypart_index()
        if first_unmarked < len(self.config_manager.get_bodyparts()):
            self.graphics_manager.set_selected_points([first_unmarked])
            self.graphics_manager.selection_changed.emit([first_unmarked])
            self.ui_manager.set_selected_unmarked_point_color(first_unmarked)
        
        self.setFocus()
    
    def _on_annotation_saved(self, _csv_path):
        self.has_unsaved_changes = False
    
    def _on_annotations_loaded(self, _all_annotations):
        pass
    
    def _on_point_added(self, x, y, bodypart_idx):
        self.annotation_manager.add_point(bodypart_idx, x, y)
        self.data_model.add_point(bodypart_idx, x, y)
        self.has_unsaved_changes = True
        
        next_idx = self.graphics_manager.get_next_bodypart_index()
        if next_idx >= len(self.config_manager.get_bodyparts()):
            self.graphics_manager.clear_selection()
            self.ui_manager.update_all_bodyparts()
        else:
            self.graphics_manager.clear_selection()
            self.graphics_manager.set_selected_points([next_idx])
            self.graphics_manager.selection_changed.emit([next_idx])
            self.ui_manager.update_all_bodyparts()
            self.ui_manager.set_selected_unmarked_point_color(next_idx)
    
    def _on_point_selected(self, _bodypart_idx):
        self._sync_data_between_managers()
    
    def _on_selection_changed(self, _selected_points):
        self._sync_data_between_managers()
    
    def _on_view_updated(self):
        pass
    
    def _on_config_updated(self, config):
        bodyparts = config.get('keypoints', {}).get('bodyparts', [])
        connections = config.get('keypoints', {}).get('connections', [])
        config_name = config.get('keypoints', {}).get('name', '')
        self.ui_manager.update_keypoint_config_name(config_name)
        self._update_keypoints_config(bodyparts, connections)
    
    def _on_keypoints_updated(self, bodyparts, connections):
        self._update_keypoints_config(bodyparts, connections)
    
    def _update_keypoints_config(self, bodyparts, connections):
        """Update keypoint configuration."""
        self.ui_manager.set_config(bodyparts, connections)
        self.ui_manager.rebuild_bodyparts_ui()
        self.graphics_manager.set_config(bodyparts, connections)
        self.annotation_manager.set_config(bodyparts, connections)
        self._sync_data_between_managers()
    
    def _handle_add_point_request(self):
        result = self.graphics_manager.add_point_at_cursor()
        if result == 'all_complete':
            self.file_manager.load_next_image()
        elif result:
            self._sync_data_between_managers()
    
    def _handle_delete_points_request(self):
        selected_points = self.graphics_manager.get_selected_points()
        if not selected_points:
            return
        
        for bodypart_idx in selected_points:
            self.annotation_manager.remove_point(bodypart_idx)
            self.data_model.remove_point(bodypart_idx)
        
        success = self.graphics_manager.delete_selected_points()
        if success:
            self.has_unsaved_changes = True
    
    def _handle_selection_click(self, scene_pos, event):
        bodypart_idx = self.graphics_manager.find_point_at_position(scene_pos)
        
        if bodypart_idx is not None:
            if event.modifiers() & Qt.ControlModifier:
                self.graphics_manager.toggle_point_selection(bodypart_idx)
            else:
                self.graphics_manager.select_point(bodypart_idx)
        else:
            self.event_handler._start_selection(scene_pos)
        
        current_selected = self.graphics_manager.get_selected_points()
        self.data_model.set_selected_points(current_selected)
    
    def _handle_rectangle_selection(self, selection_rect):
        selected_points = []
        points = self.graphics_manager.get_points()
        
        for bodypart_idx, (x, y) in points.items():
            if selection_rect.contains(x, y):
                selected_points.append(bodypart_idx)
        
        if selected_points:
            self.graphics_manager.set_selected_points(selected_points)
            self.graphics_manager.update_all_points()
            self.graphics_manager.selection_changed.emit(selected_points)
            self.data_model.set_selected_points(selected_points)
    
    def _sync_data_between_managers(self):
        """Sync data between managers."""
        points = self.annotation_manager.get_all_points()
        selected_points = self.graphics_manager.get_selected_points()
        
        current_complete_state = self.graphics_manager.all_points_complete
        
        self.graphics_manager.set_points(points)
        self.graphics_manager.set_selected_points(selected_points)
        
        self.graphics_manager.all_points_complete = current_complete_state
        
        self.ui_manager.set_points(points)
        self.ui_manager.set_selected_points(selected_points)
        
        self.ui_manager.update_all_bodyparts()
        self.graphics_manager.update_all_points()
    
    def _on_data_points_changed(self, points):
        self.graphics_manager.set_points(points)
        self.ui_manager.set_points(points)
        self.ui_manager.update_all_bodyparts()
        self.graphics_manager.update_all_points()
    
    def _on_data_selection_changed(self, selected_points):
        self.graphics_manager.set_selected_points(selected_points)
        self.ui_manager.set_selected_points(selected_points)
        self.ui_manager.update_all_bodyparts()
        self.graphics_manager.update_all_points()
    
    # Keyboard events
    
    def keyPressEvent(self, event):
        """Handle key press."""
        if self.event_handler.handle_key_press(event):
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Handle key release."""
        if self.event_handler.handle_key_release(event):
            event.accept()
        else:
            super().keyReleaseEvent(event)
    
    # Public interface
    
    def save_annotations(self):
        """Save annotations."""
        return self.annotation_manager.save_annotation()
    
    def clear_all_annotations(self):
        """Clear all annotations."""
        self.annotation_manager.clear_all_annotations()
        self.graphics_manager.set_points({})
        self.ui_manager.set_points({})
        self._sync_data_between_managers()
        self.has_unsaved_changes = False
    
    def load_image(self, image_path):
        """Load image."""
        return self.file_manager.load_image(image_path)
    
    def set_directory(self, directory):
        """Set working directory."""
        self.file_manager.set_directory(directory)
    
    def get_current_image_path(self):
        """Get current image path."""
        return self.file_manager.get_current_image_path()
    
    def get_annotation_count(self):
        """Get annotation count."""
        return self.annotation_manager.get_annotation_count()
    
    def get_total_annotation_count(self):
        """Get total annotation count."""
        return self.annotation_manager.get_total_annotation_count()
    
    def get_config_summary(self):
        """Get config summary."""
        return self.config_manager.get_config_summary()
    
    # Compatibility methods
    
    @property
    def bodyparts(self):
        return self.config_manager.get_bodyparts()
    
    @property
    def connections(self):
        return self.config_manager.get_connections()
    
    @property
    def points(self):
        return self.annotation_manager.get_all_points()
    
    @property
    def selected_points(self):
        return self.graphics_manager.get_selected_points()
    
    @property
    def current_image_path(self):
        return self.file_manager.get_current_image_path()
    
    @property
    def all_annotations(self):
        return self.annotation_manager.all_annotations
    
    def update_all_points(self):
        self.graphics_manager.update_all_points()
    
    def update_all_bodyparts(self):
        self.ui_manager.update_all_bodyparts()
    
    def update_bodyparts_display(self):
        self.ui_manager.update_bodyparts_display()
    
    def clear_points(self):
        self.annotation_manager.clear_points()
        self._sync_data_between_managers()
    
    def load_annotation(self, image_path):
        result = self.annotation_manager.load_annotation(image_path)
        self._sync_data_between_managers()
        return result
    
    def get_next_bodypart_index(self):
        return self.graphics_manager.get_next_bodypart_index()
    
    def set_selected_unmarked_point_color(self, bodypart_idx):
        self.ui_manager.set_selected_unmarked_point_color(bodypart_idx)
    
    def _handle_export_request(self):
        current_path = self.file_manager.get_current_image_path()
        if not current_path:
            QMessageBox.warning(self, "No Directory", "Please select a directory with images first.")
            return
        
        current_dir = os.path.dirname(current_path)
        default_export_dir = os.path.join(current_dir, "Export")
        
        from PySide6.QtWidgets import QFileDialog
        export_dir = QFileDialog.getExistingDirectory(
            self, 
            "Select Export Directory (default: ./Export)", 
            default_export_dir
        )
        
        if not export_dir:
            reply = QMessageBox.question(
                self, 
                "Use Default Directory?",
                f"Export to default directory?\n{default_export_dir}",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                export_dir = default_export_dir
            else:
                return
        
        from .managers.export_manager import ExportManager
        export_manager = ExportManager(self)
        export_manager.export_images_with_annotations(current_dir, export_dir)
"""
EventHandler - Handles user input events
Processes keyboard/mouse events and interaction logic
"""

from PySide6.QtWidgets import QGraphicsRectItem, QMessageBox
from PySide6.QtCore import Qt, QPointF, QRectF, QObject, Signal, QTimer
from PySide6.QtGui import QKeyEvent, QPen, QColor
from gui.style_manager import create_styled_message_box


class EventHandler(QObject):
    """Event handler for all keyboard and mouse events"""
    
    # Signals
    point_add_requested = Signal()          # Add point requested
    save_requested = Signal()               # Save requested
    next_image_requested = Signal()         # Next image requested
    previous_image_requested = Signal()     # Previous image requested
    move_view_requested = Signal(int, int)  # Move view requested (dx, dy)
    delete_points_requested = Signal()      # Delete points requested
    clear_selection_requested = Signal()    # Clear selection requested
    help_requested = Signal()               # Help requested
    selection_click = Signal(QPointF, object)  # Selection click (scene_pos, event)
    rectangle_selection = Signal(QRectF)    # Rectangle selection (selection_rect)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # Keyboard state
        self.key_pressed = False
        self.current_key = None
        self.is_repeating = False
        
        # Key repeat timer
        self.repeat_timer = QTimer()
        self.repeat_timer.timeout.connect(self._handle_key_repeat)
        self.initial_delay = 500  # Initial delay 500ms
        self.repeat_interval = 100  # Repeat interval 100ms
        
        # Selection related
        self.selection_start_pos = None
        self.selection_rect = None
        
        # Component references
        self.graphics_scene = None
        self.graphics_view = None
        
        # Move step size
        self.move_step = 20
    
    def set_graphics_components(self, graphics_view, graphics_scene):
        """Set graphics component references"""
        self.graphics_view = graphics_view
        self.graphics_scene = graphics_scene
    
    def _handle_key_repeat(self):
        """Handle key repeat"""
        if self.current_key and self.is_repeating:
            self._process_key(self.current_key)
    
    def _process_key(self, key):
        """Process specific key actions"""
        if key == Qt.Key_F:
            # F key: add point
            self.point_add_requested.emit()
        elif key == Qt.Key_S:
            # Ctrl+S: save (no repeat)
            self.save_requested.emit()
        elif key == Qt.Key_D:
            # D key: next image
            self.next_image_requested.emit()
        elif key == Qt.Key_A:
            # A key: previous image
            self.previous_image_requested.emit()
        elif key == Qt.Key_Up:
            # Up arrow: move view up
            self.move_view_requested.emit(0, -self.move_step)
        elif key == Qt.Key_Down:
            # Down arrow: move view down
            self.move_view_requested.emit(0, self.move_step)
        elif key == Qt.Key_Left:
            # Left arrow: move view left
            self.move_view_requested.emit(-self.move_step, 0)
        elif key == Qt.Key_Right:
            # Right arrow: move view right
            self.move_view_requested.emit(self.move_step, 0)
        elif key == Qt.Key_Delete or key == Qt.Key_Backspace:
            # Delete/Backspace: delete selected points (no repeat)
            self.delete_points_requested.emit()
        elif key == Qt.Key_Escape:
            # Esc: clear selection (no repeat)
            self.clear_selection_requested.emit()
        elif key == Qt.Key_F1:
            # F1: show help (no repeat)
            self.help_requested.emit()
    
    def _is_repeatable_key(self, key):
        """Check if key supports repeat"""
        repeatable_keys = [
            Qt.Key_D, Qt.Key_A,  # Image switching
            Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right  # View movement
        ]
        return key in repeatable_keys
    
    def handle_key_press(self, event):
        """Handle key press events"""
        key = event.key()
        
        # If this is auto-repeat
        if event.isAutoRepeat():
            if key == self.current_key and self._is_repeatable_key(key):
                # Start repeat mode if not already started
                if not self.is_repeating:
                    self.is_repeating = True
                    self.repeat_timer.stop()
                    self.repeat_timer.start(self.repeat_interval)
                return True
            else:
                return False  # Ignore auto-repeat for non-repeatable keys
        
        # First key press
        if self.key_pressed and key != self.current_key:
            # If pressing another key, release first
            self._stop_repeat()
        
        self.key_pressed = True
        self.current_key = key
        
        # Handle Ctrl+S combination
        if key == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self._process_key(key)
        else:
            # Process first key press immediately
            self._process_key(key)
            
            # Start delay timer for repeatable keys
            if self._is_repeatable_key(key):
                self.repeat_timer.stop()
                self.repeat_timer.start(self.initial_delay)
        
        return True  # Event handled
    
    def handle_key_release(self, event):
        """Handle key release events"""
        key = event.key()
        
        # Ignore auto-repeat release events
        if event.isAutoRepeat():
            return True
            
        # If releasing current pressed key
        if key == self.current_key:
            self._stop_repeat()
        
        return True
    
    def _stop_repeat(self):
        """Stop key repeat"""
        self.key_pressed = False
        self.current_key = None
        self.is_repeating = False
        self.repeat_timer.stop()
    
    def handle_selection_click(self, scene_pos, event):
        """Handle selection click events"""
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.ControlModifier:
                # Ctrl+click: start rectangle selection
                self._start_selection(scene_pos)
            else:
                # Normal click: emit selection signal for other modules
                self.selection_click.emit(scene_pos, event)
        
        return True
    
    def handle_selection_move(self, scene_pos):
        """Handle selection move events"""
        if self.selection_start_pos and self.graphics_scene:
            self.update_selection_rect(scene_pos)
        return True
    
    def handle_selection_release(self):
        """Handle selection release events"""
        if self.selection_rect:
            self.finalize_selection()
        return True
    
    def _start_selection(self, scene_pos):
        """Start rectangle selection"""
        self.selection_start_pos = scene_pos
        
        # Create selection rectangle
        if self.graphics_scene:
            self.selection_rect = QGraphicsRectItem()
            pen = QPen(QColor(255, 255, 255, 150), 1)
            pen.setStyle(Qt.DashLine)
            self.selection_rect.setPen(pen)
            self.selection_rect.setBrush(QColor(255, 255, 255, 30))
            self.selection_rect.setZValue(10)  # Ensure on top layer
            self.graphics_scene.addItem(self.selection_rect)
    
    def update_selection_rect(self, current_pos):
        """Update selection rectangle"""
        if not self.selection_rect or not self.selection_start_pos:
            return
        
        # Calculate rectangle
        x1, y1 = self.selection_start_pos.x(), self.selection_start_pos.y()
        x2, y2 = current_pos.x(), current_pos.y()
        
        rect = QRectF(
            min(x1, x2), min(y1, y2),
            abs(x2 - x1), abs(y2 - y1)
        )
        
        self.selection_rect.setRect(rect)
    
    def finalize_selection(self):
        """Finalize selection operation"""
        if not self.selection_rect:
            return
        
        # Get selection area
        selection_area = self.selection_rect.rect()
        
        # Send rectangle selection signal only if large enough
        if selection_area.width() > 5 and selection_area.height() > 5:
            self.rectangle_selection.emit(selection_area)
        
        # Clean up selection rectangle
        self._clear_selection_rect()
        
        # Reset selection state
        self.selection_start_pos = None
    
    def _clear_selection_rect(self):
        """Clear selection rectangle"""
        if self.selection_rect and self.graphics_scene:
            try:
                scene = self.selection_rect.scene()
                if scene is not None:
                    self.graphics_scene.removeItem(self.selection_rect)
            except (RuntimeError, ValueError, ReferenceError):
                # Catch C++ object deletion errors
                pass
            finally:
                self.selection_rect = None
    
    def clear_selection(self):
        """Clear current selection"""
        self._clear_selection_rect()
        self.selection_start_pos = None
        self.clear_selection_requested.emit()
    
    def show_help(self):
        """Show help information"""
        if self.parent:
            help_text = """
            <h3>Keyboard Shortcuts:</h3>
            <ul>
            <li><b>F</b> - Add point at cursor position</li>
            <li><b>A</b> - Previous image</li>
            <li><b>D</b> - Next image</li>
            <li><b>↑↓←→</b> - Move view</li>
            <li><b>Delete/Backspace</b> - Delete selected points</li>
            <li><b>Esc</b> - Clear selection</li>
            <li><b>Ctrl+S</b> - Save annotations</li>
            <li><b>F1</b> - Show this help</li>
            </ul>
            
            <h3>Mouse Operations:</h3>
            <ul>
            <li><b>Left Click</b> - Select point or add point</li>
            <li><b>Ctrl+Left Click</b> - Start rectangular selection</li>
            <li><b>Mouse Wheel</b> - Zoom in/out</li>
            <li><b>Right Click+Drag</b> - Pan view</li>
            </ul>
            
            <h3>Tips:</h3>
            <ul>
            <li>Click on body part names to select specific points</li>
            <li>Use point size slider to adjust point visibility</li>
            <li>All changes are auto-saved when you switch images</li>
            </ul>
            """
            
            help_dialog = create_styled_message_box(
                self.parent,
                "Help - Annotation Tool",
                help_text,
                QMessageBox.Information,
                use_primary_buttons=True
            )
            help_dialog.exec()
    
    def set_move_step(self, step):
        """Set move step size"""
        self.move_step = step
    
    def get_move_step(self):
        """Get move step size"""
        return self.move_step
    
    def is_key_pressed(self):
        """Check if any key is pressed"""
        return self.key_pressed
    
    def reset_key_state(self):
        """Reset key state"""
        self.key_pressed = False
    
    def handle_mouse_wheel(self, event):
        """Handle mouse wheel events (zoom)"""
        # Custom wheel event handling
        # Usually zoom is already handled in GraphicsView
        return True
    
    def handle_context_menu(self, event):
        """Handle right-click context menu events"""
        # Add right-click menu functionality here
        return True
    
    def set_move_step(self, step):
        """Set move step size"""
        self.move_step = step
    
    def get_move_step(self):
        """Get move step size"""
        return self.move_step
    
    def is_key_pressed(self):
        """Check if any key is pressed"""
        return self.key_pressed
    
    def reset_key_state(self):
        """Reset key state"""
        self._stop_repeat()
    
    def set_repeat_timing(self, initial_delay=500, repeat_interval=100):
        """Set key repeat timing parameters
        Args:
            initial_delay: Initial delay (ms)
            repeat_interval: Repeat interval (ms)
        """
        self.initial_delay = initial_delay
        self.repeat_interval = repeat_interval
    
    def enable_event_handling(self, widget):
        """Enable event handling for specified widget"""
        if widget:
            widget.keyPressEvent = self.handle_key_press
            widget.keyReleaseEvent = self.handle_key_release
    
    def disable_event_handling(self, widget):
        """Disable event handling for specified widget"""
        if widget and hasattr(widget, '_original_keyPressEvent'):
            widget.keyPressEvent = widget._original_keyPressEvent
            widget.keyReleaseEvent = widget._original_keyReleaseEvent
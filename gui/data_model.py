"""
DataModel - Central data model for managing annotation data
"""

from PySide6.QtCore import QObject, Signal
from typing import Dict, List, Tuple, Optional


class AnnotationDataModel(QObject):
    """Central annotation data model with observer pattern"""
    
    points_changed = Signal(dict)  # Annotation points data changed
    selection_changed = Signal(list)  # Point selection changed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Core data
        self._points = {}  # {bodypart_idx: (x, y)}
        self._selected_points = []  # [bodypart_idx, ...]
        
    # === Point data management ===
    
    def get_points(self) -> Dict[int, Tuple[float, float]]:
        """Get all annotation points"""
        return self._points.copy()
    
    def set_points(self, points: Dict[int, Tuple[float, float]]):
        """Set all annotation points"""
        if points != self._points:
            self._points = points.copy() if points else {}
            self.points_changed.emit(self._points.copy())
    
    def add_point(self, bodypart_idx: int, x: float, y: float):
        """Add single annotation point"""
        self._points[bodypart_idx] = (x, y)
        self.points_changed.emit(self._points.copy())
    
    def remove_point(self, bodypart_idx: int):
        """Remove single annotation point"""
        if bodypart_idx in self._points:
            del self._points[bodypart_idx]
            self.points_changed.emit(self._points.copy())
    
    def clear_points(self):
        """Clear all annotation points"""
        if self._points:
            self._points = {}
            self.points_changed.emit(self._points.copy())
    
    # === Selection management ===
    
    def get_selected_points(self) -> List[int]:
        """Get selected point indices"""
        return self._selected_points.copy()
    
    def set_selected_points(self, selected_points: List[int]):
        """Set selected point indices"""
        if selected_points != self._selected_points:
            self._selected_points = selected_points.copy() if selected_points else []
            self.selection_changed.emit(self._selected_points.copy())
    
    def select_point(self, bodypart_idx: int):
        """Select single point"""
        if self._selected_points != [bodypart_idx]:
            self._selected_points = [bodypart_idx]
            self.selection_changed.emit(self._selected_points.copy())
    
    def toggle_point_selection(self, bodypart_idx: int):
        """Toggle point selection state"""
        if bodypart_idx in self._selected_points:
            self._selected_points.remove(bodypart_idx)
        else:
            self._selected_points.append(bodypart_idx)
        self.selection_changed.emit(self._selected_points.copy())
    
    def clear_selection(self):
        """Clear all selections"""
        if self._selected_points:
            self._selected_points = []
            self.selection_changed.emit(self._selected_points.copy())
    

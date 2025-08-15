"""
AnnotationManager - Manages annotation data operations
Handles CRUD operations, persistence, and format conversion for annotation data
"""

import os
import csv
import json
import math
import pandas as pd
from PIL import Image
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QGraphicsEllipseItem
from gui.style_manager import apply_primary_style


class AnnotationManager(QObject):
    """Annotation data manager for all annotation-related operations"""
    
    # Signals
    annotation_dir_changed = Signal(str)  # Annotation directory changed
    annotations_loaded = Signal(dict)     # Annotations loaded
    annotation_saved = Signal(str)        # Annotation saved
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # Annotation data storage
        self.all_annotations = {}  # All image annotations {filename: {bodypart_idx: (x, y)}}
        self.points = {}          # Current image points {bodypart_idx: (x, y)}
        self.current_image_path = None
        
        # State
        self.has_unsaved_changes = False
        
        # Configuration
        self.bodyparts = []
        self.connections = []
        
        # UI component references
        self.graphics_scene = None
        self.part_labels = []
    
    def set_config(self, bodyparts, connections):
        """Set keypoint configuration"""
        self.bodyparts = bodyparts
        self.connections = connections
    
    def set_ui_components(self, graphics_scene, part_labels):
        """Set UI component references"""
        self.graphics_scene = graphics_scene
        self.part_labels = part_labels
    
    def set_current_image_path(self, image_path):
        """Set current image path"""
        self.current_image_path = image_path
    
    def load_all_annotations_from_csv(self, csv_path):
        """Load all annotation data from CSV file into memory"""
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
                
                # Check if file has at least header and data rows
                if len(rows) < 2:
                    return False
                
                # Get header
                header = rows[0]
                
                # Process data rows
                for row in rows[1:]:
                    if not row or len(row) == 0:
                        continue
                        
                    # Get image filename
                    image_filename = row[0]
                    if not image_filename:
                        continue
                    
                    # Create points dictionary for each image
                    points = {}
                    
                    # Parse coordinates for each bodypart
                    for j in range(len(self.bodyparts)):
                        col_index = j * 2 + 1  # Skip img_id column
                        if (col_index + 1 < len(row) and 
                            row[col_index] and row[col_index + 1]):
                            try:
                                x = float(row[col_index])
                                y = float(row[col_index + 1])
                                # Add point to dictionary
                                points[j] = (x, y)
                            except (ValueError, TypeError):
                                continue
                    
                    # Save data to memory
                    if points:  # Only add if there are valid points
                        self.all_annotations[image_filename] = points
                
                # Emit annotations loaded signal
                self.annotations_loaded.emit(self.all_annotations)
                return True
                
        except Exception as e:
            print(f"Error loading annotations from CSV: {str(e)}")
            return False
    
    def clear_points(self):
        """Clear all annotation points"""
        self.points = {}
        
        # Clear points from scene
        if self.graphics_scene:
            for item in self.graphics_scene.items():
                if isinstance(item, QGraphicsEllipseItem):
                    self.graphics_scene.removeItem(item)
        
        # Reset all label text
        if self.part_labels:
            for i, label in enumerate(self.part_labels):
                if i < len(self.bodyparts):
                    label.setText(f"{self.bodyparts[i]}")
                    label.setStyleSheet("color: white; background-color: transparent;")
    
    def save_annotation(self):
        """Save current image annotation data"""
        if not self.current_image_path:
            return False

        # Update current image annotations
        image_filename = os.path.basename(self.current_image_path)
        self.all_annotations[image_filename] = self.points.copy()

        # Get CSV file path from current image directory
        image_dir = os.path.dirname(self.current_image_path)
        csv_path = os.path.join(image_dir, "Keypoints.csv")
        json_path = os.path.join(image_dir, "annotations.json")

        try:
            # Write all annotations to CSV
            self._save_to_csv(csv_path)
            
            # Convert to COCO format and save as JSON
            save_message = self._save_to_json(csv_path, image_dir, json_path)

            # Reset unsaved changes flag
            self.has_unsaved_changes = False
                
            # Show success message
            self._show_save_success_dialog(save_message)
            
            # Notify directory changed
            annotation_dir = os.path.dirname(self.current_image_path)
            self.annotation_dir_changed.emit(annotation_dir)
            self.annotation_saved.emit(csv_path)
            
            return True
            
        except Exception as e:
            # Show error message
            self._show_save_error_dialog(str(e))
            return False
    
    def _save_to_csv(self, csv_path):
        """Save annotation data to CSV file"""
        with open(csv_path, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            header = ["filename"]
            for idx, part in enumerate(self.bodyparts):
                header.append(f"{part}_x")
                header.append(f"{part}_y")
            writer.writerow(header)

            # Write annotation data for each image
            for img_file, points in self.all_annotations.items():
                row = [img_file]
                for i in range(len(self.bodyparts)):
                    if i in points:
                        x, y = points[i]
                        row.append(str(x))
                        row.append(str(y))
                    else:
                        row.append("")
                        row.append("")
                writer.writerow(row)
    
    def _save_to_json(self, csv_path, image_dir, json_path):
        """Convert data to COCO format and save as JSON"""
        try:
            # Process CSV and generate COCO data
            coco_data = self.process_csv_to_coco(csv_path, image_dir)
            
            # Save generated annotations.json
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(coco_data, f, indent=4, ensure_ascii=False)
            
            return f"Annotations saved to:\\n{csv_path}\\nand\\n{json_path}"
        except Exception as e:
            # If COCO conversion fails, still save CSV with warning
            return f"Annotations saved to:\\n{csv_path}\\n\\nWarning: Failed to create COCO format: {str(e)}"
    
    def _show_save_success_dialog(self, message):
        """Show save success dialog"""
        if self.parent:
            success_dialog = QMessageBox(self.parent)
            success_dialog.setWindowTitle("Save Successful")
            success_dialog.setText(message)
            success_dialog.setStandardButtons(QMessageBox.Ok)
            apply_primary_style(success_dialog.buttons()[0])
            success_dialog.exec()
    
    def _show_save_error_dialog(self, error_message):
        """Show save error dialog"""
        if self.parent:
            error_dialog = QMessageBox(self.parent)
            error_dialog.setWindowTitle("Save Error")
            error_dialog.setText(f"Error saving annotations: {error_message}")
            error_dialog.setStandardButtons(QMessageBox.Ok)
            apply_primary_style(error_dialog.buttons()[0])
            error_dialog.exec()
    
    def load_annotation(self, image_path):
        """Load annotation data for current image from CSV"""
        # Clear current points
        self.clear_points()
        
        # Get current image filename
        image_filename = os.path.basename(image_path)
        
        # Check if annotation data exists in memory
        if image_filename in self.all_annotations:
            self.points = self.all_annotations[image_filename].copy()
            # Notify parent to update display
            if hasattr(self.parent, 'update_all_points'):
                self.parent.update_all_points()
            return True
        
        # If not in memory, try loading from CSV
        data_dir = os.path.dirname(image_path)
        csv_path = os.path.join(data_dir, "Keypoints.csv")
        
        # Check if CSV file exists
        if not os.path.exists(csv_path):
            return False
        
        return self._load_from_csv(csv_path, image_filename)
    
    def _load_from_csv(self, csv_path, image_filename):
        """Load annotation data for specific image from CSV"""
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
                
                # Check file has header and data rows
                if len(rows) < 2:
                    return False
                
                # Get header
                header = rows[0]
                
                # Find data row for current image
                for row in rows[1:]:
                    if row[0] == image_filename:
                        # Parse coordinates for each bodypart
                        for j in range(len(self.bodyparts)):
                            col_index = j * 2 + 1
                            if (col_index + 1 < len(row) and 
                                row[col_index] and row[col_index + 1]):
                                try:
                                    x = float(row[col_index])
                                    y = float(row[col_index + 1])
                                    # Add point to dictionary
                                    self.points[j] = (x, y)
                                except (ValueError, TypeError):
                                    continue
            
                        # Save data to memory
                        self.all_annotations[image_filename] = self.points.copy()
            
                        # Notify parent to update display
                        if hasattr(self.parent, 'update_all_points'):
                            self.parent.update_all_points()
                        return True
                
                return False
                
        except Exception as e:
            print(f"Error loading annotation from CSV: {str(e)}")
            return False
    
    def clear_all_annotations(self):
        """Clear all image annotation data"""
        self.all_annotations = {}
        self.clear_points()
        self.has_unsaved_changes = False
    
    def save_current_annotations(self):
        """Save current image annotation data to memory"""
        if self.current_image_path and self.points:
            image_filename = os.path.basename(self.current_image_path)
            self.all_annotations[image_filename] = self.points.copy()
    
    def process_csv_to_coco(self, csv_path, input_images_dir):
        """Process CSV file and generate COCO format data"""
        # Create COCO data structure
        coco_data = {
            "images": [],
            "annotations": [],
            "categories": [
                {
                    "id": 1,
                    "name": "mouse",
                    "supercategory": "animal",
                    "keypoints": [],
                    "skeleton": []
                }
            ]
        }
        
        # Read CSV file
        data = pd.read_csv(csv_path)
        
        # Extract column names for keypoint info
        columns = data.columns.tolist()
        
        # Extract keypoint names
        keypoints = []
        keypoint_indices = {}  # Store column indices for each keypoint
        
        # First column is filename
        filename_col = columns[0]
        
        # Process other columns for keypoint names
        for i in range(1, len(columns), 2):
            if i + 1 < len(columns):  # Ensure paired y coordinate column exists
                col_name = columns[i]
                
                # Extract keypoint name from column name
                keypoint_name = None
                if " x" in col_name:
                    keypoint_name = col_name.replace(" x", "")
                elif "_x" in col_name:
                    keypoint_name = col_name.replace("_x", "")
                    
                if keypoint_name and keypoint_name not in keypoints:
                    keypoints.append(keypoint_name)
                    keypoint_indices[keypoint_name] = (i, i+1)
        
        # Set keypoints and connections
        coco_data["categories"][0]["keypoints"] = keypoints
        coco_data["categories"][0]["skeleton"] = self.connections
        
        image_id = 1
        annotation_id = 1
        
        # Process each data row
        for idx, row in data.iterrows():
            # Get filename
            image_file_name = row[filename_col]
            
            # Build image path
            image_path = os.path.join(input_images_dir, image_file_name)
            
            # Get actual image dimensions
            image_width, image_height = self._get_image_dimensions(image_path)
            
            # Use default values if dimensions unavailable
            if image_width is None or image_height is None:
                image_width, image_height = 1024, 768
            
            image_info = {
                "id": image_id,
                "file_name": image_file_name,
                "width": image_width,
                "height": image_height
            }
            coco_data["images"].append(image_info)
            
            annotations_keypoints = []
            num_keypoints = 0

            # Process each keypoint for x,y coordinates
            for keypoint in keypoints:
                if keypoint in keypoint_indices:
                    x_idx, y_idx = keypoint_indices[keypoint]
                    try:
                        x_col = columns[x_idx]
                        y_col = columns[y_idx]
                        
                        # Robust null value checking
                        x_value = row[x_col]
                        y_value = row[y_col]
                        
                        # Check for empty values
                        is_x_empty = (x_value is None or 
                                    (isinstance(x_value, str) and not x_value.strip()) or 
                                    (isinstance(x_value, float) and math.isnan(x_value)))
                        is_y_empty = (y_value is None or 
                                    (isinstance(y_value, str) and not y_value.strip()) or 
                                    (isinstance(y_value, float) and math.isnan(y_value)))
                        
                        x = float(x_value) if not is_x_empty else 0
                        y = float(y_value) if not is_y_empty else 0
                        
                        v = 2 if (x != 0 or y != 0) else 0
                        annotations_keypoints.extend([x, y, v])
                        if v > 0:
                            num_keypoints += 1
                    except Exception as e:
                        annotations_keypoints.extend([0, 0, 0])
                        continue
                else:
                    annotations_keypoints.extend([0, 0, 0])

            # Calculate bounding box
            valid_x_values = [annotations_keypoints[i] for i in range(0, len(annotations_keypoints), 3) 
                             if annotations_keypoints[i+2] > 0]
            valid_y_values = [annotations_keypoints[i+1] for i in range(0, len(annotations_keypoints), 3) 
                             if annotations_keypoints[i+2] > 0]
            
            if valid_x_values and valid_y_values:
                bbox = [
                    min(valid_x_values), 
                    min(valid_y_values), 
                    max(valid_x_values) - min(valid_x_values), 
                    max(valid_y_values) - min(valid_y_values)
                ]
            else:
                bbox = [0, 0, 0, 0]
                
            annotation_info = {
                "id": annotation_id,
                "image_id": image_id,
                "category_id": 1,
                "keypoints": annotations_keypoints,
                "num_keypoints": num_keypoints,
                "bbox": bbox,
                "area": bbox[2] * bbox[3]
            }
            coco_data["annotations"].append(annotation_info)
            
            image_id += 1
            annotation_id += 1
        
        return coco_data
    
    def _get_image_dimensions(self, image_path):
        """Get actual image width and height"""
        try:
            if os.path.exists(image_path):
                with Image.open(image_path) as img:
                    width, height = img.size
                    return width, height
        except Exception as e:
            print(f"Cannot read image dimensions {image_path}: {e}")
        return None, None
    
    def add_point(self, bodypart_index, x, y):
        """Add annotation point"""
        self.points[bodypart_index] = (x, y)
        self.has_unsaved_changes = True
    
    def remove_point(self, bodypart_index):
        """Remove annotation point"""
        if bodypart_index in self.points:
            del self.points[bodypart_index]
            self.has_unsaved_changes = True
    
    def get_point(self, bodypart_index):
        """Get annotation point for specified bodypart"""
        return self.points.get(bodypart_index)
    
    def get_all_points(self):
        """Get all annotation points for current image"""
        return self.points.copy()
    
    def has_point(self, bodypart_index):
        """Check if annotation point exists for bodypart"""
        return bodypart_index in self.points
    
    def get_annotation_count(self):
        """Get annotation point count for current image"""
        return len(self.points)
    
    def get_total_annotation_count(self):
        """Get total annotation count for all images"""
        return len(self.all_annotations)
    
    def get_image_annotations(self, image_filename):
        """Get annotation data for specific image"""
        return self.all_annotations.get(image_filename, {})
    
    def set_image_annotations(self, image_filename, points):
        """Set annotation data for specific image"""
        self.all_annotations[image_filename] = points.copy()
        self.has_unsaved_changes = True
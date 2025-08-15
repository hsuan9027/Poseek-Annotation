"""
ExportManager - Handles image export functionality
Exports images with annotation points and connection lines drawn on them
"""

import os
import shutil
from PIL import Image, ImageDraw
from PySide6.QtWidgets import QProgressDialog, QMessageBox, QPushButton
from PySide6.QtCore import Qt, QCoreApplication
from gui.style_manager import create_styled_message_box, apply_primary_style
from gui.utils import generate_color


class ExportManager:
    """Export manager for image export operations"""
    
    def __init__(self, parent=None):
        self.parent = parent
        
    def export_images_with_annotations(self, source_dir, export_dir):
        """Export all images with annotation points drawn"""
        # Auto-create Export subfolder if source directory selected
        if os.path.abspath(source_dir) == os.path.abspath(export_dir):
            export_dir = os.path.join(export_dir, "Export")
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
        
        # Get all image files
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif']:
            import glob
            files = glob.glob(os.path.join(source_dir, ext))
            image_files.extend(files)
        
        if not image_files:
            QMessageBox.warning(self.parent, "No Images", "No image files found in the selected directory.")
            return
        
        # Sort file list
        image_files.sort(key=self._natural_key)
        
        # Create progress dialog
        progress = QProgressDialog("Exporting images with annotations...", "Cancel", 0, len(image_files), self.parent)
        progress.setWindowTitle("Export Progress")
        progress.setWindowModality(Qt.WindowModal)
        
        # Apply style to cancel button
        cancel_button = progress.findChild(QPushButton)
        if cancel_button:
            from gui.style_manager import apply_standard_style
            apply_standard_style(cancel_button)
        
        # Get bodyparts and connection info
        bodyparts = self.parent.config_manager.get_bodyparts() if hasattr(self.parent, 'config_manager') else []
        connections = self.parent.config_manager.get_connections() if hasattr(self.parent, 'config_manager') else []
        
        # Get point size setting
        point_size = self.parent.ui_manager.get_point_size() if hasattr(self.parent, 'ui_manager') else 0.2
        
        # Generate color configuration (consistent with graphics_manager)
        colors = []
        for i in range(len(bodyparts)):
            color = generate_color(i, len(bodyparts))
            colors.append(color)
        
        # Read annotation data directly from CSV file
        csv_path = os.path.join(source_dir, "Keypoints.csv")
        annotations_dict = {}
        
        if os.path.exists(csv_path):
            try:
                import csv
                with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    rows = list(reader)
                    
                    if len(rows) > 1:
                        # Parse CSV file
                        for row in rows[1:]:  # 跳过表头
                            if row and len(row) > 0:
                                filename = row[0]
                                points = {}
                                
                                # Parse coordinates for each bodypart
                                for j in range(len(bodyparts)):
                                    col_index = j * 2 + 1  # Skip filename column
                                    if (col_index + 1 < len(row) and 
                                        row[col_index] and row[col_index + 1]):
                                        try:
                                            x = float(row[col_index])
                                            y = float(row[col_index + 1])
                                            points[j] = (x, y)
                                        except ValueError:
                                            pass
                                
                                if points:  # If there are valid annotation points
                                    annotations_dict[filename] = points
                                    
            except Exception as e:
                print(f"Error reading CSV file: {e}")
        else:
            QMessageBox.warning(self.parent, "No Annotations", "No Keypoints.csv file found. Exporting images without annotations.")
        
        
        # Export each image
        exported_count = 0
        for i, image_path in enumerate(image_files):
            if progress.wasCanceled():
                break
            
            progress.setValue(i)
            QCoreApplication.processEvents()
            
            # Get filename
            filename = os.path.basename(image_path)
            
            # Get annotation data for this image
            if filename in annotations_dict:
                points = annotations_dict[filename]
                
                # Create image with annotations
                success = self._export_image_with_annotations(
                    image_path, 
                    os.path.join(export_dir, filename),
                    points,
                    bodyparts,
                    connections,
                    colors,
                    point_size
                )
                
                if success:
                    exported_count += 1
            else:
                # Copy original image if no annotations
                try:
                    dest_path = os.path.join(export_dir, filename)
                    # Ensure source file won't be overwritten
                    if os.path.abspath(image_path) != os.path.abspath(dest_path):
                        shutil.copy2(image_path, dest_path)
                        exported_count += 1
                except Exception as e:
                    print(f"Error copying {filename}: {str(e)}")
        
        progress.setValue(len(image_files))
        
        # Show completion message
        msg_box = create_styled_message_box(
            self.parent,
            "Export Complete",
            f"Successfully exported {exported_count} images to:\n{export_dir}",
            QMessageBox.Information,
            use_primary_buttons=True
        )
        msg_box.exec()
    
    def _export_image_with_annotations(self, source_path, dest_path, points, bodyparts, connections, colors, point_size):
        """Export single image with annotations"""
        try:
            # 打开图片
            img = Image.open(source_path)
            draw = ImageDraw.Draw(img)
            
            # 使用与graphics_manager完全一致的点大小
            # 在Qt中，point_size直接作为半径使用，所以这里也直接使用
            actual_point_size = point_size
            line_width = max(0.5, point_size * 0.4)  # 线宽为点大小的40%，与graphics_manager一致
            
            # 绘制连接线（与graphics_manager一致的样式）
            if connections:
                for connection in connections:
                    if len(connection) == 2:
                        idx1, idx2 = connection
                        if idx1 in points and idx2 in points and idx1 < len(colors) and idx2 < len(colors):
                            x1, y1 = points[idx1]
                            x2, y2 = points[idx2]
                            
                            # 计算混合颜色（与graphics_manager一致）
                            color1 = colors[idx1]
                            color2 = colors[idx2]
                            r = min(255, int((color1[2] + color2[2]) / 1.5))  # BGR转RGB
                            g = min(255, int((color1[1] + color2[1]) / 1.5))
                            b = min(255, int((color1[0] + color2[0]) / 1.5))
                            
                            # 绘制连接线
                            draw.line([(x1, y1), (x2, y2)], fill=(r, g, b), width=int(line_width))
            
            # 绘制标注点（与graphics_manager一致的样式）
            for idx, (x, y) in points.items():
                if idx < len(bodyparts) and idx < len(colors):
                    # 获取颜色 - colors已经是BGR格式的列表
                    color_bgr = colors[idx]
                    # 转换为RGB格式用于PIL
                    fill_color = (color_bgr[2], color_bgr[1], color_bgr[0])
                    
                    # 绘制圆点（与graphics_manager的大小和边框一致）
                    draw.ellipse(
                        [(x - actual_point_size, y - actual_point_size), 
                         (x + actual_point_size, y + actual_point_size)],
                        fill=fill_color,
                        outline=fill_color,  # 使用相同颜色作为边框
                        width=2
                    )
            
            # 保存图片
            img.save(dest_path, quality=95)
            return True
            
        except Exception as e:
            print(f"Error exporting image {source_path}: {str(e)}")
            return False
    
    def _natural_key(self, text):
        """Natural sorting key function"""
        import re
        def convert(t):
            return int(t) if t.isdigit() else t.lower()
        return [convert(c) for c in re.split('([0-9]+)', str(text))]
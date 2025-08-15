"""
FileManager - 文件和目录管理模块
负责处理文件选择、目录浏览、图片加载切换、CSV文件处理等功能
"""

import os
import glob
import json
import re
from PySide6.QtWidgets import QFileDialog, QMessageBox, QApplication
from PySide6.QtCore import Qt, QDir, QPointF, QObject, Signal
from PySide6.QtGui import QPixmap
from gui.style_manager import create_styled_message_box


class FileManager(QObject):
    """文件管理器类，处理所有文件和目录相关操作"""
    
    # 信号定义
    directory_changed = Signal(str)  # 目录改变信号
    image_loaded = Signal(str)       # 图片加载信号
    annotations_loaded = Signal(dict) # 标注数据加载信号
    
    @staticmethod
    def natural_key(text):
        """将字符串分解为文本和数字部分的列表，用于自然排序"""
        def convert(t):
            return int(t) if t.isdigit() else t.lower()
        return [convert(c) for c in re.split('([0-9]+)', str(text))]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # 文件相关属性
        self.start_directory = os.getcwd()
        self.current_image_path = None
        
        # 图片缓存
        self.pixmap_cache = {}
        self.max_cache_size = 20
        
        # 视图状态（缩放和位置）
        self.view_scale = 1.0
        self.view_center = None
        
        # 标记是否是第一次加载图片
        self.is_first_load = True
        
        # 标记是否保留视图状态（A/D键保留，鼠标点击重置）
        self.preserve_view_state = True
        
        # UI组件引用（需要从parent获取）
        self.tree_view = None
        self.file_model = None
        self.selected_folder_input = None
        self.stacked_widget = None
        self.graphics_view = None
        self.graphics_scene = None
        self.pixmap_item = None
    
    def set_ui_components(self, tree_view, file_model, selected_folder_input, 
                         stacked_widget, graphics_view, graphics_scene):
        """设置UI组件引用"""
        self.tree_view = tree_view
        self.file_model = file_model
        self.selected_folder_input = selected_folder_input
        self.stacked_widget = stacked_widget
        self.graphics_view = graphics_view
        self.graphics_scene = graphics_scene
    
    def select_directory(self):
        """打开目录选择对话框"""
        dir_path = QFileDialog.getExistingDirectory(
            self.parent, "Select Directory", self.start_directory
        )
        if dir_path:
            self._process_directory_selection(dir_path)
    
    def _process_directory_selection(self, dir_path):
        """处理目录选择的通用逻辑"""
        # 清除当前的标注数据
        if hasattr(self.parent, 'clear_all_annotations'):
            self.parent.clear_all_annotations()
        
        # 查找CSV文件并加载所有标注数据
        csv_path = self.find_csv_file(dir_path)
        if csv_path:
            self._process_csv_file(csv_path, dir_path)
        
        # 更新UI
        self._update_directory_ui(dir_path)
        
        # 发出目录改变信号
        self.directory_changed.emit(dir_path)
    
    def _process_csv_file(self, csv_path, dir_path):
        """处理CSV文件的加载和转换"""
        try:
            # 从CSV文件加载所有标注数据
            if hasattr(self.parent, 'load_all_annotations_from_csv'):
                self.parent.load_all_annotations_from_csv(csv_path)
            
            # 检查是否需要生成annotations.json文件
            annotations_path = os.path.join(dir_path, "annotations.json")
            if not os.path.exists(annotations_path):
                # 处理CSV文件并生成annotations.json
                if hasattr(self.parent, 'process_csv_to_coco'):
                    coco_data = self.parent.process_csv_to_coco(csv_path, dir_path)
                    
                    # 保存生成的annotations.json
                    with open(annotations_path, 'w') as f:
                        json.dump(coco_data, f, indent=4)
            
        except Exception as e:
            # 处理错误时显示提示
            create_styled_message_box(
                self.parent, "Error", 
                f"Error processing CSV file: {str(e)}", 
                QMessageBox.Critical, use_primary_buttons=False
            ).exec()
    
    def _update_directory_ui(self, dir_path):
        """更新目录相关的UI组件"""
        # UI更新现在由ui_manager处理
        if hasattr(self.parent, 'ui_manager'):
            self.parent.ui_manager.update_directory_ui(dir_path)
        
        self.start_directory = dir_path
    
    def on_folder_input_changed(self, text):
        """当用户手动输入路径时触发"""
        if QDir(text).exists():
            self._process_directory_selection(text)
            
            # 切换到文件浏览界面
            if self.stacked_widget:
                self.stacked_widget.setCurrentIndex(1)
            
            # 自动加载第一张图片
            self.load_first_image(text)
    
    def on_file_selected(self, index):
        """当用户单击文件时触发"""
        if not self.file_model:
            return
            
        file_path = self.file_model.filePath(index)
        if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
            # 鼠标点击文件列表时，重置视图状态
            self.preserve_view_state = False
            
            # 保存当前图片的标注数据
            if self.current_image_path and hasattr(self.parent, 'annotation_manager'):
                self.parent.annotation_manager.save_current_annotations()
            
            # 清除当前点和标签信息
            if hasattr(self.parent, 'annotation_manager'):
                self.parent.annotation_manager.clear_points()
            
            # 加载图片
            self.load_image(file_path)
            
            # 通过image_loaded信号处理后续逻辑
            # 这样可以确保所有管理器都正确处理图片加载
    
    def load_image(self, file_path):
        """加载并显示图片"""
        if not file_path or not os.path.exists(file_path):
            return
        
        # 保存当前的视图状态（如果不是第一次加载且要保留状态）
        if not self.is_first_load and self.preserve_view_state:
            self._save_current_view_state()
        
        # 获取要应用的视图状态
        if self.is_first_load or not self.preserve_view_state:
            # 第一次加载或鼠标点击文件列表时使用默认值
            target_scale = 1.0
            target_center = None
            if self.is_first_load:
                self.is_first_load = False
            # 重置preserve_view_state标记为True，为下次A/D切换准备
            self.preserve_view_state = True
        else:
            # A/D键切换时使用保存的状态
            target_scale = self.view_scale
            target_center = self.view_center
        
        # 设置当前图片路径
        self.current_image_path = file_path
        
        # 尝试从缓存中获取图片
        if file_path in self.pixmap_cache:
            pixmap = self.pixmap_cache[file_path]
        else:
            # 从文件加载图片
            pixmap = QPixmap(file_path)
            
            # 检查图片是否成功加载
            if pixmap.isNull():
                create_styled_message_box(
                    self.parent, "Error", 
                    f"Failed to load image: {file_path}", 
                    QMessageBox.Warning, use_primary_buttons=False
                ).exec()
                return
            
            # 如果缓存已满，移除最早添加的图片
            if len(self.pixmap_cache) >= self.max_cache_size:
                oldest_key = next(iter(self.pixmap_cache))
                del self.pixmap_cache[oldest_key]
            
            # 添加图片到缓存
            self.pixmap_cache[file_path] = pixmap
        
        # 更新图形场景（不延迟应用状态，避免闪烁）
        self._update_graphics_scene(pixmap, target_scale, target_center)
        
        # 不需要通知graphics_manager重新加载图片，因为我们已经处理了所有的图形显示
        # graphics_manager只需要知道当前的pixmap_item引用即可
        if hasattr(self.parent, 'graphics_manager'):
            # 设置pixmap_item引用，让graphics_manager可以绘制标注点
            self.parent.graphics_manager.pixmap_item = self.pixmap_item
            self.parent.graphics_manager.current_image_path = file_path
        
        # 发出图片加载信号
        self.image_loaded.emit(file_path)
    
    def _save_current_view_state(self):
        """保存当前的视图状态"""
        if not (hasattr(self, 'graphics_view') and self.graphics_view and
                hasattr(self.graphics_view, 'get_current_scale')):
            return
            
        try:
            # 保存缩放比例
            current_scale = self.graphics_view.get_current_scale()
            
            # 保存视图中心点
            view_center = self.graphics_view.get_view_center()
            
            # 获取当前图片尺寸（从缓存或文件）
            pixmap_width = 0
            pixmap_height = 0
            
            # 先尝试从当前图片路径获取尺寸
            if self.current_image_path:
                # 从缓存中获取
                if self.current_image_path in self.pixmap_cache:
                    pixmap = self.pixmap_cache[self.current_image_path]
                    if pixmap and not pixmap.isNull():
                        pixmap_width = pixmap.width()
                        pixmap_height = pixmap.height()
                
                # 如果缓存中没有，从文件加载
                if pixmap_width == 0 or pixmap_height == 0:
                    try:
                        from PySide6.QtGui import QPixmap
                        pixmap = QPixmap(self.current_image_path)
                        if pixmap and not pixmap.isNull():
                            pixmap_width = pixmap.width()
                            pixmap_height = pixmap.height()
                    except Exception:
                        pass
            
            # 如果有有效的图片尺寸和视图中心
            if pixmap_width > 0 and pixmap_height > 0 and view_center:
                # 直接使用视图中心计算比例，不进行裁剪
                # 这样可以保留用户移动到图片边界外的位置
                center_x_ratio = view_center.x() / pixmap_width
                center_y_ratio = view_center.y() / pixmap_height
                
                # 给予合理的容差范围，允许移动到图片外部
                center_x_ratio = max(-1.0, min(2.0, center_x_ratio))
                center_y_ratio = max(-1.0, min(2.0, center_y_ratio))
                
                
                # 保存状态
                self.view_scale = current_scale
                self.view_center = QPointF(center_x_ratio, center_y_ratio)
            else:
                # 只保存缩放比例
                self.view_scale = current_scale
                self.view_center = None
                
        except Exception as e:
            # 不要重置为默认值，保持之前的值
            pass
    
    def _update_graphics_scene(self, pixmap, target_scale, target_center):
        """更新图形场景中的图片"""
        if not self.graphics_scene or not self.graphics_view:
            return
            
        # 清除场景并重置pixmap_item引用
        self.graphics_scene.clear()
        self.pixmap_item = None  # 重置引用
        
        from PySide6.QtWidgets import QGraphicsPixmapItem
        from PySide6.QtCore import QRectF
        
        # 创建新的pixmap项
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.pixmap_item.setZValue(0)  # 在最底层
        self.graphics_scene.addItem(self.pixmap_item)
        
        # 获取图片尺寸并设置场景大小
        width = pixmap.width()
        height = pixmap.height()
        
        # 设置场景矩形
        base_rect = QRectF(0, 0, width, height)
        extra_size = getattr(self.graphics_view, '_extra_scene_size', 1000)
        extended_rect = base_rect.adjusted(-extra_size, -extra_size, extra_size, extra_size)
        self.graphics_scene.setSceneRect(extended_rect)
        
        # 先适应视图（作为基准）
        self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.graphics_view._current_scale = 1.0
        
        # 立即应用视图状态，避免闪烁
        if target_scale > 0 and target_scale != 1.0:
            # 计算缩放因子并应用
            scale_factor = target_scale / 1.0
            self.graphics_view.scale(scale_factor, scale_factor)
            self.graphics_view._current_scale = target_scale
        
        # 应用视图中心位置
        if target_center is not None:
            # 计算新图片上的中心点位置，保持用户移动的相对位置
            new_center_x = float(width) * float(target_center.x())
            new_center_y = float(height) * float(target_center.y())
            
            # 不限制坐标范围，允许用户移动到图片外部
            # 这样可以保留用户的实际移动位置
            scene_center = QPointF(new_center_x, new_center_y)
            
            # 立即居中视图
            self.graphics_view.centerOn(scene_center)
            
            # 验证实际居中的位置，如果有偏差则进行补偿
            QApplication.processEvents()  # 确保视图更新
            actual_center = self.graphics_view.get_view_center()
            
            # 计算偏差
            offset_x = scene_center.x() - actual_center.x()
            offset_y = scene_center.y() - actual_center.y()
            
            # 如果偏差超过阈值，进行补偿
            if abs(offset_x) > 0.5 or abs(offset_y) > 0.5:
                corrected_center = QPointF(scene_center.x() + offset_x, scene_center.y() + offset_y)
                self.graphics_view.centerOn(corrected_center)
        else:
            pass
    
    
    def _center_view_on_point(self, point):
        """将视图居中到指定点"""
        if self.graphics_view:
            self.graphics_view.centerOn(point)
    
    def load_first_image(self, dir_path):
        """加载目录中的第一张图片"""
        # 获取目录中的所有文件
        dir = QDir(dir_path)
        dir.setNameFilters(["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif"])
        dir.setFilter(QDir.Files)
        dir.setSorting(QDir.Name)
        
        # 获取所有图片文件
        file_list = dir.entryList()
        if file_list:
            # 按自然排序重新排列，取第一张
            file_list = sorted(file_list, key=self.natural_key)
            first_image = file_list[0]
            image_path = os.path.join(dir_path, first_image)
            
            # 在树视图中找到并选择该图片
            if self.file_model and self.tree_view:
                source_index = self.file_model.index(image_path)
                if source_index.isValid():
                    # 如果使用了代理模型，需要转换索引
                    if hasattr(self.parent, 'ui_manager') and hasattr(self.parent.ui_manager, 'proxy_model'):
                        proxy_index = self.parent.ui_manager.proxy_model.mapFromSource(source_index)
                        self.tree_view.setCurrentIndex(proxy_index)
                        self.on_file_selected(source_index)  # 但回调仍使用源索引
                    else:
                        self.tree_view.setCurrentIndex(source_index)
                        self.on_file_selected(source_index)
                else:
                    # 如果无法在树视图中找到，直接加载图片
                    self._load_image_direct(image_path)
            else:
                self._load_image_direct(image_path)
    
    def _load_image_direct(self, image_path):
        """直接加载图片（绕过树视图选择）"""
        if hasattr(self.parent, 'clear_points'):
            self.parent.clear_points()
        
        self.load_image(image_path)
        
        if hasattr(self, 'pixmap_item') and self.pixmap_item is not None:
            if hasattr(self.parent, 'load_annotation'):
                self.parent.load_annotation(image_path)
    
    def load_next_image(self):
        """加载下一张图片"""
        if hasattr(self.parent, 'set_selected_unmarked_point_color'):
            if hasattr(self.parent, 'get_next_bodypart_index'):
                self.parent.set_selected_unmarked_point_color(
                    self.parent.get_next_bodypart_index()
                )
        
        if not self.current_image_path:
            return
        
        # 获取下一张图片路径
        next_image_path = self._get_adjacent_image(1)
        if next_image_path:
            self._load_adjacent_image(next_image_path)
        # 如果没有下一张图片，静默忽略（不显示提示）
    
    def load_previous_image(self):
        """加载上一张图片"""
        if not self.current_image_path:
            return
        
        # 获取上一张图片路径
        prev_image_path = self._get_adjacent_image(-1)
        if prev_image_path:
            self._load_adjacent_image(prev_image_path)
        # 如果没有上一张图片，静默忽略（不显示提示）
    
    def _get_adjacent_image(self, direction):
        """获取相邻图片路径
        Args:
            direction: 1为下一张，-1为上一张
        Returns:
            相邻图片的完整路径，如果没有则返回None
        """
        current_dir = os.path.dirname(self.current_image_path)
        current_filename = os.path.basename(self.current_image_path)
        
        # 获取目录中所有图片文件
        dir = QDir(current_dir)
        dir.setNameFilters(["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif"])
        dir.setFilter(QDir.Files)
        dir.setSorting(QDir.Name)  # 先用基本排序
        
        file_list = dir.entryList()
        if not file_list:
            return None
        
        # 按自然排序重新排列
        file_list = sorted(file_list, key=self.natural_key)
        
        # 找到当前图片在排序后列表中的位置
        try:
            current_index = file_list.index(current_filename)
        except ValueError:
            # 如果当前图片不在列表中
            current_index = 0 if direction == 1 else len(file_list) - 1
            return os.path.join(current_dir, file_list[current_index])
        
        # 计算目标索引
        target_index = current_index + direction
        
        # 检查边界
        if target_index < 0 or target_index >= len(file_list):
            return None
        
        # 返回目标图片路径
        target_image = file_list[target_index]
        return os.path.join(current_dir, target_image)
    
    def _load_adjacent_image(self, image_path):
        """加载相邻图片的通用方法"""
        # A/D键切换时，保留视图状态
        self.preserve_view_state = True
        
        # 在树视图中找到并选择该图片
        if self.file_model and self.tree_view:
            source_index = self.file_model.index(image_path)
            if source_index.isValid():
                # 如果使用了代理模型，需要转换索引
                if hasattr(self.parent, 'ui_manager') and hasattr(self.parent.ui_manager, 'proxy_model'):
                    proxy_index = self.parent.ui_manager.proxy_model.mapFromSource(source_index)
                    self.tree_view.setCurrentIndex(proxy_index)
                    # 直接调用load_image而不是on_file_selected，避免重置视图状态
                    self._load_image_with_preserved_state(image_path)
                else:
                    self.tree_view.setCurrentIndex(source_index)
                    # 直接调用load_image而不是on_file_selected，避免重置视图状态
                    self._load_image_with_preserved_state(image_path)
                return
        
        # 如果无法在树视图中找到，直接加载图片
        self._load_image_with_preserved_state(image_path)

    def _load_image_with_preserved_state(self, image_path):
        """加载图片并保留视图状态（用于A/D键切换）"""
        # 保存当前图片的标注数据
        if self.current_image_path and hasattr(self.parent, 'annotation_manager'):
            self.parent.annotation_manager.save_current_annotations()
        
        # 清除当前点和标签信息
        if hasattr(self.parent, 'annotation_manager'):
            self.parent.annotation_manager.clear_points()
        
        # 加载图片
        self.load_image(image_path)
        
        # 设置焦点到父窗口以捕获键盘事件
        if self.parent:
            self.parent.setFocus()
    
    def set_directory(self, directory):
        """设置目录并加载文件"""
        if directory and os.path.exists(directory):
            # 检查是否已存在annotations.json文件
            annotations_path = os.path.join(directory, "annotations.json")
            
            if not os.path.exists(annotations_path):
                # 尝试查找CSV文件并创建annotations.json
                csv_path = self.find_csv_file(directory)
                if csv_path:
                    self._generate_annotations_json(csv_path, directory)
            
            # 更新目录UI
            self._update_directory_ui(directory)
            
            # 发出目录改变信号
            self.directory_changed.emit(directory)
    
    def _generate_annotations_json(self, csv_path, directory):
        """生成annotations.json文件"""
        try:
            # 处理CSV文件并生成annotations.json
            if hasattr(self.parent, 'process_csv_to_coco'):
                coco_data = self.parent.process_csv_to_coco(csv_path, directory)
                
                # 保存生成的annotations.json
                annotations_path = os.path.join(directory, "annotations.json")
                with open(annotations_path, 'w') as f:
                    json.dump(coco_data, f, indent=4)
                
        except Exception as e:
            # 处理错误时显示提示
            create_styled_message_box(
                self.parent, "Error", 
                f"Error generating annotations.json: {str(e)}", 
                QMessageBox.Critical, use_primary_buttons=False
            ).exec()
    
    def find_csv_file(self, folder_path):
        """查找CSV文件，优先查找CollectedData_x.csv"""
        default_csv = os.path.join(folder_path, "CollectedData_x.csv")
        if os.path.exists(default_csv):
            return default_csv
        
        csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
        if csv_files:
            return csv_files[0]
        
        return None
    
    def get_current_image_path(self):
        """获取当前图片路径"""
        return self.current_image_path
    
    def get_image_info(self):
        """获取当前图片信息（索引和总数）"""
        if not self.current_image_path:
            return -1, 0
        
        current_dir = os.path.dirname(self.current_image_path)
        current_filename = os.path.basename(self.current_image_path)
        
        # 获取目录中所有图片文件
        dir = QDir(current_dir)
        dir.setNameFilters(["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif"])
        dir.setFilter(QDir.Files)
        
        file_list = dir.entryList()
        if not file_list:
            return -1, 0
        
        # 按自然排序
        file_list = sorted(file_list, key=self.natural_key)
        
        try:
            current_index = file_list.index(current_filename)
            return current_index, len(file_list)
        except ValueError:
            return -1, len(file_list)
    
    def clear_cache(self):
        """清空图片缓存"""
        self.pixmap_cache.clear()
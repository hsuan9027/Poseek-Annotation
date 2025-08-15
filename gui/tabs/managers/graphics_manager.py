"""
GraphicsManager - 图像显示和标注点绘制管理模块
负责处理图像显示、标注点绘制、连接线绘制、视图管理等功能
"""

import os
import math
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, QObject, Signal
from PySide6.QtGui import QPixmap, QPen, QColor, QCursor
from gui.style_manager import create_styled_message_box
from gui.utils import generate_color


class GraphicsManager(QObject):
    """图形管理器类，处理所有图像显示和标注点绘制操作"""
    
    # 信号定义
    point_added = Signal(float, float, int)      # 点添加信号 (x, y, bodypart_idx)
    point_selected = Signal(int)                 # 点选择信号 (bodypart_idx)
    selection_changed = Signal(list)             # 选择改变信号 (selected_indices)
    view_updated = Signal()                      # 视图更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # 图形组件
        self.graphics_view = None
        self.graphics_scene = None
        self.pixmap_item = None
        
        # 标注数据（需要与AnnotationManager同步）
        self.points = {}  # {bodypart_idx: (x, y)}
        self.selected_points = []  # 选中的点索引列表
        
        # 标注完成状态
        self.all_points_complete = False  # 是否所有点都已标注完，等待按F键跳转
        
        # 选择相关
        self.selection_rect = None
        self.selection_start_pos = None
        
        # 配置
        self.bodyparts = []
        self.connections = []
        self.colors = []
        self.point_size = 0.2
        
        # 状态
        self.current_image_path = None
        
        # 图片缓存
        self.pixmap_cache = {}
        self.max_cache_size = 20
    
    def set_ui_components(self, graphics_view, graphics_scene):
        """设置UI组件引用"""
        self.graphics_view = graphics_view
        self.graphics_scene = graphics_scene
    
    def set_config(self, bodyparts, connections):
        """设置关键点配置"""
        self.bodyparts = bodyparts
        self.connections = connections
        # 为每个身体部位生成颜色
        self.colors = []
        for i in range(len(bodyparts)):
            color = generate_color(i, len(bodyparts))
            self.colors.append(color)
    
    def set_points(self, points):
        """设置当前图片的标注点"""
        self.points = points.copy() if points else {}
        # 重置完成状态，当切换图片时重新开始
        self.all_points_complete = False
    
    def set_selected_points(self, selected_points):
        """设置选中的点"""
        self.selected_points = selected_points.copy() if selected_points else []
    
    def set_point_size(self, size):
        """设置标注点大小"""
        self.point_size = float(size)
    
    def find_point_at_position(self, scene_pos):
        """查找给定位置的点"""
        for bodypart_idx, coords in self.points.items():
            # 计算点击位置与点之间的距离
            x, y = coords
            distance = math.sqrt((x - scene_pos.x()) ** 2 + (y - scene_pos.y()) ** 2)
            # 如果距离小于点的大小，则认为点击了该点
            if distance <= self.point_size * 1.5:  # 使用稍大的检测范围
                return bodypart_idx
        return None
    
    def delete_selected_points(self):
        """删除选中的点"""
        if not self.selected_points:
            return False
        
        # 保存选中点的数量用于日志
        selected_count = len(self.selected_points)
        
        # 删除选中的点
        deleted_points = []
        for bodypart_idx in self.selected_points:
            if bodypart_idx in self.points:
                deleted_points.append((bodypart_idx, self.points[bodypart_idx]))
                del self.points[bodypart_idx]
        
        # 重置完成状态，因为删除点后可能不再是全部完成
        self.all_points_complete = False
        
        # 清除选择
        self.selected_points = []
        
        # 更新场景显示
        self.update_all_points()
        
        # 发出选择改变信号
        self.selection_changed.emit(self.selected_points)
        
        return len(deleted_points) > 0
    
    def update_all_points(self):
        """更新所有标注点的大小和选中状态"""
        if not self.graphics_scene:
            return
            
        # 清除场景中的所有标注点和线
        items_to_remove = []
        for item in self.graphics_scene.items():
            if isinstance(item, (QGraphicsEllipseItem, QGraphicsLineItem)):
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.graphics_scene.removeItem(item)
        
        # 重新添加所有点
        for bodypart_idx, (x, y) in self.points.items():
            self.add_point_to_scene(x, y, bodypart_idx)
        
        # 添加连接线
        self.draw_connections()
        
        # 发出视图更新信号
        self.view_updated.emit()
    
    def draw_connections(self):
        """绘制连接线"""
        if not self.connections or not self.graphics_scene:
            return
        
        # 计算线宽，比点的大小更小
        line_width = max(0.5, self.point_size * 0.4)  # 线宽为点大小的40%，但至少0.5
        
        for connection in self.connections:
            # 每个连接应该是一个包含两个索引的列表或元组
            if len(connection) != 2:
                continue
                
            idx1, idx2 = connection
            
            # 确保两个索引都在点字典中
            if idx1 in self.points and idx2 in self.points:
                x1, y1 = self.points[idx1]
                x2, y2 = self.points[idx2]
                
                # 创建线条
                line = QGraphicsLineItem(x1, y1, x2, y2)
                line.setZValue(0.5)  # 设置在点和图片之间
                
                # 使用混合颜色的半透明线条
                if idx1 < len(self.colors) and idx2 < len(self.colors):
                    color1 = self.colors[idx1]
                    color2 = self.colors[idx2]
                    
                    # 计算混合颜色，但提高亮度以增强可见性
                    r = min(255, int((color1[2] + color2[2]) / 1.5))
                    g = min(255, int((color1[1] + color2[1]) / 1.5))
                    b = min(255, int((color1[0] + color2[0]) / 1.5))
                    
                    # 设置线条颜色和宽度
                    pen = QPen(QColor(r, g, b, 200))  # 降低不透明度为200
                    pen.setWidthF(line_width)  # 使用浮点数设置线宽
                    line.setPen(pen)
                else:
                    # 默认颜色 - 使用白色
                    pen = QPen(QColor(255, 255, 255, 200))  # 白色，半透明
                    pen.setWidthF(line_width)
                    line.setPen(pen)
                
                # 将线条添加到场景中
                self.graphics_scene.addItem(line)
    
    def add_point_to_scene(self, x, y, bodypart_idx=None):
        """添加点到场景"""
        if not self.graphics_scene:
            return
            
        size = self.point_size
        point_item = QGraphicsEllipseItem(x - size, y - size, size * 2, size * 2)
        
        # 设置点的Z值为1，确保它们显示在连接线和图片之上
        point_item.setZValue(1)
        
        # 使用自动生成的颜色
        if bodypart_idx is not None and bodypart_idx < len(self.colors):
            color = self.colors[bodypart_idx]
            point_color = QColor(color[2], color[1], color[0])  # BGR to RGB
            
            # 检查点是否被选中
            if bodypart_idx in self.selected_points:
                # 选中的点只增加大小和添加2像素的白边
                point_item.setPen(QPen(Qt.white, 2))  # 2像素白色边框
                point_item.setBrush(QColor(color[2], color[1], color[0], 255))  # 保持原色
                # 增加点的大小
                point_item.setRect(x - size * 1.2, y - size * 1.2, size * 2.4, size * 2.4)
            else:
                point_item.setPen(QPen(point_color, 2))
                point_item.setBrush(QColor(color[2], color[1], color[0], 255))
        else:
            # 默认的黑色点
            if bodypart_idx in self.selected_points:
                point_item.setPen(QPen(Qt.white, 2))  # 2像素白色边框
                point_item.setBrush(QColor(0, 0, 0, 255))
                # 增加点的大小
                point_item.setRect(x - size * 1.2, y - size * 1.2, size * 2.4, size * 2.4)
            else:
                point_item.setPen(QPen(QColor(0, 0, 0), 2))
                point_item.setBrush(QColor(0, 0, 0, 255))
        
        self.graphics_scene.addItem(point_item)
    
    def center_view_on_point(self, scene_point):
        """将视图中心设置到指定的场景坐标点"""
        if self.graphics_view:
            self.graphics_view.centerOn(scene_point)
    
    def add_point_at_cursor(self):
        """在光标位置添加点"""
        if not self.pixmap_item or not self.graphics_view:
            return False
        
        # 首先检查是否所有点都已标注完且处于等待跳转状态
        if self.all_points_complete:
            # 所有点都已标注完，用户再次按F键，跳转到下一张图片
            self.all_points_complete = False  # 重置状态
            return 'all_complete'
        
        # 获取当前选中的部位索引，如果没有选中则获取下一个未标注的部位
        if self.selected_points:
            current_index = self.selected_points[0]
        else:
            current_index = self.get_next_bodypart_index()
        
        if current_index >= len(self.bodyparts):
            # 所有点都已标注完，不应该到这里
            return False
        
        # 获取当前光标位置
        if self.parent:
            cursor_pos = self.graphics_view.mapFromGlobal(self.parent.cursor().pos())
        else:
            cursor_pos = self.graphics_view.mapFromGlobal(QCursor.pos())
        scene_pos = self.graphics_view.mapToScene(cursor_pos)
        
        # 安全地检查pixmap_item并获取包含关系
        try:
            if not (self.pixmap_item and hasattr(self.pixmap_item, 'contains')):
                return False
            
            pixmap_contains = self.pixmap_item.contains(scene_pos)
            if not pixmap_contains:
                return False
                
            # 安全地获取图片尺寸
            original_width = self.pixmap_item.pixmap().width()
            original_height = self.pixmap_item.pixmap().height()
        except (RuntimeError, AttributeError):
            # pixmap_item对象已被删除或无效
            return False
        
        if True:  # 替换原来的if条件
            
            # 获取点击位置在原始图片上的坐标（保留小数点）
            original_x = float(scene_pos.x())
            original_y = float(scene_pos.y())
            
            # 确保坐标在图片范围内
            original_x = max(0.0, min(original_x, original_width - 0.001))
            original_y = max(0.0, min(original_y, original_height - 0.001))
            
            # 添加点到字典
            self.points[current_index] = (original_x, original_y)
            
            # 更新显示 - 先更新所有点和连接线
            self.update_all_points()
            
            # 发出点添加信号
            self.point_added.emit(original_x, original_y, current_index)
            
            # 检查是否所有点都已标注完
            next_idx = self.get_next_bodypart_index()
            if next_idx >= len(self.bodyparts):
                # 所有点都已标注完，设置状态等待下次按F键跳转
                self.all_points_complete = True
                QApplication.processEvents()  # 确保UI更新
                return True  # 返回True表示点添加成功，但不跳转图片
            else:
                # 清除当前选择并选中下一个未标注的点
                self.clear_selection()
                self.selected_points = [next_idx]
                self.selection_changed.emit(self.selected_points)
            
            return True
        
        return False
    
    def get_next_bodypart_index(self):
        """获取下一个要标注的身体部位索引"""
        next_idx = None
        
        # 如果有选中的点，从选中的点开始
        if self.selected_points:
            current_idx = self.selected_points[0]
            # 从当前选中的点开始向后查找
            for i in range(current_idx, len(self.bodyparts)):
                if i not in self.points:
                    next_idx = i
                    break
            # 如果后面没有未标注的点，则从头开始查找
            if next_idx is None:
                for i in range(len(self.bodyparts)):
                    if i not in self.points:
                        next_idx = i
                        break
        else:
            # 如果没有选中的点，从头开始查找
            for i in range(len(self.bodyparts)):
                if i not in self.points:
                    next_idx = i
                    break
        
        # 如果找到了下一个要标注的点
        if next_idx is not None and next_idx < len(self.bodyparts):
            return next_idx
        
        return len(self.bodyparts)  # 如果所有部位都已标注，返回超出范围的索引
    
    def clear_selection(self):
        """清除所有选择"""
        self.selected_points = []
        
        # 重新绘制所有点，移除选中状态
        self.update_all_points()
        
        # 移除选择框
        if self.selection_rect is not None:
            try:
                # 尝试移除选择框，防止C++对象已删除错误
                scene = self.selection_rect.scene()
                if scene is not None:  # 确保项目仍在场景中
                    self.graphics_scene.removeItem(self.selection_rect)
            except (RuntimeError, ValueError, ReferenceError):
                # 捕获任何可能的错误，表示对象已被删除或无效
                pass
            finally:
                self.selection_rect = None
        
        # 发出选择改变信号
        self.selection_changed.emit(self.selected_points)
    
    def move_image(self, dx, dy):
        """移动图片视图"""
        if not self.graphics_view:
            return
            
        # 获取当前滚动条位置
        h_bar = self.graphics_view.horizontalScrollBar()
        v_bar = self.graphics_view.verticalScrollBar()
        
        # 计算新位置
        h_bar.setValue(h_bar.value() + dx)
        v_bar.setValue(v_bar.value() + dy)
    
    def load_image(self, file_path):
        """加载并显示图片"""
        if not file_path or not os.path.exists(file_path):
            return False
        
        if not self.graphics_view or not self.graphics_scene:
            return False
        
        # 保存当前的缩放比例和视图中心点
        current_scale = 1.0
        view_center = None
        
        if hasattr(self.graphics_view, '_current_scale'):
            current_scale = self.graphics_view._current_scale
            
            # 获取当前视图中心在场景中的坐标
            view_rect = self.graphics_view.viewport().rect()
            view_center = self.graphics_view.mapToScene(view_rect.center())
            
            # 安全地获取图片尺寸
            try:
                if (self.pixmap_item is not None and 
                    hasattr(self.pixmap_item, 'pixmap')):
                    pixmap_width = self.pixmap_item.pixmap().width()
                    pixmap_height = self.pixmap_item.pixmap().height()
                    if pixmap_width > 0 and pixmap_height > 0:
                        # 计算中心点相对于图片的比例位置（0.0-1.0）
                        center_x_ratio = view_center.x() / pixmap_width
                        center_y_ratio = view_center.y() / pixmap_height
                        view_center = QPointF(center_x_ratio, center_y_ratio)
                    else:
                        view_center = None
                else:
                    view_center = None
            except (RuntimeError, AttributeError):
                # pixmap_item对象已被删除或无效
                view_center = None
        
        # 设置当前图片路径
        self.current_image_path = file_path
        
        # 尝试从缓存中获取图片
        pixmap = self._get_pixmap_from_cache(file_path)
        if pixmap is None:
            return False
        
        # 更新图形场景
        self._update_graphics_scene(pixmap, current_scale, view_center)
        
        return True
    
    def _get_pixmap_from_cache(self, file_path):
        """从缓存获取或加载图片"""
        if file_path in self.pixmap_cache:
            return self.pixmap_cache[file_path]
        
        # 从文件加载图片
        pixmap = QPixmap(file_path)
        
        # 检查图片是否成功加载
        if pixmap.isNull():
            if self.parent:
                create_styled_message_box(
                    self.parent, "Error", 
                    f"Failed to load image: {file_path}", 
                    QMessageBox.Warning, use_primary_buttons=False
                ).exec()
            return None
        
        # 如果缓存已满，移除最早添加的图片
        if len(self.pixmap_cache) >= self.max_cache_size:
            oldest_key = next(iter(self.pixmap_cache))
            del self.pixmap_cache[oldest_key]
        
        # 添加图片到缓存
        self.pixmap_cache[file_path] = pixmap
        return pixmap
    
    def _update_graphics_scene(self, pixmap, current_scale, view_center):
        """更新图形场景中的图片"""
        # 清除场景并重置pixmap_item引用
        self.graphics_scene.clear()
        self.pixmap_item = None  # 重置引用，避免访问已删除的对象
        
        # 创建新的pixmap项
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        
        # 设置图片项的Z值为0（在最底层）
        self.pixmap_item.setZValue(0)
        
        self.graphics_scene.addItem(self.pixmap_item)
        
        # 获取图片尺寸并设置场景大小
        width = pixmap.width()
        height = pixmap.height()
        
        # 设置场景矩形
        base_rect = QRectF(0, 0, width, height)
        extra_size = getattr(self.graphics_view, '_extra_scene_size', 1000)
        extended_rect = base_rect.adjusted(-extra_size, -extra_size, extra_size, extra_size)
        self.graphics_scene.setSceneRect(extended_rect)
        
        # 处理视图缩放和定位
        self._adjust_view_scale_and_position(current_scale, view_center, width, height)
        
        # 如果有标注数据，显示标注点
        if self.points:
            self.update_all_points()
    
    def _adjust_view_scale_and_position(self, current_scale, view_center, width, height):
        """调整视图缩放和位置"""
        # 如果是第一次加载图片或没有保存的视图中心，使用适应视图的缩放
        if current_scale == 1.0 or view_center is None:
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.graphics_view._current_scale = 1.0  # 设置当前缩放比例为1.0
        else:
            # 先适应视图
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.graphics_view._current_scale = 1.0  # 重置为1.0
            
            # 应用保存的缩放比例
            self.graphics_view.scale(current_scale, current_scale)
            self.graphics_view._current_scale = current_scale
            
            # 计算新图片上的中心点位置
            new_center_x = width * view_center.x()
            new_center_y = height * view_center.y()
            
            # 将视图中心设置到计算出的位置
            QTimer.singleShot(
                50, 
                lambda: self.center_view_on_point(QPointF(new_center_x, new_center_y))
            )
    
    def select_point(self, bodypart_idx):
        """选择指定的点"""
        if bodypart_idx in self.points:
            # 如果该点已经标注，选中它
            self.selected_points = [bodypart_idx]
            self.update_all_points()
            self.point_selected.emit(bodypart_idx)
            self.selection_changed.emit(self.selected_points)
            return True
        else:
            # 如果该点未标注，设置为待标注状态
            self.selected_points = [bodypart_idx]
            self.selection_changed.emit(self.selected_points)
            return False
    
    def toggle_point_selection(self, bodypart_idx):
        """切换点的选择状态"""
        if bodypart_idx in self.selected_points:
            self.selected_points.remove(bodypart_idx)
        else:
            self.selected_points.append(bodypart_idx)
        
        self.update_all_points()
        self.selection_changed.emit(self.selected_points)
    
    def get_selected_points(self):
        """获取当前选中的点"""
        return self.selected_points.copy()
    
    def get_points(self):
        """获取所有标注点"""
        return self.points.copy()
    
    def clear_cache(self):
        """清空图片缓存"""
        self.pixmap_cache.clear()
    
    def update_point_size(self, size):
        """更新标注点大小"""
        self.point_size = float(size)
        self.update_all_points()
    
    def get_image_dimensions(self):
        """获取当前图片的尺寸"""
        try:
            if (self.pixmap_item and hasattr(self.pixmap_item, 'pixmap')):
                pixmap = self.pixmap_item.pixmap()
                return pixmap.width(), pixmap.height()
        except (RuntimeError, AttributeError):
            # pixmap_item对象已被删除或无效
            pass
        return None, None
    
    def is_point_in_image(self, scene_pos):
        """检查点是否在图片区域内"""
        try:
            if self.pixmap_item and hasattr(self.pixmap_item, 'contains'):
                return self.pixmap_item.contains(scene_pos)
        except (RuntimeError, AttributeError):
            # pixmap_item对象已被删除或无效
            pass
        return False
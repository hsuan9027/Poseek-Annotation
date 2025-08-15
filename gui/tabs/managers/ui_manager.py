"""
UIManager - Handles UI layout and interaction management
Creates interface layouts, manages UI components, and handles display updates
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTreeView, QSplitter, QFileSystemModel, QSizePolicy, QLineEdit,
    QScrollArea, QStackedWidget, QFrame, QDoubleSpinBox, QApplication
)
from PySide6.QtCore import Qt, QObject, Signal, QSortFilterProxyModel
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QCursor
import re
from gui.style_manager import apply_standard_style, apply_help_style, apply_primary_style
from gui.utils import generate_color
from gui.components import GraphicsView
from PySide6.QtWidgets import QGraphicsScene


class NaturalSortProxyModel(QSortFilterProxyModel):
    """Custom sorting proxy model for natural sorting (numeric values sorted by size)"""
    
    def lessThan(self, left, right):
        """重写比较函数以实现自然排序"""
        if not self.sourceModel():
            return super().lessThan(left, right)
            
        left_data = self.sourceModel().data(left, Qt.DisplayRole)
        right_data = self.sourceModel().data(right, Qt.DisplayRole)
        
        if left_data is None or right_data is None:
            return super().lessThan(left, right)
        
        # 自然排序的关键：将字符串分解为文本和数字部分
        def natural_key(text):
            """将字符串分解为文本和数字部分的列表"""
            def convert(t):
                return int(t) if t.isdigit() else t.lower()
            return [convert(c) for c in re.split('([0-9]+)', str(text))]
        
        return natural_key(left_data) < natural_key(right_data)


class UIManager(QObject):
    """UI manager for all interface layout and interaction operations"""
    
    # 信号定义
    folder_selected = Signal()              # 文件夹选择信号
    file_selected = Signal(object)          # 文件选择信号 (QModelIndex)
    folder_input_changed = Signal(str)      # 文件夹输入改变信号
    point_size_changed = Signal(float)      # 点大小改变信号
    edit_keypoints_clicked = Signal()       # 编辑关键点信号
    bodypart_clicked = Signal(int)          # 身体部位点击信号 (bodypart_idx)
    save_clicked = Signal()                 # 保存点击信号
    help_clicked = Signal()                 # 帮助点击信号
    export_clicked = Signal()               # 导出点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # UI组件引用
        self.splitter = None
        self.select_folder_button = None
        self.selected_folder_input = None
        self.stacked_widget = None
        self.file_model = None
        self.tree_view = None
        self.point_size_spinbox = None
        self.edit_button = None
        self.bodyparts_label = None
        self.empty_bodyparts_container = None
        self.part_labels = []
        self.part_widgets = []
        self.help_button = None
        self.save_button = None
        self.export_button = None
        self.image_scroll_area = None
        self.graphics_view = None
        self.graphics_scene = None
        
        # 配置数据
        self.bodyparts = []
        self.connections = []
        self.colors = []
        self.points = {}
        self.selected_points = []
        
        # 设置
        self.start_directory = "."
        self.point_size = 0.2
    
    def init_ui(self, main_widget):
        """初始化主UI"""
        # 主布局使用QSplitter来实现可调整大小的三栏布局
        self.splitter = QSplitter(Qt.Horizontal)
        self.setup_splitter_style()
        
        # 创建三个主要区域
        left_widget = self.create_left_panel()
        center_widget = self.create_center_panel()
        right_widget = self.create_right_panel()
        
        # 将三个区域添加到splitter
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(center_widget)
        self.splitter.addWidget(right_widget)
        
        # 设置各区域的初始比例，使中间区域尽可能大
        self.splitter.setSizes([100, 600, 100])
        
        # 设置主布局
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.addWidget(self.splitter)
        main_widget.setLayout(main_layout)
        
        # 应用按钮样式
        apply_standard_style(self.select_folder_button)
        apply_primary_style(self.save_button)
        apply_help_style(self.help_button)
        apply_standard_style(self.export_button)
    
    def setup_splitter_style(self):
        """设置分割线样式"""
        self.splitter.setHandleWidth(1)  # 分割线宽度
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background: #444444;
                border: 1px solid #555555;
            }
            QSplitter::handle:hover {
                background: #666666;
            }
        """)
        self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    def create_left_panel(self):
        """创建左侧文件浏览面板"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)
        
        # 添加选择目录按钮
        self.select_folder_button = QPushButton("Select Folder")
        self.select_folder_button.clicked.connect(lambda: self.folder_selected.emit())
        self.select_folder_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        left_layout.addWidget(self.select_folder_button, alignment=Qt.AlignLeft)
        
        left_layout.addSpacing(10)
        
        # 文本框
        self.selected_folder_input = QLineEdit()
        self.selected_folder_input.setPlaceholderText("Enter folder path or select from below")
        self.selected_folder_input.textChanged.connect(self.folder_input_changed.emit)
        left_layout.addWidget(self.selected_folder_input)
        
        # 创建堆叠小部件，用于切换显示提示信息和文件树
        self.stacked_widget = QStackedWidget()
        
        # 创建提示标签
        prompt_widget = QWidget()
        prompt_layout = QVBoxLayout(prompt_widget)
        prompt_label = QLabel("Select a folder")
        prompt_label.setAlignment(Qt.AlignCenter)
        prompt_layout.addWidget(prompt_label)
        self.stacked_widget.addWidget(prompt_widget)
        
        # 创建文件系统模型和树视图
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(self.start_directory)
        
        # 设置过滤器只显示图片文件和目录
        self.file_model.setNameFilters(["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif"])
        self.file_model.setNameFilterDisables(False)
        
        # 创建自然排序的代理模型
        self.proxy_model = NaturalSortProxyModel()
        self.proxy_model.setSourceModel(self.file_model)
        self.proxy_model.setDynamicSortFilter(True)
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.proxy_model)  # 使用代理模型
        self.tree_view.clicked.connect(self._on_tree_view_clicked)  # 需要处理代理索引
        
        # 设置排序 - 按文件名升序排列
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(0, Qt.AscendingOrder)  # 0 是名称列
        
        self.stacked_widget.addWidget(self.tree_view)
        
        # 初始显示提示信息
        self.stacked_widget.setCurrentIndex(0)
        
        left_layout.addWidget(self.stacked_widget)
        
        return left_widget
    
    def create_center_panel(self):
        """创建中间图片显示面板"""
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(8, 8, 8, 2)  # 减小底部边距
        center_layout.setSpacing(4)  # 减小间距
        
        # 添加控制按钮布局
        controls_layout = QHBoxLayout()
        
        # 快捷键显示容器
        shortcuts_container = self._create_shortcuts_container()
        controls_layout.addWidget(shortcuts_container)
        
        # 添加弹性空间，使按钮靠右
        controls_layout.addStretch()
        
        # 添加导出按钮
        self.export_button = QPushButton("Export")
        self.export_button.setToolTip("Export all images with annotations")
        self.export_button.clicked.connect(lambda: self.export_clicked.emit())
        controls_layout.addWidget(self.export_button)
        
        # 添加间距
        spacer1 = QWidget()
        spacer1.setFixedWidth(10)
        controls_layout.addWidget(spacer1)
        
        # 添加帮助按钮
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(20, 20)
        self.help_button.setToolTip("Help")
        self.help_button.clicked.connect(lambda: self.help_clicked.emit())
        controls_layout.addWidget(self.help_button)
        
        # 添加间距
        spacer2 = QWidget()
        spacer2.setFixedWidth(10)
        controls_layout.addWidget(spacer2)
        
        # 保存按钮
        self.save_button = QPushButton("Save")
        self.save_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(lambda: self.save_clicked.emit())
        controls_layout.addWidget(self.save_button)
        
        # 先添加控制按钮布局
        center_layout.addLayout(controls_layout)
        
        # 图片显示区域
        self.image_scroll_area = QScrollArea()
        self.image_scroll_area.setWidgetResizable(True)
        
        # 使用自定义的 GraphicsView 和 QGraphicsScene 显示图片
        self.graphics_view = GraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.setup_graphics_view()
        
        self.image_scroll_area.setWidget(self.graphics_view)
        center_layout.addWidget(self.image_scroll_area, stretch=1)
        
        # 添加信息栏（类似快捷键容器的样式）
        info_container = self._create_info_container()
        center_layout.addWidget(info_container)
        
        return center_widget
    
    def _create_shortcuts_container(self):
        """创建快捷键显示容器"""
        shortcuts_container = QWidget()
        shortcuts_layout = QHBoxLayout(shortcuts_container)
        shortcuts_layout.setContentsMargins(0, 0, 0, 0)
        shortcuts_layout.setSpacing(20)
        
        # 创建各个快捷键标签
        shortcut_pairs = [
            ("F", "Add Point"),
            ("A", "Previous"),
            ("D", "Next"),
            (["↑", "↓", "←", "→"], "Move"),
            ("Mouse Wheel", "Zoom")
        ]
        
        for key, description in shortcut_pairs:
            pair_widget = QWidget()
            pair_layout = QHBoxLayout(pair_widget)
            pair_layout.setContentsMargins(0, 0, 0, 0)
            pair_layout.setSpacing(5)
            
            if isinstance(key, list):  # 处理方向键组
                arrows_widget = QWidget()
                arrows_layout = QHBoxLayout(arrows_widget)
                arrows_layout.setContentsMargins(0, 0, 0, 0)
                arrows_layout.setSpacing(2)
                
                for arrow in key:
                    key_label = QLabel(arrow)
                    key_label.setStyleSheet("""
                        background-color: rgba(180, 180, 180, 0.3);
                        border: 1px solid rgba(200, 200, 200, 0.4);
                        border-radius: 4px;
                        padding: 1px 1px;
                        font-weight: bold;
                        font-size: 12px;
                        color: white;
                    """)
                    arrows_layout.addWidget(key_label)
                
                pair_layout.addWidget(arrows_widget)
            else:
                key_label = QLabel(key)
                key_label.setStyleSheet("""
                    background-color: rgba(180, 180, 180, 0.3);
                    border: 1px solid rgba(200, 200, 200, 0.4);
                    border-radius: 4px;
                    padding: 1px 1px;
                    font-weight: bold;
                    font-size: 12px;
                    color: white;
                """)
                pair_layout.addWidget(key_label)
            
            # 创建描述标签
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: white; font-size: 12px;")
            pair_layout.addWidget(desc_label)
            shortcuts_layout.addWidget(pair_widget)
        
        shortcuts_layout.addStretch()
        return shortcuts_container
    
    def _create_info_container(self):
        """创建信息显示容器"""
        info_container = QWidget()
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(10, 0, 10, 0)
        info_layout.setSpacing(30)  # 增加间距
        
        # 设置容器固定高度
        info_container.setFixedHeight(14)
        
        # 通用标签样式
        label_style = "color: white; font-size: 12px;"
        
        # 图片编号信息 - 固定宽度
        self.image_info_label = QLabel("Image: --/--")
        self.image_info_label.setStyleSheet(label_style)
        self.image_info_label.setFixedWidth(100)  # 固定宽度
        info_layout.addWidget(self.image_info_label)
        
        # 鼠标坐标信息 - 固定宽度
        self.mouse_coord_label = QLabel("Position: (--, --)")
        self.mouse_coord_label.setStyleSheet(label_style)
        self.mouse_coord_label.setFixedWidth(150)  # 固定宽度
        info_layout.addWidget(self.mouse_coord_label)
        
        # 关键点配置名称 - 固定宽度
        self.keypoint_config_label = QLabel("Keypoints: --")
        self.keypoint_config_label.setStyleSheet(label_style)
        self.keypoint_config_label.setFixedWidth(200)  # 固定宽度
        info_layout.addWidget(self.keypoint_config_label)
        
        info_layout.addStretch()
        
        return info_container
    
    def setup_graphics_view(self):
        """设置图形视图的属性"""
        self.graphics_view.setScene(self.graphics_scene)
        
        # 确保图形视图可以接收键盘事件
        self.graphics_view.setFocusPolicy(Qt.StrongFocus)
        
        # 创建细十字光标
        cursor_size = 12
        cursor_pixmap = QPixmap(cursor_size, cursor_size)
        cursor_pixmap.fill(Qt.transparent)
        
        painter = QPainter(cursor_pixmap)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        # 绘制十字线
        painter.drawLine(cursor_size//2, cursor_size//2 - 8, cursor_size//2, cursor_size//2 + 8)
        painter.drawLine(cursor_size//2 - 8, cursor_size//2, cursor_size//2 + 8, cursor_size//2)
        painter.end()
        
        # 创建自定义光标
        thin_cross_cursor = QCursor(cursor_pixmap, cursor_size//2, cursor_size//2)
        self.graphics_view.viewport().setCursor(thin_cross_cursor)
    
    def create_right_panel(self):
        """创建右侧标注工具面板"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(8)
        
        # 添加点大小调整控件
        point_size_layout = QHBoxLayout()
        point_size_layout.setSpacing(4)
        
        point_size_label = QLabel("Point Size:")
        point_size_layout.addWidget(point_size_label)
        
        self.point_size_spinbox = QDoubleSpinBox()
        self.point_size_spinbox.setMinimum(0.1)
        self.point_size_spinbox.setMaximum(30.0)
        self.point_size_spinbox.setValue(self.point_size)
        self.point_size_spinbox.setSingleStep(0.1)
        self.point_size_spinbox.setDecimals(1)
        self.point_size_spinbox.valueChanged.connect(self.point_size_changed.emit)
        self.point_size_spinbox.setFixedWidth(50)
        
        point_size_layout.addWidget(self.point_size_spinbox)
        point_size_layout.addStretch()
        
        right_layout.addLayout(point_size_layout)
        right_layout.addSpacing(4)
        
        # 添加编辑按钮
        self.edit_button = QPushButton("Edit Keypoints")
        self.edit_button.clicked.connect(lambda: self.edit_keypoints_clicked.emit())
        apply_standard_style(self.edit_button)
        right_layout.addWidget(self.edit_button)

        # 添加身体部位列表标签
        self.bodyparts_label = QLabel("Body Parts:")
        right_layout.addWidget(self.bodyparts_label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
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
        """)
        
        # 初始创建空的身体部位容器
        self._create_bodyparts_container(scroll_area)
        
        # 将滚动区域添加到右侧面板
        right_layout.addWidget(scroll_area, 1)
        
        return right_widget
    
    def _create_bodyparts_container(self, scroll_area):
        """创建身体部位容器"""
        parts_container = QWidget()
        parts_layout = QVBoxLayout(parts_container)
        parts_layout.setContentsMargins(0, 0, 0, 0)
        parts_layout.setSpacing(2)
        
        # 创建提示容器
        self.empty_bodyparts_container = QWidget()
        empty_layout = QVBoxLayout(self.empty_bodyparts_container)
        empty_layout.setContentsMargins(0, 350, 0, 0)
        empty_layout.addStretch(1)
        
        empty_bodyparts_label = QLabel("No keypoints defined.\\nClick 'Edit Keypoints'.")
        empty_bodyparts_label.setStyleSheet("color: white; font-size: 13px;")
        empty_bodyparts_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_bodyparts_label)
        empty_layout.addStretch(2)
        
        self.empty_bodyparts_container.setStyleSheet("background-color: transparent;")
        parts_layout.addWidget(self.empty_bodyparts_container)
        
        # 初始化空列表
        self.part_labels = []
        self.part_widgets = []
        
        # 显示提示信息
        self.empty_bodyparts_container.setVisible(True)
        
        parts_layout.addStretch()
        scroll_area.setWidget(parts_container)
    
    def set_config(self, bodyparts, connections):
        """设置关键点配置"""
        self.bodyparts = bodyparts
        self.connections = connections
        
        # 生成颜色
        self.colors = []
        for i in range(len(bodyparts)):
            color = generate_color(i, len(bodyparts))
            self.colors.append(color)
    
    def set_points(self, points):
        """设置当前图片的标注点"""
        self.points = points.copy() if points else {}
    
    def set_selected_points(self, selected_points):
        """设置选中的点"""
        self.selected_points = selected_points.copy() if selected_points else []
    
    def update_all_bodyparts(self):
        """更新所有身体部位的显示"""
        for i, label in enumerate(self.part_labels):
            if i < len(self.bodyparts):
                if i in self.points:
                    x, y = self.points[i]
                    label.setText(f"{self.bodyparts[i]} - ({x:.1f}, {y:.1f})")
                    
                    if i in self.selected_points:
                        # 选中的点使用高亮样式
                        label.setStyleSheet(
                            "font-weight: bold; color: white; "
                            "background-color: rgba(100, 100, 255, 120); "
                            "border-radius: 4px; padding: 2px 8px;"
                        )
                    else:
                        # 未选中的已标注点
                        label.setStyleSheet(
                            "font-weight: bold; color: rgba(255, 255, 255, 150); "
                            "background-color: transparent;"
                        )
                else:
                    # 未标注的部位
                    label.setText(f"{self.bodyparts[i]}")
                    if i in self.selected_points:
                        # 未标注但选中的部位 - 使用该部位的颜色高亮
                        bg_color = "rgba(120, 180, 240, 100)"  # 默认亮蓝色
                        
                        # 如果有颜色配置，使用对应的颜色
                        if self.colors and i < len(self.colors):
                            color = self.colors[i]
                            if isinstance(color, list) and len(color) == 3:
                                # BGR转RGB并提高亮度
                                r = min(255, int(color[2] * 2.0))
                                g = min(255, int(color[1] * 2.0))
                                b = min(255, int(color[0] * 2.0))
                                bg_color = f"rgba({r}, {g}, {b}, 100)"
                        
                        label.setStyleSheet(
                            f"font-weight: bold; color: white; "
                            f"background-color: {bg_color}; "
                            f"border-radius: 4px; padding: 2px 8px;"
                        )
                    else:
                        # 未标注且未选中的部位
                        label.setStyleSheet("color: white; background-color: transparent;")
    
    def rebuild_bodyparts_ui(self):
        """重建右侧面板中的身体部位标签界面"""
        # 获取右侧面板的滚动区域
        right_panel = self.splitter.widget(2)
        if not right_panel:
            return
            
        scroll_area = None
        for i in range(right_panel.layout().count()):
            item = right_panel.layout().itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QScrollArea):
                scroll_area = item.widget()
                break
        
        if not scroll_area:
            return
        
        # 清除旧内容
        old_widget = scroll_area.takeWidget()
        if old_widget:
            old_widget.deleteLater()
        
        # 创建新容器
        parts_container = QWidget()
        parts_layout = QVBoxLayout(parts_container)
        parts_layout.setContentsMargins(0, 0, 0, 0)
        parts_layout.setSpacing(2)
        
        # 清空旧引用
        self.part_labels = []
        self.part_widgets = []
        
        # 重新创建空状态容器
        self.empty_bodyparts_container = QWidget()
        empty_layout = QVBoxLayout(self.empty_bodyparts_container)
        empty_layout.setContentsMargins(0, 360, 0, 0)
        empty_layout.addStretch(1)
        
        empty_bodyparts_label = QLabel("No keypoints defined.\\nClick 'Edit Keypoints'.")
        empty_bodyparts_label.setStyleSheet("color: white; font-size: 13px;")
        empty_bodyparts_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_bodyparts_label)
        empty_layout.addStretch(2)
        
        self.empty_bodyparts_container.setStyleSheet("background-color: transparent;")
        parts_layout.addWidget(self.empty_bodyparts_container)
        
        # 根据是否有bodyparts决定显示内容
        if not self.bodyparts:
            self.empty_bodyparts_container.setVisible(True)
        else:
            self.empty_bodyparts_container.setVisible(False)
            
            for i, part in enumerate(self.bodyparts):
                part_widget = self._create_bodypart_widget(i, part)
                parts_layout.addWidget(part_widget)
                self.part_widgets.append(part_widget)
        
        parts_layout.addStretch()
        scroll_area.setWidget(parts_container)
        
        # 设置事件
        self.setup_bodyparts_events()
    
    def _create_bodypart_widget(self, index, part_name):
        """创建单个身体部位控件"""
        # 创建水平布局
        part_layout = QHBoxLayout()
        part_layout.setContentsMargins(0, 0, 0, 0)
        part_layout.setSpacing(10)
        
        # 创建颜色点
        color_dot = QLabel()
        color_dot.setFixedSize(8, 8)
        color_dot.setAlignment(Qt.AlignCenter)
        
        # 创建文本标签
        label = QLabel(part_name)
        label.setWordWrap(True)
        label.setTextFormat(Qt.PlainText)
        label.setMinimumWidth(250)
        label.setStyleSheet("color: white; background-color: transparent;")
        label.setContentsMargins(0, 0, 0, 0)
        
        # 设置颜色
        if index < len(self.colors):
            color = self.colors[index]
            color_style = f"background-color: rgb({color[2]}, {color[1]}, {color[0]}); border-radius: 4px;"
            color_dot.setStyleSheet(color_style)
        
        # 添加到布局
        part_layout.addWidget(color_dot, 0, Qt.AlignLeft | Qt.AlignVCenter)
        part_layout.addWidget(label, 1, Qt.AlignLeft | Qt.AlignVCenter)
        
        # 创建容器
        part_widget = QWidget()
        part_widget.setLayout(part_layout)
        part_widget.setMinimumHeight(20)
        part_widget.setMinimumWidth(150)
        part_widget.bodypart_idx = index
        
        # 设置样式
        part_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QWidget:hover {
                background-color: rgba(100, 100, 100, 50);
                border-radius: 4px;
            }
        """)
        
        # 存储标签引用
        self.part_labels.append(label)
        
        return part_widget
    
    def _on_tree_view_clicked(self, proxy_index):
        """处理树视图点击事件，将代理索引转换为源索引"""
        # 将代理模型索引转换为源模型索引
        source_index = self.proxy_model.mapToSource(proxy_index)
        # 发出信号，传递源索引
        self.file_selected.emit(source_index)
    
    def setup_bodyparts_events(self):
        """设置身体部位标签的点击事件"""
        for i, widget in enumerate(self.part_widgets):
            # 使部件可以接收鼠标事件
            widget.setAttribute(Qt.WA_Hover)
            widget.setCursor(Qt.PointingHandCursor)
            # 创建独立的点击处理函数，避免闭包问题
            widget.mousePressEvent = self._create_click_handler(i)
        
        # 更新显示
        self.update_all_bodyparts()
    
    def _create_click_handler(self, idx):
        """创建点击处理函数"""
        def handler(_):
            self.bodypart_clicked.emit(idx)
        return handler
    
    def update_image_info(self, current_index, total_count):
        """更新图片信息显示"""
        if hasattr(self, 'image_info_label'):
            if current_index >= 0 and total_count > 0:
                self.image_info_label.setText(f"Image: {current_index + 1}/{total_count}")
            else:
                self.image_info_label.setText("Image: --/--")
    
    def update_mouse_coordinates(self, x, y):
        """更新鼠标坐标显示"""
        if hasattr(self, 'mouse_coord_label'):
            if x is not None and y is not None:
                self.mouse_coord_label.setText(f"Position: ({int(x)}, {int(y)})")
            else:
                self.mouse_coord_label.setText("Position: (--, --)")
    
    def update_keypoint_config_name(self, config_name):
        """更新关键点配置名称显示"""
        if hasattr(self, 'keypoint_config_label'):
            if config_name:
                self.keypoint_config_label.setText(f"Keypoints: {config_name}")
            else:
                self.keypoint_config_label.setText("Keypoints: --")
    
    def set_selected_unmarked_point_color(self, bodypart_idx):
        """设置特殊背景颜色给未标记的选中点"""
        if 0 <= bodypart_idx < len(self.part_labels):
            label = self.part_labels[bodypart_idx]
            
            # 默认使用明亮的背景色
            bg_color = "rgba(120, 180, 240, 230)"
            
            # 如果有颜色配置，使用对应的颜色
            if self.colors and bodypart_idx < len(self.colors):
                color = self.colors[bodypart_idx]
                if isinstance(color, list) and len(color) == 3:
                    r = min(255, int(color[2] * 2.0))
                    g = min(255, int(color[1] * 2.0))
                    b = min(255, int(color[0] * 2.0))
                    bg_color = f"rgba({r}, {g}, {b}, 100)"
            
            # 应用样式
            label.setStyleSheet(f"""
                font-weight: bold; 
                color: white;
                background-color: {bg_color}; 
                border-radius: 5px; 
                padding: 3px 10px;
                margin: 2px;
            """)
            
            # 确保标签文本不包含坐标信息
            if bodypart_idx < len(self.bodyparts):
                label.setText(self.bodyparts[bodypart_idx])
    
    def update_bodyparts_display(self):
        """完全重建身体部位标签显示"""
        self.rebuild_bodyparts_ui()
    
    def update_directory_ui(self, dir_path):
        """更新目录相关的UI组件"""
        if self.tree_view and self.file_model and self.proxy_model:
            # 获取源模型索引并转换为代理模型索引
            source_index = self.file_model.index(dir_path)
            proxy_index = self.proxy_model.mapFromSource(source_index)
            
            self.tree_view.setRootIndex(proxy_index)
            self.tree_view.expand(proxy_index)
            self.tree_view.setColumnWidth(0, 250)
        
        if self.selected_folder_input:
            self.selected_folder_input.setText(dir_path)
        
        # 切换到文件树视图
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(1)
    
    def get_graphics_components(self):
        """获取图形组件"""
        return self.graphics_view, self.graphics_scene
    
    def get_file_model_components(self):
        """获取文件模型组件"""
        # 返回源模型，file_manager需要使用源模型进行文件路径操作
        return self.file_model, self.tree_view
    
    def get_point_size(self):
        """获取当前点大小设置"""
        return self.point_size_spinbox.value() if self.point_size_spinbox else self.point_size
    
    def set_point_size(self, size):
        """设置点大小"""
        self.point_size = size
        if self.point_size_spinbox:
            self.point_size_spinbox.setValue(size)
    
    def show_prompt_widget(self):
        """显示提示信息"""
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(0)
    
    def show_file_tree(self):
        """显示文件树"""
        if self.stacked_widget:
            self.stacked_widget.setCurrentIndex(1)
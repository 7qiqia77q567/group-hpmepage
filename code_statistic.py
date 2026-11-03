import sys
import os
import zipfile
import tempfile
import statistics
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush

# 现代精美 QSS 样式表
MODERN_STYLE = """
QMainWindow {
    background-color: #f4f6f9;
}
QLabel {
    color: #2c3e50;
    font-family: "Segoe UI", Arial, sans-serif;
}
QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: bold;
    font-family: "Segoe UI", Arial, sans-serif;
}
QPushButton:hover {
    background-color: #2980b9;
}
QPushButton:pressed {
    background-color: #1f618d;
}
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f9fafc;
    border: 1px solid #e1e8ed;
    border-radius: 8px;
    gridline-color: #e1e8ed;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #2c3e50;
}
QTableWidget::item {
    color: #2c3e50;
    padding: 4px;
}
QHeaderView::section {
    background-color: #2c3e50;
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
    font-size: 13px;
}
QTableWidget QTableCornerButton::section {
    background-color: #2c3e50;
    border: none;
}
"""

class PieChartWidget(QWidget):
    """自定义现代化环形占比图组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}  # 格式: {'C': 120, 'C++': 300, ...}
        # 各语言专属视觉配色方案
        self.colors = {
            'C': QColor('#e74c3c'),      # 红色
            'C++': QColor('#3498db'),    # 蓝色
            'JAVA': QColor('#e67e22'),   # 橙色
            'Python': QColor('#2ecc71'), # 绿色
            'C#': QColor('#9b59b6')      # 紫色
        }
        self.setMinimumSize(320, 280)

    def set_data(self, data_dict):
        self.data = data_dict
        self.update()  # 触发重新绘制

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 绘制背景卡片边框
        painter.setPen(QPen(QColor('#e1e8ed'), 1))
        painter.setBrush(QBrush(QColor('#ffffff')))
        painter.drawRoundedRect(QRectF(10, 10, width - 20, height - 20), 8, 8)

        total = sum(self.data.values())
        if total == 0:
            painter.setPen(QColor('#7f8c8d'))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            painter.drawText(QRectF(10, 10, width - 20, height - 20), Qt.AlignmentFlag.AlignCenter, "📊 暂无代码统计数据\n请先选择文件夹或压缩包")
            return

        # 计算图表尺寸与位置（左侧显示圆环，右侧显示图例）
        chart_size = min(width - 140, height - 40)
        cx = 95
        cy = height / 2
        r = chart_size / 2 - 15
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)

        start_angle = 0  # Qt 角度单位为 1/16 度
        for lang, val in self.data.items():
            if val <= 0:
                continue
            span_angle = int((val / total) * 360 * 16)
            painter.setBrush(QBrush(self.colors.get(lang, QColor('#95a5a6'))))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPie(rect, start_angle, span_angle)
            start_angle += span_angle

        # 绘制内部空白圆孔（形成精致的环形图效果）
        inner_r = r * 0.58
        inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
        painter.setBrush(QBrush(QColor('#ffffff')))
        painter.drawEllipse(inner_rect)

        # 环形图中心文字
        painter.setPen(QColor('#2c3e50'))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(inner_rect, Qt.AlignmentFlag.AlignCenter, f"代码总行\n{total}")

        # 右侧图例与百分比说明
        legend_x = cx + r + 25
        legend_y = cy - r + 10
        painter.setFont(QFont("Segoe UI", 10))
        for lang, val in self.data.items():
            if val <= 0:
                continue
            percent = (val / total) * 100
            # 颜色色块
            painter.setBrush(QBrush(self.colors.get(lang, QColor('#95a5a6'))))
            painter.drawRect(QRectF(legend_x, legend_y + 3, 12, 12))
            # 文字说明
            painter.setPen(QColor('#2c3e50'))
            painter.drawText(QRectF(legend_x + 20, legend_y, 160, 20), Qt.AlignmentFlag.AlignLeft, f"{lang}: {val}行 ({percent:.1f}%)")
            legend_y += 26


class CodeAnalyzer:
    """核心代码解析与统计引擎"""
    EXTENSIONS = {
        'C': ['.c', '.h'],
        'C++': ['.cpp', '.cc', '.cxx', '.hpp', '.hxx'],
        'JAVA': ['.java'],
        'Python': ['.py'],
        'C#': ['.cs']
    }

    def __init__(self, root_dir):
        self.root_dir = root_dir

    def analyze(self):
        stats = {lang: {'files': 0, 'code_lines': [], 'blank': 0, 'comment': 0, 'funcs': 0} 
                 for lang in self.EXTENSIONS}

        for dirpath, _, filenames in os.walk(self.root_dir):
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                target_lang = None
                for lang, exts in self.EXTENSIONS.items():
                    if ext in exts:
                        target_lang = lang
                        break
                
                if target_lang:
                    file_path = os.path.join(dirpath, filename)
                    self._parse_file(file_path, target_lang, stats)
        
        return stats

    def _parse_file(self, file_path, lang, stats):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return

        stats[lang]['files'] += 1
        total_lines = len(lines)
        blank_lines = 0
        comment_lines = 0
        func_count = 0
        in_block_comment = False

        py_func_re = re.compile(r'^\s*def\s+[a-zA-Z_]\w*\s*\(')
        file_code_lines = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
                continue

            if lang in ['C', 'C++', 'JAVA', 'C#']:
                if in_block_comment:
                    comment_lines += 1
                    if '*/' in stripped:
                        in_block_comment = False
                    continue
                if stripped.startswith('/*'):
                    comment_lines += 1
                    if '*/' not in stripped:
                        in_block_comment = True
                    continue
                if stripped.startswith('//'):
                    comment_lines += 1
                    continue
            elif lang == 'Python':
                if stripped.startswith('#'):
                    comment_lines += 1
                    continue

            file_code_lines += 1

            if lang == 'Python':
                if py_func_re.match(line):
                    func_count += 1
            else:
                if '{' in line and '(' in line and ')' in line and not any(k in stripped for k in ['if', 'for', 'while', 'switch', 'catch', 'return']):
                    func_count += 1

        stats[lang]['code_lines'].append(file_code_lines if file_code_lines > 0 else total_lines)
        stats[lang]['blank'] += blank_lines
        stats[lang]['comment'] += comment_lines
        stats[lang]['funcs'] += func_count


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级代码数据统计分析系统")
        self.resize(1150, 700)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 顶部操作栏
        top_layout = QHBoxLayout()
        self.btn_folder = QPushButton("📁 选择源代码文件夹")
        self.btn_folder.clicked.connect(self.select_folder)
        
        self.btn_zip = QPushButton("📦 导入压缩包 (.zip)")
        self.btn_zip.clicked.connect(self.select_zip)

        self.lbl_path = QLabel("当前未选择目录或文件")
        self.lbl_path.setStyleSheet("color: #7f8c8d; font-style: italic; font-size: 13px;")

        top_layout.addWidget(self.btn_folder)
        top_layout.addWidget(self.btn_zip)
        top_layout.addWidget(self.lbl_path, 1)
        main_layout.addLayout(top_layout)

        # 中部：表格展示区
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "语言", "源文件数", "代码行数", "空行数", "注释行数", 
            "函数个数", "最大值", "最小值", "均值", "中位数"
        ])
        
        header = self.table.horizontalHeader()
        for i in range(10):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMaximumHeight(240)  # 限制表格高度，留出空间给下方的图表
        main_layout.addWidget(self.table)

        # 底部：现代化占比图组件
        self.chart_widget = PieChartWidget()
        main_layout.addWidget(self.chart_widget)

        self.populate_table(None)

    def populate_table(self, stats):
        languages = ['C', 'C++', 'JAVA', 'Python', 'C#']
        self.table.setRowCount(len(languages))

        chart_data = {}

        for row, lang in enumerate(languages):
            files = 0
            code_sum = 0
            blank = 0
            comment = 0
            funcs = 0
            max_val = 0
            min_val = 0
            mean_val = 0
            median_val = 0

            if stats and lang in stats and stats[lang]['files'] > 0:
                s = stats[lang]
                files = s['files']
                code_sum = sum(s['code_lines'])
                blank = s['blank']
                comment = s['comment']
                funcs = s['funcs']
                lines_list = s['code_lines']
                if lines_list:
                    max_val = max(lines_list)
                    min_val = min(lines_list)
                    mean_val = round(statistics.mean(lines_list), 1)
                    median_val = round(statistics.median(lines_list), 1)

            chart_data[lang] = code_sum

            row_data = [
                lang, str(files), str(code_sum), str(blank), str(comment),
                str(funcs), str(max_val), str(min_val), str(mean_val), str(median_val)
            ]

            for col, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.table.setItem(row, col, item)

        # 将统计数据实时传递给环形图组件进行绘制
        self.chart_widget.set_data(chart_data)

    def select_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择代码文件夹")
        if dir_path:
            self.lbl_path.setText(f"已选择目录: {dir_path}")
            self.process_directory(dir_path)

    def select_zip(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择代码压缩包", "", "ZIP Files (*.zip)")
        if file_path:
            self.lbl_path.setText(f"正在解压并分析: {os.path.basename(file_path)}")
            temp_dir = tempfile.mkdtemp()
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                self.process_directory(temp_dir)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"解压或读取压缩包失败: {str(e)}")

    def process_directory(self, path):
        analyzer = CodeAnalyzer(path)
        stats = analyzer.analyze()
        self.populate_table(stats)
        QMessageBox.information(self, "完成", "代码数据统计分析及占比图生成已成功完成！")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
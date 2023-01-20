# -*- coding: utf-8 -*-
# @File    : Main.py
# @Date    : 2023-01-17
# @Author  : 王超逸
# @Brief   :
import sys

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPainter, QPen, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QMenu, QAction, \
    QMessageBox

import command
import dialog
from mytime import MyDateTime
from winEffect import WindowEffect
import exception_hook
assert exception_hook.qt_exception_hook  # 仅仅是为了让IDE知道，上面那一行不是无用的引入


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.window_pos = None
        self.press_pos = None
        self.setWindowTitle("当前时间")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.windowEffect = WindowEffect()
        self.windowEffect.setAeroEffect(int(self.winId()))
        # icon_path = Path(sys.argv[0]).resolve().parent / '时间.png'
        icon_path = path_def.BUNDLED_ASSETS_DIR / "时间.png"
        if not icon_path.exists():
            raise FileNotFoundError(f"{icon_path}找不到")
        self.setWindowIcon(QtGui.QIcon(str(icon_path)))

        self.layout = QVBoxLayout()
        self.label = QLabel()
        self.label.setMargin(5)
        self.label.setFont(QFont("Microsoft Yahei UI", 50))
        self.label.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        self.label2 = QLabel()
        self.label2.setMargin(5)
        self.label2.setFont(QFont("Microsoft Yahei UI", 20))
        # self.label.setStyleSheet("color:#e0f0ff;")
        # self.label2.setStyleSheet("color:#e0f0ff;")
        self.label2.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.label2)
        self.root = QWidget()
        self.root.setLayout(self.layout)
        self.update_time()

        # Set the central widget of the Window.
        self.setCentralWidget(self.root)
        self.setFixedSize(self.root.minimumSize())
        self.checkThreadTimer = QTimer(self)
        self.checkThreadTimer.setInterval(500)  # .5 seconds
        self.checkThreadTimer.timeout.connect(self.update_time)
        self.checkThreadTimer.start()

        # 创建右键菜单
        context = QMenu(self)
        t = QAction("晚安", self)
        t.triggered.connect(self.good_night)
        context.addAction(t)

        def _1():
            tt = dialog.SetHourTodayDialog(self)
            tt.exec()

        t = QAction("今天要多少小时？", self)
        t.triggered.connect(_1)
        context.addAction(t)

        t = QAction("现在还是昨天！", self)
        t.triggered.connect(lambda: command.today_is_yesterday())
        context.addAction(t)

        t = QAction("退出", self)
        t.triggered.connect(lambda x: app.quit())
        context.addAction(t)
        self.context = context

    def good_night(self):
        button = QMessageBox.question(self, "呀", "要睡了吗")

        if button == QMessageBox.Yes:
            command.good_night()

    def contextMenuEvent(self, e):
        self.context.exec(e.globalPos())

    def mousePressEvent(self, e):
        self.press_pos = e.globalPos()
        self.window_pos = self.pos()

    def mouseMoveEvent(self, e):
        self.move(self.window_pos + (e.globalPos() - self.press_pos))

    def update_time(self):
        t = MyDateTime.now()
        today = MyDateTime(t.stage, t.cycle, t.day)
        next_day = MyDateTime(t.stage, t.cycle, t.day + 1)
        self.label.setText(f"{t.stage}-{t.cycle}-{t.day}  {t.hour:02}:{t.minute:02}:{t.second:02}")
        self.label2.setText(
            f"今天有{((next_day - today).total_seconds() / 3600):.1f}小时, 还剩{((next_day - t).total_seconds() / 3600):.01f}小时")

    def paintEvent(self, event=None):
        painter = QPainter(self)
        painter.setOpacity(0.05)
        painter.setBrush(QColor(255, 180, 255))
        painter.setPen(QPen(Qt.red))
        painter.drawRect(self.rect())


Debug = False
if __name__ == '__main__':
    import ctypes, path_def

    path_def.init_path(__file__)
    # 传递appid，使得windows知道这个app不应该使用python的图标
    myappid = 'ChaochaoTime'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()

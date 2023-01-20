# -*- coding: utf-8 -*-


# @File    : dialog.py
# @Date    : 2023-01-19
# @Author  : 王超逸
# @Brief   :

from generated_ui.set_hour_today_ui import Ui_Dialog as SetHourTodayUI
from PyQt5.QtWidgets import QDialog
import command


class SetHourTodayDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.ui = SetHourTodayUI()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self.accepted)
        self.ui.buttonBox.rejected.connect(lambda: self.close())

    def accepted(self):
        command.set_today_hours(self.ui.doubleSpinBox.value())
        self.close()

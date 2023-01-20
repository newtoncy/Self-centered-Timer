# -*- coding: utf-8 -*-
# @File    : path_def.py
# @Date    : 2023-01-19
# @Author  : 王超逸
# @Brief   :
from pathlib import Path, WindowsPath, PosixPath
import sys

if sys.platform.startswith("win"):
    PathClass = WindowsPath
else:
    PathClass = PosixPath

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    IS_RELEASE = True
else:
    IS_RELEASE = False

# 程序入口所在的文件夹，__main__模块或者exe文件
ENTRY_POINT_DIR = None
# pyinstaller打包文件所在的文件夹
BUNDLED_ASSETS_DIR = None


def init_path(main_mod_path: str):
    global ENTRY_POINT_DIR, BUNDLED_ASSETS_DIR

    BUNDLED_ASSETS_DIR = PathClass(main_mod_path).parent.resolve() / "bundled_assets"
    if IS_RELEASE:
        ENTRY_POINT_DIR = PathClass(sys.executable).parent.resolve()
    else:
        ENTRY_POINT_DIR = PathClass(main_mod_path).parent.resolve()


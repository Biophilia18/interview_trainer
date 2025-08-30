# !/usr/bin/env python3
"""
# -*- coding: utf-8 -*-
@File    : build.py
@Author  : admin1
@Date    : 2025/8/30 10:14
@Description : 
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime


def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def main():
    print("开始构建 InterviewTrainer...")
    print(f"工作目录: {os.getcwd()}")

    # 创建构建目录
    build_dir = "build"
    dist_dir = "dist"

    # 清理之前的构建
    if os.path.exists(build_dir):
        print("清理 build 目录...")
        shutil.rmtree(build_dir)
    if os.path.exists(dist_dir):
        print("清理 dist 目录...")
        shutil.rmtree(dist_dir)

    # 检查依赖
    print("检查Python依赖...")
    dependencies = ['pymysql', 'customtkinter', 'werkzeug']
    missing_deps = []
    for dep in dependencies:
        success, stdout, stderr = run_command(f"pip show {dep}")
        if not success:
            missing_deps.append(dep)

    if missing_deps:
        print(f"警告: 缺少以下依赖: {', '.join(missing_deps)}")
        print("请运行: pip install pymysql customtkinter werkzeug")

    # 运行PyInstaller
    print("运行PyInstaller构建EXE文件...")

    # 构建命令 - 使用相对路径
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "InterviewTrainer",
        "--add-data", "config;config",
        "--add-data", "src;src",
        "--add-data", "data;data",
        "--hidden-import", "pymysql",
        "--hidden-import", "customtkinter",
        "--hidden-import", "werkzeug.security",
        "main_gui.py"
    ]

    success, stdout, stderr = run_command(" ".join(cmd))

    if success:
        print("✅ 构建成功!")

        # 确保dist目录存在
        dist_app_path = os.path.join(dist_dir, "InterviewTrainer.exe")
        if os.path.exists(dist_app_path):
            print(f"可执行文件位置: {os.path.abspath(dist_app_path)}")

            # 复制必要的配置文件（如果PyInstaller没有正确复制）
            dist_config_dir = os.path.join(dist_dir, "config")
            if not os.path.exists(dist_config_dir):
                os.makedirs(dist_config_dir)

            if os.path.exists("config/db_config.py"):
                shutil.copy2("config/db_config.py", os.path.join(dist_config_dir, "db_config.py"))
                print("已复制配置文件")
        else:
            print("警告: 未找到生成的可执行文件")

    else:
        print("❌ 构建失败!")
        print("错误信息:")
        print(stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

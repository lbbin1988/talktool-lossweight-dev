#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 使用 PyInstaller 打包成可执行文件
"""

import os
import sys
import subprocess
from pathlib import Path

def check_pyinstaller():
    """检查是否安装了 PyInstaller"""
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
        return True
    except ImportError:
        print("❌ PyInstaller 未安装")
        print("正在安装 PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller 安装成功")
        return True

def build_web_app():
    """打包 Web 服务版本"""
    print("\n" + "="*60)
    print("📦 正在打包 Web 服务版本...")
    print("="*60)
    
    # PyInstaller 参数
    pyinstaller_args = [
        "pyinstaller",
        "--name=Instagram截流工具",
        "--onefile",
        "--windowed",
        "--clean",
        "--add-data=intercept_bot_local.py:.",
        "web_service.py"
    ]
    
    print("执行命令：", " ".join(pyinstaller_args))
    result = subprocess.run(pyinstaller_args)
    
    if result.returncode == 0:
        print("\n✅ 打包成功！")
        print("可执行文件位置：dist/Instagram截流工具")
    else:
        print("\n❌ 打包失败")
    
    return result.returncode

def build_console_app():
    """打包命令行版本"""
    print("\n" + "="*60)
    print("📦 正在打包命令行版本...")
    print("="*60)
    
    pyinstaller_args = [
        "pyinstaller",
        "--name=Instagram截流工具-CLI",
        "--onefile",
        "--console",
        "--clean",
        "--add-data=intercept_bot_local.py:.",
        "intercept_bot_local.py"
    ]
    
    print("执行命令：", " ".join(pyinstaller_args))
    result = subprocess.run(pyinstaller_args)
    
    if result.returncode == 0:
        print("\n✅ 打包成功！")
        print("可执行文件位置：dist/Instagram截流工具-CLI")
    else:
        print("\n❌ 打包失败")
    
    return result.returncode

def main():
    print("="*60)
    print("🚀 Instagram 截流工具 - 打包程序")
    print("="*60)
    print("\n请选择打包方式：")
    print("1. Web 服务版本（带网页界面，推荐）")
    print("2. 命令行版本")
    print("3. 两者都打包")
    
    choice = input("\n请输入选项 (1/2/3)：").strip()
    
    check_pyinstaller()
    
    if choice == "1":
        build_web_app()
    elif choice == "2":
        build_console_app()
    elif choice == "3":
        build_web_app()
        build_console_app()
    else:
        print("❌ 无效选项")
        sys.exit(1)

if __name__ == "__main__":
    main()
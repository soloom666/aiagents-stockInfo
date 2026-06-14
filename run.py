#!/usr/bin/env python3
"""
AI股票分析系统启动脚本
运行命令: python run.py
"""

import subprocess
import sys
import os

def check_requirements():
    """检查必要的依赖是否安装"""
    try:
        import streamlit
        import pandas
        import plotly
        import yfinance
        import akshare
        import openai
        print("✅ 所有依赖包已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("请运行: python -m pip install -r requirements.txt")
        return False

def check_config():
    """检查配置文件"""
    try:
        print("ℹ️ 启动检查已跳过全局大模型 Key 校验")
        print("ℹ️ 股票分析现在使用登录用户自己的大模型配置，请在页面“环境配置”中设置")
        return True
    except Exception as exc:
        print(f"⚠️ 配置检查提示输出失败: {exc}")
        return True

def main():
    """主函数"""
    print("🚀 启动AI股票分析系统...")
    print("=" * 50)
    
    # 检查依赖
    if not check_requirements():
        return
    
    # 检查配置
    config_ok = check_config()
    
    # 启动Streamlit应用
    print("🌐 正在启动Web界面...")
    print("📝 本地访问: http://localhost:8503")
    print("📝 局域网访问: http://<本机IP>:8503")
    print("⏹️  按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8503",
            "--server.address", "0.0.0.0"
        ])
    except KeyboardInterrupt:
        print("\n👋 感谢使用AI股票分析系统！")

if __name__ == "__main__":
    main()

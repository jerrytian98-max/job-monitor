@echo off
chcp 65001 > nul
echo =========================================
echo 🚀 正在启动 【用户1(默认)】 的招聘监测配置面板
echo =========================================
set JOB_PROFILE=
set FLASK_PORT=5000
python app.py
pause

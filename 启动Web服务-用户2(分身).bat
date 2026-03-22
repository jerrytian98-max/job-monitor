@echo off
chcp 65001 > nul
echo =========================================
echo 🚀 正在启动 【用户2(分身)】 的招聘监测配置面板
echo =========================================
set JOB_PROFILE=user2
set FLASK_PORT=5001
python app.py
pause

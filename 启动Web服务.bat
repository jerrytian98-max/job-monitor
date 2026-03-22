@echo off
chcp 65001 >nul
echo ========================================
echo    招聘监测系统 - Web服务启动
echo ========================================
echo.
echo 正在启动Web服务...
echo 服务地址: http://127.0.0.1:5000
echo.
echo 按 Ctrl+C 可停止服务
echo ========================================
echo.

python app.py

pause

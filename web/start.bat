@echo off
chcp 65001 >nul
echo ========================================
echo   通话记录展示网页 - 启动
echo ========================================

echo.
echo [1/3] 安装后端依赖...
pip install fastapi uvicorn openpyxl -q

echo [2/3] 安装前端依赖...
cd /d d:\code\code\chaohuyun\web\frontend
call npm install

echo [3/3] 启动服务...
echo.
echo 后端: http://localhost:8066
echo 前端: http://localhost:3112
echo.

start "后端API" cmd /c "cd /d d:\code\code\chaohuyun\web\backend && python main.py"
timeout /t 2 >nul
start "前端" cmd /c "cd /d d:\code\code\chaohuyun\web\frontend && npm run dev"

echo 启动完成! 浏览器打开 http://localhost:3000
pause

@echo off
chcp 65001 >nul
title Pandy AI 打标器 V1.01
echo ========================================
echo   Pandy AI 打标器 V1.01
echo ========================================
echo.
echo 正在启动服务...
echo 启动后将自动打开浏览器
echo 请勿关闭此窗口
echo.
cd /d "%~dp0"
PandyTagger.exe
pause

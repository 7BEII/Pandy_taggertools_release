@echo off
chcp 65001 >nul
title Pandy AI 打标器
echo ========================================
echo    Pandy AI 打标器 - 启动中...
echo ========================================
echo.

REM 获取当前批处理文件所在目录
cd /d "%~dp0"

REM 检查 PandyTagger.exe 是否存在
if not exist "PandyTagger.exe" (
    echo [错误] 找不到 PandyTagger.exe
    echo 请确保此批处理文件与 PandyTagger.exe 在同一目录
    echo.
    pause
    exit /b 1
)

echo [启动] 正在启动 Pandy AI 打标器...
echo [提示] 浏览器将自动打开，请勿关闭此窗口
echo [提示] 关闭此窗口将停止服务
echo.
echo ========================================
echo.

REM 启动主程序
PandyTagger.exe

REM 如果程序异常退出，暂停以便查看错误信息
if errorlevel 1 (
    echo.
    echo ========================================
    echo [错误] 程序异常退出
    echo ========================================
    pause
)

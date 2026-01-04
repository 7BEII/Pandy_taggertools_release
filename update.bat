@echo off
chcp 65001 >nul
title Pandy AI 打标器 - 自动更新
cd /d "%~dp0"

echo ========================================
echo   Pandy AI 打标器 - 自动更新
echo ========================================
echo.

:: 需要保留的用户配置文件
set "CONFIG1=Pandy AI 打标器_V1.01\apikey_config\默认单图反推.json"
set "CONFIG2=Pandy AI 打标器_V1.01\apikey_config\默认编辑模型.json"

:: 检查是否安装了 Git
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Git，请先安装 Git
    echo 下载地址: https://git-scm.com/downloads
    echo.
    pause
    exit /b 1
)

:: 检查是否是 Git 仓库
if not exist ".git" (
    echo [提示] 当前目录不是 Git 仓库，正在克隆...
    echo.
    git clone https://github.com/7BEII/Pandy_taggertools_release.git .
    if %errorlevel% neq 0 (
        echo [错误] 克隆失败，请检查网络连接
        pause
        exit /b 1
    )
) else (
    :: 备份用户配置
    echo 正在备份用户配置...
    if exist "%CONFIG1%" copy "%CONFIG1%" "%CONFIG1%.bak" >nul
    if exist "%CONFIG2%" copy "%CONFIG2%" "%CONFIG2%.bak" >nul
    
    echo 正在从远程仓库拉取最新代码...
    echo.
    git fetch origin
    git reset --hard origin/main
    
    :: 恢复用户配置
    echo 正在恢复用户配置...
    if exist "%CONFIG1%.bak" (
        copy "%CONFIG1%.bak" "%CONFIG1%" >nul
        del "%CONFIG1%.bak" >nul
    )
    if exist "%CONFIG2%.bak" (
        copy "%CONFIG2%.bak" "%CONFIG2%" >nul
        del "%CONFIG2%.bak" >nul
    )
)

echo.
echo ========================================
echo   更新完成！
echo ========================================
echo.
pause

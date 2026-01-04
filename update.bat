@echo off
chcp 65001 >nul
echo ========================================
echo   Pandy AI 打标器 - 自动更新
echo ========================================
echo.
echo 正在从远程仓库拉取最新代码...
echo.

git fetch origin
git reset --hard origin/main

echo.
echo ========================================
echo   更新完成！
echo ========================================
echo.
pause

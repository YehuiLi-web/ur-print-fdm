@echo off
chcp 65001 >nul
echo ============================================
echo   UR Print FDM - 打包构建脚本
echo ============================================
echo.

REM Step 1: Install PyInstaller if not present
echo [1/3] 检查并安装 PyInstaller ...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo      正在安装 PyInstaller ...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败！
        pause
        exit /b 1
    )
)
echo      PyInstaller 已就绪。
echo.

REM Step 2: Build with PyInstaller
echo [2/3] 使用 PyInstaller 打包应用 ...
pyinstaller --noconfirm ur_print_fdm.spec
if errorlevel 1 (
    echo [错误] PyInstaller 打包失败！
    pause
    exit /b 1
)
echo      打包完成，输出目录: dist\UR Print FDM\
echo.

REM Step 3: Build installer with Inno Setup (if available)
echo [3/3] 生成安装程序 ...
set INNO_PATH=
where iscc >nul 2>&1
if not errorlevel 1 (
    set INNO_PATH=iscc
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if defined INNO_PATH (
    "%INNO_PATH%" installer.iss
    if errorlevel 1 (
        echo [错误] Inno Setup 编译失败！
        pause
        exit /b 1
    )
    echo      安装程序已生成: installer_output\UR_Print_FDM_Setup_0.1.0.exe
) else (
    echo [提示] 未检测到 Inno Setup 6，跳过安装程序生成。
    echo      你可以直接运行 dist\UR Print FDM\UR Print FDM.exe
    echo      或安装 Inno Setup 6 后运行: iscc installer.iss
)

echo.
echo ============================================
echo   构建完成！
echo ============================================
pause

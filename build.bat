@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY_CMD=py -3.11"
set "APP_SPEC=ur_print_fdm.spec"
set "PORTABLE_SPEC=ur_print_fdm_portable.spec"
set "INSTALLER_SCRIPT=installer.iss"
set "PORTABLE_EXE=dist\UR Print FDM Portable.exe"
set "APP_DIR=dist\UR Print FDM"
set "SETUP_EXE=installer_output\UR_Print_FDM_Setup_0.1.1.exe"
set "INNO_PATH="

echo ============================================
echo   UR Print FDM - 一键打包脚本
echo ============================================
echo.

echo [1/4] 检查 Python 3.11 ...
%PY_CMD% -c "import sys; print(sys.version)" >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python 3.11，请先安装后再执行打包。
    pause
    exit /b 1
)
echo      Python 3.11 已就绪。
echo.

echo [2/4] 检查并安装 PyInstaller ...
%PY_CMD% -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo      正在安装 PyInstaller ...
    %PY_CMD% -m pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败！
        pause
        exit /b 1
    )
)
echo      PyInstaller 已就绪。
echo.

echo [3/4] 构建可执行文件 ...
echo      生成目录版 ...
%PY_CMD% -m PyInstaller --noconfirm --clean "%APP_SPEC%"
if errorlevel 1 (
    echo [错误] 目录版打包失败！
    pause
    exit /b 1
)

echo      生成绿色单文件版 ...
%PY_CMD% -m PyInstaller --noconfirm --clean "%PORTABLE_SPEC%"
if errorlevel 1 (
    echo [错误] 绿色单文件版打包失败！
    pause
    exit /b 1
)
echo      可执行文件构建完成。
echo.

echo [4/4] 生成安装程序 ...
where iscc >nul 2>&1
if not errorlevel 1 (
    set "INNO_PATH=iscc"
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "INNO_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)

if defined INNO_PATH (
    "%INNO_PATH%" "%INSTALLER_SCRIPT%"
    if errorlevel 1 (
        echo [错误] Inno Setup 编译失败！
        pause
        exit /b 1
    )
    echo      安装程序已生成: %SETUP_EXE%
) else (
    echo [提示] 未检测到 Inno Setup 6，跳过安装程序生成。
    echo      如需安装版，请先安装 Inno Setup 6 后重新运行 build.bat。
)

echo.
echo ============================================
echo   打包完成！
echo ============================================
echo 绿色单文件版: %PORTABLE_EXE%
echo 目录版入口:   %APP_DIR%\UR Print FDM.exe
if exist "%SETUP_EXE%" echo 安装版:       %SETUP_EXE%
echo.
pause

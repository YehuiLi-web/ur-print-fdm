@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY_EXE="
set "PY_ARGS="
set "RELEASE_PREPARE_SCRIPT=scripts\prepare_release.py"
set "RELEASE_NOTES_FILE=release_notes\latest.txt"
set "APP_SPEC=ur_print_fdm.spec"
set "PORTABLE_SPEC=ur_print_fdm_portable.spec"
set "INSTALLER_SCRIPT=installer.iss"
set "PORTABLE_EXE=dist\UR Print FDM Portable.exe"
set "APP_DIR=dist\UR Print FDM"
set "APP_VERSION="
set "SETUP_EXE="
set "INNO_PATH="
set "VERSION_TMP=%TEMP%\ur_print_fdm_build_version.txt"

echo ============================================
echo   UR Print FDM - 一键打包脚本
echo ============================================
echo.

echo [1/5] 检查 Python 3.11 ...
call :find_python
if errorlevel 1 (
    echo [错误] 未找到 Python 3.11，请先安装后再执行打包。
    pause
    exit /b 1
)
"%PY_EXE%" %PY_ARGS% -c "import sys; print(sys.version)" >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 3.11 检查失败。
    pause
    exit /b 1
)
echo      Python 3.11 已就绪。
echo.

echo [2/5] 设置版本号与版本说明 ...
if not exist "%RELEASE_PREPARE_SCRIPT%" (
    echo [错误] 未找到发布准备脚本: %RELEASE_PREPARE_SCRIPT%
    pause
    exit /b 1
)
"%PY_EXE%" %PY_ARGS% "%RELEASE_PREPARE_SCRIPT%"
if errorlevel 1 (
    echo [错误] 版本信息准备失败！
    pause
    exit /b 1
)
call :load_version
if errorlevel 1 (
    echo [错误] 无法读取更新后的版本号！
    pause
    exit /b 1
)
echo      本次构建版本: %APP_VERSION%
echo      版本说明文件: %RELEASE_NOTES_FILE%
echo.

echo [3/5] 检查并安装 PyInstaller ...
"%PY_EXE%" %PY_ARGS% -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo      正在安装 PyInstaller ...
    "%PY_EXE%" %PY_ARGS% -m pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败！
        pause
        exit /b 1
    )
)
echo      PyInstaller 已就绪。
echo.

echo [4/5] 构建可执行文件 ...
echo      生成目录版 ...
"%PY_EXE%" %PY_ARGS% -m PyInstaller --noconfirm --clean "%APP_SPEC%"
if errorlevel 1 (
    echo [错误] 目录版打包失败！
    pause
    exit /b 1
)

echo      生成绿色单文件版 ...
"%PY_EXE%" %PY_ARGS% -m PyInstaller --noconfirm --clean "%PORTABLE_SPEC%"
if errorlevel 1 (
    echo [错误] 绿色单文件版打包失败！
    pause
    exit /b 1
)
echo      可执行文件构建完成。
echo.

echo [5/5] 生成安装程序 ...
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
    "%INNO_PATH%" /DMyAppVersion=%APP_VERSION% /DMyReleaseNotesFile=%RELEASE_NOTES_FILE% "%INSTALLER_SCRIPT%"
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
exit /b 0

:load_version
set "APP_VERSION="
"%PY_EXE%" %PY_ARGS% -c "import tomllib; from pathlib import Path; print(tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])" > "%VERSION_TMP%"
if errorlevel 1 exit /b 1
set /p APP_VERSION=<"%VERSION_TMP%"
del "%VERSION_TMP%" >nul 2>&1
if not defined APP_VERSION exit /b 1
set "SETUP_EXE=installer_output\UR_Print_FDM_Setup_%APP_VERSION%.exe"
exit /b 0

:find_python
call :probe_python py -3.11
if not errorlevel 1 exit /b 0

call :probe_python python
if not errorlevel 1 exit /b 0

call :probe_python "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not errorlevel 1 exit /b 0

call :probe_python "C:\Program Files\Python311\python.exe"
if not errorlevel 1 exit /b 0

call :probe_python "C:\Program Files (x86)\Python311\python.exe"
if not errorlevel 1 exit /b 0

exit /b 1

:probe_python
set "CANDIDATE_EXE=%~1"
set "CANDIDATE_ARGS="
if "%~2"=="" goto :probe_python_check
set "CANDIDATE_ARGS=%~2"

:probe_python_check
if not "%CANDIDATE_EXE%"=="py" if not "%CANDIDATE_EXE%"=="python" if not exist "%CANDIDATE_EXE%" exit /b 1
"%CANDIDATE_EXE%" %CANDIDATE_ARGS% -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 exit /b 1
set "PY_EXE=%CANDIDATE_EXE%"
set "PY_ARGS=%CANDIDATE_ARGS%"
exit /b 0

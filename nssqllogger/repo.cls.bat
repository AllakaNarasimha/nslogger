@echo off
REM =====================================================================
REM Repository Cleanup Script
REM =====================================================================
REM This script deletes specified files and folders from the repository
REM =====================================================================

echo =====================================================
echo Repository Cleanup Script
echo =====================================================
echo.

REM =====================================================================
REM FILES/FOLDERS TO DELETE - EDIT THIS LIST
REM =====================================================================

set "items_to_delete=build dist install_monitor logs error.txt *.log"

echo Items to delete:
echo %items_to_delete%
echo.

set /p confirm="Are you sure you want to delete these items? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo Operation cancelled.
    exit /b 0
)

echo.
echo Starting cleanup...
echo.

REM Delete each item
for %%i in (%items_to_delete%) do (
    if exist "%%i\" (
        echo Deleting directory: %%i
        rd /s /q "%%i" 2>nul
        if errorlevel 1 (
            echo   [FAILED] Could not delete directory: %%i
        ) else (
            echo   Ok Deleted directory: %%i
        )
    ) else if exist "%%i" (
        echo Deleting file: %%i
        del /f /q "%%i" 2>nul
        if errorlevel 1 (
            echo   [FAILED] Could not delete file: %%i
        ) else (
            echo   Ok Deleted file: %%i
        )
    ) else (
        echo   [SKIP] Not found: %%i
    )
)

REM Handle wildcard deletions separately
echo.
echo Handling wildcard deletions...

REM Delete .egg-info directories
if exist "*.egg-info" (
    echo Deleting .egg-info directories...
    for /d %%i in (*.egg-info) do (
        echo Deleting: %%i
        rd /s /q "%%i" 2>nul
        if errorlevel 1 (
            echo   [FAILED] Could not delete: %%i
        ) else (
            echo   Ok Deleted: %%i
        )
    )
) else (
    echo   [SKIP] No .egg-info directories found
)

REM Delete __pycache__ directories recursively
echo.
echo Deleting __pycache__ directories recursively...
for /d /r %%i in (__pycache__) do (
    echo Deleting: %%i
    rd /s /q "%%i" 2>nul
    if errorlevel 1 (
        echo   [FAILED] Could not delete: %%i
    ) else (
        echo   Ok Deleted: %%i
    )
)

echo.
echo =====================================================
echo Cleanup completed!
echo =====================================================
pause

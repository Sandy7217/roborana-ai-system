@echo off
title RoboRana n8n Server
echo ========================================
echo     Starting RoboRana n8n Environment
echo ========================================
echo.

:: Force change to RoboRana folder (this line fixes the issue)
cd /d "C:\Users\Sandeep\Desktop\roborana_ai_system\RoboRana_AI_Data"

:: Confirm current path
echo Current directory: %CD%

:: Activate Python virtual environment
call .venv312\Scripts\activate

:: Start n8n
echo Launching n8n from %CD%...
n8n start

:: Keep window open
pause
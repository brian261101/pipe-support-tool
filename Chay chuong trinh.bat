@echo off
title Pipe Support Analysis Tool
cd /d "%~dp0"
python run.py
if errorlevel 1 (
  echo.
  echo Khong chay duoc. Kiem tra da cai Python 3.10+ chua: python --version
  pause
)

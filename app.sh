#!/bin/bash
# 設置當前工作目錄為腳本所在目錄，確保相對路徑正常工作
cd "$(dirname "$0")" 
# 運行 Python 程式
python app.py
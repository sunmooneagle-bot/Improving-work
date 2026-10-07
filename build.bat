@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
REM ==========================================================================
REM  결과입력 자동 프로그램 - 실행파일(exe) 만들기
REM  - exe 파일 아이콘 / 프로그램 창 좌측 상단 / 작업표시줄(하단) 모두 icon_white.ico
REM  - 이 배치파일과 같은 폴더에 amis_qr_saver.py (또는 run.pyw + qrsaver 폴더) 가 있어야 합니다
REM ==========================================================================

where python > nul 2>&1
if errorlevel 1 (
    echo [오류] Python 을 찾을 수 없습니다. Python 설치 시 "Add Python to PATH" 를 체크해 주세요.
    pause
    exit /b 1
)

set "SRC=amis_qr_saver.py"
if not exist "%SRC%" set "SRC=run.pyw"
if not exist "%SRC%" (
    echo [오류] amis_qr_saver.py 또는 run.pyw 가 이 폴더에 없습니다.
    pause
    exit /b 1
)

REM 아이콘 파일이 없으면 amis_qr_saver.py 안에 들어 있는 아이콘을 꺼내서 만듦
if exist "icon_white.ico" goto icon_ok
if not exist "amis_qr_saver.py" goto icon_ok
python -c "import re,base64;s=open('amis_qr_saver.py',encoding='utf-8').read();m=re.search('ICON_B64 = .([A-Za-z0-9+/=]+)',s);open('icon_white.ico','wb').write(base64.b64decode(m.group(1)))"
:icon_ok
if not exist "icon_white.ico" (
    echo [오류] icon_white.ico 가 없습니다. 아이콘 파일을 이 폴더에 넣어 주세요.
    pause
    exit /b 1
)

echo.
echo [1/3] 필요한 모듈 설치 중...
python -m pip install --upgrade pillow uiautomation pyinstaller
if errorlevel 1 (
    echo [오류] 모듈 설치에 실패했습니다. 인터넷 연결을 확인해 주세요.
    pause
    exit /b 1
)

echo.
echo [2/3] 실행파일 만드는 중... (%SRC%)
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name AMIS_QR_Saver ^
    --icon "icon_white.ico" ^
    --add-data "icon_white.ico;." ^
    --hidden-import tkinter --hidden-import tkinter.ttk --hidden-import tkinter.messagebox ^
    --hidden-import PIL.Image --hidden-import PIL.ImageDraw --hidden-import PIL.ImageTk ^
    --hidden-import ctypes.wintypes --hidden-import queue --hidden-import json ^
    --hidden-import zipfile --hidden-import xml.etree.ElementTree ^
    --hidden-import base64 --hidden-import tempfile --hidden-import contextlib ^
    --collect-all uiautomation --collect-submodules comtypes ^
    "%SRC%"
if errorlevel 1 (
    echo [오류] 실행파일을 만들지 못했습니다. 위 메시지를 확인해 주세요.
    pause
    exit /b 1
)

echo.
echo [3/3] 실행에 필요한 파일 복사 중...
copy /y "icon_white.ico" "dist\" > nul
if exist "검사코드.xlsx" copy /y "검사코드.xlsx" "dist\" > nul
if exist "settings.json" if not exist "dist\settings.json" copy /y "settings.json" "dist\" > nul

echo.
echo ==========================================================================
echo  완료: dist\AMIS_QR_Saver.exe
echo  dist 폴더의 파일(AMIS_QR_Saver.exe, icon_white.ico, 검사코드.xlsx)을
echo  함께 복사해서 사용하세요.
echo  ※ exe 아이콘이 예전 그림으로 보이면 Windows 아이콘 캐시 때문이니
echo    파일을 다른 폴더로 옮기거나 PC 를 다시 시작하면 바뀝니다.
echo ==========================================================================
pause

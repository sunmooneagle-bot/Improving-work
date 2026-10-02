@echo off
chcp 65001 > nul
REM AMIS QR 일괄저장 - 단일 실행파일(exe) 만들기
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --collect-all uiautomation --collect-submodules comtypes --name AMIS_QR_Saver run.pyw
echo.
echo 완료: dist\AMIS_QR_Saver.exe
pause

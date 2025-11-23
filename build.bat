@echo off
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pyinstaller --noconfirm --clean --onefile --windowed --icon=resources\icon.ico main.py
    pause

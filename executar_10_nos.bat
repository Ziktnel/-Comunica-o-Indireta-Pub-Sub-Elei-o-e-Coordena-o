@echo off
cd /d "C:\Users\gbzik\OneDrive\Área de Trabalho\ppd_lab"

echo Iniciando Nó 1...
start cmd /k "call venv\Scripts\activate && python ppd.py"

echo Iniciando Nó 2...
start cmd /k "call venv\Scripts\activate && python ppd.py"

echo Iniciando Nó 3...
start cmd /k "call venv\Scripts\activate && python ppd.py"


echo Todos os nós foram iniciados!
pause

@echo off
mode con: cols=118 lines=38
title LW-DEMO
set /p OTARI_API_KEY=<C:\Users\jesse\Documents\Otari.txt
set LOCAL_BASE_URL=http://127.0.0.1:8080/v1
set LOCAL_MODEL=Llama-3.2-1B-Instruct-Q6_K.gguf
set DEMO_TOOLS=code
cd /d C:\Users\jesse\Documents\PythonDev\local-wilding

echo.
echo   ==========================================================
echo    LOCAL-WILDING  ^|  devs-wilding
echo    a 1B local model with no tools does real research.
echo.
echo    left arm : llamafile (Llama-3.2-1B, CPU) - no tools, weights only
echo    right arm: same loop via hosted Otari - server-side tools,
echo               client-side budget ledger, decision receipts
echo   ==========================================================
echo.
ping -n 9 127.0.0.1 >nul

python demo.py

echo.
echo   ============  BEAT 4: the receipts  ============
echo.
echo  -- evidence/ raw files --
dir /b evidence
echo.
echo  -- receipts.jsonl (every call: why + how much) --
type evidence\receipts.jsonl
echo.
echo  -- self-score (certificates only - unexercised claims score 0) --
python sphere_fitness.py
echo.
echo   ==== done - every claim above is backed by a file in evidence/ ====

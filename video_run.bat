@echo off
mode con: cols=118 lines=38
title LW-DEMO
set /p OTARI_API_KEY=<C:\Users\jesse\Documents\Otari.txt
set LOCAL_BASE_URL=http://127.0.0.1:8080/v1
set LOCAL_MODEL=Llama-3.2-1B-Instruct-Q6_K.gguf
set DEMO_TOOLS=code
set DEMO_VIDEO=1
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
ping -n 12 127.0.0.1 >nul

echo   ==== BEAT 0: what can this key do? GET /api/v1/tools ====
echo.
python probe_tools.py
echo.
ping -n 14 127.0.0.1 >nul

echo   ==== BEATS 1-3: the demo ====
echo.
python demo.py

echo.
echo   ============  BEAT 4: the receipts  ============
echo.
ping -n 4 127.0.0.1 >nul
echo  -- evidence/ raw files --
dir /b evidence
echo.
ping -n 8 127.0.0.1 >nul
echo  -- a raw gateway response: otari_tool_calls, on the wire --
echo.
type evidence\02_step1_openai_gpt-oss-120b.json
echo.
ping -n 14 127.0.0.1 >nul
echo  -- receipts.jsonl (every call: who served, why, how much) --
echo.
type evidence\receipts.jsonl
echo.
ping -n 12 127.0.0.1 >nul
echo  -- the ledger (reserve, settle, refuse) --
echo.
type evidence\spend_ledger.jsonl
echo.
ping -n 12 127.0.0.1 >nul
echo  -- self-score: certificates only - unexercised claims score 0 --
echo.
python sphere_fitness.py
echo.
ping -n 6 127.0.0.1 >nul
echo   ==== done - every claim above is backed by a file in evidence/ ====
echo.
ping -n 10 127.0.0.1 >nul

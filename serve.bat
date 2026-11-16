@echo off
echo Paper Search 로컬 서버 시작 중...
echo 브라우저에서 http://localhost:8080 으로 접속하세요.
echo 종료하려면 이 창을 닫으세요.
echo.
start "" "http://localhost:8080"
python -m http.server 8080
pause

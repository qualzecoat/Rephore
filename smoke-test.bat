@echo off
REM ============================================================
REM  Rephore smoke test (Windows cmd)
REM  Jalankan dari folder repo SETELAH:  docker compose up --build -d
REM  Mengecek: container running, backend /health OK, frontend OK,
REM  worker polling. Menangkap crash startup (mis. import error)
REM  dalam hitungan detik tanpa harus buka halaman satu per satu.
REM ============================================================
setlocal enabledelayedexpansion
set FAIL=0

echo.
echo [1/4] Status container:
docker compose ps
echo.

echo [2/4] Menunggu backend siap (maks 90 detik)...
set READY=0
for /L %%i in (1,1,18) do (
  curl -sf -o nul http://localhost:8000/health 2>nul
  if !errorlevel! equ 0 ( set READY=1 & goto :backend_ok )
  timeout /t 5 /nobreak >nul
)
:backend_ok
if %READY% equ 1 (
  echo     backend OK (http://localhost:8000/health)
) else (
  echo     GAGAL: backend tidak menjawab /health — cek: docker compose logs backend
  set FAIL=1
)

echo [3/4] Mengecek frontend...
curl -sf -o nul http://localhost:3000 2>nul
if %errorlevel% equ 0 (
  echo     frontend OK (http://localhost:3000)
) else (
  echo     GAGAL: frontend tidak menjawab — cek: docker compose logs frontend
  set FAIL=1
)

echo [4/4] Mengecek worker...
docker compose logs worker --tail 3 2>nul | findstr /i "siap" >nul
if %errorlevel% equ 0 (
  echo     worker OK (polling berjalan)
) else (
  echo     PERINGATAN: worker belum terlihat polling — cek: docker compose logs worker
)

echo.
if %FAIL% equ 0 (
  echo SMOKE TEST LULUS — semua layanan jalan.
) else (
  echo SMOKE TEST GAGAL — lihat pesan di atas, lalu: docker compose logs [nama-service]
)
exit /b %FAIL%

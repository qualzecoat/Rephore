#!/bin/bash
# ============================================================
#  Rephore smoke test (Linux / VPS Sirius)
#  Jalankan dari /opt/sirius/projects/rephore SETELAH rebuild:
#    DOMAIN=rephore.aditiamh.my.id docker compose -f docker-compose.yml \
#      -f docker-compose.prod.yml \
#      -f /opt/sirius/compose/rephore/docker-compose.sirius.yml \
#      up -d --build postgres redis backend worker frontend
#
#  Mengecek: container running, backend /health OK (via exec,
#  karena port tidak dipublish ke host), worker polling, dan
#  situs HTTPS menjawab 200.
# ============================================================
set -u
FAIL=0
DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml -f /opt/sirius/compose/rephore/docker-compose.sirius.yml"

echo
echo "[1/4] Status container:"
$DC ps
echo

echo "[2/4] Menunggu backend siap (maks 90 detik)..."
READY=0
for i in $(seq 1 18); do
  if $DC exec -T backend curl -sf -o /dev/null http://localhost:8000/health 2>/dev/null; then
    READY=1
    break
  fi
  sleep 5
done
if [ "$READY" = "1" ]; then
  echo "    backend OK (/health)"
else
  echo "    GAGAL: backend tidak menjawab /health — cek: $DC logs backend"
  FAIL=1
fi

echo "[3/4] Mengecek worker..."
if $DC logs worker --tail 3 2>/dev/null | grep -qi "siap"; then
  echo "    worker OK (polling berjalan)"
else
  echo "    PERINGATAN: worker belum terlihat polling — cek: $DC logs worker"
fi

echo "[4/4] Mengecek situs HTTPS..."
CODE=$(curl -sk -o /dev/null -w "%{http_code}" https://rephore.aditiamh.my.id/ 2>/dev/null)
if [ "$CODE" = "200" ]; then
  echo "    situs OK (https://rephore.aditiamh.my.id -> 200)"
else
  echo "    GAGAL: situs menjawab $CODE — cek Caddy + $DC logs frontend"
  FAIL=1
fi

echo
if [ "$FAIL" = "0" ]; then
  echo "SMOKE TEST LULUS — semua layanan jalan."
else
  echo "SMOKE TEST GAGAL — lihat pesan di atas."
fi
exit $FAIL

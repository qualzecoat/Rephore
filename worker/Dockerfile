# Build context = root repo (lihat docker-compose.yml),
# supaya worker bisa memakai kode backend/app yang sama.
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY worker/main.py ./main.py
CMD ["python", "main.py"]

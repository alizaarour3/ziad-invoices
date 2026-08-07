FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=10000 \
    ZIAD_DATA_DIR=/tmp/ziad-data

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libreoffice-writer \
       fontconfig \
       fonts-dejavu-core \
       fonts-noto-core \
       fonts-noto-extra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .
RUN mkdir -p /tmp/ziad-data/attachments /tmp/ziad-data/generated /tmp/ziad-data/backups

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]

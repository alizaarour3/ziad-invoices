FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=10000 \
    ZIAD_DATA_DIR=/tmp/ziad-data

# Runtime document tools, Arabic fonts, and the native text-shaping stack used
# by Pillow/RAQM for correct Arabic joining and RTL/BiDi order. Build packages
# are included so Pillow is compiled against the same RAQM libraries available
# at runtime instead of relying on an unknown prebuilt wheel configuration.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libreoffice-writer \
       fontconfig \
       fonts-dejavu-core \
       fonts-noto-core \
       fonts-noto-extra \
       build-essential \
       pkg-config \
       libfreetype6-dev \
       libjpeg62-turbo-dev \
       zlib1g-dev \
       libharfbuzz-dev \
       libfribidi-dev \
       libraqm-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./

# Force Pillow to build from source so RAQM/Harfbuzz/FriBiDi support is
# deterministic on Render. Then verify the shaping engine before the image is
# allowed to deploy.
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-binary=Pillow Pillow==12.2.0 \
    && pip install -r requirements.txt \
    && python -c "from PIL import features; print('RAQM:', features.check('raqm'), 'Harfbuzz:', features.check('harfbuzz'), 'FriBiDi:', features.check('fribidi')); assert features.check('raqm') and features.check('harfbuzz') and features.check('fribidi'), 'Arabic shaping engine is not available'"

COPY . .
RUN mkdir -p /tmp/ziad-data/attachments /tmp/ziad-data/generated /tmp/ziad-data/backups

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]

# ndlocr/Dockerfile
# NDLOCR-Lite を git clone してFastAPIラッパーをかぶせる
#
# ビルド時に ndlocr-lite をクローンしてモデルファイルをイメージに焼き込む。
# → サーバ起動後にダウンロード不要・再現性が高い

FROM python:3.11-slim

WORKDIR /app

# システム依存（lxml, Pillow, pdf2image用）
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl libgomp1 libgl1 libglib2.0-0 poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# NDLOCR-Lite をクローン（モデルファイルごと）
# ※ .onnx モデルは src/model/ に同梱されているので追加DL不要
RUN git clone https://github.com/ndl-lab/ndlocr-lite.git /ndlocr-lite \
    && pip install --no-cache-dir -r /ndlocr-lite/requirements.txt

# REST APIラッパーの依存
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# ラッパーサーバのコード
COPY server.py .

# NDLOCR-Lite の src を Python パスに追加するため環境変数で指定
ENV PYTHONPATH=/ndlocr-lite/src
ENV OCR_SRC=/ndlocr-lite/src

EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]

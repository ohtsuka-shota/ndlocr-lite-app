# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# 依存インストール（コードより先にキャッシュ効かせる）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# コードコピー（開発時はvolumeマウントで上書きされる）
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# ndlocr-lite-app

NDLOCR-Lite（国立国会図書館製 OCR）と Claude API を組み合わせた OCR → AI校正 → JSON構造化パイプラインです。

## ドキュメント

- [環境図・通信フロー（Phase 1）](docs/環境図・通信フロー-phase01.md)

## 機能

- 画像・PDF をアップロードして OCR テキストを抽出
- OCR テキストを Claude API で校正・JSON構造化
- React UI またはREST API から利用可能

## システム構成

```
[ブラウザ / REST クライアント]
        ↓
[frontend]  React + Vite  :5173（開発）/ :80（本番）
        ↓ /api/* プロキシ
[backend]   FastAPI        :8000  ← Claude API で校正・構造化
        ↓
[ndlocr]    FastAPI        :8080  ← NDLOCR-Lite OCR エンジン
```

## 対応ファイル形式

`.pdf` `.jpg` `.jpeg` `.png` `.tiff` `.tif` `.bmp` `.jp2`

## 必要環境

| ツール | バージョン |
|--------|-----------|
| Docker Engine | 最新 |
| Git | 最新 |

GPU 不要・CPU のみで動作します。

## セットアップ

```bash
git clone https://github.com/ohtsuka-shota/ndlocr-lite-app.git
cd ndlocr-lite-app

cp .env.example .env
# .env を開いて ANTHROPIC_KEY を記入
```

## 起動（フェーズ別）

### Phase 1 — NDLOCR-Lite 単体確認

```bash
docker compose -f docker-compose.phase01.yml build
docker compose -f docker-compose.phase01.yml up -d
```

| エンドポイント | URL |
|--------------|-----|
| ヘルスチェック | http://localhost:8080/health |
| Swagger UI | http://localhost:8080/docs |

```bash
# OCR テスト
curl -X POST http://localhost:8080/ocr -F "file=@サンプル.pdf"
```

### Phase 2 — バックエンド API 確認

```bash
docker compose -f docker-compose.phase02.yml up -d
```

| エンドポイント | URL |
|--------------|-----|
| ヘルスチェック | http://localhost:8000/health |
| Swagger UI | http://localhost:8000/docs |

### Phase 3 — フルスタック（開発）

```bash
docker compose -f docker-compose.phase03.yml up -d
```

| サービス | URL |
|---------|-----|
| フロントエンド | http://localhost:5173 |
| バックエンド Swagger | http://localhost:8000/docs |

## 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `ANTHROPIC_KEY` | Anthropic API キー（必須） | — |
| `LLM_MODEL` | 使用モデル | `claude-haiku-4-5-20251001` |
| `NDLOCR_URL` | ndlocr の URL | `http://ndlocr:8080` |

## ディレクトリ構成

```
ndlocr-lite-app/
├── ndlocr/               # NDLOCR-Lite FastAPI ラッパー
│   ├── Dockerfile
│   ├── server.py
│   └── requirements-server.txt
├── backend/              # LLM補正・中継 API
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── frontend/             # React UI
│   ├── Dockerfile.dev
│   ├── Dockerfile.prod
│   ├── nginx.conf
│   ├── vite.config.js
│   └── src/
│       └── App.jsx
├── docker-compose.phase01.yml
├── docker-compose.phase02.yml
├── docker-compose.phase03.yml
├── docker-compose.yml    # Phase 3 と同等（開発用）
└── .env.example
```

## 停止

```bash
docker compose -f docker-compose.phase01.yml down
```

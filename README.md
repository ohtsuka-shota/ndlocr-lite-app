# ndlocr-lite-app

NDLOCR-Lite（国立国会図書館製 OCR）を使って画像・PDF からテキストを抽出し、
AWS Bedrock の LLM で補正・JSON 構造化する Web アプリです。

## 現在の実装状況

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | ndlocr 単体 OCR API | ✅ 完了 |
| Phase 2 | React UI + ndlocr 連携（2層） | ✅ 完了 |
| Phase 3 | backend + AWS Bedrock LLM 補正（3層） | ✅ 完了・動作確認中 |

## 機能

| 機能 | WebUI | REST API |
|------|-------|----------|
| 画像・PDF アップロード | ✅ | ✅ |
| OCR テキスト抽出 | ✅ | ✅ |
| AI 補正・JSON 構造化 | ✅ | ✅ |
| 結果のクリップボードコピー | ✅ | — |

### 対応文書種別（AI 補正）

名刺 / 請求書 / 見積書 / 納品書 / 領収書 / 契約書 / 帳票 / その他

## システム構成（Phase 3）

```
[ブラウザ / REST クライアント]
    ↓ HTTP :5173
[frontend]  React + nginx  :80  ← nginx.phase03.conf
    ├─ POST /api/ocr      → ndlocr:8080   （OCR・LLM なし）
    └─ POST /api/correct  → backend:8000  （LLM 補正）
                                ↓
[backend]   FastAPI + boto3 :8000
                                ↓ HTTPS
                        AWS Bedrock (us-east-1)

[ndlocr]    FastAPI + NDLOCR-Lite :8080
```

## 必要環境

| ツール | バージョン |
|--------|-----------|
| Docker Engine | 最新 |
| Git | 最新 |
| AWS アカウント | Bedrock 有効化済み |

GPU 不要・CPU のみで動作します。

## セットアップ

```bash
git clone https://github.com/ohtsuka-shota/ndlocr-lite-app.git
cd ndlocr-lite-app

# 環境変数ファイルを作成
cp .env.example .env
```

`.env` を編集して AWS 認証情報を設定します。

```env
LLM_PROVIDER=bedrock
LLM_MODEL=amazon.nova-lite-v1:0
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1
```

> IAM ユーザーに `bedrock:InvokeModel` 権限が必要です。

## 起動

### Phase 3 — フル機能（推奨）

```bash
docker compose -f docker-compose.phase03.yml up --build -d
```

| サービス | URL |
|---------|-----|
| フロントエンド | http://localhost:5173 |
| backend ヘルスチェック | http://localhost:8000/health |
| ndlocr ヘルスチェック | http://localhost:8080/health |

### Phase 2 — OCR のみ（LLM 補正なし）

```bash
docker compose -f docker-compose.phase02.yml up --build -d
```

### Phase 1 — ndlocr 単体確認

```bash
docker compose -f docker-compose.phase01.yml up --build -d
```

## REST API リファレンス

### OCR 実行

```bash
# ndlocr 直接（Phase 1 / 2 / 3 共通）
curl -X POST http://localhost:8080/ocr -F "file=@サンプル.pdf"

# nginx 経由（Phase 3）
curl -X POST http://localhost:5173/api/ocr -F "file=@サンプル.pdf"
```

レスポンス:
```json
{"text": "...", "layout_hint": "名刺", "regions": [...]}
```

### AI 補正・JSON 構造化

```bash
# backend 直接
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "山囲 太郎\n株式会社サンプル\n開発部", "hint": "名刺"}'

# nginx 経由
curl -X POST http://localhost:5173/api/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "山囲 太郎\n株式会社サンプル\n開発部", "hint": "名刺"}'
```

レスポンス:
```json
{
  "corrected": "山田 太郎\n株式会社サンプル\n開発部",
  "structured": {
    "name": "山田 太郎",
    "company": "株式会社サンプル",
    "department": "開発部",
    ...
  }
}
```

### ヘルスチェック

```bash
curl http://localhost:8000/health
# → {"status":"ok","provider":"bedrock","model":"amazon.nova-lite-v1:0"}

curl http://localhost:8080/health
# → {"status":"ok","engine":"loaded","mode":"subprocess"}
```

## LLM プロバイダの切り替え

`.env` の `LLM_MODEL` を変更してコンテナを再起動するだけで切り替え可能です。

| プロバイダ | LLM_MODEL |
|---|---|
| Amazon Nova Lite（デフォルト） | `amazon.nova-lite-v1:0` |
| Anthropic Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |

## ディレクトリ構成

```
ndlocr-lite-app/
├── .env.example
├── docker-compose.phase01.yml
├── docker-compose.phase02.yml
├── docker-compose.phase03.yml
├── ndlocr/                        # NDLOCR-Lite FastAPI ラッパー
│   ├── Dockerfile
│   ├── server.py
│   └── requirements-server.txt
├── backend/                       # LLM 補正 API（Phase 3）
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
└── frontend/                      # React UI
    ├── Dockerfile
    ├── nginx.conf                 # Phase 2 用
    ├── nginx.phase03.conf         # Phase 3 用
    ├── vite.config.js
    ├── package.json
    ├── index.html
    └── src/
        ├── main.jsx
        └── App.jsx
```

## ドキュメント

- [環境図・通信フロー（Phase 1）](docs/環境図・通信フロー-phase01.md)
- [環境図・通信フロー（Phase 2）](docs/環境図・通信フロー-phase02.md)
- [環境図・通信フロー（Phase 3）](docs/環境図・通信フロー-phase03.md)

## 停止

```bash
docker compose -f docker-compose.phase03.yml down
```

# ndlocr-lite-app

NDLOCR-Lite（国立国会図書館製 OCR）を使って画像・PDF からテキストを抽出する Web アプリです。

## 現在の実装状況

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | ndlocr 単体 OCR API | ✅ 完了 |
| Phase 2 | React UI + ndlocr 連携 | ✅ 完了 |

## ドキュメント

- [環境図・通信フロー（Phase 1）](docs/環境図・通信フロー-phase01.md)
- [環境図・通信フロー（Phase 2）](docs/環境図・通信フロー-phase02.md)

## 機能（Phase 2 時点）

- 画像・PDF をドラッグ＆ドロップまたはクリック選択でアップロード
- PDF はブラウザ内プレビュー表示
- OCR 実行でテキスト抽出
- 結果をワンクリックでクリップボードにコピー

## システム構成

### Phase 2（現在）

```
[ブラウザ]
    ↓ HTTP :5173
[frontend]  React + nginx  :80
    ↓ /api/* プロキシ
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

### Phase 2 — フロントエンド + ndlocr 確認

```bash
docker compose -f docker-compose.phase02.yml build
docker compose -f docker-compose.phase02.yml up -d
```

| サービス | URL |
|---------|-----|
| フロントエンド | http://localhost:5173 |
| ヘルスチェック | http://localhost:8080/health |
| Swagger UI | http://localhost:8080/docs |

## ディレクトリ構成

```
ndlocr-lite-app/
├── ndlocr/                    # NDLOCR-Lite FastAPI ラッパー
│   ├── Dockerfile
│   ├── server.py
│   └── requirements-server.txt
├── frontend/                  # React UI
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── vite.config.js
│   ├── package.json
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       └── App.jsx
├── docker-compose.phase01.yml
├── docker-compose.phase02.yml
└── .env.example
```

## 停止

```bash
docker compose -f docker-compose.phase02.yml down
```

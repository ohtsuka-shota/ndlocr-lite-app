# 環境図・通信フロー — Phase 2

Phase 2 は frontend（nginx）と ndlocr の 2 コンテナを起動し、
ブラウザから直接 OCR を呼び出せることを確認するフェーズ。

---

## 環境図

```mermaid
graph TB
    Browser["ブラウザ\nhttp://localhost:5173"]
    RestClient["REST クライアント\n(curl / Postman 等)\nhttp://localhost:8080"]

    subgraph Docker["Docker ネットワーク (ndlocr-lite-app)"]
        Frontend["frontend コンテナ\nnginx :80\n（React ビルド済み）"]
        Ndlocr["ndlocr コンテナ\nFastAPI + NDLOCR-Lite\n:8080（外部公開）"]
    end

    Browser -- "HTTP :5173" --> Frontend
    Frontend -- "/api/* → ndlocr:8080" --> Ndlocr
    RestClient -- "HTTP :8080" --> Ndlocr
```

---

## ポート対応表

| コンテナ     | 内部ポート | 外部公開     | アクセス元           |
| -------- | ----- | -------- | --------------- |
| frontend | 80    | **5173** | ブラウザ            |
| ndlocr   | 8080  | 8080     | Powershell等のCLI |

---

## 通信フロー① ページ読み込み

```mermaid
sequenceDiagram
    actor User as ブラウザ
    participant FE as frontend（nginx）:80

    User ->> FE: GET http://localhost:5173
    FE -->> User: HTML / React バンドル（ビルド済み静的ファイル）
    Note over User: React アプリが描画される
```

---

## 通信フロー② ファイル選択・プレビュー

```mermaid
sequenceDiagram
    actor User as ブラウザ
    participant FE as React App（ローカル）

    User ->> FE: 画像をドラッグ＆ドロップ（またはクリック選択）
    Note over FE: URL.createObjectURL() でプレビュー生成
    FE -->> User: 画像プレビュー表示
```

> API は呼ばれない。ブラウザ内で完結する。

---

## 通信フロー③ OCR 実行

```mermaid
sequenceDiagram
    actor User as ブラウザ
    participant FE as React App
    participant NX as nginx（frontend コンテナ）
    participant OCR as ndlocr :8080

    User ->> FE: 「OCR 実行」ボタンをクリック
    FE ->> NX: POST /api/ocr（画像ファイル）
    NX ->> OCR: POST http://ndlocr:8080/ocr
    Note over OCR: NDLOCR-Lite で OCR 処理
    OCR -->> NX: {"text":"...","layout_hint":"...","regions":[...]}
    NX -->> FE: OCR レスポンス
    FE -->> User: OCR テキスト表示
```

---

## 通信フロー④ CLI から ndlocr を直接キック

```mermaid
sequenceDiagram
    actor Dev as 開発者（curl / Postman）
    participant OCR as ndlocr :8080

    Dev ->> OCR: POST http://localhost:8080/ocr<br/>-F "file=@test.pdf"
    Note over OCR: NDLOCR-Lite で OCR 処理
    OCR -->> Dev: {"text":"...","layout_hint":"...","regions":[...]}
```

```bash
# ヘルスチェック
curl http://localhost:8080/health

# OCR 実行
curl -X POST http://localhost:8080/ocr -F "file=@サンプル.jpg"
```

---

## 起動コマンド

```bash
cd /mnt/c/Users/ohtsu/Documents/アプリ/ndlocr-lite-app
docker compose -f docker-compose.phase02.yml up --build
```

ブラウザで `http://localhost:5173` を開く。

"""
ndlocr/server.py
NDLOCR-Lite を REST API として公開するラッパー

NDLOCR-Lite の ocr.py は CLI前提の設計なので、
内部の OCR エンジン（DEIMv2 + PARSeq）を直接呼ぶ形でラップする。
"""

import os
import sys
import io
import json
import tempfile
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# NDLOCR-Lite の src を import
OCR_SRC = os.environ.get("OCR_SRC", "/ndlocr-lite/src")
sys.path.insert(0, OCR_SRC)

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "info").upper())
logger = logging.getLogger(__name__)

app = FastAPI(title="NDLOCR-Lite API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── モデルを起動時に一度だけロード ──────────────────────────────
# NDLOCR-Lite の内部モジュールを使う
# （ocr.py の main() ではなく、エンジンだけ取り出す）
_ocr_engine = None

def get_engine():
    global _ocr_engine
    if _ocr_engine is None:
        logger.info("Loading NDLOCR-Lite models...")
        try:
            from ocr import OcrEngine  # NDLOCR-Lite v1.x の内部クラス
            _ocr_engine = OcrEngine()
            logger.info("Models loaded.")
        except ImportError:
            # OcrEngine が直接 export されていないバージョン用フォールバック
            # → subprocess で ocr.py を叩く方式に切り替え
            logger.warning("OcrEngine not found, falling back to subprocess mode")
            _ocr_engine = "subprocess"
    return _ocr_engine


# ── エンドポイント ──────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """起動時にモデルをウォームアップ"""
    get_engine()


@app.get("/health")
def health():
    engine = get_engine()
    return {
        "status": "ok",
        "engine": "loaded" if engine else "not_loaded",
        "mode": "subprocess" if engine == "subprocess" else "direct",
    }


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    """
    画像または PDF を受け取り、OCR結果を返す。

    Response:
      {
        "text": "抽出テキスト全体",
        "layout_hint": "検出されたレイアウト種別（カンマ区切り）",
        "regions": [   // 領域ごとの詳細（任意）
          {
            "text": "...",
            "type": "本文" | "見出し" | "図表" | ...,
            "order": 0
          }
        ]
      }
    """
    content = await file.read()
    suffix  = Path(file.filename or "upload").suffix.lower()

    if suffix not in {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".jp2", ".pdf"}:
        raise HTTPException(400, f"未対応のファイル形式: {suffix}")

    engine = get_engine()

    # ─ PDF は先にページ画像へ変換してから処理 ─
    if suffix == ".pdf":
        return await _run_pdf(engine, content)

    # ─ Direct モード（OcrEngineを直接使う） ─
    if engine != "subprocess":
        return await _run_direct(engine, content, suffix)

    # ─ Subprocess モード（ocr.py を外部プロセスで叩く） ─
    return await _run_subprocess(content, suffix)


# ── PDF モード ──────────────────────────────────────────────────

async def _run_pdf(engine, content: bytes) -> dict:
    """PDF をページ画像に展開して各ページを OCR し結合する"""
    try:
        from pdf2image import convert_from_bytes
        pages = convert_from_bytes(content)
    except Exception as e:
        raise HTTPException(400, f"PDF 変換エラー: {e}")

    all_regions = []
    for img in pages:
        if engine != "subprocess":
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, engine.run, img)
            page = _format_result(result)
        else:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            page = await _run_subprocess(buf.getvalue(), ".png")
        all_regions.extend(page.get("regions", []))

    full_text = "\n".join(r["text"] for r in all_regions if r.get("text"))
    return {"text": full_text, "layout_hint": _guess_layout_hint(all_regions), "regions": all_regions}


# ── Direct モード ───────────────────────────────────────────────

async def _run_direct(engine, content: bytes, suffix: str) -> dict:
    import asyncio
    from PIL import Image

    try:
        img = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as e:
        raise HTTPException(400, f"画像読み込みエラー: {e}")

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, engine.run, img)
    return _format_result(result)


# ── Subprocess モード ────────────────────────────────────────────

async def _run_subprocess(content: bytes, suffix: str) -> dict:
    import asyncio
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        in_path  = Path(tmpdir) / f"input{suffix}"
        out_dir  = Path(tmpdir) / "output"
        out_dir.mkdir()
        in_path.write_bytes(content)

        cmd = [
            sys.executable,
            str(Path(OCR_SRC) / "ocr.py"),
            "--sourceimg", str(in_path),
            "--output",    str(out_dir),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode != 0:
            logger.error("ocr.py stderr: %s", stderr.decode())
            raise HTTPException(500, f"OCR処理エラー: {stderr.decode()[:200]}")

        return _parse_output_dir(out_dir, in_path.stem)


def _parse_output_dir(out_dir: Path, stem: str) -> dict:
    """ocr.py が出力したファイル群を読んでレスポンスを組み立てる"""

    # JSON出力を優先して読む
    json_files = list(out_dir.glob(f"{stem}*.json"))
    txt_files  = list(out_dir.glob(f"{stem}*.txt"))

    regions     = []
    layout_hint = ""

    if json_files:
        try:
            data = json.loads(json_files[0].read_text(encoding="utf-8"))
            contents = data.get("contents") or data.get("regions") or []
            # NDLOCR-Lite の contents は [[{...}, ...], [...]] のネスト構造
            if contents and isinstance(contents[0], list):
                contents = [item for sublist in contents for item in sublist]
            for i, item in enumerate(contents):
                text = item.get("text") or item.get("content") or ""
                rtype = item.get("type") or item.get("category") or "本文"
                regions.append({"text": text, "type": rtype, "order": i})
            layout_hint = _guess_layout_hint(regions)
        except Exception as e:
            logger.warning("JSON parse error: %s", e)

    # JSON がなければ TXT フォールバック
    full_text = "\n".join(r["text"] for r in regions)
    if not full_text and txt_files:
        full_text = txt_files[0].read_text(encoding="utf-8")

    return {
        "text":        full_text,
        "layout_hint": layout_hint,
        "regions":     regions,
    }


def _format_result(result) -> dict:
    """Direct モード用：エンジンの戻り値を整形"""
    # OcrEngine.run() の戻り値形式に合わせて調整が必要
    # ここでは汎用的なフォールバック
    if isinstance(result, str):
        return {"text": result, "layout_hint": "", "regions": []}
    if isinstance(result, dict):
        return {
            "text":        result.get("text", ""),
            "layout_hint": _guess_layout_hint(result.get("regions", [])),
            "regions":     result.get("regions", []),
        }
    return {"text": str(result), "layout_hint": "", "regions": []}


def _guess_layout_hint(regions: list) -> str:
    """領域タイプからレイアウトヒント文字列を生成"""
    types = [r.get("type", "") for r in regions if r.get("type")]
    seen  = list(dict.fromkeys(types))  # 重複除去・順序保持
    return ", ".join(seen)

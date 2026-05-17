import os
import json
import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="NDL OCR Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "bedrock")
LLM_MODEL    = os.getenv("LLM_MODEL", "amazon.nova-lite-v1:0")
AWS_REGION   = os.getenv("AWS_REGION", "us-east-1")

# boto3 converse API はAnthropicモデル・Amazonモデル両方対応
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


class CorrectRequest(BaseModel):
    text: str
    hint: str = ""


@app.get("/health")
def health():
    return {"status": "ok", "provider": LLM_PROVIDER, "model": LLM_MODEL}


@app.post("/correct")
async def correct(req: CorrectRequest):
    prompt = _build_prompt(req.text, req.hint)
    try:
        response = bedrock.converse(
            modelId=LLM_MODEL,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 8000, "temperature": 0},
        )
        raw = response["output"]["message"]["content"][0]["text"].strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM 呼び出しエラー: {e}")

    print(f"[DEBUG] LLM raw response:\n{raw}\n---", flush=True)

    # ```json ... ``` ブロックで返ってきた場合を吸収
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        print(f"[DEBUG] JSON parse error: {e}", flush=True)
        raise HTTPException(status_code=502, detail=f"LLM が JSON を返しませんでした: {e}")


def _build_prompt(text: str, hint: str) -> str:
    example = _examples_by_hint(hint)
    return f"""<instruction>
OCRテキストの誤字・脱字を校正し、下記のJSON形式のみを返してください。
説明文・前置き・コードブロックは不要です。JSONのみを出力してください。
</instruction>

<document_type>{hint or "不明"}</document_type>

<ocr_text>
{text}
</ocr_text>

<output_example>
{example}
</output_example>"""


def _examples_by_hint(hint: str) -> str:
    if "名刺" in hint:
        return """{
  "corrected": "山田 太郎\\n株式会社サンプル\\n営業部 部長\\n〒100-0001 東京都千代田区丸の内1-1-1\\nTEL: 03-1234-5678 / FAX: 03-1234-5679\\nMobile: 090-1234-5678\\nyamada@example.com\\nhttps://www.example.com",
  "structured": {
    "name": "山田 太郎",
    "company": "株式会社サンプル",
    "department": "営業部",
    "title": "部長",
    "postal_code": "100-0001",
    "address": "東京都千代田区丸の内1-1-1",
    "tel": "03-1234-5678",
    "fax": "03-1234-5679",
    "mobile": "090-1234-5678",
    "email": "yamada@example.com",
    "website": "https://www.example.com"
  }
}"""
    if "請求書" in hint:
        return """{
  "corrected": "請求書\\n請求書番号: INV-2026-001\\n発行日: 2026年5月17日\\n支払期限: 2026年6月17日\\n\\n株式会社サンプル 御中\\n\\n品目: システム開発業務\\n数量: 1\\n単価: 500,000円\\n小計: 500,000円\\n消費税(10%): 50,000円\\n合計: 550,000円",
  "structured": {
    "document_type": "請求書",
    "invoice_number": "INV-2026-001",
    "date": "2026-05-17",
    "due_date": "2026-06-17",
    "issuer": "株式会社テスト",
    "recipient": "株式会社サンプル",
    "items": [
      {"name": "システム開発業務", "quantity": 1, "unit_price": 500000, "amount": 500000}
    ],
    "subtotal": 500000,
    "tax_rate": 10,
    "tax_amount": 50000,
    "total_amount": 550000,
    "currency": "JPY",
    "bank_name": null,
    "bank_account": null,
    "notes": null
  }
}"""
    if "見積書" in hint:
        return """{
  "corrected": "見積書\\n見積番号: QUO-2026-001\\n発行日: 2026年5月17日\\n有効期限: 2026年6月17日\\n\\n株式会社サンプル 御中\\n\\n品目: システム開発業務\\n数量: 1\\n単価: 500,000円\\n小計: 500,000円\\n消費税(10%): 50,000円\\n合計: 550,000円",
  "structured": {
    "document_type": "見積書",
    "quote_number": "QUO-2026-001",
    "date": "2026-05-17",
    "valid_until": "2026-06-17",
    "issuer": "株式会社テスト",
    "recipient": "株式会社サンプル",
    "items": [
      {"name": "システム開発業務", "quantity": 1, "unit_price": 500000, "amount": 500000}
    ],
    "subtotal": 500000,
    "tax_rate": 10,
    "tax_amount": 50000,
    "total_amount": 550000,
    "currency": "JPY",
    "notes": null
  }
}"""
    if "納品書" in hint:
        return """{
  "corrected": "納品書\\n納品番号: DEL-2026-001\\n納品日: 2026年5月17日\\n\\n株式会社サンプル 御中\\n\\n品目: コピー用紙 A4\\n数量: 10箱\\n単価: 3,000円\\n金額: 30,000円",
  "structured": {
    "document_type": "納品書",
    "delivery_number": "DEL-2026-001",
    "date": "2026-05-17",
    "issuer": "株式会社テスト",
    "recipient": "株式会社サンプル",
    "items": [
      {"name": "コピー用紙 A4", "quantity": 10, "unit": "箱", "unit_price": 3000, "amount": 30000}
    ],
    "total_amount": 30000,
    "currency": "JPY",
    "notes": null
  }
}"""
    if "領収書" in hint:
        return """{
  "corrected": "領収書\\n領収書番号: REC-2026-001\\n発行日: 2026年5月17日\\n\\n株式会社サンプル 様\\n\\n金額: ¥550,000-\\nうち消費税(10%): ¥50,000\\n但し: システム開発業務代として\\n上記正に領収いたしました",
  "structured": {
    "document_type": "領収書",
    "receipt_number": "REC-2026-001",
    "date": "2026-05-17",
    "issuer": "株式会社テスト",
    "recipient": "株式会社サンプル",
    "amount": 550000,
    "tax_rate": 10,
    "tax_amount": 50000,
    "purpose": "システム開発業務代として",
    "payment_method": null,
    "currency": "JPY"
  }
}"""
    if "契約書" in hint:
        return """{
  "corrected": "業務委託契約書\\n\\n委託者（甲）: 株式会社サンプル\\n代表取締役: 山田 太郎\\n所在地: 東京都千代田区丸の内1-1-1\\n\\n受託者（乙）: 株式会社テスト\\n代表取締役: 田中 花子\\n所在地: 大阪府大阪市北区梅田2-2-2\\n\\n委託期間: 2026年4月1日〜2027年3月31日\\n委託料: 月額100,000円（税別）",
  "structured": {
    "document_type": "契約書",
    "title": "業務委託契約書",
    "contract_number": null,
    "date": null,
    "effective_date": "2026-04-01",
    "expiry_date": "2027-03-31",
    "party_a": {
      "role": "委託者（甲）",
      "company": "株式会社サンプル",
      "representative": "山田 太郎",
      "address": "東京都千代田区丸の内1-1-1"
    },
    "party_b": {
      "role": "受託者（乙）",
      "company": "株式会社テスト",
      "representative": "田中 花子",
      "address": "大阪府大阪市北区梅田2-2-2"
    },
    "amount": 100000,
    "payment_terms": "月額（税別）",
    "currency": "JPY",
    "governing_law": null,
    "notes": null
  }
}"""
    if "帳票" in hint:
        return """{
  "corrected": "納品書\\n2026年5月17日\\n品名: コピー用紙 A4\\n数量: 10箱",
  "structured": {
    "document_type": "帳票",
    "title": "納品書",
    "date": "2026-05-17",
    "document_number": null,
    "issuer": null,
    "recipient": null,
    "items": [
      {"name": "コピー用紙 A4", "quantity": 10, "unit": "箱"}
    ],
    "total_amount": null,
    "notes": null
  }
}"""
    return """{
  "corrected": "補正後の全文",
  "structured": {
    "summary": "文書の概要を一文で記載"
  }
}"""

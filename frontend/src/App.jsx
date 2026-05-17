import { useState, useRef, useCallback, useEffect } from "react";

const HINT_OPTIONS = ["名刺", "請求書", "見積書", "納品書", "領収書", "契約書", "帳票", "その他"];

export default function App() {
  const [file, setFile] = useState(null);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [preview, setPreview] = useState(null);
  const [running, setRunning] = useState(false);
  const [correcting, setCorrecting] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);
  const [correctResult, setCorrectResult] = useState(null);
  const [hint, setHint] = useState("名刺");
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState(null);
  const [copied, setCopied] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((data) => { if (data.provider) setAiEnabled(true); })
      .catch(() => {});
  }, []);

  const selectFile = (f) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setOcrResult(null);
    setCorrectResult(null);
    setError(null);
    setActiveTab(null);
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) selectFile(f);
  }, []);

  const onDragOver = (e) => e.preventDefault();

  const runOcr = async () => {
    if (!file) return;
    setError(null);
    setOcrResult(null);
    setCorrectResult(null);
    setRunning(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/ocr", { method: "POST", body: formData });
      if (!res.ok) throw new Error(`OCR エラー: ${res.status}`);
      const { text, layout_hint } = await res.json();
      setOcrResult({ text, layout_hint });
      setActiveTab("ocr");
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const runCorrect = async () => {
    if (!ocrResult?.text) return;
    setError(null);
    setCorrecting(true);
    try {
      const res = await fetch("/api/correct", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: ocrResult.text, hint }),
      });
      if (!res.ok) throw new Error(`補正エラー: ${res.status}`);
      setCorrectResult(await res.json());
      setActiveTab("corrected");
    } catch (e) {
      setError(e.message);
    } finally {
      setCorrecting(false);
    }
  };

  const copyText = async (text) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const tabs = [
    ocrResult && { key: "ocr", label: "OCR 結果" },
    correctResult && { key: "corrected", label: "補正結果" },
    correctResult?.structured && { key: "structured", label: "構造化 JSON" },
  ].filter(Boolean);

  return (
    <div style={s.container}>
      <h1 style={s.title}>NDLOCR-Lite OCR</h1>

      {/* ファイル選択エリア */}
      <div
        style={s.dropzone}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onClick={() => inputRef.current.click()}
      >
        {preview ? (
          file?.type === "application/pdf" ? (
            <embed src={preview} type="application/pdf" style={s.pdfPreview} />
          ) : (
            <img src={preview} alt="preview" style={s.preview} />
          )
        ) : (
          <span style={s.dropText}>
            画像をドラッグ＆ドロップ
            <br />
            またはクリックして選択
          </span>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/*,application/pdf"
          style={{ display: "none" }}
          onChange={(e) => selectFile(e.target.files[0])}
        />
      </div>
      {file && <p style={s.fileName}>{file.name}</p>}

      {/* ボタン行 */}
      <div style={s.buttonRow}>
        <button
          style={{ ...s.button, opacity: !file || running ? 0.5 : 1 }}
          onClick={runOcr}
          disabled={!file || running}
        >
          {running ? "⏳ OCR 実行中…" : "① OCR 実行"}
        </button>

        {ocrResult && aiEnabled && (
          <>
            <select
              style={s.select}
              value={hint}
              onChange={(e) => setHint(e.target.value)}
            >
              {HINT_OPTIONS.map((h) => <option key={h} value={h}>{h}</option>)}
            </select>
            <button
              style={{ ...s.correctButton, opacity: correcting ? 0.5 : 1 }}
              onClick={runCorrect}
              disabled={correcting}
            >
              {correcting ? "⏳ 補正中…" : "② AI 補正を実行"}
            </button>
          </>
        )}
      </div>

      {error && <div style={s.error}>{error}</div>}

      {/* タブ */}
      {tabs.length > 0 && (
        <div style={s.tabArea}>
          <div style={s.tabBar}>
            {tabs.map((tab) => (
              <button
                key={tab.key}
                style={{
                  ...s.tab,
                  ...(activeTab === tab.key ? s.tabActive : {}),
                }}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div style={s.tabContent}>
            {activeTab === "ocr" && ocrResult && (
              <>
                {ocrResult.layout_hint && (
                  <p style={s.hint}>文書種別: {ocrResult.layout_hint}</p>
                )}
                <div style={s.copyRow}>
                  <button style={s.copyButton} onClick={() => copyText(ocrResult.text)}>
                    {copied ? "コピー済み ✓" : "コピー"}
                  </button>
                </div>
                <pre style={s.pre}>{ocrResult.text}</pre>
              </>
            )}

            {activeTab === "corrected" && correctResult && (
              <>
                <div style={s.copyRow}>
                  <button style={s.copyButton} onClick={() => copyText(correctResult.corrected)}>
                    {copied ? "コピー済み ✓" : "コピー"}
                  </button>
                </div>
                <pre style={s.pre}>{correctResult.corrected}</pre>
              </>
            )}

            {activeTab === "structured" && correctResult?.structured && (
              <>
                <div style={s.copyRow}>
                  <button
                    style={s.copyButton}
                    onClick={() => copyText(JSON.stringify(correctResult.structured, null, 2))}
                  >
                    {copied ? "コピー済み ✓" : "コピー"}
                  </button>
                </div>
                <pre style={{ ...s.pre, background: "#f1f5f9", padding: 12, borderRadius: 8 }}>
                  {JSON.stringify(correctResult.structured, null, 2)}
                </pre>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const s = {
  container: { maxWidth: 720, margin: "40px auto", padding: "0 16px", fontFamily: "sans-serif" },
  title: { textAlign: "center", fontSize: 24, marginBottom: 24 },
  dropzone: {
    border: "2px dashed #9ca3af",
    borderRadius: 12,
    padding: 24,
    textAlign: "center",
    cursor: "pointer",
    minHeight: 180,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#f9fafb",
    marginBottom: 12,
  },
  dropText: { color: "#6b7280", lineHeight: 2 },
  preview: { maxHeight: 240, maxWidth: "100%", objectFit: "contain" },
  pdfPreview: { width: "100%", height: 240, border: "none" },
  fileName: { textAlign: "center", color: "#374151", fontSize: 14, marginBottom: 12 },
  buttonRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginBottom: 16,
    flexWrap: "wrap",
  },
  button: {
    padding: "10px 28px",
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 15,
    cursor: "pointer",
  },
  correctButton: {
    padding: "10px 28px",
    background: "#16a34a",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 15,
    cursor: "pointer",
  },
  select: {
    padding: "9px 12px",
    fontSize: 14,
    borderRadius: 8,
    border: "1px solid #d1d5db",
    background: "#fff",
    cursor: "pointer",
  },
  error: {
    background: "#fee2e2",
    color: "#b91c1c",
    border: "1px solid #fca5a5",
    borderRadius: 8,
    padding: "12px 16px",
    marginBottom: 16,
  },
  tabArea: {
    border: "1px solid #e5e7eb",
    borderRadius: 12,
    overflow: "hidden",
  },
  tabBar: {
    display: "flex",
    borderBottom: "1px solid #e5e7eb",
    background: "#f9fafb",
  },
  tab: {
    padding: "10px 20px",
    border: "none",
    background: "transparent",
    fontSize: 14,
    cursor: "pointer",
    color: "#6b7280",
    borderBottom: "2px solid transparent",
  },
  tabActive: {
    color: "#2563eb",
    fontWeight: 700,
    borderBottom: "2px solid #2563eb",
    background: "#fff",
  },
  tabContent: {
    padding: 16,
  },
  hint: { margin: "0 0 8px", fontSize: 13, color: "#6b7280" },
  copyRow: { display: "flex", justifyContent: "flex-end", marginBottom: 8 },
  copyButton: {
    padding: "6px 16px",
    fontSize: 13,
    fontWeight: 600,
    border: "none",
    borderRadius: 8,
    background: "#2563eb",
    color: "#fff",
    cursor: "pointer",
  },
  pre: { margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 13, lineHeight: 1.6 },
};

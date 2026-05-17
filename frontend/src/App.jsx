import { useState, useRef, useCallback } from "react";

export default function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const inputRef = useRef(null);

  const selectFile = (f) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setError(null);
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
    setResult(null);
    setRunning(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/ocr", { method: "POST", body: formData });
      if (!res.ok) throw new Error(`OCR エラー: ${res.status}`);
      const { text, layout_hint } = await res.json();
      setResult({ text, layout_hint });
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={s.container}>
      <h1 style={s.title}>NDLOCR-Lite OCR</h1>

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

      <button
        style={{ ...s.button, opacity: !file || running ? 0.5 : 1 }}
        onClick={runOcr}
        disabled={!file || running}
      >
        {running ? "⏳ OCR 実行中…" : "OCR 実行"}
      </button>

      {error && <div style={s.error}>{error}</div>}

      {result && (
        <div style={s.resultBox}>
          <div style={s.resultHeader}>
            {result.layout_hint && (
              <p style={s.hint}>文書種別: {result.layout_hint}</p>
            )}
            <button
              style={s.copyButton}
              onClick={async () => {
                await navigator.clipboard.writeText(result.text);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
            >
              {copied ? "コピー済み ✓" : "コピー"}
            </button>
          </div>
          <pre style={s.pre}>{result.text}</pre>
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
  button: {
    display: "block",
    margin: "0 auto 24px",
    padding: "10px 32px",
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 16,
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
  resultBox: {
    border: "1px solid #e5e7eb",
    borderRadius: 12,
    padding: 16,
  },
  resultHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  hint: { margin: 0, fontSize: 13, color: "#6b7280" },
  copyButton: {
    padding: "8px 20px",
    fontSize: 14,
    fontWeight: 600,
    border: "none",
    borderRadius: 8,
    background: "#2563eb",
    color: "#fff",
    cursor: "pointer",
    flexShrink: 0,
  },
  pre: { margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 13, lineHeight: 1.6 },
};

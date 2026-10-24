import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  BrainCircuit,
  Languages,
  Users,
  BarChart3,
  ShieldCheck,
  Workflow,
  Copy,
  Pencil,
  RefreshCw,
  Send,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
} from "lucide-react";
import api from "../services/api";
import "./AIStudio.css";

/* ------------------------------------------------------------------ */
/*  Language map — backend uses full names, not ISO codes              */
/* ------------------------------------------------------------------ */
const LANGUAGES = [
  { name: "Hindi", code: "hi", native: "हिन्दी", rtl: false },
  { name: "Kannada", code: "kn", native: "ಕನ್ನಡ", rtl: false },
  { name: "Tamil", code: "ta", native: "தமிழ்", rtl: false },
  { name: "Telugu", code: "te", native: "తెలుగు", rtl: false },
  { name: "Marathi", code: "mr", native: "मराठी", rtl: false },
  { name: "Bengali", code: "bn", native: "বাংলা", rtl: false },
  { name: "Gujarati", code: "gu", native: "ગુજરાતી", rtl: false },
  { name: "Malayalam", code: "ml", native: "മലയാളം", rtl: false },
  { name: "Punjabi", code: "pa", native: "ਪੰਜਾਬੀ", rtl: false },
  { name: "Urdu", code: "ur", native: "اردو", rtl: true },
];

const TONES = ["Informative", "Urgent", "Empathetic", "Formal", "Persuasive"];
const CHANNELS = ["SMS", "WhatsApp", "Email", "Social Media"];
const TABS = [
  { key: "Generate", icon: BrainCircuit, label: "Generate" },
  { key: "Translate", icon: Languages, label: "Translate" },
  { key: "Personalize", icon: Users, label: "Personalize" },
  { key: "Analyze", icon: BarChart3, label: "Analyze" },
  { key: "Review", icon: ShieldCheck, label: "Review" },
  { key: "Workflow", icon: Workflow, label: "Workflow" },
];

export default function AIStudio() {
  const navigate = useNavigate();

  /* ---- auth guard ---- */
  useEffect(() => {
    if (!sessionStorage.getItem("access_token")) {
      navigate("/login", { replace: true });
    }
  }, [navigate]);

  /* ---- shared state ---- */
  const [tab, setTab] = useState("Generate");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  /* ---- Generate state ---- */
  const [prompt, setPrompt] = useState("");
  const [tone, setTone] = useState("Informative");
  const [channel, setChannel] = useState("SMS");
  const [genResult, setGenResult] = useState(null);

  /* ---- Translate state ---- */
  const [transText, setTransText] = useState("");
  const [targetLang, setTargetLang] = useState("Hindi");
  const [batchMode, setBatchMode] = useState(false);
  const [batchLangs, setBatchLangs] = useState(
    LANGUAGES.map((l) => l.name)
  );
  const [transResult, setTransResult] = useState(null);
  const [editedTranslations, setEditedTranslations] = useState({});

  /* ---- Personalize state ---- */
  const [persoText, setPersoText] = useState(
    "Dear {{name}}, important update for {{preferred_language}}-speaking community."
  );
  const [persoMemberId, setPersoMemberId] = useState("");
  const [persoSegmentId, setPersoSegmentId] = useState("");
  const [persoResult, setPersoResult] = useState(null);

  /* ---- Analyze state ---- */
  const [analyzeText, setAnalyzeText] = useState("");
  const [analyzeResult, setAnalyzeResult] = useState(null);
  const [improveResult, setImproveResult] = useState(null);

  /* ---- Review state ---- */
  const [reviewText, setReviewText] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewResult, setReviewResult] = useState(null);
  const [reviewList, setReviewList] = useState([]);
  const [reviewSubTab, setReviewSubTab] = useState("check");

  /* ---- Workflow state ---- */
  const [wfPrompt, setWfPrompt] = useState("");
  const [wfSegmentId, setWfSegmentId] = useState("");
  const [wfLangs, setWfLangs] = useState(LANGUAGES.map((l) => l.name));
  const [wfResult, setWfResult] = useState(null);

  /* ---- History state ---- */
  const [history, setHistory] = useState([]);

  /* ================================================================ */
  /*  ACTIONS                                                         */
  /* ================================================================ */

  function resetResult() {
    setError("");
    setCopied(false);
  }

  function switchTab(t) {
    setTab(t);
    resetResult();
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* fallback */
    }
  }

  /* ---- Generate ---- */
  async function handleGenerate() {
    setBusy(true);
    resetResult();
    try {
      const res = await api.post("/ai/generate", {
        prompt,
        channel,
        tone,
        target_audience: "General Public",
        variations: 2,
      });
      setGenResult(res.data);
    } catch (err) {
      setError(fmtErr(err));
    } finally {
      setBusy(false);
    }
  }

  async function loadHistory() {
    try {
      const res = await api.get("/ai/history?limit=10");
      setHistory(res.data);
    } catch {
      /* silent */
    }
  }

  /* ---- Translate ---- */
  async function handleTranslate() {
    setBusy(true);
    resetResult();
    try {
      if (batchMode) {
        const res = await api.post("/translate/batch", {
          text: transText,
          target_languages: batchLangs,
          source_language: "English",
        });
        setTransResult({ batch: true, data: res.data });
      } else {
        const res = await api.post("/translate", {
          text: transText,
          target_language: targetLang,
          source_language: "English",
        });
        setTransResult({ batch: false, data: res.data });
      }
    } catch (err) {
      setError(fmtErr(err));
    } finally {
      setBusy(false);
    }
  }

  /* ---- Personalize ---- */
  async function handlePersonalize() {
    setBusy(true);
    resetResult();
    try {
      if (persoSegmentId) {
        const res = await api.post("/personalize/variants", {
          base_text: persoText,
          segment_id: Number(persoSegmentId),
          sample_limit: 5,
        });
        setPersoResult({ type: "variants", data: res.data });
      } else {
        const res = await api.post("/personalize/preview", {
          template_text: persoText,
          audience_member_id: persoMemberId ? Number(persoMemberId) : null,
          custom_attributes: {},
        });
        setPersoResult({ type: "preview", data: res.data });
      }
    } catch (err) {
      setError(fmtErr(err));
    } finally {
      setBusy(false);
    }
  }

  /* ---- Analyze ---- */
  async function handleAnalyze() {
    setBusy(true);
    resetResult();
    try {
      const res = await api.post("/analysis/tone-readability", {
        content: analyzeText,
        channel,
        target_tone: tone,
      });
      setAnalyzeResult(res.data);
    } catch (err) {
      setError(fmtErr(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleImproveTone(specificTone) {
    setBusy(true);
    resetResult();
    const toneToUse = specificTone || tone;
    try {
      const res = await api.post("/ai/improve-tone", {
        content: analyzeText,
        target_tone: toneToUse,
        channel,
      });
      setImproveResult(res.data);
    } catch (err) {
      setError(fmtErr(err));
    } finally {
      setBusy(false);
    }
  }

  /* ---- Review ---- */
  async function handleComplianceCheck() {
    setBusy(true);
    resetResult();
    try {
      const res = await api.post("/review/compliance-check", {
        content: reviewText,
        channel,
        language: "English",
      });
      setReviewResult({ type: "compliance", data: res.data });
    } catch (err) {
      setError(fmtErr(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitForReview() {
    setBusy(true);
    resetResult();
    try {
      const res = await api.post("/review/submit", {
        content: reviewText,
        channel,
        language: "English",
        reviewer_notes: reviewNotes || null,
      });
      setReviewResult({ type: "submitted", data: res.data });
      loadReviewList();
    } catch (err) {
      setError(fmtErr(err));
    } finally {
      setBusy(false);
    }
  }

  async function loadReviewList() {
    try {
      const res = await api.get("/review/list?limit=10");
      setReviewList(res.data);
    } catch {
      /* silent */
    }
  }

  async function handleDecision(reviewId, decision) {
    try {
      await api.post(`/review/${reviewId}/decision`, {
        decision,
        reviewer_notes: `${decision} via AI Studio`,
      });
      loadReviewList();
    } catch (err) {
      setError(fmtErr(err));
    }
  }

  /* ---- Workflow ---- */
  async function handleWorkflow() {
    setBusy(true);
    resetResult();
    try {
      const res = await api.post("/workflow/run", {
        prompt: wfPrompt,
        channel,
        tone,
        target_languages: wfLangs,
        segment_id: wfSegmentId ? Number(wfSegmentId) : null,
        auto_submit_for_review: true,
      });
      setWfResult(res.data);
    } catch (err) {
      setError(fmtErr(err));
    } finally {
      setBusy(false);
    }
  }

  /* ---- Helpers ---- */
  function fmtErr(err) {
    const d = err.response?.data?.detail;
    if (Array.isArray(d)) return d.map((i) => i.msg || i).join(", ");
    if (typeof d === "string") return d;
    return err.message || "Request failed. Check that the backend is running.";
  }

  function langInfo(name) {
    return LANGUAGES.find((l) => l.name === name) || {};
  }

  function toggleBatchLang(name) {
    setBatchLangs((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  }
  function toggleWfLang(name) {
    setWfLangs((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  }

  function useAsContent(text) {
    setTransText(text);
    setAnalyzeText(text);
    setReviewText(text);
    setPersoText(text);
  }

  /* ================================================================ */
  /*  RENDER HELPERS                                                  */
  /* ================================================================ */

  function handleTranslationChange(langCode, newText) {
    setEditedTranslations((prev) => ({
      ...prev,
      [langCode]: newText,
    }));
  }

  function renderTranslationCard(tr) {
    const isRtl = tr.is_rtl || tr.direction === "rtl" || tr.language === "Urdu";
    const defaultText = tr.bidi_safe_text || tr.translated_text || "";
    const currentText =
      editedTranslations[tr.language_code] !== undefined
        ? editedTranslations[tr.language_code]
        : defaultText;
    const isEdited =
      editedTranslations[tr.language_code] !== undefined &&
      editedTranslations[tr.language_code] !== defaultText;

    return (
      <div
        className={`aist-translation-card ${isRtl ? "aist-rtl-card" : ""}`}
        key={tr.language_code}
      >
        <div className="aist-trans-header">
          <span className="aist-lang-badge">
            {tr.native_name} ({tr.language})
          </span>
          {isRtl && <span className="aist-rtl-badge">RTL (اردو)</span>}
          <span className="aist-provider-badge">
            {tr.is_fallback ? "Offline demo translation" : tr.provider}
          </span>
        </div>

        {/* Editable translation field */}
        <div className="aist-trans-edit-box">
          <label className="aist-trans-label">
            {isRtl ? "ترمیم شدہ ترجمہ (Editable Translation):" : "Editable Translation:"}
          </label>
          <textarea
            className={`aist-trans-textarea ${isRtl ? "aist-rtl-textarea" : ""}`}
            rows={3}
            dir={isRtl ? "rtl" : "ltr"}
            lang={isRtl ? "ur" : undefined}
            value={currentText}
            onChange={(e) => handleTranslationChange(tr.language_code, e.target.value)}
            style={
              isRtl
                ? {
                    fontFamily: "'Noto Nastaliq Urdu', 'Segoe UI', Tahoma, sans-serif",
                    lineHeight: 2.0,
                    fontSize: "16px",
                    textAlign: "right",
                    direction: "rtl",
                    unicodeBidi: "plaintext",
                  }
                : {}
            }
          />
        </div>

        {/* Live formatted preview */}
        <div className="aist-trans-preview-box">
          <label className="aist-trans-label">
            {isRtl ? "پیش نظارہ (RTL Preview):" : "Live Preview:"}
          </label>
          <div
            className={`aist-trans-body ${isRtl ? "aist-rtl-preview" : ""}`}
            dir={isRtl ? "rtl" : "ltr"}
            lang={isRtl ? "ur" : undefined}
            style={
              isRtl
                ? {
                    fontFamily: "'Noto Nastaliq Urdu', 'Segoe UI', Tahoma, sans-serif",
                    lineHeight: 2.2,
                    fontSize: "17px",
                    textAlign: "right",
                    direction: "rtl",
                    unicodeBidi: "isolate",
                  }
                : {}
            }
          >
            {currentText}
          </div>
        </div>

        {/* Action buttons */}
        <div className="aist-trans-actions">
          <button className="aist-copy-btn" onClick={() => copyText(currentText)}>
            <Copy size={13} /> Copy
          </button>
          <button className="aist-copy-btn" onClick={() => useAsContent(currentText)}>
            <Pencil size={13} /> Use
          </button>
          {isEdited && (
            <button
              className="aist-copy-btn"
              onClick={() => handleTranslationChange(tr.language_code, defaultText)}
            >
              <RefreshCw size={13} /> Reset
            </button>
          )}
        </div>
      </div>
    );
  }

  function renderClarityGauge(score) {
    const color = score >= 80 ? "#22c55e" : score >= 60 ? "#f59e0b" : "#ef4444";
    return (
      <div className="aist-gauge">
        <svg viewBox="0 0 36 36" className="aist-gauge-svg">
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke="#e5e8f1" strokeWidth="3"
          />
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={`${score}, 100`}
          />
        </svg>
        <span className="aist-gauge-label" style={{ color }}>{score}</span>
      </div>
    );
  }

  function renderComplianceIssues(issues) {
    return (
      <ul className="aist-issues-list">
        {issues.map((issue, i) => (
          <li key={i} className={`aist-issue aist-issue-${issue.severity}`}>
            {issue.passed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
            <span>{issue.message}</span>
            <small>{issue.rule}</small>
          </li>
        ))}
      </ul>
    );
  }

  /* ================================================================ */
  /*  MAIN RENDER                                                     */
  /* ================================================================ */

  const selectedLang = langInfo(targetLang);

  return (
    <main className="ai-studio">
      {/* Header */}
      <header className="ai-studio-header">
        <button className="aist-back-btn" onClick={() => navigate("/dashboard")}>
          <ArrowLeft size={16} /> Dashboard
        </button>
        <p className="ai-studio-eyebrow">
          <Sparkles size={12} /> NEXAREACH · AI CONTENT STUDIO
        </p>
        <h1>AI Content Studio</h1>
        <p>Generate, translate, personalize, analyze, and review public awareness messages.</p>
      </header>

      {/* Tabs */}
      <nav className="ai-studio-tabs" aria-label="Content tools">
        {TABS.map(({ key, icon: Icon, label }) => (
          <button
            key={key}
            className={tab === key ? "active" : ""}
            onClick={() => switchTab(key)}
          >
            <Icon size={15} /> {label}
          </button>
        ))}
      </nav>

      {/* Panel */}
      <section className="ai-studio-panel">

        {/* ============== GENERATE ============== */}
        {tab === "Generate" && (
          <>
            <label>
              Campaign topic / prompt *
              <input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. Dengue prevention tips for monsoon season"
                minLength={3}
              />
            </label>
            <div className="aist-row">
              <label>
                Tone
                <select value={tone} onChange={(e) => setTone(e.target.value)}>
                  {TONES.map((t) => <option key={t}>{t}</option>)}
                </select>
              </label>
              <label>
                Channel
                <select value={channel} onChange={(e) => setChannel(e.target.value)}>
                  {CHANNELS.map((c) => <option key={c}>{c}</option>)}
                </select>
              </label>
            </div>
            <div className="aist-actions">
              <button className="ai-studio-primary" onClick={handleGenerate} disabled={busy || prompt.trim().length < 3}>
                <BrainCircuit size={15} /> {busy ? "Generating..." : "Generate Content"}
              </button>
              <button className="aist-secondary" onClick={loadHistory}>
                <Clock size={14} /> Load History
              </button>
            </div>

            {genResult && (
              <div className="aist-result-card">
                <div className="aist-result-meta">
                  <span className="aist-provider-badge">
                    {genResult.is_fallback ? "⚡ Offline demo content" : `✨ ${genResult.provider}`}
                  </span>
                  <span>Channel: {genResult.channel}</span>
                  <span>Tone: {genResult.tone}</span>
                </div>
                <h3>Generated Content</h3>
                <div className="aist-content-block">{genResult.content}</div>
                <div className="aist-btn-row">
                  <button onClick={() => copyText(genResult.content)}>
                    <Copy size={13} /> {copied ? "Copied!" : "Copy"}
                  </button>
                  <button onClick={() => useAsContent(genResult.content)}>
                    <Pencil size={13} /> Use in other tabs
                  </button>
                  <button onClick={handleGenerate} disabled={busy}>
                    <RefreshCw size={13} /> Regenerate
                  </button>
                </div>
                {genResult.variations && genResult.variations.length > 1 && (
                  <details className="aist-variations">
                    <summary>View {genResult.variations.length} variations</summary>
                    {genResult.variations.map((v, i) => (
                      <div key={i} className="aist-variation">
                        <span className="aist-var-label">Variation {i + 1}</span>
                        <p>{v}</p>
                        <button onClick={() => copyText(v)}><Copy size={12} /> Copy</button>
                        <button onClick={() => useAsContent(v)}><Pencil size={12} /> Use</button>
                      </div>
                    ))}
                  </details>
                )}
              </div>
            )}

            {history.length > 0 && (
              <details className="aist-history">
                <summary>Generation History ({history.length} recent)</summary>
                {history.map((h) => (
                  <div key={h.id} className="aist-history-item">
                    <div className="aist-hist-meta">
                      <strong>{h.prompt.slice(0, 60)}{h.prompt.length > 60 ? "..." : ""}</strong>
                      <small>{h.channel} · {h.tone} · {h.is_fallback ? "Offline" : h.provider}</small>
                    </div>
                    <p>{h.generated_content.slice(0, 120)}...</p>
                    <button onClick={() => { useAsContent(h.generated_content); setPrompt(h.prompt); }}>
                      <Pencil size={12} /> Reuse
                    </button>
                  </div>
                ))}
              </details>
            )}
          </>
        )}

        {/* ============== TRANSLATE ============== */}
        {tab === "Translate" && (
          <>
            <label>
              Source text (English) *
              <textarea
                rows={5}
                value={transText}
                onChange={(e) => setTransText(e.target.value)}
                placeholder="Enter your campaign message to translate..."
              />
            </label>
            <div className="aist-row">
              <label className="aist-toggle-label">
                <input
                  type="checkbox"
                  checked={batchMode}
                  onChange={(e) => setBatchMode(e.target.checked)}
                />
                Batch translate (all selected languages)
              </label>
            </div>
            {!batchMode ? (
              <label>
                Target language
                <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
                  {LANGUAGES.map(({ name, native, rtl }) => (
                    <option key={name} value={name}>
                      {name} — {native} {rtl ? "(RTL)" : ""}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <div className="aist-lang-checkboxes">
                {LANGUAGES.map(({ name, native, rtl }) => (
                  <label key={name} className="aist-lang-check">
                    <input
                      type="checkbox"
                      checked={batchLangs.includes(name)}
                      onChange={() => toggleBatchLang(name)}
                    />
                    {name} — {native} {rtl ? "(RTL)" : ""}
                  </label>
                ))}
              </div>
            )}
            <button
              className="ai-studio-primary"
              onClick={handleTranslate}
              disabled={busy || !transText.trim()}
            >
              <Languages size={15} /> {busy ? "Translating..." : batchMode ? "Batch Translate" : "Translate"}
            </button>

            {transResult && !transResult.batch && (
              <div className="aist-result-card">
                <h3>Translation Result</h3>
                {renderTranslationCard(transResult.data)}
              </div>
            )}
            {transResult && transResult.batch && (
              <div className="aist-result-card">
                <h3>Batch Translation — {transResult.data.results.length} languages</h3>
                <div className="aist-trans-grid">
                  {transResult.data.results.map(renderTranslationCard)}
                </div>
              </div>
            )}
          </>
        )}

        {/* ============== PERSONALIZE ============== */}
        {tab === "Personalize" && (
          <>
            <label>
              Message template (use {"{{name}}"}, {"{{preferred_language}}"}, etc.) *
              <textarea
                rows={4}
                value={persoText}
                onChange={(e) => setPersoText(e.target.value)}
                placeholder='Dear {{name}}, health update for {{preferred_language}}-speaking community.'
              />
            </label>
            <div className="aist-row">
              <label>
                Audience member ID (optional)
                <input
                  type="number"
                  min={1}
                  value={persoMemberId}
                  onChange={(e) => setPersoMemberId(e.target.value)}
                  placeholder="e.g. 1"
                />
              </label>
              <label>
                Segment ID (for variant generation)
                <input
                  type="number"
                  min={1}
                  value={persoSegmentId}
                  onChange={(e) => setPersoSegmentId(e.target.value)}
                  placeholder="e.g. 1"
                />
              </label>
            </div>
            <p className="aist-hint">
              {persoSegmentId
                ? "Will generate segment variants for matched audience members."
                : "Will preview placeholder replacement for a single member."}
            </p>
            <button className="ai-studio-primary" onClick={handlePersonalize} disabled={busy || !persoText.trim()}>
              <Users size={15} /> {busy ? "Processing..." : "Personalize"}
            </button>

            {persoResult?.type === "preview" && (
              <div className="aist-result-card">
                <h3>Personalized Preview</h3>
                <div className="aist-kv">
                  <span>Original:</span>
                  <p>{persoResult.data.original_text}</p>
                </div>
                <div className="aist-kv aist-highlight">
                  <span>Personalized:</span>
                  <p>{persoResult.data.personalized_text}</p>
                </div>
                <div className="aist-kv">
                  <span>Tokens found:</span>
                  <p>{persoResult.data.tokens_found.join(", ") || "None"}</p>
                </div>
                {persoResult.data.missing_tokens.length > 0 && (
                  <div className="aist-kv aist-warn">
                    <span>Missing tokens:</span>
                    <p>{persoResult.data.missing_tokens.join(", ")}</p>
                  </div>
                )}
                <button onClick={() => copyText(persoResult.data.personalized_text)}>
                  <Copy size={13} /> Copy personalized text
                </button>
              </div>
            )}
            {persoResult?.type === "variants" && (
              <div className="aist-result-card">
                <h3>Segment Variants — {persoResult.data.segment_name}</h3>
                <p className="aist-meta-line">
                  Matched {persoResult.data.total_matched_members} audience members
                  {persoResult.data.criteria && Object.keys(persoResult.data.criteria).length > 0
                    ? ` · Criteria: ${JSON.stringify(persoResult.data.criteria)}`
                    : ""}
                </p>
                <div className="aist-variants-list">
                  {persoResult.data.sample_variants.map((v) => (
                    <div key={v.audience_member_id} className="aist-variant-card">
                      <strong>{v.full_name}</strong>
                      <small>{v.preferred_language} · {v.email || v.phone || `ID ${v.audience_member_id}`}</small>
                      <p>{v.personalized_content}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* ============== ANALYZE ============== */}
        {tab === "Analyze" && (
          <>
            <label>
              Message content to analyze *
              <textarea
                rows={5}
                value={analyzeText}
                onChange={(e) => setAnalyzeText(e.target.value)}
                placeholder="Paste your campaign message here..."
              />
            </label>
            <div className="aist-row">
              <label>
                Channel
                <select value={channel} onChange={(e) => setChannel(e.target.value)}>
                  {CHANNELS.map((c) => <option key={c}>{c}</option>)}
                </select>
              </label>
              <label>
                Target tone
                <select value={tone} onChange={(e) => setTone(e.target.value)}>
                  {TONES.map((t) => <option key={t}>{t}</option>)}
                </select>
              </label>
            </div>
            <div className="aist-actions">
              <button className="ai-studio-primary" onClick={handleAnalyze} disabled={busy || !analyzeText.trim()}>
                <BarChart3 size={15} /> {busy ? "Analyzing..." : "Analyze Readability & Tone"}
              </button>
              <button className="aist-secondary" onClick={() => handleImproveTone()} disabled={busy || !analyzeText.trim()}>
                <Sparkles size={14} /> {busy ? "Optimizing..." : "Improve & Rewrite"}
              </button>
            </div>

            <div className="aist-quick-tones">
              <span className="aist-quick-tone-label">Quick tone rewrites:</span>
              <button type="button" className="aist-tone-chip" onClick={() => handleImproveTone("Urgent")} disabled={busy || !analyzeText.trim()}>
                🚨 Urgent
              </button>
              <button type="button" className="aist-tone-chip" onClick={() => handleImproveTone("Empathetic")} disabled={busy || !analyzeText.trim()}>
                🤝 Empathetic
              </button>
              <button type="button" className="aist-tone-chip" onClick={() => handleImproveTone("Formal")} disabled={busy || !analyzeText.trim()}>
                🏛️ Formal
              </button>
              <button type="button" className="aist-tone-chip" onClick={() => handleImproveTone("Persuasive")} disabled={busy || !analyzeText.trim()}>
                📢 Persuasive
              </button>
            </div>

            {improveResult && (
              <div className="aist-result-card aist-improve-card">
                <div className="aist-result-meta">
                  <span className="aist-provider-badge">
                    {improveResult.is_fallback ? "⚡ Offline rewrite" : `✨ ${improveResult.provider}`}
                  </span>
                  <span>Tone: {improveResult.target_tone}</span>
                  <span>Channel: {improveResult.channel}</span>
                  <span>{improveResult.character_count} characters {improveResult.channel === "SMS" && "(SMS limit: 160)"}</span>
                </div>
                <h3>Rewritten & Improved Content</h3>
                <div className="aist-content-block">{improveResult.improved_content}</div>
                <div className="aist-btn-row">
                  <button onClick={() => copyText(improveResult.improved_content)}>
                    <Copy size={13} /> {copied ? "Copied!" : "Copy"}
                  </button>
                  <button onClick={() => setAnalyzeText(improveResult.improved_content)}>
                    <RefreshCw size={13} /> Replace Editor Text
                  </button>
                  <button onClick={() => useAsContent(improveResult.improved_content)}>
                    <Pencil size={13} /> Use in other tabs
                  </button>
                </div>
                {improveResult.suggestions && improveResult.suggestions.length > 0 && (
                  <div className="aist-recommendations">
                    <h4>Tone & Channel Optimization Applied</h4>
                    <ul>
                      {improveResult.suggestions.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {analyzeResult && (
              <div className="aist-result-card">
                <h3>Analysis Results</h3>
                <div className="aist-metrics-row">
                  <div className="aist-metric-box">
                    <span>Public Clarity Score</span>
                    {renderClarityGauge(analyzeResult.readability.public_clarity_score)}
                  </div>
                  <div className="aist-metric-box">
                    <span>Flesch Reading Ease</span>
                    <strong>{analyzeResult.readability.flesch_reading_ease}</strong>
                    <small>{analyzeResult.readability.reading_ease_level}</small>
                  </div>
                  <div className="aist-metric-box">
                    <span>Grade Level</span>
                    <strong>{analyzeResult.readability.flesch_kincaid_grade}</strong>
                  </div>
                  <div className="aist-metric-box">
                    <span>Words / Sentences</span>
                    <strong>{analyzeResult.readability.word_count} / {analyzeResult.readability.sentence_count}</strong>
                  </div>
                </div>
                <div className="aist-tone-section">
                  <h4>Tone: {analyzeResult.tone.primary_tone}
                    {analyzeResult.tone.secondary_tone ? ` / ${analyzeResult.tone.secondary_tone}` : ""}</h4>
                  <p>Sentiment: {analyzeResult.tone.sentiment} · Confidence: {(analyzeResult.tone.confidence * 100).toFixed(0)}%</p>
                </div>
                {analyzeResult.recommendations.length > 0 && (
                  <div className="aist-recommendations">
                    <h4>Recommendations</h4>
                    <ul>
                      {analyzeResult.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* ============== REVIEW ============== */}
        {tab === "Review" && (
          <>
            <div className="aist-sub-tabs">
              <button className={reviewSubTab === "check" ? "active" : ""} onClick={() => setReviewSubTab("check")}>Compliance Check</button>
              <button className={reviewSubTab === "submit" ? "active" : ""} onClick={() => setReviewSubTab("submit")}>Submit for Review</button>
              <button className={reviewSubTab === "list" ? "active" : ""} onClick={() => { setReviewSubTab("list"); loadReviewList(); }}>Review Queue</button>
            </div>

            {(reviewSubTab === "check" || reviewSubTab === "submit") && (
              <>
                <label>
                  Message content *
                  <textarea
                    rows={5}
                    value={reviewText}
                    onChange={(e) => setReviewText(e.target.value)}
                    placeholder="Enter your campaign message to check..."
                  />
                </label>
                <div className="aist-row">
                  <label>
                    Channel
                    <select value={channel} onChange={(e) => setChannel(e.target.value)}>
                      {CHANNELS.map((c) => <option key={c}>{c}</option>)}
                    </select>
                  </label>
                </div>
              </>
            )}

            {reviewSubTab === "check" && (
              <>
                <button className="ai-studio-primary" onClick={handleComplianceCheck} disabled={busy || !reviewText.trim()}>
                  <ShieldCheck size={15} /> {busy ? "Checking..." : "Run Compliance Check"}
                </button>
                {reviewResult?.type === "compliance" && (
                  <div className="aist-result-card">
                    <div className="aist-compliance-header">
                      <h3>{reviewResult.data.passed ? "✅ Compliant" : "❌ Issues Found"}</h3>
                      <span className="aist-score-badge" style={{
                        background: reviewResult.data.score >= 80 ? "#dcfce7" : reviewResult.data.score >= 60 ? "#fef3c7" : "#fee2e2",
                        color: reviewResult.data.score >= 80 ? "#166534" : reviewResult.data.score >= 60 ? "#92400e" : "#991b1b",
                      }}>
                        Score: {reviewResult.data.score}/100
                      </span>
                    </div>
                    <p>{reviewResult.data.character_count} chars (max recommended: {reviewResult.data.max_recommended_characters})</p>
                    {renderComplianceIssues(reviewResult.data.issues)}
                  </div>
                )}
              </>
            )}

            {reviewSubTab === "submit" && (
              <>
                <label>
                  Reviewer notes (optional)
                  <input value={reviewNotes} onChange={(e) => setReviewNotes(e.target.value)} placeholder="Notes for the reviewer..." />
                </label>
                <button className="ai-studio-primary" onClick={handleSubmitForReview} disabled={busy || !reviewText.trim()}>
                  <Send size={15} /> {busy ? "Submitting..." : "Submit for Review"}
                </button>
                {reviewResult?.type === "submitted" && (
                  <div className="aist-result-card aist-success">
                    <h3>✅ Submitted for Review</h3>
                    <p>Review ID: #{reviewResult.data.id} · Status: {reviewResult.data.status}</p>
                    <p>Compliance Score: {reviewResult.data.compliance_score}/100</p>
                  </div>
                )}
              </>
            )}

            {reviewSubTab === "list" && (
              <div className="aist-result-card">
                <div className="aist-review-header-row">
                  <h3>Review Queue ({reviewList.length})</h3>
                  <button className="aist-secondary" onClick={loadReviewList}><RefreshCw size={13} /> Refresh</button>
                </div>
                {reviewList.length === 0 && <p className="aist-empty">No reviews found. Submit content for review first.</p>}
                {reviewList.map((r) => (
                  <div key={r.id} className="aist-review-item">
                    <div className="aist-review-meta">
                      <strong>Review #{r.id}</strong>
                      <span className={`aist-status aist-status-${r.status}`}>{r.status}</span>
                      <span>Score: {r.compliance_score}/100</span>
                    </div>
                    {r.reviewer_notes && <p className="aist-review-notes">Notes: {r.reviewer_notes}</p>}
                    {r.status === "pending_review" && (
                      <div className="aist-btn-row">
                        <button className="aist-approve" onClick={() => handleDecision(r.id, "approved")}>
                          <CheckCircle2 size={13} /> Approve
                        </button>
                        <button className="aist-reject" onClick={() => handleDecision(r.id, "rejected")}>
                          <XCircle size={13} /> Reject
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* ============== WORKFLOW ============== */}
        {tab === "Workflow" && (
          <>
            <label>
              Campaign topic / prompt *
              <input
                value={wfPrompt}
                onChange={(e) => setWfPrompt(e.target.value)}
                placeholder="e.g. Water contamination alert for sector 9"
                minLength={3}
              />
            </label>
            <div className="aist-row">
              <label>
                Tone
                <select value={tone} onChange={(e) => setTone(e.target.value)}>
                  {TONES.map((t) => <option key={t}>{t}</option>)}
                </select>
              </label>
              <label>
                Channel
                <select value={channel} onChange={(e) => setChannel(e.target.value)}>
                  {CHANNELS.map((c) => <option key={c}>{c}</option>)}
                </select>
              </label>
              <label>
                Segment ID (optional)
                <input
                  type="number"
                  min={1}
                  value={wfSegmentId}
                  onChange={(e) => setWfSegmentId(e.target.value)}
                  placeholder="e.g. 1"
                />
              </label>
            </div>
            <div className="aist-lang-checkboxes">
              <p className="aist-hint">Target languages for batch translation:</p>
              {LANGUAGES.map(({ name, native, rtl }) => (
                <label key={name} className="aist-lang-check">
                  <input type="checkbox" checked={wfLangs.includes(name)} onChange={() => toggleWfLang(name)} />
                  {name} — {native} {rtl ? "(RTL)" : ""}
                </label>
              ))}
            </div>
            <button className="ai-studio-primary" onClick={handleWorkflow} disabled={busy || wfPrompt.trim().length < 3}>
              <Workflow size={15} /> {busy ? "Running pipeline..." : "Run Full Workflow"}
            </button>

            {wfResult && (
              <div className="aist-result-card">
                <h3>✅ Workflow Complete — {wfResult.status}</h3>

                {/* Generation */}
                <details open>
                  <summary>1. Generated Content ({wfResult.generated_content.is_fallback ? "Offline demo" : wfResult.generated_content.provider})</summary>
                  <div className="aist-content-block">{wfResult.generated_content.content}</div>
                  <div className="aist-btn-row">
                    <button onClick={() => copyText(wfResult.generated_content.content)}><Copy size={12} /> Copy</button>
                    <button onClick={() => useAsContent(wfResult.generated_content.content)}><Pencil size={12} /> Use in other tabs</button>
                  </div>
                </details>

                {/* Translations */}
                <details>
                  <summary>2. Translations ({wfResult.translations.results.length} languages)</summary>
                  <div className="aist-trans-grid">
                    {wfResult.translations.results.map(renderTranslationCard)}
                  </div>
                </details>

                {/* Personalization */}
                {wfResult.personalization && (
                  <details>
                    <summary>3. Personalization — {wfResult.personalization.segment_name} ({wfResult.personalization.total_matched_members} members)</summary>
                    <div className="aist-variants-list">
                      {wfResult.personalization.sample_variants.map((v) => (
                        <div key={v.audience_member_id} className="aist-variant-card">
                          <strong>{v.full_name}</strong>
                          <small>{v.preferred_language}</small>
                          <p>{v.personalized_content}</p>
                        </div>
                      ))}
                    </div>
                  </details>
                )}

                {/* Analysis */}
                <details>
                  <summary>4. Analysis — Clarity {wfResult.analysis.readability.public_clarity_score}/100 · {wfResult.analysis.tone.primary_tone}</summary>
                  <div className="aist-metrics-row">
                    <div className="aist-metric-box">
                      <span>Clarity</span>
                      {renderClarityGauge(wfResult.analysis.readability.public_clarity_score)}
                    </div>
                    <div className="aist-metric-box">
                      <span>Tone</span>
                      <strong>{wfResult.analysis.tone.primary_tone}</strong>
                    </div>
                    <div className="aist-metric-box">
                      <span>Sentiment</span>
                      <strong>{wfResult.analysis.tone.sentiment}</strong>
                    </div>
                  </div>
                </details>

                {/* Compliance */}
                <details>
                  <summary>5. Compliance — {wfResult.compliance.passed ? "✅ Passed" : "⚠ Issues"} (Score: {wfResult.compliance.score}/100)</summary>
                  {renderComplianceIssues(wfResult.compliance.issues)}
                </details>

                {/* Review */}
                {wfResult.review && (
                  <details>
                    <summary>6. Review — #{wfResult.review.id} · {wfResult.review.status}</summary>
                    <p>Compliance score: {wfResult.review.compliance_score}/100</p>
                    {wfResult.review.reviewer_notes && <p>Notes: {wfResult.review.reviewer_notes}</p>}
                  </details>
                )}
              </div>
            )}
          </>
        )}

        {/* Error display */}
        {error && <p className="ai-studio-error" role="alert">{String(error)}</p>}
      </section>
    </main>
  );
}

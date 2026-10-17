
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Users, Plus, RefreshCw, ArrowLeft, Layers } from "lucide-react";
import api from "../services/api";
import "./Segments.css";

export default function Segments() {
  const navigate = useNavigate();
  const [segments, setSegments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    description: "",
    criteria: "{}",
  });

  async function loadSegments() {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/segments");
      setSegments(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to load segments.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!sessionStorage.getItem("access_token")) {
      navigate("/login", { replace: true });
      return;
    }

    loadSegments();
  }, [navigate]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    let criteria;

    try {
      criteria = JSON.parse(form.criteria || "{}");

      if (
        criteria === null ||
        Array.isArray(criteria) ||
        typeof criteria !== "object"
      ) {
        throw new Error("Criteria must be a JSON object.");
      }
    } catch {
      setError('Criteria must be valid JSON, for example: {"language":"Telugu"}');
      return;
    }

    setSaving(true);

    try {
      await api.post("/segments", {
        name: form.name.trim(),
        description: form.description.trim() || null,
        criteria,
      });

      setForm({ name: "", description: "", criteria: "{}" });
      await loadSegments();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : typeof detail === "string"
            ? detail
            : "Unable to create segment."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="segments-page">
      <header className="segments-header">
        <div>
          <span className="segments-breadcrumb">Workspace / Segments</span>
          <h1><Layers size={25} /> Audience Segments</h1>
          <p>Organize audiences into groups for targeted public awareness campaigns.</p>
        </div>

        <button
          className="segments-secondary"
          onClick={() => navigate("/dashboard")}
        >
          <ArrowLeft size={16} /> Dashboard
        </button>
      </header>

      <section className="segments-hero">
        <div>
          <span className="segments-eyebrow">TARGET THE RIGHT AUDIENCE</span>
          <h2>Reach the people<br /><span>who matter most.</span></h2>
          <p>Create and manage reusable audience groups for your campaigns.</p>
        </div>
        <div className="segments-hero-icon">
          <Users size={52} />
        </div>
      </section>

      <section className="segments-panel">
        <h2><Plus size={19} /> Create a segment</h2>
        <p className="segments-subtitle">
          Define a group and store its targeting criteria.
        </p>

        <form className="segments-form" onSubmit={handleSubmit}>
          <label>
            Segment name *
            <input
              value={form.name}
              onChange={(event) =>
                setForm({ ...form, name: event.target.value })
              }
              placeholder="e.g. Telugu-speaking audience"
              minLength={2}
              maxLength={150}
              required
            />
          </label>

          <label>
            Description
            <input
              value={form.description}
              onChange={(event) =>
                setForm({ ...form, description: event.target.value })
              }
              placeholder="What is this segment for?"
            />
          </label>

          <label>
            Targeting criteria (JSON)
            <textarea
              value={form.criteria}
              onChange={(event) =>
                setForm({ ...form, criteria: event.target.value })
              }
              rows={4}
              placeholder='{"language":"Telugu"}'
              required
            />
            <span className="segments-hint">
              Example: {"{"}"language": "Telugu"{"}"} . This stores criteria;
              automatic member filtering depends on backend support.
            </span>
          </label>

          {error && <p className="segments-error">{String(error)}</p>}

          <button className="segments-primary" type="submit" disabled={saving}>
            <Plus size={17} />
            {saving ? "Saving..." : "Create segment"}
          </button>
        </form>
      </section>

      <section className="segments-panel">
        <div className="segments-list-header">
          <div>
            <h2>Saved segments</h2>
            <p className="segments-subtitle">
              {segments.length} segment{segments.length === 1 ? "" : "s"} created
            </p>
          </div>

          <button
            className="segments-secondary"
            onClick={loadSegments}
            disabled={loading}
          >
            <RefreshCw size={15} /> Refresh
          </button>
        </div>

        {loading ? (
          <p className="segments-empty">Loading segments...</p>
        ) : segments.length === 0 ? (
          <p className="segments-empty">
            No segments yet. Create your first segment above.
          </p>
        ) : (
          <div className="segments-grid">
            {segments.map((segment) => (
              <article className="segment-card" key={segment.id}>
                <span className="segment-icon"><Users size={21} /></span>
                <h3>{segment.name}</h3>
                <p>{segment.description || "No description provided."}</p>
                <span className="segment-id">Segment #{segment.id}</span>
                <details>
                  <summary>View criteria</summary>
                  <pre>{JSON.stringify(segment.criteria, null, 2)}</pre>
                </details>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

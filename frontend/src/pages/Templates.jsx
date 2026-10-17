
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Plus,
  RefreshCw,
  ArrowLeft,
  ArrowUpRight,
  Languages,
} from "lucide-react";
import api from "../services/api";
import "./Templates.css";

export default function Templates() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    channel: "SMS",
    language: "English",
    subject: "",
    body: "",
  });

  const loadTemplates = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/templates");
      const data = response.data;
      setTemplates(Array.isArray(data) ? data : data.items || []);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to load templates.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!sessionStorage.getItem("access_token")) {
      navigate("/login", { replace: true });
      return;
    }

    loadTemplates();
  }, [navigate]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");

    try {
      await api.post("/templates", {
        name: form.name.trim(),
        channel: form.channel,
        language: form.language,
        subject: form.subject.trim() || null,
        body: form.body.trim(),
      });

      setForm({
        name: "",
        channel: "SMS",
        language: "English",
        subject: "",
        body: "",
      });

      await loadTemplates();
      alert("Template created successfully!");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : typeof detail === "string"
            ? detail
            : "Could not create template. Check the required fields."
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="templates-page">
      <header className="templates-topbar">
        <div>
          <span className="templates-breadcrumb">Workspace / Templates</span>
          <h1><FileText size={25} /> Template Library</h1>
          <p>Create reusable messages for multilingual communication.</p>
        </div>

        <button
          className="templates-secondary-btn"
          onClick={() => navigate("/dashboard")}
        >
          <ArrowLeft size={16} /> Dashboard
        </button>
      </header>

      <section className="templates-banner">
        <div>
          <span className="templates-eyebrow">
            <Languages size={15} /> MULTILINGUAL COMMUNICATION
          </span>
          <h2>One message.<br /><span>Many communities.</span></h2>
          <p>Build reusable awareness messages for your preferred channels and languages.</p>
        </div>

        <div className="templates-banner-icon">
          <Languages size={55} strokeWidth={1.4} />
        </div>
      </section>

      <section className="templates-panel">
        <div className="templates-panel-heading">
          <div>
            <h2><Plus size={19} /> Create a template</h2>
            <p>Save a message that can be reused in campaigns.</p>
          </div>
        </div>

        <form className="templates-form" onSubmit={handleSubmit}>
          <label>
            Template name *
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Public Health Awareness"
              minLength={2}
              maxLength={150}
              required
            />
          </label>

          <div className="templates-form-row">
            <label>
              Channel *
              <select
                value={form.channel}
                onChange={(e) => setForm({ ...form, channel: e.target.value })}
              >
                <option value="SMS">SMS</option>
                <option value="Email">Email</option>
                <option value="WhatsApp">WhatsApp</option>
                <option value="Social Media">Social Media</option>
              </select>
            </label>

            <label>
              Language *
              <select
                value={form.language}
                onChange={(e) => setForm({ ...form, language: e.target.value })}
              >
                <option>English</option>
                <option>Telugu</option>
                <option>Hindi</option>
                <option>Tamil</option>
                <option>Kannada</option>
                <option>Malayalam</option>
                <option>Marathi</option>
                <option>Bengali</option>
              </select>
            </label>
          </div>

          <label>
            Subject <span className="templates-optional">(optional)</span>
            <input
              value={form.subject}
              onChange={(e) => setForm({ ...form, subject: e.target.value })}
              placeholder="Email subject, if applicable"
              maxLength={255}
            />
          </label>

          <label>
            Message body *
            <textarea
              value={form.body}
              onChange={(e) => setForm({ ...form, body: e.target.value })}
              placeholder="Write your public awareness message..."
              rows={5}
              required
            />
          </label>

          {error && <p className="templates-error" role="alert">{String(error)}</p>}

          <button type="submit" className="templates-primary-btn" disabled={saving}>
            <Plus size={17} />
            {saving ? "Saving..." : "Save template"}
          </button>
        </form>
      </section>

      <section className="templates-panel">
        <div className="templates-list-heading">
          <div>
            <h2>Saved templates</h2>
            <p>Your reusable messages, ready for campaign workflows.</p>
          </div>

          <button
            className="templates-secondary-btn"
            onClick={loadTemplates}
            disabled={loading}
          >
            <RefreshCw size={15} /> Refresh
          </button>
        </div>

        {loading ? (
          <p className="templates-empty">Loading templates...</p>
        ) : error && templates.length === 0 ? (
          <p className="templates-empty">{String(error)}</p>
        ) : templates.length === 0 ? (
          <div className="templates-empty">
            <FileText size={30} />
            <p>No templates yet. Create your first reusable message above.</p>
          </div>
        ) : (
          <div className="templates-grid">
            {templates.map((template) => (
              <article className="template-card" key={template.id}>
                <div className="template-card-top">
                  <span className="template-card-icon"><FileText size={21} /></span>
                  <span className="template-language">
                    {template.language || "English"}
                  </span>
                </div>

                <h3>{template.name}</h3>
                <span className="template-channel">{template.channel}</span>

                {template.subject && (
                  <p className="template-subject">
                    Subject: {template.subject}
                  </p>
                )}

                <p className="template-body">{template.body}</p>

                <div className="template-card-bottom">
                  <span>Template #{template.id}</span>
                  <ArrowUpRight size={16} />
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <footer className="templates-footer">
        © 2026 NexaReach · Empowering communication for everyone.
      </footer>
    </main>
  );
}

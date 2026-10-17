
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Megaphone,
  Plus,
  RefreshCw,
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  Layers,
  FileText,
} from "lucide-react";
import api from "../services/api";
import "./Campaigns.css";

export default function Campaigns() {
  const navigate = useNavigate();

  const [campaigns, setCampaigns] = useState([]);
  const [segments, setSegments] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [form, setForm] = useState({
    name: "",
    objective: "",
    segment_id: "",
    template_id: "",
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [campaignResponse, segmentResponse, templateResponse] =
        await Promise.all([
          api.get("/campaigns"),
          api.get("/segments"),
          api.get("/templates"),
        ]);

      const campaignData = campaignResponse.data;
      const segmentData = segmentResponse.data;
      const templateData = templateResponse.data;

      setCampaigns(
        Array.isArray(campaignData)
          ? campaignData
          : campaignData.items || []
      );

      setSegments(
        Array.isArray(segmentData) ? segmentData : segmentData.items || []
      );

      setTemplates(
        Array.isArray(templateData) ? templateData : templateData.items || []
      );
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Unable to load campaigns, segments, or templates. Check that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!sessionStorage.getItem("access_token")) {
      navigate("/login", { replace: true });
      return;
    }

    loadData();
  }, [navigate, loadData]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");

    try {
      const payload = {
        name: form.name.trim(),
        objective: form.objective.trim(),
      };

      if (form.segment_id) {
        payload.segment_id = Number(form.segment_id);
      }

      await api.post("/campaigns", payload);

      setForm({
        name: "",
        objective: "",
        segment_id: "",
        template_id: "",
      });

      setNotice(
        form.template_id
          ? "Campaign created! The selected template is not yet linked automatically to the campaign by the current backend."
          : "Campaign created successfully!"
      );

      await loadData();
    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : typeof detail === "string"
            ? detail
            : "Could not create campaign. Check the required fields and backend response."
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="campaigns-page">
      <header className="campaigns-topbar">
        <div>
          <span className="campaigns-breadcrumb">
            Workspace / Campaigns
          </span>
          <h1>
            <Megaphone size={25} /> Campaign Management
          </h1>
          <p>Create and organize your public awareness initiatives.</p>
        </div>

        <button
          type="button"
          className="campaigns-secondary-btn"
          onClick={() => navigate("/dashboard")}
        >
          <ArrowLeft size={16} /> Dashboard
        </button>
      </header>

      <section className="campaigns-banner">
        <div>
          <span className="campaigns-eyebrow">
            <Megaphone size={15} /> CAMPAIGN WORKSPACE
          </span>
          <h2>
            Turn important messages
            <br />
            <span>into real-world impact.</span>
          </h2>
          <p>
            Plan public awareness campaigns and organize your communication
            activities.
          </p>
        </div>

        <div className="campaigns-banner-icon">
          <Megaphone size={55} strokeWidth={1.4} />
        </div>
      </section>

      <section className="campaigns-panel">
        <div className="campaigns-panel-heading">
          <div>
            <h2>
              <Plus size={19} /> Create a campaign
            </h2>
            <p>Choose a campaign name, objective, audience segment, and template.</p>
          </div>
        </div>

        <form className="campaigns-form" onSubmit={handleSubmit}>
          <label>
            Campaign name *
            <input
              value={form.name}
              onChange={(event) =>
                setForm({ ...form, name: event.target.value })
              }
              placeholder="e.g. Community Health Awareness"
              minLength={2}
              maxLength={150}
              required
            />
          </label>

          <label>
            Campaign objective *
            <textarea
              value={form.objective}
              onChange={(event) =>
                setForm({ ...form, objective: event.target.value })
              }
              placeholder="Describe the goal and intended audience..."
              rows={4}
              required
            />
          </label>

          <label>
            <Layers size={14} /> Audience segment
            <select
              value={form.segment_id}
              onChange={(event) =>
                setForm({ ...form, segment_id: event.target.value })
              }
            >
              <option value="">All audience / No segment selected</option>
              {segments.map((segment) => (
                <option key={segment.id} value={segment.id}>
                  {segment.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            <FileText size={14} /> Message template
            <select
              value={form.template_id}
              onChange={(event) =>
                setForm({ ...form, template_id: event.target.value })
              }
            >
              <option value="">Choose a template (optional)</option>
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name} — {template.language || "English"} (
                  {template.channel || "General"})
                </option>
              ))}
            </select>
            <small>
              The selected template is for reference. Automatic template
              association requires a backend workflow change.
            </small>
          </label>

          {error && (
            <p className="campaigns-error" role="alert">
              {String(error)}
            </p>
          )}

          {notice && (
            <p role="status" className="campaigns-success">
              {notice}
            </p>
          )}

          <button
            type="submit"
            className="campaigns-primary-btn"
            disabled={saving}
          >
            <Plus size={17} />
            {saving ? "Creating..." : "Create campaign"}
          </button>
        </form>
      </section>

      <section className="campaigns-panel">
        <div className="campaigns-list-heading">
          <div>
            <h2>Your campaigns</h2>
            <p>Review the campaigns saved in your workspace.</p>
          </div>

          <button
            type="button"
            className="campaigns-secondary-btn"
            onClick={loadData}
            disabled={loading}
          >
            <RefreshCw size={15} /> Refresh
          </button>
        </div>

        {loading ? (
          <p className="campaigns-empty">Loading workspace data...</p>
        ) : campaigns.length === 0 ? (
          <div className="campaigns-empty">
            <Megaphone size={30} />
            <p>
              {error ||
                "No campaigns yet. Create your first campaign above."}
            </p>
          </div>
        ) : (
          <div className="campaigns-grid">
            {campaigns.map((campaign) => (
              <article className="campaign-card" key={campaign.id}>
                <div className="campaign-card-top">
                  <span className="campaign-card-icon">
                    <Megaphone size={20} />
                  </span>
                  <span className="campaign-status">
                    {campaign.status || "Draft"}
                  </span>
                </div>

                <h3>{campaign.name}</h3>
                <p>{campaign.objective || "No objective provided."}</p>

                {campaign.segment_id && (
                  <p>
                    <Layers size={14} /> Segment #{campaign.segment_id}
                  </p>
                )}

                <div className="campaign-card-bottom">
                  <span>
                    <CalendarDays size={14} /> Campaign #{campaign.id}
                  </span>
                  <ArrowUpRight size={17} />
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <footer className="campaigns-footer">
        © 2026 NexaReach · Empowering communication for everyone.
      </footer>
    </main>
  );
}

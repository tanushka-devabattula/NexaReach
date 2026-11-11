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
  Pencil,
  Trash2,
  X,
  Copy,
  Search,
} from "lucide-react";
import api from "../services/api";
import "./Campaigns.css";

function formatScheduleDate(value) {
  if (!value) return "?";
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value);
  const date = new Date(hasTimezone ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function toLocalDateTimeInput(value) {
  if (!value) return "";
  const hasTimezone = /(?:Z|[+-]\\d{2}:\\d{2})$/i.test(value);
  const date = new Date(hasTimezone ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}

export default function Campaigns() {
  const navigate = useNavigate();

  const [campaigns, setCampaigns] = useState([]);
  const [segments, setSegments] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
const [statusFilter, setStatusFilter] = useState("all");

  const [form, setForm] = useState({
    name: "",
    objective: "",
    segment_id: "",
    template_id: "",
    scheduled_at: "",
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
        Array.isArray(campaignData) ? campaignData : campaignData.items || [],
      );

      setSegments(
        Array.isArray(segmentData) ? segmentData : segmentData.items || [],
      );

      setTemplates(
        Array.isArray(templateData) ? templateData : templateData.items || [],
      );
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Unable to load campaigns, segments, or templates. Check that the backend is running.",
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

      if (form.scheduled_at) {
        const scheduledDate = new Date(form.scheduled_at);
        if (Number.isNaN(scheduledDate.getTime())) {
          throw new Error("Please select a valid schedule date and time.");
        }
        payload.scheduled_at = scheduledDate.toISOString();
      }

      if (form.segment_id) {
        payload.segment_id = Number(form.segment_id);
      }

      if (form.template_id) {
        payload.template_id = Number(form.template_id);
      }

      const wasEditing = Boolean(editingId);
      if (wasEditing) {
        payload.segment_id = form.segment_id ? Number(form.segment_id) : null;
        payload.template_id = form.template_id ? Number(form.template_id) : null;
        payload.scheduled_at = form.scheduled_at
          ? new Date(form.scheduled_at).toISOString()
          : null;
        await api.patch(`/campaigns/${editingId}`, payload);
      } else {
        await api.post("/campaigns", payload);
      }

      setForm({
        name: "",
        objective: "",
        segment_id: "",
        template_id: "",
        scheduled_at: "",
      });
      setEditingId(null);

      setNotice(
        wasEditing
          ? "Campaign updated successfully."
          : form.scheduled_at
            ? "Campaign created and scheduled. Ensure approved content is available before the scheduled time."
            : form.template_id
              ? "Campaign created and a draft copy of the selected template was added for approval."
              : "Campaign created successfully!",
      );

      await loadData();
    } catch (err) {
      const detail = err.response?.data?.detail;

      setError(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : typeof detail === "string"
            ? detail
            : "Could not create campaign. Check the required fields and backend response.",
      );
    } finally {
      setSaving(false);
    }
  };

  function handleEdit(campaign) {
    setEditingId(campaign.id);
    setForm({
      name: campaign.name || "",
      objective: campaign.objective || "",
      segment_id: campaign.segment_id ? String(campaign.segment_id) : "",
      template_id: campaign.template_id ? String(campaign.template_id) : "",
      scheduled_at: toLocalDateTimeInput(campaign.scheduled_at),
    });
    setError("");
    setNotice("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleDelete(campaign) {
    if (!window.confirm(`Delete campaign "${campaign.name}"?`)) return;
    setError("");
    setNotice("");

    try {
      await api.delete(`/campaigns/${campaign.id}`);
      if (editingId === campaign.id) {
        setEditingId(null);
        setForm({
          name: "",
          objective: "",
          segment_id: "",
          template_id: "",
          scheduled_at: "",
        });
      }
      setNotice("Campaign deleted successfully.");
      await loadData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string" ? detail : "Unable to delete this campaign."
      );
    }
  }
  async function handleClone(campaign) {
  if (!window.confirm(`Clone "${campaign.name}" as a draft?`)) return;

  setError("");
  setNotice("");

  try {
    const response = await api.post(
      `/campaigns/${campaign.id}/clone`
    );

    setNotice(
      `Campaign cloned successfully: ${response.data.name}`
    );

    await loadData();
  } catch (err) {
    setError(
      err.response?.data?.detail || "Unable to clone campaign."
    );
  }
}
const filteredCampaigns = campaigns.filter((campaign) => {
  const matchesSearch = (campaign.name || "")
    .toLowerCase()
    .includes(searchTerm.toLowerCase());

  const matchesStatus =
    statusFilter === "all" ||
    (campaign.status || "draft").toLowerCase() === statusFilter;

  return matchesSearch && matchesStatus;
});
  return (
    <main className="campaigns-page">
      <header className="campaigns-topbar">
        <div>
          <span className="campaigns-breadcrumb">Workspace / Campaigns</span>
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
              <Plus size={19} /> {editingId ? `Edit campaign #${editingId}` : "Create a campaign"}
            </h2>
            <p>
              Choose a campaign name, objective, audience segment, and template.
            </p>
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
            <CalendarDays size={14} /> Schedule delivery (optional)
            <input
              type="datetime-local"
              value={form.scheduled_at}
              onChange={(event) =>
                setForm({ ...form, scheduled_at: event.target.value })
              }
            />
            <small>
              Leave empty to create an unscheduled campaign. A scheduled
              campaign needs approved content before its scheduled time.
            </small>
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
              The selected template is linked to this campaign and copied
              into campaign content as a draft for review and approval.
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

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <button
              type="submit"
              className="campaigns-primary-btn"
              disabled={saving}
            >
              {editingId ? <Pencil size={16} /> : <Plus size={17} />}
              {saving ? "Saving..." : editingId ? "Update campaign" : "Create campaign"}
            </button>
            {editingId && (
              <button
                type="button"
                className="campaigns-secondary-btn"
                onClick={() => {
                  setEditingId(null);
                  setForm({
                    name: "",
                    objective: "",
                    segment_id: "",
                    template_id: "",
                    scheduled_at: "",
                  });
                  setError("");
                  setNotice("");
                }}
              >
                <X size={15} /> Cancel edit
              </button>
            )}
          </div>
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
          <div className="campaigns-toolbar">
  <div className="campaigns-search">
    <Search size={17} />
    <input
      type="search"
      placeholder="Search campaigns by name..."
      value={searchTerm}
      onChange={(event) => setSearchTerm(event.target.value)}
    />
  </div>

  <select
    className="campaigns-status-filter"
    value={statusFilter}
    onChange={(event) => setStatusFilter(event.target.value)}
    aria-label="Filter campaigns by status"
  >
    <option value="all">All statuses</option>
    <option value="draft">Draft</option>
    <option value="scheduled">Scheduled</option>
    <option value="active">Active</option>
    <option value="completed">Completed</option>
    <option value="failed">Failed</option>
  </select>
</div>
        {loading ? (
          <p className="campaigns-empty">Loading workspace data...</p>
        ) : campaigns.length === 0 ? (
  <div className="campaigns-empty">
    <Megaphone size={30} />
    <p>
      {error || "No campaigns yet. Create your first campaign above."}
    </p>
  </div>
) : filteredCampaigns.length === 0 ? (
  <p className="campaigns-empty">
    No campaigns match your search or selected status.
  </p>
) : (
  <div className="campaigns-grid">
    {filteredCampaigns.map((campaign) => (
              <article
  className="campaign-card"
  key={campaign.id}
>
                <div className="campaign-card-top">
                  <span className="campaign-card-icon">
                    <Megaphone size={20} />
                  </span>
                  <span className="campaign-status">
                    {campaign.status || "Draft"}
                  </span>
                  <button
                    style={{
                      marginTop: "10px",
                      padding: "6px 12px",
                      background: "#7c3aed",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      cursor: "pointer",
                    }}
                    onClick={async (e) => {
                      e.stopPropagation();
                      try {
                        const res = await api.post(
                          `/campaigns/${campaign.id}/send`,
                        );
                        alert(
                          `Campaign Dispatched Successfully!\nTotal audience: ${res.data.total_audience_considered || 0}`,
                        );
                      } catch (err) {
                        alert(
                          `Dispatch failed: ${err.response?.data?.detail || err.message}`,
                        );
                      }
                    }}
                  >
                    Send Campaign
                  </button>
                </div>

                <h3>{campaign.name}</h3>
                <p>{campaign.objective || "No objective provided."}</p>

                {campaign.scheduled_at && (
                  <div className="campaign-schedule-details">
                    <p>
                      <CalendarDays size={14} /> Scheduled:
                      {" "}{formatScheduleDate(campaign.scheduled_at)}
                    </p>
                    <p>
                      Scheduler status: {campaign.schedule_status || "scheduled"}
                    </p>
                    <p>
                      Retry attempts: {campaign.retry_count ?? 0}
                      {" / "}{campaign.max_retries ?? 3}
                    </p>
                    {campaign.next_retry_at && (
                      <p>
                        Next retry: {formatScheduleDate(campaign.next_retry_at)}
                      </p>
                    )}
                  </div>
                )}

                {campaign.segment_id && (
                  <p>
                    <Layers size={14} /> Segment #{campaign.segment_id}
                  </p>
                )}

                {campaign.template_id && (
                  <p><FileText size={14} /> Template #{campaign.template_id}</p>
                )}

                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "12px" }}>
                  <button
                    type="button"
                    className="campaigns-secondary-btn"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleEdit(campaign);
                    }}
                  >
                    <Pencil size={14} /> Edit
                  </button>
                  <button
  type="button"
  className="campaigns-secondary-btn"
  onClick={(event) => {
    event.stopPropagation();
    handleClone(campaign);
  }}
>
  <Copy size={14} /> Clone
</button>
                  <button
                    type="button"
                    className="campaigns-secondary-btn"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleDelete(campaign);
                    }}
                  >
                    <Trash2 size={14} /> Delete
                  </button>
                </div>

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

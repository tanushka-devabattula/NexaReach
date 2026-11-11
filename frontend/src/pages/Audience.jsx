
import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users, Plus, RefreshCw, ArrowLeft, Search, Globe2,
  Pencil, Trash2, Upload, ChevronLeft, ChevronRight, X
} from "lucide-react";
import api from "../services/api";
import "./Audience.css";

const languages = [
  "English", "Telugu", "Hindi", "Tamil", "Kannada",
  "Malayalam", "Marathi", "Bengali", "Gujarati",
  "Punjabi", "Odia"
];

const emptyForm = {
  full_name: "",
  email: "",
  phone: "",
  age: "",
  gender: "",
  city: "",
  state: "",
  occupation: "",
  department: "",
  preferred_language: "English",
  preferred_channel: "",
  consent: false
};

export default function Audience() {
  const navigate = useNavigate();

  const [members, setMembers] = useState([]);
  const [stats, setStats] = useState({});
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [languageFilter, setLanguageFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  const loadMembers = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/audience", {
        params: {
          page,
          page_size: 10,
          search: search || undefined,
          language: languageFilter || undefined
        }
      });

      const data = response.data;
      setMembers(data.items || []);
      setTotal(data.total || 0);
      setPages(Math.max(data.pages || 1, 1));
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to load audience.");
    } finally {
      setLoading(false);
    }
  }, [page, search, languageFilter]);

  const loadStats = async () => {
    try {
      const response = await api.get("/audience/stats");
      setStats(response.data || {});
    } catch {
      // Statistics are optional if this request fails.
    }
  };

  useEffect(() => {
    if (!sessionStorage.getItem("access_token")) {
      navigate("/login", { replace: true });
      return;
    }
    loadStats();
  }, [navigate]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const updateField = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value
    }));
  };

  const resetForm = () => {
    setForm(emptyForm);
    setEditingId(null);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");

    const payload = {
      ...form,
      full_name: form.full_name.trim(),
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      age: form.age === "" ? null : Number(form.age)
    };

    try {
      if (editingId) {
        await api.patch(`/audience/${editingId}`, payload);
        alert("Audience member updated successfully.");
      } else {
        await api.post("/audience", payload);
        alert("Audience member added successfully.");
      }

      resetForm();
      await loadMembers();
      await loadStats();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : typeof detail === "string"
            ? detail
            : "Unable to save audience member."
      );
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (member) => {
    setEditingId(member.id);
    setForm({
      full_name: member.full_name || "",
      email: member.email || "",
      phone: member.phone || "",
      age: member.age ?? "",
      gender: member.gender || "",
      city: member.city || "",
      state: member.state || "",
      occupation: member.occupation || "",
      department: member.department || "",
      preferred_language: member.preferred_language || "English",
      preferred_channel: member.preferred_channel || "",
      consent: Boolean(member.consent)
    });

    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleDelete = async (member) => {
    if (!window.confirm(`Delete ${member.full_name}?`)) return;

    try {
      await api.delete(`/audience/${member.id}`);
      await loadMembers();
      await loadStats();
      alert("Audience member deleted.");
    } catch (err) {
      const detail = err.response?.data?.detail;
      alert(typeof detail === "string" ? detail : "Unable to delete member.");
    }
  };

  const handleBulkUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const allowed = /\.(csv|xlsx)$/i.test(file.name);
    if (!allowed) {
      alert("Please select a CSV or XLSX file.");
      event.target.value = "";
      return;
    }

    const data = new FormData();
    data.append("file", file);

    setUploading(true);
    setUploadResult(null);
    setError("");

    try {
      const response = await api.post("/audience/bulk", data);
      setUploadResult(response.data);
      await loadMembers();
      await loadStats();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Bulk upload failed.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  return (
    <div className="audience-page">
      <header className="audience-topbar">
        <div>
          <span className="audience-breadcrumb">Workspace / Audience</span>
          <h1><Users size={25} /> Audience Management</h1>
          <p>Organize your audience and reach communities effectively.</p>
        </div>
        <button className="audience-back" onClick={() => navigate("/dashboard")}>
          <ArrowLeft size={16} /> Dashboard
        </button>
      </header>

      <section className="audience-banner">
        <div>
          <span className="audience-eyebrow">
            <Globe2 size={15} /> COMMUNITY MANAGEMENT
          </span>
          <h2>Know your audience.<br /><span>Amplify your impact.</span></h2>
          <p>Manage contact details, preferences and audience information.</p>
        </div>
        <div className="audience-banner-icon">
          <Users size={58} strokeWidth={1.4} />
        </div>
      </section>

      <section className="audience-stats">
        <article className="audience-stat-card">
          <span className="audience-stat-icon"><Users size={21} /></span>
          <p>Total audience members</p>
          <h3>{stats.total ?? total}</h3>
        </article>
        <article className="audience-stat-card">
          <span className="audience-stat-icon language"><Globe2 size={21} /></span>
          <p>Languages represented</p>
          <h3>{stats.languages_count ?? "—"}</h3>
        </article>
      </section>

      <section className="audience-panel" id="audience-form">
        <div className="audience-panel-heading">
          <div>
            <h2>
              {editingId ? <Pencil size={19} /> : <Plus size={19} />}
              {editingId ? "Edit audience member" : "Add audience member"}
            </h2>
            <p>Provide at least an email address or phone number.</p>
          </div>
          {editingId && (
            <button className="audience-refresh-btn" type="button" onClick={resetForm}>
              <X size={15} /> Cancel edit
            </button>
          )}
        </div>

        <form className="audience-form" onSubmit={handleSubmit}>
          <label>Full name *
            <input name="full_name" value={form.full_name}
              onChange={updateField} required minLength={2}
              placeholder="Enter full name" />
          </label>

          <label>Email address
            <input name="email" type="email" value={form.email}
              onChange={updateField} placeholder="person@example.com" />
          </label>

          <label>Phone number
            <input name="phone" type="tel" value={form.phone}
              onChange={updateField} placeholder="Phone number" />
          </label>

          <label>Age
            <input name="age" type="number" min="0" max="120"
              value={form.age} onChange={updateField} />
          </label>

          <label>Gender
            <select name="gender" value={form.gender} onChange={updateField}>
              <option value="">Select gender</option>
              <option>Male</option>
              <option>Female</option>
              <option>Other</option>
            </select>
          </label>

          <label>City
            <input name="city" value={form.city} onChange={updateField} />
          </label>

          <label>State
            <input name="state" value={form.state} onChange={updateField} />
          </label>

          <label>Occupation
            <input name="occupation" value={form.occupation} onChange={updateField} />
          </label>

          <label>Department
            <input name="department" value={form.department} onChange={updateField} />
          </label>

          <label>Preferred language
            <select name="preferred_language" value={form.preferred_language}
              onChange={updateField}>
              {languages.map((language) => (
                <option key={language}>{language}</option>
              ))}
            </select>
          </label>

          <label>Preferred channel
            <select name="preferred_channel" value={form.preferred_channel}
              onChange={updateField}>
              <option value="">Select channel</option>
              <option value="WHATSAPP">WhatsApp</option>
              <option value="SMS">SMS</option>
              <option value="EMAIL">Email</option>
              <option value="PUSH">Push notification</option>
            </select>
          </label>

          <label className="audience-consent">
            <input type="checkbox" name="consent" checked={form.consent}
              onChange={updateField} />
            Consent received
          </label>

          <button className="audience-primary-btn" type="submit" disabled={saving}>
            {editingId ? <Pencil size={16} /> : <Plus size={17} />}
            {saving ? "Saving..." : editingId ? "Update member" : "Add member"}
          </button>
        </form>

        {error && <p className="audience-error" role="alert">{String(error)}</p>}
      </section>

      <section className="audience-panel">
        <div className="audience-list-heading">
          <div>
            <h2>Audience directory</h2>
            <p>{total} saved audience members</p>
          </div>
          <button className="audience-refresh-btn"
            onClick={() => { loadMembers(); loadStats(); }} disabled={loading}>
            <RefreshCw size={15} /> Refresh
          </button>
        </div>

        <div className="audience-toolbar">
          <div className="audience-search">
            <Search size={17} />
            <input value={search}
              onChange={(e) => { setPage(1); setSearch(e.target.value); }}
              placeholder="Search name, email, phone, city..." />
          </div>

          <select className="audience-filter" value={languageFilter}
            onChange={(e) => { setPage(1); setLanguageFilter(e.target.value); }}>
            <option value="">All languages</option>
            {languages.map((language) => (
              <option key={language}>{language}</option>
            ))}
          </select>

          <label className="audience-upload-btn">
            <Upload size={15} /> {uploading ? "Uploading..." : "Bulk upload"}
            <input type="file" accept=".csv,.xlsx"
              onChange={handleBulkUpload} disabled={uploading} hidden />
          </label>
        </div>

        {uploadResult && (
          <div className="audience-upload-result">
            <strong>Upload result:</strong> {uploadResult.added} added,
            {" "}{uploadResult.failed} failed out of {uploadResult.total_rows}.
            {uploadResult.errors?.length > 0 && (
              <ul>
                {uploadResult.errors.map((item, index) => (
                  <li key={index}>Row {item.row}: {item.reason}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {loading ? (
          <p className="audience-empty">Loading audience members...</p>
        ) : members.length === 0 ? (
          <p className="audience-empty">
            {search || languageFilter
              ? "No matching audience members."
              : "No audience members yet. Add your first member above."}
          </p>
        ) : (
          <div className="audience-table-wrap">
            <table className="audience-table">
              <thead>
                <tr>
                  <th>Member</th><th>Email</th><th>Phone</th>
                  <th>City</th><th>Language</th><th>Consent</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id}>
                    <td>
                      <div className="audience-member-name">
                        <span>{(member.full_name || "?").charAt(0).toUpperCase()}</span>
                        {member.full_name}
                      </div>
                    </td>
                    <td>{member.email || "—"}</td>
                    <td>{member.phone || "—"}</td>
                    <td>{member.city || "—"}</td>
                    <td><span className="audience-language">
                      {member.preferred_language || "English"}
                    </span></td>
                    <td>{member.consent ? "Yes" : "No"}</td>
                    <td>
                      <div className="audience-actions">
                        <button title="Edit" onClick={() => handleEdit(member)}>
                          <Pencil size={15} />
                        </button>
                        <button title="Delete" onClick={() => handleDelete(member)}>
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="audience-pagination">
          <span>Page {page} of {pages} · {total} members</span>
          <div>
            <button disabled={page <= 1 || loading}
              onClick={() => setPage((p) => p - 1)}>
              <ChevronLeft size={16} /> Previous
            </button>
            <button disabled={page >= pages || loading}
              onClick={() => setPage((p) => p + 1)}>
              Next <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </section>

      <footer className="audience-footer">
        © 2026 NexaReach · Empowering communication for everyone.
      </footer>
    </div>
  );
}

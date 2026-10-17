
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users,
  Plus,
  RefreshCw,
  ArrowLeft,
  Search,
  Globe2,
} from "lucide-react";
import api from "../services/api";
import "./Audience.css";

export default function Audience() {
  const navigate = useNavigate();
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    preferred_language: "English",
  });

  const loadMembers = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api.get("/audience");
      const data = response.data;
      setMembers(Array.isArray(data) ? data : data.items || []);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Unable to load audience members."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!sessionStorage.getItem("access_token")) {
      navigate("/login", { replace: true });
      return;
    }

    loadMembers();
  }, [navigate]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");

    try {
      await api.post("/audience", {
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || null,
        preferred_language: form.preferred_language,
      });

      setForm({
        full_name: "",
        email: "",
        phone: "",
        preferred_language: "English",
      });

      await loadMembers();
      alert("Audience member added successfully!");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : typeof detail === "string"
            ? detail
            : "Could not add member. Please check the entered details."
      );
    } finally {
      setSaving(false);
    }
  };

  const filteredMembers = members.filter((member) => {
    const query = search.toLowerCase();
    return (
      (member.full_name || "").toLowerCase().includes(query) ||
      (member.email || "").toLowerCase().includes(query) ||
      (member.preferred_language || "").toLowerCase().includes(query)
    );
  });

  return (
    <div className="audience-page">
      <header className="audience-topbar">
        <div>
          <span className="audience-breadcrumb">Workspace / Audience</span>
          <h1><Users size={25} /> Audience Management</h1>
          <p>Organize your audience and reach communities effectively.</p>
        </div>

        <button
          className="audience-back"
          onClick={() => navigate("/dashboard")}
        >
          <ArrowLeft size={16} /> Dashboard
        </button>
      </header>

      <section className="audience-banner">
        <div>
          <span className="audience-eyebrow">
            <Globe2 size={15} /> COMMUNITY MANAGEMENT
          </span>
          <h2>Know your audience.<br /><span>Amplify your impact.</span></h2>
          <p>Keep audience contact details and language preferences organized.</p>
        </div>

        <div className="audience-banner-icon">
          <Users size={58} strokeWidth={1.4} />
        </div>
      </section>

      <section className="audience-stats">
        <article className="audience-stat-card">
          <span className="audience-stat-icon"><Users size={21} /></span>
          <p>Total audience members</p>
          <h3>{members.length}</h3>
        </article>

        <article className="audience-stat-card">
          <span className="audience-stat-icon language"><Globe2 size={21} /></span>
          <p>Languages represented</p>
          <h3>
            {new Set(members.map((m) => m.preferred_language || "English")).size}
          </h3>
        </article>
      </section>

      <section className="audience-panel">
        <div className="audience-panel-heading">
          <div>
            <h2><Plus size={19} /> Add audience member</h2>
            <p>Enter the contact details below.</p>
          </div>
        </div>

        <form className="audience-form" onSubmit={handleSubmit}>
          <label>
            Full name *
            <input
              value={form.full_name}
              onChange={(e) =>
                setForm({ ...form, full_name: e.target.value })
              }
              placeholder="Enter full name"
              minLength={2}
              maxLength={150}
              required
            />
          </label>

          <label>
            Email address *
            <input
              type="email"
              value={form.email}
              onChange={(e) =>
                setForm({ ...form, email: e.target.value })
              }
              placeholder="person@example.com"
              required
            />
          </label>

          <label>
            Phone number
            <input
              type="tel"
              value={form.phone}
              onChange={(e) =>
                setForm({ ...form, phone: e.target.value })
              }
              placeholder="Optional phone number"
              maxLength={20}
            />
          </label>

          <label>
            Preferred language
            <select
              value={form.preferred_language}
              onChange={(e) =>
                setForm({ ...form, preferred_language: e.target.value })
              }
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

          <button className="audience-primary-btn" type="submit" disabled={saving}>
            <Plus size={17} /> {saving ? "Adding member..." : "Add member"}
          </button>
        </form>

        {error && <p className="audience-error" role="alert">{String(error)}</p>}
      </section>

      <section className="audience-panel">
        <div className="audience-list-heading">
          <div>
            <h2>Audience directory</h2>
            <p>View and search your saved audience members.</p>
          </div>

          <button
            className="audience-refresh-btn"
            onClick={loadMembers}
            disabled={loading}
          >
            <RefreshCw size={15} /> Refresh
          </button>
        </div>

        <div className="audience-search">
          <Search size={17} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, email, or language..."
          />
        </div>

        {loading ? (
          <p className="audience-empty">Loading audience members...</p>
        ) : error && members.length === 0 ? (
          <p className="audience-empty">{String(error)}</p>
        ) : filteredMembers.length === 0 ? (
          <p className="audience-empty">
            {search ? "No matching audience members." : "No audience members yet. Add your first member above."}
          </p>
        ) : (
          <div className="audience-table-wrap">
            <table className="audience-table">
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Language</th>
                </tr>
              </thead>
              <tbody>
                {filteredMembers.map((member) => (
                  <tr key={member.id}>
                    <td>
                      <div className="audience-member-name">
                        <span>{(member.full_name || "?").charAt(0).toUpperCase()}</span>
                        {member.full_name}
                      </div>
                    </td>
                    <td>{member.email}</td>
                    <td>{member.phone || "—"}</td>
                    <td>
                      <span className="audience-language">
                        {member.preferred_language || "English"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <footer className="audience-footer">
        © 2026 NexaReach · Empowering communication for everyone.
      </footer>
    </div>
  );
}

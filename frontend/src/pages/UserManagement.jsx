import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, RefreshCw } from "lucide-react";
import api, { getSession } from "../services/api";
import "./UserManagement.css";

const ROLES = [
  { value: "admin", label: "Admin" },
  { value: "campaign_manager", label: "Campaign Manager" },
  { value: "communication_team", label: "Communication Team" },
  { value: "user", label: "User" },
];

const errorText = (err) => {
  const detail = err.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
  return detail || err.message || "Something went wrong.";
};

export default function UserManagement() {
  const navigate = useNavigate();
  const me = getSession().user;
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [message, setMessage] = useState(null); // { type: "ok" | "err", text }

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/admin/users");
      setUsers(res.data);
    } catch (err) {
      setMessage({ type: "err", text: errorText(err) });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const update = async (user, path, body, okText) => {
    setBusyId(user.id);
    setMessage(null);
    try {
      const res = await api.patch(`/admin/users/${user.id}/${path}`, body);
      setUsers((list) => list.map((u) => (u.id === user.id ? res.data : u)));
      setMessage({ type: "ok", text: okText });
    } catch (err) {
      setMessage({ type: "err", text: errorText(err) });
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="um-page">
      <header className="um-top">
        <div>
          <span className="um-crumb">Workspace / User Management</span>
          <h1>User Management</h1>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="um-back" onClick={loadUsers}>
            <RefreshCw size={15} /> Refresh
          </button>
          <button className="um-back" onClick={() => navigate("/dashboard")}>
            <ArrowLeft size={15} /> Dashboard
          </button>
        </div>
      </header>

      {message && (
        <p className={`um-msg ${message.type}`} role="alert">
          {message.text}
        </p>
      )}

      <section className="um-card">
        {loading ? (
          <p>Loading users...</p>
        ) : users.length === 0 ? (
          <p>No users found.</p>
        ) : (
          <table className="um-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isMe = me && me.id === u.id;
                return (
                  <tr key={u.id}>
                    <td>{u.full_name}{isMe ? " (you)" : ""}</td>
                    <td>{u.email}</td>
                    <td>
                      <select
                        className="um-select"
                        value={u.role || "user"}
                        disabled={busyId === u.id || isMe}
                        onChange={(e) =>
                          update(u, "role", { role: e.target.value }, `Role changed for ${u.full_name}.`)
                        }
                      >
                        {ROLES.map((r) => (
                          <option key={r.value} value={r.value}>{r.label}</option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <span className={`um-badge ${u.is_active ? "um-on" : "um-off"}`}>
                        {u.is_active ? "Active" : "Deactivated"}
                      </span>
                    </td>
                    <td>
                      <button
                        className="um-btn"
                        disabled={busyId === u.id || isMe}
                        onClick={() =>
                          update(
                            u,
                            "active",
                            { is_active: !u.is_active },
                            `${u.full_name} is now ${u.is_active ? "deactivated" : "active"}.`
                          )
                        }
                      >
                        {u.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

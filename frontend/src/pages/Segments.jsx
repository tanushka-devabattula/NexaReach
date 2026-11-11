
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users, Plus, RefreshCw, ArrowLeft, Layers,
  Eye, Pencil, Trash2, X, SlidersHorizontal
} from "lucide-react";
import api from "../services/api";
import "./Segments.css";

const FIELDS = [
  { value: "preferred_language", label: "Preferred language" },
  { value: "age", label: "Age" },
  { value: "gender", label: "Gender" },
  { value: "city", label: "City" },
  { value: "state", label: "State" },
  { value: "occupation", label: "Occupation" },
  { value: "department", label: "Department" },
  { value: "preferred_channel", label: "Preferred channel" },
  { value: "consent", label: "Consent" },
];

const OPERATORS = [
  { value: "equals", label: "Equals" },
  { value: "in", label: "Is one of" },
  { value: "greater_than", label: "Greater than" },
  { value: "greater_than_or_equal", label: "At least" },
  { value: "less_than", label: "Less than" },
  { value: "less_than_or_equal", label: "At most" },
  { value: "between", label: "Between" },
];

const EMPTY_RULE = {
  field: "preferred_language",
  operator: "equals",
  value: "",
};

const EMPTY_FORM = {
  name: "",
  description: "",
};

function criteriaToRules(criteria) {
  if (criteria?.rules && Array.isArray(criteria.rules)) {
    return {
      logic: criteria.logic === "OR" ? "OR" : "AND",
      rules: criteria.rules.length
        ? criteria.rules.map((rule) => ({
            field: rule.field || "preferred_language",
            operator: rule.operator || "equals",
            value: Array.isArray(rule.value)
              ? rule.value.join(", ")
              : String(rule.value ?? ""),
          }))
        : [{ ...EMPTY_RULE }],
    };
  }

  if (criteria && typeof criteria === "object") {
    const rules = Object.entries(criteria)
      .filter(([key]) => key !== "logic")
      .map(([field, value]) => ({
        field: field === "language" ? "preferred_language" : field,
        operator: field === "min_age"
          ? "greater_than_or_equal"
          : field === "max_age"
            ? "less_than_or_equal"
            : Array.isArray(value) ? "in" : "equals",
        value: Array.isArray(value)
          ? value.join(", ")
          : String(value ?? ""),
      }));

    return {
      logic: "AND",
      rules: rules.length ? rules : [{ ...EMPTY_RULE }],
    };
  }

  return { logic: "AND", rules: [{ ...EMPTY_RULE }] };
}

function buildCriteria(logic, rules) {
  const validRules = rules
    .filter((rule) => String(rule.value).trim() !== "")
    .map((rule) => {
      let value = rule.value;

      if (rule.operator === "in") {
        value = String(value)
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);
      } else if (rule.field === "consent") {
        value = String(value).toLowerCase() === "true";
      } else if (rule.field === "age") {
        if (rule.operator === "between") {
          value = String(value)
            .split(",")
            .map((item) => Number(item.trim()));
        } else {
          value = Number(value);
        }
      }

      return {
        field: rule.field,
        operator: rule.operator,
        value,
      };
    });

  return { logic, rules: validRules };
}

export default function Segments() {
  const navigate = useNavigate();

  const [segments, setSegments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [editingId, setEditingId] = useState(null);

  const [form, setForm] = useState(EMPTY_FORM);
  const [logic, setLogic] = useState("AND");
  const [rules, setRules] = useState([{ ...EMPTY_RULE }]);

  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(null);
  const [previewError, setPreviewError] = useState("");

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

  function resetForm() {
    setForm(EMPTY_FORM);
    setLogic("AND");
    setRules([{ ...EMPTY_RULE }]);
    setEditingId(null);
    setPreviewData(null);
  }

  function updateRule(index, key, value) {
    setRules((previous) =>
      previous.map((rule, i) =>
        i === index
          ? {
              ...rule,
              [key]: value,
              ...(key === "field" ? { operator: "equals", value: "" } : {}),
            }
          : rule
      )
    );
  }

  function addRule() {
    setRules((previous) => [...previous, { ...EMPTY_RULE }]);
  }

  function removeRule(index) {
    setRules((previous) =>
      previous.length === 1
        ? previous
        : previous.filter((_, i) => i !== index)
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!form.name.trim()) {
      setError("Please enter a segment name.");
      return;
    }

    if (rules.some((rule) => !String(rule.value).trim())) {
      setError("Please complete every targeting rule or remove the empty rule.");
      return;
    }

    const criteria = buildCriteria(logic, rules);

    if (!criteria.rules.length) {
      setError("Add at least one targeting rule.");
      return;
    }

    for (const rule of criteria.rules) {
      if (
        rule.field === "age" &&
        (
          (rule.operator === "between" &&
            (rule.value.length !== 2 || rule.value.some(Number.isNaN))) ||
          (rule.operator !== "between" &&
            !Number.isFinite(rule.value))
        )
      ) {
        setError("Enter a valid age. For Between, enter two numbers separated by a comma.");
        return;
      }

      if (
        rule.field === "age" &&
        rule.operator === "between" &&
        rule.value[0] > rule.value[1]
      ) {
        setError("The minimum age cannot be greater than the maximum age.");
        return;
      }
    }

    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      criteria,
    };

    setSaving(true);

    try {
      if (editingId) {
        await api.patch(`/segments/${editingId}`, payload);
        setSuccess("Segment updated successfully.");
      } else {
        await api.post("/segments", payload);
        setSuccess("Segment created successfully.");
      }

      resetForm();
      await loadSegments();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : typeof detail === "string"
            ? detail
            : "Unable to save segment."
      );
    } finally {
      setSaving(false);
    }
  }

  function handleEdit(segment) {
    const parsed = criteriaToRules(segment.criteria);

    setEditingId(segment.id);
    setForm({
      name: segment.name || "",
      description: segment.description || "",
    });
    setLogic(parsed.logic);
    setRules(parsed.rules);
    setError("");
    setSuccess("");
    setPreviewData(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handlePreview(segmentId) {
    setPreviewLoading(segmentId);
    setPreviewError("");
    setPreviewData(null);

    try {
      const response = await api.get(`/segments/${segmentId}/preview`);
      setPreviewData(response.data);
    } catch (err) {
      setPreviewError(
        err.response?.data?.detail || "Unable to preview this segment."
      );
    } finally {
      setPreviewLoading(null);
    }
  }

  async function handleDelete(segment) {
    if (!window.confirm(`Delete segment "${segment.name}"?`)) return;

    setError("");
    setSuccess("");

    try {
      await api.delete(`/segments/${segment.id}`);
      setSuccess(`Segment "${segment.name}" deleted successfully.`);

      if (previewData?.segment_id === segment.id) {
        setPreviewData(null);
      }

      if (editingId === segment.id) resetForm();

      await loadSegments();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Unable to delete this segment."
      );
    }
  }

  function operatorOptions(field) {
    if (field === "age") return OPERATORS;

    return OPERATORS.filter((operator) =>
      ["equals", "in"].includes(operator.value)
    );
  }

  function valueInput(rule, index) {
    if (rule.field === "consent") {
      return (
        <select
          value={rule.value}
          onChange={(event) =>
            updateRule(index, "value", event.target.value)
          }
          required
        >
          <option value="">Choose consent</option>
          <option value="true">Consented</option>
          <option value="false">Not consented</option>
        </select>
      );
    }

    return (
      <input
        type={rule.field === "age" && rule.operator !== "between" ? "number" : "text"}
        min={rule.field === "age" ? 0 : undefined}
        value={rule.value}
        onChange={(event) =>
          updateRule(index, "value", event.target.value)
        }
        placeholder={
          rule.operator === "between"
            ? "e.g. 18, 40"
            : rule.operator === "in"
              ? "e.g. Telugu, Hindi"
              : rule.field === "age"
                ? "Enter age"
                : "Enter value"
        }
        required
      />
    );
  }

  return (
    <main className="segments-page">
      <header className="segments-header">
        <div>
          <span className="segments-breadcrumb">Workspace / Segments</span>
          <h1><Layers size={25} /> Audience Segments</h1>
          <p>Build targeted audience groups using flexible filtering rules.</p>
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
          <p>Create reusable audience groups for targeted public awareness campaigns.</p>
        </div>
        <div className="segments-hero-icon">
          <Users size={52} />
        </div>
      </section>

      <section className="segments-panel">
        <h2><Plus size={19} /> {editingId ? "Edit segment" : "Create a segment"}</h2>
        <p className="segments-subtitle">
          Add conditions to decide who belongs in this audience.
        </p>

        <form className="segments-form" onSubmit={handleSubmit}>
          <label>
            Segment name *
            <input
              value={form.name}
              onChange={(event) =>
                setForm({ ...form, name: event.target.value })
              }
              placeholder="e.g. Telugu-speaking farmers above 40"
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

          <div className="segment-rule-heading">
            <h3><SlidersHorizontal size={17} /> Targeting rules</h3>
            <span className="segments-hint">Choose how your conditions should match.</span>
          </div>

          <div className="segment-logic-control">
            <span>Match</span>
            <button
              type="button"
              className={logic === "AND" ? "segments-primary" : "segments-secondary"}
              onClick={() => setLogic("AND")}
            >
              ALL rules (AND)
            </button>
            <button
              type="button"
              className={logic === "OR" ? "segments-primary" : "segments-secondary"}
              onClick={() => setLogic("OR")}
            >
              ANY rule (OR)
            </button>
          </div>

          <div className="segment-rules-list">
            {rules.map((rule, index) => (
              <div className="segment-rule-row" key={index}>
                <span className="segment-rule-number">{index + 1}</span>

                <select
                  value={rule.field}
                  onChange={(event) =>
                    updateRule(index, "field", event.target.value)
                  }
                  aria-label="Target field"
                >
                  {FIELDS.map((field) => (
                    <option value={field.value} key={field.value}>
                      {field.label}
                    </option>
                  ))}
                </select>

                <select
                  value={rule.operator}
                  onChange={(event) =>
                    updateRule(index, "operator", event.target.value)
                  }
                  aria-label="Operator"
                >
                  {operatorOptions(rule.field).map((operator) => (
                    <option value={operator.value} key={operator.value}>
                      {operator.label}
                    </option>
                  ))}
                </select>

                {valueInput(rule, index)}

                <button
                  type="button"
                  className="segments-secondary"
                  onClick={() => removeRule(index)}
                  disabled={rules.length === 1}
                  aria-label="Remove rule"
                  title="Remove rule"
                >
                  <X size={16} />
                </button>
              </div>
            ))}
          </div>

          <button
            type="button"
            className="segments-secondary"
            onClick={addRule}
          >
            <Plus size={16} /> Add rule
          </button>

          <p className="segments-hint">
            Example: Preferred language equals Telugu AND age is at least 40.
            For multiple values, separate them with commas.
          </p>

          {error && <p className="segments-error" role="alert">{String(error)}</p>}
          {success && <p className="segments-success" role="status">{success}</p>}

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <button className="segments-primary" type="submit" disabled={saving}>
              <Plus size={17} />
              {saving ? "Saving..." : editingId ? "Update segment" : "Create segment"}
            </button>

            {editingId && (
              <button
                className="segments-secondary"
                type="button"
                onClick={resetForm}
              >
                <X size={16} /> Cancel edit
              </button>
            )}
          </div>
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

                <div style={{
                  display: "flex",
                  gap: "8px",
                  flexWrap: "wrap",
                  marginTop: "14px"
                }}>
                  <button
                    type="button"
                    className="segments-secondary"
                    onClick={() => handlePreview(segment.id)}
                    disabled={previewLoading === segment.id}
                  >
                    <Eye size={14} />
                    {previewLoading === segment.id ? "Previewing..." : "Preview"}
                  </button>

                  <button
                    type="button"
                    className="segments-secondary"
                    onClick={() => handleEdit(segment)}
                  >
                    <Pencil size={14} /> Edit
                  </button>

                  <button
                    type="button"
                    className="segments-secondary"
                    onClick={() => handleDelete(segment)}
                  >
                    <Trash2 size={14} /> Delete
                  </button>
                </div>

                {previewError && previewLoading === null && !previewData && (
                  <p className="segments-error" role="alert">{previewError}</p>
                )}

                {previewData?.segment_id === segment.id && (
                  <div className="segment-preview" style={{
                    marginTop: "14px",
                    padding: "14px",
                    borderRadius: "10px",
                    background: "rgba(124, 58, 237, 0.07)"
                  }}>
                    <strong>Audience preview</strong>
                    <p>Total audience: {previewData.total_audience}</p>
                    <p>Matching members: {previewData.total_matched_members}</p>
                    <p>With consent: {previewData.consented_members}</p>
                    <p>With phone: {previewData.members_with_phone}</p>
                    <p>With email: {previewData.members_with_email}</p>
                    <p>By language:</p>
                    <ul>
                      {Object.entries(previewData.by_language || {}).map(
                        ([language, count]) => (
                          <li key={language}>{language}: {count}</li>
                        )
                      )}
                    </ul>
                  </div>
                )}

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

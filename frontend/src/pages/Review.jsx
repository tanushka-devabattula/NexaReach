import { useCallback, useEffect, useState } from "react";
import api, { getSession } from "../services/api";
import "./Review.css";

const FILTERS = [
  { label: "Pending", value: "pending_review" },
  { label: "Approved", value: "approved" },
  { label: "Rejected", value: "rejected" },
  { label: "Changes requested", value: "changes_requested" },
  { label: "All reviews", value: "all" },
];

export default function Review() {
  const { user } = getSession();
  const canDecide = ["admin", "reviewer", "communication_team"].includes(
    user?.role?.toLowerCase(),
  );

  const [filter, setFilter] = useState("pending_review");
  const [reviews, setReviews] = useState([]);
  const [contents, setContents] = useState({});
  const [notes, setNotes] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [message, setMessage] = useState("");

  const loadReviews = useCallback(async () => {
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const params = filter === "all" ? {} : { status_filter: filter };

      const response = await api.get("/review/list", { params });
      const records = response.data || [];
      setReviews(records);

      const linkedIds = [
        ...new Set(
          records
            .map((review) => review.campaign_content_id)
            .filter((id) => id != null),
        ),
      ];

      const contentResults = await Promise.all(
        linkedIds.map(async (id) => {
          try {
            const result = await api.get(`/campaign-content/${id}`);
            return [id, result.data];
          } catch {
            return [id, null];
          }
        }),
      );

      setContents(Object.fromEntries(contentResults));
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Unable to load reviews. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  const submitDecision = async (reviewId, decision) => {
    setBusyId(reviewId);
    setError("");
    setMessage("");

    try {
      await api.post(`/review/${reviewId}/decision`, {
        decision,
        reviewer_notes: notes[reviewId]?.trim() || null,
      });

      setMessage(`Review #${reviewId}: ${decision.replaceAll("_", " ")}.`);
      await loadReviews();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Unable to submit the review decision.",
      );
    } finally {
      setBusyId(null);
    }
  };

  const formatDate = (value) => {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
  };

  return (
    <main className="review-page">
      <header className="review-header">
        <div>
          <p className="review-eyebrow">QUALITY & COMPLIANCE</p>
          <h1>Content Review</h1>
          <p>Inspect campaign content and record review decisions.</p>
        </div>

        <button
          className="review-refresh"
          onClick={loadReviews}
          disabled={loading}
        >
          {loading ? "Loading..." : "↻ Refresh"}
        </button>
      </header>

      <section className="review-filters">
        {FILTERS.map((item) => (
          <button
            key={item.value}
            className={filter === item.value ? "active" : ""}
            onClick={() => setFilter(item.value)}
          >
            {item.label}
          </button>
        ))}
      </section>

      {message && <div className="review-success">{message}</div>}
      {error && <div className="review-error">{error}</div>}

      {!canDecide && (
        <div className="review-notice">
          You can view reviews, but your role does not have permission to
          approve or reject content.
        </div>
      )}

      {loading ? (
        <div className="review-empty">Loading reviews...</div>
      ) : reviews.length === 0 ? (
        <div className="review-empty">
          <h3>No reviews found</h3>
          <p>There are no records in this review category.</p>
        </div>
      ) : (
        <section className="review-list">
          {reviews.map((review) => {
            const content = contents[review.campaign_content_id];
            const messageText =
              content?.content || review.readability_metrics?.content || null;
            const language =
              content?.language ||
              review.readability_metrics?.language ||
              "Not available";
            const channel =
              content?.channel ||
              review.readability_metrics?.channel ||
              "Not available";
            const isPending = review.status === "pending_review";

            return (
              <article className="review-card" key={review.id}>
                <div className="review-card-header">
                  <div>
                    <h2>Review #{review.id}</h2>
                    <span className="review-meta">
                      Campaign #{review.campaign_id ?? "—"}
                      {" · "}
                      Content #{review.campaign_content_id ?? "—"}
                    </span>
                  </div>

                  <span className={`review-status ${review.status}`}>
                    {review.status?.replaceAll("_", " ")}
                  </span>
                </div>

                <div className="review-score">
                  <span>Compliance score</span>
                  <strong>{review.compliance_score ?? "—"}/100</strong>
                </div>

                <div className="review-details">
                  <p>
                    <strong>Language:</strong> {language}
                  </p>
                  <p>
                    <strong>Channel:</strong> {channel}
                  </p>
                  <p>
                    <strong>Submitted:</strong> {formatDate(review.created_at)}
                  </p>
                  <p>
                    <strong>Reviewed:</strong> {formatDate(review.reviewed_at)}
                  </p>
                </div>

                <div className="review-content">
                  <h3>Message content</h3>
                  {messageText ? (
                    <p>{messageText}</p>
                  ) : (
                    <p className="review-muted">
                      No message content is available for this review.
                    </p>
                  )}
                </div>

                <div className="review-issues">
                  <h3>Compliance findings</h3>
                  {review.compliance_issues?.length ? (
                    <ul>
                      {review.compliance_issues.map((issue, index) => (
                        <li key={index}>
                          {typeof issue === "string"
                            ? issue
                            : issue.message ||
                              issue.description ||
                              JSON.stringify(issue)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="review-muted">
                      No compliance issues recorded.
                    </p>
                  )}
                </div>

                {review.readability_metrics && (
                  <div className="review-metrics">
                    <h3>Readability metrics</h3>
                    <pre>
                      {JSON.stringify(review.readability_metrics, null, 2)}
                    </pre>
                  </div>
                )}

                {review.reviewer_notes && (
                  <div className="review-existing-notes">
                    <strong>Reviewer notes:</strong>
                    <p>{review.reviewer_notes}</p>
                  </div>
                )}

                {canDecide && isPending && (
                  <div className="review-actions">
                    <label htmlFor={`notes-${review.id}`}>Reviewer notes</label>
                    <textarea
                      id={`notes-${review.id}`}
                      value={notes[review.id] || ""}
                      onChange={(event) =>
                        setNotes((previous) => ({
                          ...previous,
                          [review.id]: event.target.value,
                        }))
                      }
                      placeholder="Add feedback or explain the decision..."
                      rows={3}
                    />

                    <div className="review-buttons">
                      <button
                        className="approve"
                        disabled={busyId !== null}
                        onClick={() => submitDecision(review.id, "approved")}
                      >
                        {busyId === review.id ? "Saving..." : "Approve"}
                      </button>

                      <button
                        className="request-changes"
                        disabled={busyId !== null}
                        onClick={() =>
                          submitDecision(review.id, "changes_requested")
                        }
                      >
                        Request changes
                      </button>

                      <button
                        className="reject"
                        disabled={busyId !== null}
                        onClick={() => submitDecision(review.id, "rejected")}
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}

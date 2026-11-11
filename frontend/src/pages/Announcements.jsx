import React, { useEffect, useState } from 'react';
import api from '../services/api';

function Announcements() {
  const [announcements, setAnnouncements] = useState([]);
  const [language, setLanguage] = useState('en');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setError('');
    setLoading(true);

    // 1. Fetch campaigns directly from backend API
    const loadAnnouncements = async () => {
      try {
        const res = await api.get('/campaigns');
        const data = Array.isArray(res.data) ? res.data : (res.data.items || []);
        if (isMounted) {
          setAnnouncements(data);
          setLoading(false);
        }
      } catch (err) {
        // Fallback fetch if api helper uses a relative path
        try {
          const res = await fetch('http://127.0.0.1:8000/campaigns');
          const data = await res.json();
          if (isMounted) {
            setAnnouncements(Array.isArray(data) ? data : (data.items || []));
            setLoading(false);
          }
        } catch (fallbackErr) {
          if (isMounted) {
            setError('Unable to load announcements. Ensure the backend server is running on port 8000.');
            setLoading(false);
          }
        }
      }
    };

    loadAnnouncements();

    // 2. Connect SSE stream using full backend URL
    const streamUrl = `http://127.0.0.1:8000/announcements/stream?lang=${language}`;
    const eventSource = new EventSource(streamUrl);

    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (isMounted) {
          setAnnouncements((prev) => [data, ...prev]);
        }
      } catch (_) {}
    };

    eventSource.onerror = () => {
      // Close stream on idle/error without removing loaded REST announcements
      eventSource.close();
    };

    return () => {
      isMounted = false;
      eventSource.close();
    };
  }, [language]);

  return (
    <main className="announcements-page" style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h2>Public Announcements</h2>
      <div style={{ marginBottom: '1.5rem' }}>
        <label>
          Language:{' '}
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="en">English</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
          </select>
        </label>
      </div>

      {loading && <p>Loading public announcements...</p>}
      {error && <p className="error" style={{ color: 'red' }}>{error}</p>}

      {!loading && announcements.length === 0 && (
        <p>No active public announcements found.</p>
      )}

      <ul style={{ listStyle: 'none', padding: 0 }}>
        {announcements.map((a, i) => (
          <li
            key={a.id || i}
            style={{
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '1.25rem',
              marginBottom: '1rem',
              backgroundColor: '#ffffff',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
            }}
          >
            <h3 style={{ margin: '0 0 0.5rem 0', color: '#2b6cb0' }}>
              {a.name || a.title || 'Public Notice'}
            </h3>
            <p style={{ margin: 0, color: '#4a5568', fontSize: '1rem' }}>
              {a.objective || a.body || a.content || 'Public awareness update.'}
            </p>
            <span style={{ fontSize: '0.8rem', color: '#718096', marginTop: '0.75rem', display: 'block' }}>
              Status: <strong>{a.status || 'approved'}</strong>
            </span>
          </li>
        ))}
      </ul>
    </main>
  );
}

export default Announcements;
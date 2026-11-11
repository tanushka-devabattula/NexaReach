import React, { useState, useEffect } from 'react';
import api from '../services/api';

function ChannelSelector({ campaignId, initialOrder = [] }) {
  const [order, setOrder] = useState(initialOrder);
  const [available, setAvailable] = useState(['whatsapp', 'sms', 'email']);
  const [status, setStatus] = useState('');

  useEffect(() => {
    // On mount, maybe fetch existing order for campaign
    if (campaignId) {
      api.get(`/campaigns/${campaignId}`).then((res) => {
        setOrder(res.data.fallback_order || []);
      }).catch(()=>{});
    }
  }, [campaignId]);

  const toggleChannel = (ch) => {
    setOrder((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );
  };

  const saveOrder = async () => {
    setStatus('Saving...');
    try {
      await api.patch(`/campaigns/${campaignId}`, { fallback_order: order });
      setStatus('Saved');
    } catch (err) {
      setStatus(err.response?.data?.detail || 'Save failed');
    }
  };

  return (
    <div className="channel-selector">
      <h4>Channel Fallback Order</h4>
      {available.map((ch) => (
        <label key={ch} style={{ marginRight: '1rem' }}>
          <input
            type="checkbox"
            checked={order.includes(ch)}
            onChange={() => toggleChannel(ch)}
          />
          {ch}
        </label>
      ))}
      <button type="button" onClick={saveOrder}>Save Order</button>
      {status && <p>{status}</p>}
    </div>
  );
}

export default ChannelSelector;

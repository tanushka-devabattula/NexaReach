import React, { useState } from 'react';
import api from '../services/api';

function ChannelSettings() {
  const [whatsappConfig, setWhatsappConfig] = useState({
    providerUrl: '',
    apiKey: '',
    templateId: '',
  });
  const [pushConfig, setPushConfig] = useState({
    firebaseServerKey: '',
    enabled: false,
  });
  const [status, setStatus] = useState('');

  const handleChange = (setter) => (e) => {
    const { name, value, type, checked } = e.target;
    setter((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const testConnection = async (type) => {
    setStatus('Testing...');
    try {
      const endpoint = type === 'whatsapp' ? '/whatsapp/test' : '/push/test';
      const payload = type === 'whatsapp' ? whatsappConfig : pushConfig;
      await api.post(endpoint, payload);
      setStatus('Success! Connection works.');
    } catch (err) {
      setStatus(
        err.response?.data?.detail || 'Connection test failed. Check configuration.'
      );
    }
  };

  const saveSettings = async () => {
    setStatus('Saving...');
    try {
      await api.post('/settings/channel', {
        whatsapp: whatsappConfig,
        push: pushConfig,
      });
      setStatus('Settings saved.');
    } catch (err) {
      setStatus('Save failed: ' + (err.response?.data?.detail || 'Unknown error'));
    }
  };

  return (
    <main className="channel-settings-page">
      <h2>Channel Settings</h2>
      <section>
        <h3>WhatsApp</h3>
        <label>
          Provider URL:
          <input
            name="providerUrl"
            value={whatsappConfig.providerUrl}
            onChange={handleChange(setWhatsappConfig)}
            placeholder="https://example.com"
          />
        </label>
        <label>
          API Key:
          <input
            name="apiKey"
            value={whatsappConfig.apiKey}
            onChange={handleChange(setWhatsappConfig)}
          />
        </label>
        <label>
          Template ID:
          <input
            name="templateId"
            value={whatsappConfig.templateId}
            onChange={handleChange(setWhatsappConfig)}
          />
        </label>
        <button type="button" onClick={() => testConnection('whatsapp')}>
          Test WhatsApp Connection
        </button>
      </section>
      <section>
        <h3>Push Notifications</h3>
        <label>
          Firebase Server Key:
          <input
            name="firebaseServerKey"
            type="password"
            value={pushConfig.firebaseServerKey}
            onChange={handleChange(setPushConfig)}
          />
        </label>
        <label>
          Enabled:
          <input
            name="enabled"
            type="checkbox"
            checked={pushConfig.enabled}
            onChange={handleChange(setPushConfig)}
          />
        </label>
        <button type="button" onClick={() => testConnection('push')}>
          Test Push Notification
        </button>
      </section>
      <button type="button" onClick={saveSettings}>
        Save Settings
      </button>
      {status && <p>{status}</p>}
    </main>
  );
}

export default ChannelSettings;

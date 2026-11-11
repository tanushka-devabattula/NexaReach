import React, { useEffect, useState } from 'react';
import api from '../services/api';

function PushPermission() {
  const [permission, setPermission] = useState(Notification?.permission || 'default');
  const [status, setStatus] = useState('');

  const requestPermission = async () => {
    if (!('Notification' in window)) {
      setStatus('This browser does not support notifications.');
      return;
    }
    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      if (result === 'granted') {
        // Register token with backend (placeholder token generation)
        const token = 'dummy-browser-token-' + Date.now();
        await api.post('/push/register', { token, platform: 'web' });
        setStatus('Push token registered.');
      } else {
        setStatus('Permission denied.');
      }
    } catch (err) {
      setStatus('Error registering push token.');
    }
  };

  const unregister = async () => {
    try {
      await api.post('/push/unregister', { token: 'dummy-browser-token' });
      setStatus('Push token unregistered.');
    } catch (err) {
      setStatus('Error unregistering token.');
    }
  };

  useEffect(() => {
    // Update permission state on mount
    setPermission(Notification?.permission || 'default');
  }, []);

  return (
    <div className="push-permission">
      <p>Notification permission: {permission}</p>
      {permission !== 'granted' && (
        <button type="button" onClick={requestPermission}>
          Request Permission
        </button>
      )}
      {permission === 'granted' && (
        <button type="button" onClick={unregister}>
          Unregister Push
        </button>
      )}
      {status && <p>{status}</p>}
    </div>
  );
}

export default PushPermission;

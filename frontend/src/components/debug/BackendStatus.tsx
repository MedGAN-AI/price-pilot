import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';

const BackendStatus: React.FC = () => {
  const [status, setStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [backendInfo, setBackendInfo] = useState<any>(null);

  const checkBackendStatus = async () => {
    setStatus('checking');
    try {
      const health = await apiService.healthCheck();
      const info = await apiService.getAgentsStatus();
      
      setBackendInfo({ health, agents: info });
      setStatus('connected');
    } catch (error) {
      console.error('Backend connection failed:', error);
      setStatus('disconnected');
    }
  };

  useEffect(() => {
    checkBackendStatus();
    // Check every 30 seconds
    const interval = setInterval(checkBackendStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = () => {
    switch (status) {
      case 'connected': return 'text-green-600 bg-green-100';
      case 'disconnected': return 'text-red-600 bg-red-100';
      default: return 'text-yellow-600 bg-yellow-100';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'connected': return '✅ Backend Connected';
      case 'disconnected': return '❌ Backend Disconnected';
      default: return '⏳ Checking...';
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-20">
      <div className={`px-3 py-2 rounded-lg text-xs font-medium ${getStatusColor()} shadow-soft`}>
        {getStatusText()}
      </div>
      
      {status === 'connected' && backendInfo && (
        <div className="mt-2 text-xs text-secondary-500">
          {Object.keys(backendInfo.agents || {}).length} agents active
        </div>
      )}
      
      {status === 'disconnected' && (
        <button
          onClick={checkBackendStatus}
          className="mt-2 text-xs text-red-600 hover:text-red-800 underline"
        >
          Retry Connection
        </button>
      )}
    </div>
  );
};

export default BackendStatus;

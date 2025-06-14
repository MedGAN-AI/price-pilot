import React, { useState, useEffect } from 'react';
import { apiService, type HealthResponse, type ChatResponse } from '../services/api';

const ConnectionTest: React.FC = () => {
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testMessage, setTestMessage] = useState('');
  const [chatResponse, setChatResponse] = useState<ChatResponse | null>(null);

  // Test backend connection on component mount
  useEffect(() => {
    testConnection();
  }, []);

  const testConnection = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const health = await apiService.healthCheck();
      setHealthData(health);
      console.log('✅ Backend connection successful:', health);
    } catch (err: any) {
      setError(`Connection failed: ${err.message}`);
      console.error('❌ Backend connection failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const sendTestMessage = async () => {
    if (!testMessage.trim()) return;
    
    setLoading(true);
    setError(null);
    setChatResponse(null);
    
    try {
      const response = await apiService.sendMessage({
        message: testMessage,
        session_id: `test_${Date.now()}`
      });
      setChatResponse(response);
      console.log('✅ Chat message sent successfully:', response);
    } catch (err: any) {
      setError(`Chat failed: ${err.message}`);
      console.error('❌ Chat message failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '2rem auto', padding: '1rem' }}>
      <h1 style={{ textAlign: 'center', color: '#333', marginBottom: '2rem' }}>
        🚀 Price Pilot - Connection Test
      </h1>

      {/* Backend Health Status */}
      <div style={{ 
        backgroundColor: 'white', 
        padding: '1.5rem', 
        borderRadius: '8px', 
        marginBottom: '2rem',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)' 
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#333' }}>🔧 Backend Status</h2>
        
        {loading && <p>Testing connection...</p>}
        {error && <p style={{ color: 'red' }}>❌ {error}</p>}
        
        {healthData && (
          <div>
            <p style={{ color: 'green', fontWeight: 'bold' }}>
              ✅ Status: {healthData.status}
            </p>
            <p><strong>Version:</strong> {healthData.version}</p>
            <p><strong>Timestamp:</strong> {new Date(healthData.timestamp).toLocaleString()}</p>
            
            <h3 style={{ marginTop: '1rem', marginBottom: '0.5rem' }}>Agents Status:</h3>
            <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem' }}>
              {Object.entries(healthData.agents_status).map(([agent, status]) => (
                <li key={agent} style={{ marginBottom: '0.25rem' }}>
                  <strong>{agent}:</strong> {status}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        <button 
          onClick={testConnection} 
          disabled={loading}
          style={{
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            padding: '0.5rem 1rem',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            marginTop: '1rem'
          }}
        >
          {loading ? 'Testing...' : 'Test Connection'}
        </button>
      </div>

      {/* Chat Test */}
      <div style={{ 
        backgroundColor: 'white', 
        padding: '1.5rem', 
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)' 
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#333' }}>💬 Chat Test</h2>
        
        <div style={{ marginBottom: '1rem' }}>
          <input
            type="text"
            value={testMessage}
            onChange={(e) => setTestMessage(e.target.value)}
            placeholder="Type a test message (e.g., 'Hello' or 'What products do you have?')"
            style={{
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #ccc',
              borderRadius: '4px',
              fontSize: '1rem',
              marginBottom: '0.5rem'
            }}
            onKeyPress={(e) => e.key === 'Enter' && sendTestMessage()}
          />
          <button
            onClick={sendTestMessage}
            disabled={loading || !testMessage.trim()}
            style={{
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              padding: '0.75rem 1.5rem',
              borderRadius: '4px',
              cursor: loading || !testMessage.trim() ? 'not-allowed' : 'pointer',
              fontSize: '1rem'
            }}
          >
            {loading ? 'Sending...' : 'Send to ChatAgent'}
          </button>
        </div>

        {chatResponse && (
          <div style={{ 
            backgroundColor: '#f0f9ff', 
            padding: '1rem', 
            borderRadius: '4px',
            border: '1px solid #0ea5e9'
          }}>
            <h3 style={{ margin: '0 0 0.5rem 0', color: '#0c4a6e' }}>Response:</h3>
            <p style={{ margin: '0 0 0.5rem 0', fontSize: '1.1rem' }}>
              "{chatResponse.response}"
            </p>
            <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
              <p><strong>Agent:</strong> {chatResponse.agent_used}</p>
              <p><strong>Intent:</strong> {chatResponse.intent} (confidence: {Math.round(chatResponse.confidence * 100)}%)</p>
              <p><strong>Session:</strong> {chatResponse.session_id}</p>
              <p><strong>Time:</strong> {new Date(chatResponse.timestamp).toLocaleString()}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConnectionTest;

import React, { useState } from 'react';
import { ShieldCheck, Key, Cpu, Sparkles, Terminal, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { checkModelAvailability, updateConfig } from '../services/api';

export default function Header({
  serverConfig,
  apiKey,
  setApiKey,
  devMode,
  setDevMode,
  onConfigUpdated
}) {
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [tempKey, setTempKey] = useState(apiKey || '');
  const [isTesting, setIsTesting] = useState(false);
  const [testStatus, setTestStatus] = useState(null); // 'success' | 'error' | null
  const [testMessage, setTestMessage] = useState('');

  const handleOpenModal = () => {
    setTempKey(apiKey || '');
    setTestStatus(null);
    setTestMessage('');
    setShowKeyModal(true);
  };

  const handleTestKey = async () => {
    const keyToTest = tempKey.trim();
    if (!keyToTest) {
      setTestStatus('error');
      setTestMessage('Please enter an API key to test.');
      return;
    }
    setIsTesting(true);
    setTestStatus(null);
    setTestMessage('');
    try {
      const res = await checkModelAvailability(keyToTest);
      if (res.status === 'available') {
        setTestStatus('success');
        setTestMessage(`Connection verified: ${res.model} is online and available.`);
      } else {
        setTestStatus('error');
        setTestMessage(res.message || 'Model check returned unconfigured status.');
      }
    } catch (err) {
      setTestStatus('error');
      const detail = err.response?.data?.detail || err.message || 'Failed to verify key with Gemini API.';
      setTestMessage(detail);
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveKey = async () => {
    const cleanKey = tempKey.trim();
    setApiKey(cleanKey);
    try {
      const updated = await updateConfig({ api_key: cleanKey });
      if (onConfigUpdated) onConfigUpdated(updated);
    } catch {
      // Keep memory state if backend call fails
    }
    setShowKeyModal(false);
  };

  const handleClearKey = async () => {
    setTempKey('');
    setApiKey('');
    setTestStatus(null);
    setTestMessage('');
    try {
      const updated = await updateConfig({ api_key: '' });
      if (onConfigUpdated) onConfigUpdated(updated);
    } catch {
      // Keep memory state
    }
    setShowKeyModal(false);
  };

  const isCloudReady = Boolean(serverConfig?.has_gemini_api_key || apiKey);

  return (
    <header className="glass-panel" style={{ padding: '16px 24px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Brand Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
            padding: '10px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)'
          }}>
            <ShieldCheck size={28} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.4rem', color: '#ffffff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              Second Opinion
              <span style={{
                fontSize: '0.72rem',
                padding: '2px 8px',
                borderRadius: '6px',
                background: 'rgba(99, 102, 241, 0.2)',
                border: '1px solid rgba(99, 102, 241, 0.4)',
                color: '#a5b4fc',
                fontWeight: 600
              }}>
                BIT N BUILD CRCE
              </span>
            </h1>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: 0 }}>
              Explainable, Claim-Level AI Answer Auditor & Evidence Verifier
            </p>
          </div>
        </div>

        {/* Engine Status & Developer Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          
          {/* Readiness Badge */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            borderRadius: '20px',
            fontSize: '0.8rem',
            fontWeight: 600,
            background: isCloudReady ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
            border: `1px solid ${isCloudReady ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`,
            color: isCloudReady ? '#10b981' : '#f59e0b'
          }}>
            {isCloudReady ? <Sparkles size={14} /> : <Cpu size={14} />}
            <span>{isCloudReady ? `${serverConfig?.default_model || 'Gemini 3.8 Flash'} Online` : 'Offline Deterministic Ready'}</span>
          </div>

          {/* Dev Mode Toggle */}
          <button
            onClick={() => setDevMode(!devMode)}
            className="btn-secondary"
            style={{
              padding: '6px 12px',
              fontSize: '0.78rem',
              background: devMode ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.05)',
              borderColor: devMode ? 'rgba(99, 102, 241, 0.5)' : 'var(--border-color)',
              color: devMode ? '#a5b4fc' : 'var(--text-muted)'
            }}
            title="Toggle Developer Diagnostics and Raw Inspection Mode"
          >
            <Terminal size={14} />
            <span>{devMode ? 'Dev Mode ON' : 'Dev Mode'}</span>
          </button>

          {/* API Key Modal Button */}
          <button
            className="btn-secondary"
            onClick={handleOpenModal}
            style={{ padding: '6px 12px', fontSize: '0.78rem' }}
          >
            <Key size={14} />
            <span>{apiKey ? 'API Key Set' : 'Configure Key'}</span>
          </button>
        </div>
      </div>

      {/* API Key Modal */}
      {showKeyModal && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(6px)',
          WebkitBackdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10000,
          padding: '20px'
        }}>
          <div className="glass-panel" style={{ width: '480px', padding: '26px', background: '#0f172a' }}>
            <h3 style={{ marginBottom: '8px', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Key size={20} color="#6366f1" />
              Configure Gemini API Key
            </h3>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: 1.5 }}>
              Keys are stored securely in memory for this session and never exposed in generated reports. Leave blank to run in 100% Offline Deterministic Mode.
            </p>
            <input
              type="password"
              value={tempKey}
              onChange={(e) => {
                setTempKey(e.target.value);
                setTestStatus(null);
                setTestMessage('');
              }}
              placeholder="AIzaSy..."
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '8px',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-color)',
                color: '#ffffff',
                marginBottom: '12px',
                fontFamily: 'monospace'
              }}
            />

            {/* Test Status Feedback */}
            {testStatus === 'success' && (
              <div style={{
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '8px',
                padding: '8px 12px',
                marginBottom: '16px',
                color: '#10b981',
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <CheckCircle2 size={16} />
                <span>{testMessage}</span>
              </div>
            )}
            {testStatus === 'error' && (
              <div style={{
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                borderRadius: '8px',
                padding: '8px 12px',
                marginBottom: '16px',
                color: '#fda4af',
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertCircle size={16} />
                <span>{testMessage}</span>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                {apiKey && (
                  <button
                    className="btn-secondary"
                    onClick={handleClearKey}
                    style={{ padding: '6px 12px', fontSize: '0.78rem', color: '#f87171' }}
                  >
                    Clear Key
                  </button>
                )}
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  className="btn-secondary"
                  onClick={handleTestKey}
                  disabled={isTesting || !tempKey.trim()}
                  style={{ padding: '6px 14px', fontSize: '0.78rem' }}
                >
                  {isTesting ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />}
                  <span>{isTesting ? 'Verifying...' : 'Test Connection'}</span>
                </button>
                <button className="btn-secondary" onClick={() => setShowKeyModal(false)}>Cancel</button>
                <button className="btn-primary" onClick={handleSaveKey}>Save Key</button>
              </div>
            </div>
          </div>
        </div>
      )}

    </header>
  );
}

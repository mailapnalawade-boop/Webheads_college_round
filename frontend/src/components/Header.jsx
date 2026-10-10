import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ShieldCheck, Key, Sparkles, CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react';
import { checkModelAvailability, updateConfig } from '../services/api';

export default function Header({
  serverConfig,
  apiKey,
  setApiKey,
  onConfigUpdated
}) {
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [tempKey, setTempKey] = useState(apiKey || '');
  const [isTesting, setIsTesting] = useState(false);
  const [testStatus, setTestStatus] = useState(null); // 'success' | 'error' | null
  const [testMessage, setTestMessage] = useState('');

  // Close modal on Escape key press
  useEffect(() => {
    if (!showKeyModal) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setShowKeyModal(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showKeyModal]);

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
            <h1 style={{ fontSize: '1.4rem', color: '#ffffff', margin: 0 }}>
              Second Opinion
            </h1>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: 0 }}>
              Explainable, Claim-Level AI Answer Auditor & Evidence Verifier
            </p>
          </div>
        </div>

        {/* Header Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          
          {/* Cloud Model Status (only displayed when active) */}
          {isCloudReady && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '20px',
              fontSize: '0.8rem',
              fontWeight: 600,
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: '#10b981'
            }}>
              <Sparkles size={14} />
              <span>{serverConfig?.default_model || 'Gemini 3.8 Flash'} Online</span>
            </div>
          )}

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

      {/* API Key Modal portaled to document.body so parent backdrop-filter/transforms never clip it */}
      {showKeyModal && typeof document !== 'undefined' && createPortal(
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowKeyModal(false);
          }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            width: '100vw',
            height: '100vh',
            background: 'rgba(5, 8, 16, 0.8)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 999999,
            padding: '16px',
            boxSizing: 'border-box'
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '490px',
              maxHeight: 'min(90vh, 580px)',
              display: 'flex',
              flexDirection: 'column',
              background: '#0d1322',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '16px',
              padding: '24px',
              boxShadow: '0 25px 60px -10px rgba(0, 0, 0, 0.85), 0 0 0 1px rgba(99, 102, 241, 0.2)',
              boxSizing: 'border-box',
              position: 'relative',
              overflowY: 'auto'
            }}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h3 style={{ margin: 0, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.15rem' }}>
                <Key size={20} color="#6366f1" />
                Configure Gemini API Key
              </h3>
              <button
                onClick={() => setShowKeyModal(false)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '6px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.2s ease'
                }}
                title="Close"
              >
                <X size={16} />
              </button>
            </div>

            <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: 1.5 }}>
              Keys are stored securely in memory for this session and never exposed in generated reports.
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
                background: 'rgba(0, 0, 0, 0.45)',
                border: '1px solid var(--border-color)',
                color: '#ffffff',
                marginBottom: '14px',
                fontFamily: 'monospace',
                fontSize: '0.9rem',
                boxSizing: 'border-box'
              }}
            />

            {/* Test Status Feedback */}
            {testStatus === 'success' && (
              <div style={{
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '8px',
                padding: '10px 12px',
                marginBottom: '16px',
                color: '#10b981',
                fontSize: '0.82rem',
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
                padding: '10px 12px',
                marginBottom: '16px',
                color: '#fda4af',
                fontSize: '0.82rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertCircle size={16} />
                <span>{testMessage}</span>
              </div>
            )}

            {/* Footer Buttons */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '12px',
              paddingTop: '12px',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              flexWrap: 'wrap',
              gap: '8px'
            }}>
              <div>
                {apiKey && (
                  <button
                    className="btn-secondary"
                    onClick={handleClearKey}
                    style={{ padding: '7px 12px', fontSize: '0.78rem', color: '#f87171' }}
                  >
                    Clear Key
                  </button>
                )}
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  className="btn-secondary"
                  onClick={handleTestKey}
                  disabled={isTesting || !tempKey.trim()}
                  style={{ padding: '7px 14px', fontSize: '0.78rem' }}
                >
                  {isTesting ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />}
                  <span>{isTesting ? 'Verifying...' : 'Test Connection'}</span>
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => setShowKeyModal(false)}
                  style={{ padding: '7px 14px', fontSize: '0.78rem' }}
                >
                  Cancel
                </button>
                <button
                  className="btn-primary"
                  onClick={handleSaveKey}
                  style={{ padding: '7px 18px', fontSize: '0.78rem' }}
                >
                  Save Key
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}

    </header>
  );
}

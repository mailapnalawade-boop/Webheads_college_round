import React, { useState } from 'react';
import { ShieldCheck, Key, FileText, Cpu, Sparkles } from 'lucide-react';

export default function Header({ apiKey, setApiKey, onLoadSample, isLiveMode }) {
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [tempKey, setTempKey] = useState(apiKey || '');

  const handleSaveKey = () => {
    setApiKey(tempKey.trim());
    setShowKeyModal(false);
  };

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
            boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)'
          }}>
            <ShieldCheck size={28} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.4rem', color: '#ffffff', margin: 0 }}>
              Second Opinion <span style={{ fontSize: '0.8rem', padding: '2px 8px', borderRadius: '6px', background: 'rgba(99, 102, 241, 0.2)', border: '1px solid rgba(99, 102, 241, 0.4)', color: '#a5b4fc', marginLeft: '8px' }}>v1.0 Hackathon Edition</span>
            </h1>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
              Explainable, Claim-Level AI Answer Auditor & Evidence Verifier
            </p>
          </div>
        </div>

        {/* Action Controls & Engine Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Mode Badge */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            borderRadius: '20px',
            fontSize: '0.8rem',
            fontWeight: 500,
            background: isLiveMode ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
            border: `1px solid ${isLiveMode ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`,
            color: isLiveMode ? '#10b981' : '#f59e0b'
          }}>
            {isLiveMode ? <Sparkles size={14} /> : <Cpu size={14} />}
            <span>{isLiveMode ? 'Gemini 2.5 Flash Engine' : 'Offline Deterministic Fallback'}</span>
          </div>

          {/* Sample Loader */}
          <button className="btn-secondary" onClick={onLoadSample}>
            <FileText size={16} />
            <span>Load Sample Case</span>
          </button>

          {/* API Key Modal Button */}
          <button className="btn-secondary" onClick={() => setShowKeyModal(true)}>
            <Key size={16} />
            <span>{apiKey ? 'API Key Set' : 'Configure API Key'}</span>
          </button>
        </div>
      </div>

      {/* API Key Modal */}
      {showKeyModal && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div className="glass-panel" style={{ width: '450px', padding: '24px', background: '#0f172a' }}>
            <h3 style={{ marginBottom: '8px', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Key size={20} color="#6366f1" />
              Configure Gemini API Key
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Optional: Enter a free Gemini API key for LLM explanations. Leave blank to run 100% offline with BM25 & Rule Fallback.
            </p>
            <input
              type="password"
              value={tempKey}
              onChange={(e) => setTempKey(e.target.value)}
              placeholder="AIzaSy..."
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '8px',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-color)',
                color: '#ffffff',
                marginBottom: '20px',
                fontFamily: 'monospace'
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button className="btn-secondary" onClick={() => setShowKeyModal(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleSaveKey}>Save Key</button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

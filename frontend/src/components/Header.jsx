import React from 'react';
import { ShieldCheck, Sparkles, Cpu } from 'lucide-react';

export default function Header({ serverConfig }) {
  const isOnline = Boolean(serverConfig?.has_gemini_api_key);

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

        {/* Header Actions & Read-Only Status Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {isOnline ? (
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
              <span>{serverConfig?.default_model || 'gemini-2.5-flash'} Online</span>
            </div>
          ) : (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '20px',
              fontSize: '0.8rem',
              fontWeight: 600,
              background: 'rgba(148, 163, 184, 0.15)',
              border: '1px solid rgba(148, 163, 184, 0.4)',
              color: '#94a3b8'
            }}>
              <Cpu size={14} />
              <span>Offline mode</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

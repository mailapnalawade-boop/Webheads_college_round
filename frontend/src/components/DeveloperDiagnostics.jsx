import React, { useState } from 'react';
import { Terminal, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';

export default function DeveloperDiagnostics({ auditResult }) {
  const [copied, setCopied] = useState(false);
  const [showJson, setShowJson] = useState(false);

  if (!auditResult) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(auditResult, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-panel" style={{
      padding: '20px 24px',
      marginBottom: '24px',
      border: '1px dashed rgba(99, 102, 241, 0.4)',
      background: 'rgba(10, 15, 30, 0.7)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={18} color="#818cf8" />
          <h3 style={{ fontSize: '0.95rem', color: '#a5b4fc', margin: 0 }}>
            Developer Diagnostics & Engine Telemetry
          </h3>
          <span style={{ fontSize: '0.7rem', padding: '1px 6px', borderRadius: '4px', background: 'rgba(99, 102, 241, 0.2)', color: '#c7d2fe' }}>
            DEBUG MODE ACTIVE
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="btn-secondary"
            onClick={handleCopy}
            style={{ padding: '4px 10px', fontSize: '0.75rem', gap: '4px' }}
          >
            {copied ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
            <span>{copied ? 'Copied Payload' : 'Copy JSON'}</span>
          </button>
          <button
            className="btn-secondary"
            onClick={() => setShowJson(!showJson)}
            style={{ padding: '4px 10px', fontSize: '0.75rem', gap: '4px' }}
          >
            {showJson ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            <span>{showJson ? 'Hide Raw JSON' : 'Inspect JSON'}</span>
          </button>
        </div>
      </div>

      {/* Metadata Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '10px',
        fontSize: '0.78rem',
        color: 'var(--text-muted)',
        marginBottom: showJson ? '14px' : '0'
      }}>
        <div><strong>Audit ID:</strong> <code>{auditResult.audit_id}</code></div>
        <div><strong>Verification Mode:</strong> <code>{auditResult.verification_mode}</code></div>
        <div><strong>Model:</strong> <code>{auditResult.model_info}</code></div>
        <div><strong>Cache Hit:</strong> <code>{auditResult.cached ? 'True' : 'False'}</code></div>
        <div><strong>Timestamp:</strong> <code>{auditResult.timestamp}</code></div>
        <div><strong>Formula:</strong> <code>{auditResult.summary.credibility_breakdown?.formula || 'N/A'}</code></div>
      </div>

      {/* Raw JSON Inspector */}
      {showJson && (
        <pre style={{
          background: 'rgba(0, 0, 0, 0.6)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '14px',
          maxHeight: '300px',
          overflowY: 'auto',
          fontSize: '0.75rem',
          color: '#a5b4fc',
          fontFamily: 'JetBrains Mono, monospace',
          margin: 0
        }}>
          {JSON.stringify(auditResult, null, 2)}
        </pre>
      )}
    </div>
  );
}

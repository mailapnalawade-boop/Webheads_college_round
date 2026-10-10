import React from 'react';
import { Loader2, AlertCircle, RefreshCw, ShieldAlert, Cpu } from 'lucide-react';

const AUDIT_STAGES = [
  { id: 1, name: 'Processing source documents', desc: 'Parsing PDF & text passages into indexed chunks' },
  { id: 2, name: 'Extracting claims', desc: 'Decomposing answer into atomic verifiable statements' },
  { id: 3, name: 'Retrieving evidence', desc: 'BM25 & semantic matching against reference sources' },
  { id: 4, name: 'Verifying claims', desc: 'Evidence-grounded entailment & contradiction check' },
  { id: 5, name: 'Checking logical inconsistencies', desc: 'Evaluating mutual internal conflicts & non-sequiturs' },
  { id: 6, name: 'Evaluating potentially unsafe recommendations', desc: 'Screening directives for clinical, financial, or security risks' },
  { id: 7, name: 'Preparing report', desc: 'Validating structured schema & calculating metrics' }
];

export default function AuditLoadingOverlay({
  isLoading,
  errorMsg,
  onRetry,
  onSwitchOfflineAndRetry,
  onDismissError
}) {
  if (!isLoading && !errorMsg) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(5, 8, 16, 0.85)',
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div className="glass-panel" style={{
        maxWidth: '560px',
        width: '100%',
        padding: '32px',
        background: '#0d1322',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8)',
        position: 'relative'
      }}>
        {/* Error State */}
        {errorMsg ? (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                background: 'rgba(244, 63, 94, 0.15)',
                padding: '10px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(244, 63, 94, 0.4)'
              }}>
                <ShieldAlert size={26} color="#f43f5e" />
              </div>
              <div>
                <h3 style={{ fontSize: '1.2rem', color: '#ffffff', margin: 0 }}>
                  Audit Execution Interrupted
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Your inputs and uploaded documents have been preserved.
                </span>
              </div>
            </div>

            <div style={{
              background: 'rgba(244, 63, 94, 0.08)',
              border: '1px solid rgba(244, 63, 94, 0.25)',
              borderRadius: '10px',
              padding: '14px 16px',
              marginBottom: '20px',
              color: '#fda4af',
              fontSize: '0.88rem',
              lineHeight: 1.5
            }}>
              <AlertCircle size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom' }} />
              {errorMsg}
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              <button
                className="btn-secondary"
                onClick={onDismissError}
                style={{ fontSize: '0.85rem' }}
              >
                Close & Edit Inputs
              </button>

              {onSwitchOfflineAndRetry && (
                <button
                  className="btn-secondary"
                  onClick={onSwitchOfflineAndRetry}
                  style={{
                    fontSize: '0.85rem',
                    background: 'rgba(245, 158, 11, 0.15)',
                    borderColor: 'rgba(245, 158, 11, 0.4)',
                    color: '#f59e0b'
                  }}
                >
                  <Cpu size={14} /> Switch to Offline Mode & Retry
                </button>
              )}

              <button
                className="btn-primary"
                onClick={onRetry}
                style={{ fontSize: '0.85rem' }}
              >
                <RefreshCw size={14} /> Retry Audit
              </button>
            </div>
          </div>
        ) : (
          /* Loading State */
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '20px' }}>
              <div style={{
                background: 'rgba(99, 102, 241, 0.15)',
                padding: '12px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid rgba(99, 102, 241, 0.3)'
              }}>
                <Loader2 size={28} color="#818cf8" className="animate-spin" />
              </div>
              <div>
                <h3 style={{ fontSize: '1.25rem', color: '#ffffff', margin: 0 }}>
                  Auditing your answer...
                </h3>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                  Rigorous verification against reference evidence in progress
                </p>
              </div>
            </div>

            {/* Stages Pipeline */}
            <div style={{
              background: 'rgba(0, 0, 0, 0.4)',
              borderRadius: '12px',
              border: '1px solid var(--border-color)',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}>
              {AUDIT_STAGES.map((st) => (
                <div key={st.id} style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  padding: '6px 8px',
                  borderRadius: '6px',
                  background: 'rgba(255, 255, 255, 0.02)'
                }}>
                  <div style={{
                    minWidth: '22px',
                    height: '22px',
                    borderRadius: '50%',
                    background: 'rgba(99, 102, 241, 0.2)',
                    border: '1px solid rgba(99, 102, 241, 0.5)',
                    color: '#a5b4fc',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginTop: '2px'
                  }}>
                    {st.id}
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#ffffff', fontWeight: 500 }}>
                      {st.name}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {st.desc}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div style={{
              marginTop: '16px',
              textAlign: 'center',
              fontSize: '0.78rem',
              color: 'var(--text-dim)'
            }}>
              Synchronous deterministic evaluation • Please wait while evidence is parsed
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

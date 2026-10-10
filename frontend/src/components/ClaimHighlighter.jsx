import React from 'react';

export default function ClaimHighlighter({ claims, originalText, selectedClaimId, setSelectedClaimId }) {
  if (!originalText || !claims || claims.length === 0) return null;

  const getVerdictStyles = (verdict, isSelected) => {
    switch (verdict) {
      case 'SUPPORTED':
        return {
          background: isSelected ? 'rgba(16, 185, 129, 0.4)' : 'rgba(16, 185, 129, 0.18)',
          borderBottom: '2px solid #10b981',
          color: '#ffffff'
        };
      case 'CONTRADICTED':
        return {
          background: isSelected ? 'rgba(244, 63, 94, 0.45)' : 'rgba(244, 63, 94, 0.22)',
          borderBottom: '2px solid #f43f5e',
          color: '#ffffff'
        };
      case 'INSUFFICIENT_EVIDENCE':
      default:
        return {
          background: isSelected ? 'rgba(245, 158, 11, 0.4)' : 'rgba(245, 158, 11, 0.2)',
          borderBottom: '2px solid #f59e0b',
          color: '#ffffff'
        };
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ fontSize: '1rem', color: '#ffffff' }}>
          Interactive Answer Claim Highlighter
        </h3>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
          Click any claim to jump to its detailed evidence verification
        </span>
      </div>

      <div style={{
        background: 'rgba(0, 0, 0, 0.35)',
        padding: '20px',
        borderRadius: '12px',
        border: '1px solid var(--border-color)',
        lineHeight: 1.8,
        fontSize: '0.95rem',
        color: '#e5e7eb',
        maxHeight: '300px',
        overflowY: 'auto'
      }}>
        {claims.map((claim) => {
          const isSelected = selectedClaimId === claim.claim_id;
          const styles = getVerdictStyles(claim.verdict, isSelected);

          return (
            <span
              key={claim.claim_id}
              onClick={() => setSelectedClaimId(claim.claim_id)}
              style={{
                ...styles,
                padding: '2px 6px',
                margin: '0 2px',
                borderRadius: '4px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                display: 'inline',
                fontWeight: isSelected ? 600 : 400,
                outline: isSelected ? '2px solid rgba(255,255,255,0.8)' : 'none'
              }}
              title={`Claim #${claim.claim_id}: ${claim.verdict} (${Math.round(claim.confidence * 100)}% confidence)`}
            >
              {claim.text}{' '}
            </span>
          );
        })}
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, FileText, ChevronDown, ChevronUp, AlertOctagon, HelpCircle } from 'lucide-react';

export default function ClaimCard({ claim, isSelected, onSelect }) {
  const [expanded, setExpanded] = useState(true);

  const getVerdictMeta = (verdict) => {
    switch (verdict) {
      case 'SUPPORTED':
        return {
          icon: <CheckCircle2 size={18} color="#10b981" />,
          color: '#10b981',
          bg: 'var(--status-supported-bg)',
          border: 'var(--status-supported-border)',
          label: 'SUPPORTED'
        };
      case 'CONTRADICTED':
        return {
          icon: <XCircle size={18} color="#f43f5e" />,
          color: '#f43f5e',
          bg: 'var(--status-contradicted-bg)',
          border: 'var(--status-contradicted-border)',
          label: 'CONTRADICTED'
        };
      case 'INSUFFICIENT_EVIDENCE':
      default:
        return {
          icon: <AlertTriangle size={18} color="#f59e0b" />,
          color: '#f59e0b',
          bg: 'var(--status-insufficient-bg)',
          border: 'var(--status-insufficient-border)',
          label: 'INSUFFICIENT EVIDENCE'
        };
    }
  };

  const meta = getVerdictMeta(claim.verdict);

  return (
    <div
      id={claim.claim_id}
      onClick={onSelect}
      className="glass-panel"
      style={{
        padding: '18px 22px',
        marginBottom: '14px',
        border: isSelected ? `2px solid ${meta.color}` : '1px solid var(--border-color)',
        boxShadow: isSelected ? `0 0 20px ${meta.color}33` : 'none',
        transition: 'all 0.2s ease'
      }}
    >
      {/* Claim Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
        
        {/* Left: Verdict Badge & Claim Text */}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
            
            {/* Badge */}
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '20px',
              fontSize: '0.75rem',
              fontWeight: 700,
              background: meta.bg,
              border: `1px solid ${meta.border}`,
              color: meta.color
            }}>
              {meta.icon}
              {meta.label}
            </span>

            {/* Confidence */}
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', background: 'rgba(255,255,255,0.04)', padding: '2px 8px', borderRadius: '12px' }}>
              Confidence: {Math.round(claim.confidence * 100)}%
            </span>

            {/* Warning Flags */}
            {claim.flags?.internal_contradiction && (
              <span style={{ fontSize: '0.75rem', color: '#f43f5e', background: 'rgba(244,63,94,0.15)', border: '1px solid rgba(244,63,94,0.3)', padding: '2px 8px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertOctagon size={12} /> Internal Conflict
              </span>
            )}

            {claim.flags?.is_ambiguous && (
              <span style={{ fontSize: '0.75rem', color: '#f59e0b', background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', padding: '2px 8px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <HelpCircle size={12} /> Ambiguous Context
              </span>
            )}
          </div>

          <h4 style={{ fontSize: '0.95rem', color: '#ffffff', fontWeight: 600, lineHeight: 1.4, margin: '6px 0 10px 0' }}>
            "{claim.text}"
          </h4>
        </div>

        {/* Expand / Collapse Button */}
        <button
          onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: '4px' }}
        >
          {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
      </div>

      {/* Explanation Box */}
      <div style={{
        background: 'rgba(0, 0, 0, 0.25)',
        padding: '10px 14px',
        borderRadius: '8px',
        borderLeft: `3px solid ${meta.color}`,
        fontSize: '0.85rem',
        color: 'var(--text-muted)',
        marginBottom: expanded && claim.evidence.length > 0 ? '14px' : '0'
      }}>
        {claim.explanation}
      </div>

      {/* Evidence Excerpts */}
      {expanded && claim.evidence.length > 0 && (
        <div style={{ marginTop: '12px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '12px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FileText size={14} color="#6366f1" />
            Ground-Truth Evidence Excerpts ({claim.evidence.length})
          </div>

          {claim.evidence.map((ev, idx) => (
            <div key={idx} style={{
              background: 'rgba(255, 255, 255, 0.02)',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              marginBottom: '8px',
              fontSize: '0.82rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', color: '#a5b4fc', fontWeight: 500 }}>
                <span>📄 {ev.source_name} (Page {ev.page_number})</span>
                <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>
                  Match Relevance: {Math.round(ev.relevance_score * 100)}%
                </span>
              </div>
              <p style={{ color: '#d1d5db', fontStyle: 'italic', margin: 0 }}>
                "{ev.excerpt}"
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

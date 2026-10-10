import React from 'react';
import { GitCompare, CornerDownRight } from 'lucide-react';

export default function LogicalInconsistenciesSection({
  logicalInconsistencies,
  onSelectClaim
}) {
  if (!logicalInconsistencies || logicalInconsistencies.length === 0) return null;

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            background: 'rgba(168, 85, 247, 0.15)',
            padding: '8px',
            borderRadius: '10px',
            border: '1px solid rgba(168, 85, 247, 0.4)'
          }}>
            <GitCompare size={20} color="#c084fc" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', color: '#ffffff', margin: 0 }}>
              Logical Inconsistencies & Internal Conflicts ({logicalInconsistencies.length})
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
              Direct statement contradictions and premise-conclusion reasoning gaps within the answer
            </p>
          </div>
        </div>

        <span style={{
          fontSize: '0.75rem',
          padding: '4px 10px',
          borderRadius: '16px',
          fontWeight: 600,
          background: 'rgba(168, 85, 247, 0.15)',
          border: '1px solid rgba(168, 85, 247, 0.4)',
          color: '#c084fc'
        }}>
          Independent Logical Audit
        </span>
      </div>

      {/* Inconsistency List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {logicalInconsistencies.map((conflict, idx) => (
          <div key={conflict.conflict_id || idx} style={{
            background: 'rgba(0, 0, 0, 0.35)',
            border: '1px solid rgba(168, 85, 247, 0.25)',
            borderLeft: '4px solid #a855f7',
            borderRadius: '12px',
            padding: '16px 20px'
          }}>
            
            {/* Top Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
              <span style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '12px',
                background: 'rgba(168, 85, 247, 0.2)',
                border: '1px solid rgba(168, 85, 247, 0.4)',
                color: '#d8b4fe'
              }}>
                {conflict.inconsistency_type === 'non_sequitur' ? 'NON-SEQUITUR / REASONING GAP' : 'MUTUAL CONTRADICTION'}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                Conflict #{idx + 1}
              </span>
            </div>

            {/* Claims Comparison Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '12px',
              marginBottom: '14px'
            }}>
              {/* Claim 1 */}
              <div
                onClick={() => onSelectClaim && onSelectClaim(conflict.claim_id_1)}
                style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '8px',
                  padding: '12px 14px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
                title="Click to locate Claim in Answer"
              >
                <div style={{ fontSize: '0.75rem', color: '#a5b4fc', fontWeight: 600, marginBottom: '4px' }}>
                  Statement A [{conflict.claim_id_1}]
                </div>
                <div style={{ fontSize: '0.85rem', color: '#ffffff', fontStyle: 'italic' }}>
                  "{conflict.claim_text_1}"
                </div>
              </div>

              {/* Claim 2 */}
              {conflict.claim_id_2 && (
                <div
                  onClick={() => onSelectClaim && onSelectClaim(conflict.claim_id_2)}
                  style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '8px',
                    padding: '12px 14px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  title="Click to locate Claim in Answer"
                >
                  <div style={{ fontSize: '0.75rem', color: '#c084fc', fontWeight: 600, marginBottom: '4px' }}>
                    Statement B [{conflict.claim_id_2}]
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#ffffff', fontStyle: 'italic' }}>
                    "{conflict.claim_text_2}"
                  </div>
                </div>
              )}
            </div>

            {/* Explanation */}
            <div style={{
              background: 'rgba(168, 85, 247, 0.08)',
              border: '1px solid rgba(168, 85, 247, 0.2)',
              borderRadius: '8px',
              padding: '10px 14px',
              fontSize: '0.85rem',
              color: '#e9d5ff',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px'
            }}>
              <CornerDownRight size={16} color="#c084fc" style={{ marginTop: '2px', flexShrink: 0 }} />
              <div>
                <strong style={{ color: '#f3e8ff' }}>Reasoning Conflict: </strong>
                {conflict.explanation}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

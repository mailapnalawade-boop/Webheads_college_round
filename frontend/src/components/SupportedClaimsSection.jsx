import React, { useState } from 'react';
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText
} from 'lucide-react';
import { getShortExcerpt, deduplicateClaims } from '../utils/reportUtils';

export default function SupportedClaimsSection({
  claims,
  selectedClaimId,
  setSelectedClaimId
}) {
  // Collapsed by default per Requirement 4
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedEvidenceIds, setExpandedEvidenceIds] = useState(new Set());

  const rawSupported = claims.filter((c) => c.verdict === 'SUPPORTED');
  const supportedClaims = deduplicateClaims(rawSupported);

  if (supportedClaims.length === 0) return null;

  const toggleEvidence = (claimId, e) => {
    e.stopPropagation();
    setExpandedEvidenceIds((prev) => {
      const next = new Set(prev);
      if (next.has(claimId)) {
        next.delete(claimId);
      } else {
        next.add(claimId);
      }
      return next;
    });
  };

  return (
    <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
      {/* Collapsible Section Header Bar */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
          userSelect: 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '8px',
            background: 'var(--status-supported-bg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <CheckCircle2 size={16} color="#10b981" />
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ fontSize: '1.05rem', color: '#ffffff', margin: 0, fontWeight: 700 }}>
                Supported Claims ({supportedClaims.length})
              </h3>
              <span style={{
                fontSize: '0.72rem',
                color: '#10b981',
                background: 'var(--status-supported-bg)',
                border: '1px solid var(--status-supported-border)',
                padding: '2px 8px',
                borderRadius: '12px',
                fontWeight: 600
              }}>
                Corroborated
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>
              {isExpanded
                ? 'Showing all statements confirmed by source documentation.'
                : 'Click to expand and view verified claims and evidence passages.'}
            </p>
          </div>
        </div>

        <button
          style={{
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-main)',
            borderRadius: '8px',
            padding: '6px 12px',
            fontSize: '0.78rem',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontWeight: 500
          }}
        >
          {isExpanded ? 'Collapse' : `View ${supportedClaims.length} Claims`}
          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div style={{ marginTop: '16px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
          {supportedClaims.map((claim, idx) => {
            const isSelected = selectedClaimId === claim.claim_id;
            const topEvidence = claim.evidence && claim.evidence.length > 0 ? claim.evidence[0] : null;
            const showFull = expandedEvidenceIds.has(claim.claim_id);

            return (
              <div
                key={claim.claim_id}
                id={claim.claim_id}
                onClick={() => setSelectedClaimId(claim.claim_id)}
                style={{
                  background: isSelected ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: isSelected ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.05)',
                  borderRadius: '10px',
                  padding: '14px 16px',
                  marginBottom: '10px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {/* Claim Statement & Status */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', flex: 1 }}>
                    <span style={{ fontSize: '0.78rem', color: '#10b981', fontWeight: 700, marginTop: '2px' }}>
                      ✓ #{idx + 1}
                    </span>
                    <p style={{ fontSize: '0.88rem', color: '#ffffff', margin: 0, fontWeight: 500, lineHeight: 1.4 }}>
                      "{claim.text}"
                    </p>
                  </div>

                  <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', flexShrink: 0 }}>
                    Confidence: {Math.round((claim.confidence || 0.8) * 100)}%
                  </span>
                </div>

                {/* Evidence Passage (if available) */}
                {topEvidence && (
                  <div style={{
                    background: 'rgba(0, 0, 0, 0.25)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    fontSize: '0.8rem',
                    borderLeft: '2px solid #10b981'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ color: '#818cf8', fontSize: '0.74rem', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>
                        <FileText size={12} />
                        {topEvidence.source_name || 'Source'}
                        {topEvidence.page_number ? ` • Page ${topEvidence.page_number}` : ''}
                      </span>

                      {topEvidence.excerpt && topEvidence.excerpt.length > 120 && (
                        <button
                          onClick={(e) => toggleEvidence(claim.claim_id, e)}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: '#818cf8',
                            fontSize: '0.72rem',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '2px',
                            padding: 0
                          }}
                        >
                          {showFull ? 'Show less' : 'View full evidence'}
                          {showFull ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                        </button>
                      )}
                    </div>

                    <p style={{ color: '#9ca3af', fontStyle: 'italic', margin: 0, lineHeight: 1.4 }}>
                      "{showFull ? topEvidence.excerpt : getShortExcerpt(topEvidence.excerpt, 120)}"
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

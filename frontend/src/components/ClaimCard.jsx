import React from 'react';
import IssueCard from './IssueCard';
import { CheckCircle2, FileText, Globe } from 'lucide-react';
import { getShortExcerpt } from '../utils/reportUtils';

export default function ClaimCard({
  claim,
  index,
  isSelected,
  onSelect,
  _onJumpToAnswer
}) {
  if (
    claim.verdict === 'CONTRADICTED' ||
    claim.verdict === 'INSUFFICIENT_EVIDENCE' ||
    claim.verdict === 'LOGICAL_INCONSISTENCY' ||
    claim.flags?.internal_contradiction
  ) {
    return <IssueCard claim={claim} isSelected={isSelected} onSelect={onSelect} />;
  }

  // Supported Claim card
  const topEvidence = (claim.supporting_evidence && claim.supporting_evidence.length > 0)
    ? claim.supporting_evidence[0]
    : (claim.evidence && claim.evidence.length > 0 ? claim.evidence[0] : null);

  return (
    <div
      id={claim.claim_id}
      onClick={onSelect}
      className={`glass-panel ${isSelected ? 'card-selected-pulse' : ''}`}
      style={{
        padding: '16px 20px',
        marginBottom: '12px',
        border: isSelected ? '2px solid #10b981' : '1px solid var(--border-color)',
        boxShadow: isSelected ? '0 0 20px rgba(16, 185, 129, 0.25)' : 'none',
        transition: 'all 0.2s ease',
        cursor: 'pointer'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '0.72rem',
              fontWeight: 700,
              background: 'var(--status-supported-bg)',
              border: '1px solid var(--status-supported-border)',
              color: '#10b981'
            }}>
              <CheckCircle2 size={13} />
              SUPPORTED
            </span>

            {index !== undefined && (
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                #{index + 1}
              </span>
            )}

            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
              Confidence: {Math.round((claim.confidence || 0.8) * 100)}%
            </span>
          </div>

          <h4 style={{ fontSize: '0.92rem', color: '#ffffff', margin: '4px 0 8px 0', fontWeight: 500 }}>
            "{claim.text}"
          </h4>

          {topEvidence && (
            <div style={{
              background: 'rgba(0, 0, 0, 0.25)',
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '0.8rem',
              borderLeft: '2px solid #10b981'
            }}>
              <div style={{ color: '#818cf8', fontSize: '0.73rem', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '3px' }}>
                {topEvidence.is_external ? <Globe size={12} /> : <FileText size={12} />}
                {topEvidence.source_name || 'Source'} (Page {topEvidence.page_number || 1})
              </div>
              <p style={{ color: '#9ca3af', fontStyle: 'italic', margin: 0 }}>
                "{getShortExcerpt(topEvidence.excerpt, 130)}"
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

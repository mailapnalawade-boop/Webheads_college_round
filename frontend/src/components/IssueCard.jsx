import React, { useState } from 'react';
import {
  XCircle,
  AlertTriangle,
  AlertOctagon,
  FileText,
  ChevronDown,
  ChevronUp,
  Lightbulb
} from 'lucide-react';
import {
  getIssueClassification,
  getIssueTitle,
  getConciseWhyItMatters,
  getSuggestedCorrection,
  getShortExcerpt
} from '../utils/reportUtils';

export default function IssueCard({ claim, isSelected, onSelect }) {
  const [showFullEvidence, setShowFullEvidence] = useState(false);

  const classification = getIssueClassification(claim);
  const issueTitle = getIssueTitle(claim);
  const whyItMatters = getConciseWhyItMatters(claim);
  const suggestedCorrection = getSuggestedCorrection(claim);

  const topEvidence = claim.evidence && claim.evidence.length > 0 ? claim.evidence[0] : null;
  const hasEvidence = Boolean(topEvidence && topEvidence.excerpt);

  const renderBadgeIcon = () => {
    switch (classification.type) {
      case 'LOGICAL_INCONSISTENCY':
        return <AlertOctagon size={14} color={classification.color} />;
      case 'CONTRADICTED':
        return <XCircle size={14} color={classification.color} />;
      case 'UNVERIFIED':
      default:
        return <AlertTriangle size={14} color={classification.color} />;
    }
  };

  return (
    <div
      id={claim.claim_id}
      onClick={onSelect}
      className="glass-panel"
      style={{
        padding: '18px 20px',
        marginBottom: '14px',
        border: isSelected
          ? `2px solid ${classification.color}`
          : `1px solid ${classification.border}`,
        background: isSelected
          ? 'rgba(26, 37, 60, 0.95)'
          : 'var(--bg-card)',
        boxShadow: isSelected
          ? `0 0 20px ${classification.color}33`
          : 'none',
        transition: 'all 0.2s ease',
        cursor: 'pointer'
      }}
    >
      {/* Top Header: Specific Issue Title + Badge */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* Status Badge */}
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            padding: '3px 10px',
            borderRadius: '20px',
            fontSize: '0.72rem',
            fontWeight: 700,
            background: classification.bg,
            border: `1px solid ${classification.border}`,
            color: classification.color
          }}>
            {renderBadgeIcon()}
            {classification.badgeText}
          </span>

          {/* Issue Title */}
          <h4 style={{
            fontSize: '0.95rem',
            color: '#ffffff',
            margin: 0,
            fontWeight: 600
          }}>
            {issueTitle}
          </h4>
        </div>

        {/* Confidence or Source Indicator */}
        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>Confidence: {Math.round((claim.confidence || 0.5) * 100)}%</span>
        </div>
      </div>

      {/* Audited Statement / Claim */}
      <div style={{
        background: 'rgba(0, 0, 0, 0.25)',
        borderLeft: `3px solid ${classification.color}`,
        borderRadius: '0 8px 8px 0',
        padding: '10px 14px',
        marginBottom: '12px'
      }}>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600, display: 'block', marginBottom: '2px' }}>
          Audited Statement:
        </span>
        <p style={{
          fontSize: '0.92rem',
          color: '#ffffff',
          margin: 0,
          fontWeight: 500,
          lineHeight: 1.45
        }}>
          "{claim.text}"
        </p>
      </div>

      {/* Why it matters (1-2 sentences) */}
      <div style={{ marginBottom: '12px' }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '3px' }}>
          Why it matters:
        </div>
        <p style={{ fontSize: '0.85rem', color: '#d1d5db', margin: 0, lineHeight: 1.45 }}>
          {whyItMatters}
        </p>
      </div>

      {/* Source Evidence Section */}
      <div style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '10px 12px',
        marginBottom: suggestedCorrection ? '10px' : '0'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '6px',
          flexWrap: 'wrap',
          gap: '6px'
        }}>
          <span style={{
            fontSize: '0.75rem',
            color: '#818cf8',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontWeight: 600
          }}>
            <FileText size={13} />
            Source Evidence
            {topEvidence && ` (${topEvidence.source_name || 'Document'}${topEvidence.page_number ? ` • Pg ${topEvidence.page_number}` : ''})`}
          </span>

          {hasEvidence && topEvidence.excerpt.length > 130 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowFullEvidence(!showFullEvidence);
              }}
              style={{
                background: 'none',
                border: 'none',
                color: '#818cf8',
                fontSize: '0.73rem',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '2px',
                padding: 0,
                fontWeight: 500
              }}
            >
              {showFullEvidence ? 'Show short excerpt' : 'View full evidence'}
              {showFullEvidence ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          )}
        </div>

        {hasEvidence ? (
          <p style={{
            color: '#9ca3af',
            fontSize: '0.82rem',
            fontStyle: 'italic',
            margin: 0,
            lineHeight: 1.4
          }}>
            "{showFullEvidence ? topEvidence.excerpt : getShortExcerpt(topEvidence.excerpt, 130)}"
          </p>
        ) : (
          <p style={{
            color: 'var(--text-dim)',
            fontSize: '0.8rem',
            fontStyle: 'italic',
            margin: 0
          }}>
            No verifying passage found in reference document.
          </p>
        )}
      </div>

      {/* Suggested Actionable Correction (Only when useful) */}
      {suggestedCorrection && (
        <div style={{
          background: 'rgba(99, 102, 241, 0.08)',
          border: '1px solid rgba(99, 102, 241, 0.25)',
          borderRadius: '8px',
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <Lightbulb size={14} color="#818cf8" style={{ flexShrink: 0 }} />
          <div style={{ fontSize: '0.8rem', color: '#c7d2fe', lineHeight: 1.35 }}>
            <strong style={{ color: '#ffffff' }}>Suggested correction: </strong>
            {suggestedCorrection}
          </div>
        </div>
      )}
    </div>
  );
}

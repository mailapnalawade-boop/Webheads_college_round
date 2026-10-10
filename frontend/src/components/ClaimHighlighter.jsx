import React, { useMemo } from 'react';
import { MousePointerClick } from 'lucide-react';

export default function ClaimHighlighter({
  claims,
  originalText,
  selectedClaimId,
  onSelectClaim
}) {
  // Segment original text into claim spans and non-claim text preserving 100% of characters
  const segments = useMemo(() => {
    if (!originalText) return [];
    if (!claims || claims.length === 0) {
      return [{ isClaim: false, text: originalText }];
    }

    // Validate and sort claims by start_char
    const validClaims = claims
      .map((c) => {
        let start = c.start_char;
        let end = c.end_char;

        // If offset is out of bounds or doesn't match, verify with indexOf
        if (
          start === undefined ||
          end === undefined ||
          start < 0 ||
          end > originalText.length ||
          originalText.slice(start, end) !== c.text
        ) {
          const found = originalText.indexOf(c.text);
          if (found !== -1) {
            start = found;
            end = found + c.text.length;
          } else {
            start = Math.max(0, start || 0);
            end = Math.min(originalText.length, end || start + c.text.length);
          }
        }
        return { ...c, start_char: start, end_char: end };
      })
      .filter((c) => c.start_char < c.end_char && c.start_char < originalText.length)
      .sort((a, b) => a.start_char - b.start_char || a.end_char - b.end_char);

    const result = [];
    let cursor = 0;

    for (const c of validClaims) {
      if (c.start_char > cursor) {
        // Non-claim text between cursor and claim
        result.push({
          isClaim: false,
          text: originalText.slice(cursor, c.start_char)
        });
      }

      const segStart = Math.max(cursor, c.start_char);
      const segEnd = Math.max(segStart, c.end_char);

      if (segEnd > segStart) {
        result.push({
          isClaim: true,
          claim: c,
          start: segStart,
          text: originalText.slice(segStart, segEnd)
        });
        cursor = segEnd;
      }
    }

    if (cursor < originalText.length) {
      result.push({
        isClaim: false,
        text: originalText.slice(cursor)
      });
    }

    return result;
  }, [claims, originalText]);

  if (!originalText) return null;

  const getVerdictStyle = (verdict, isSelected) => {
    switch (verdict) {
      case 'SUPPORTED':
        return {
          bg: isSelected ? 'rgba(16, 185, 129, 0.38)' : 'rgba(16, 185, 129, 0.18)',
          borderBottom: '2px solid #10b981',
          color: '#ffffff',
          badgeColor: '#10b981',
          label: 'SUPPORTED'
        };
      case 'CONTRADICTED':
        return {
          bg: isSelected ? 'rgba(244, 63, 94, 0.42)' : 'rgba(244, 63, 94, 0.22)',
          borderBottom: '2px solid #f43f5e',
          color: '#ffffff',
          badgeColor: '#f43f5e',
          label: 'CONTRADICTED'
        };
      case 'LOGICAL_INCONSISTENCY':
        return {
          bg: isSelected ? 'rgba(168, 85, 247, 0.42)' : 'rgba(168, 85, 247, 0.22)',
          borderBottom: '2px solid #a855f7',
          color: '#ffffff',
          badgeColor: '#c084fc',
          label: 'LOGIC CONFLICT'
        };
      case 'AMBIGUOUS':
        return {
          bg: isSelected ? 'rgba(96, 165, 250, 0.38)' : 'rgba(96, 165, 250, 0.18)',
          borderBottom: '2px dashed #60a5fa',
          color: '#ffffff',
          badgeColor: '#60a5fa',
          label: 'AMBIGUOUS'
        };
      case 'INSUFFICIENT_EVIDENCE':
      default:
        return {
          bg: isSelected ? 'rgba(245, 158, 11, 0.38)' : 'rgba(245, 158, 11, 0.18)',
          borderBottom: '2px solid #f59e0b',
          color: '#ffffff',
          badgeColor: '#f59e0b',
          label: 'UNVERIFIED'
        };
    }
  };

  // Highlights the exact words that contain the error (backend verifies answer[start:end] === text)
  const renderWithErrorSpan = (seg, claim) => {
    const span = claim.error_span;
    if (!span || claim.verdict === 'SUPPORTED') return seg.text;
    const from = span.start_char - seg.start;
    const to = span.end_char - seg.start;
    if (from < 0 || to > seg.text.length || from >= to) return seg.text;
    const approximate = span.precision !== 'exact';
    return (
      <>
        {seg.text.slice(0, from)}
        <u
          title={approximate ? 'Suspected error (approximate)' : 'Exact error: ' + span.text}
          style={{
            background: 'rgba(244, 63, 94, 0.55)',
            textDecoration: approximate ? 'underline dashed #fff' : 'underline wavy #fff',
            textUnderlineOffset: '3px',
            borderRadius: '3px',
            padding: '0 2px',
            fontWeight: 700
          }}
        >
          {seg.text.slice(from, to)}
        </u>
        {seg.text.slice(to)}
      </>
    );
  };

  const handleSpanClick = (claimId) => {
    if (onSelectClaim) {
      onSelectClaim(claimId);
    }
    const el = document.getElementById(claimId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      
      {/* Title & Legend */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h3 style={{ fontSize: '1.05rem', color: '#ffffff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MousePointerClick size={18} color="#6366f1" />
            Original Answer with Synchronized Claim Highlighting
          </h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Click any highlighted claim to jump directly to its verification card
          </span>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', fontSize: '0.75rem', fontWeight: 600 }}>
          <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} /> Supported
          </span>
          <span style={{ color: '#f43f5e', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f43f5e' }} /> Contradicted
          </span>
          <span style={{ color: '#a855f7', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#a855f7' }} /> Logic Conflict
          </span>
          <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }} /> Insufficient Evidence
          </span>
        </div>
      </div>

      {/* Answer Text Container */}
      <div
        id="original-answer-container"
        style={{
          background: 'rgba(0, 0, 0, 0.4)',
          padding: '22px 24px',
          borderRadius: '12px',
          border: '1px solid var(--border-color)',
          lineHeight: 1.85,
          fontSize: '0.93rem',
          color: '#e5e7eb',
          maxHeight: '360px',
          overflowY: 'auto',
          whiteSpace: 'pre-wrap',
          fontFamily: 'inherit'
        }}
      >
        {segments.map((seg, idx) => {
          if (!seg.isClaim) {
            return <span key={idx}>{seg.text}</span>;
          }

          const claim = seg.claim;
          const isSelected = selectedClaimId === claim.claim_id;
          const style = getVerdictStyle(claim.verdict, isSelected);

          return (
            <mark
              key={idx}
              id={`highlight-${claim.claim_id}`}
              className="highlight-span-target"
              onClick={() => handleSpanClick(claim.claim_id)}
              style={{
                background: style.bg,
                borderBottom: style.borderBottom,
                color: style.color,
                padding: '2px 6px',
                margin: '0 2px',
                borderRadius: '4px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                display: 'inline',
                fontWeight: isSelected ? 600 : 400,
                outline: isSelected ? '2px solid rgba(255, 255, 255, 0.9)' : 'none',
                boxShadow: isSelected ? '0 0 12px rgba(99, 102, 241, 0.5)' : 'none'
              }}
              title={`[${claim.verdict}] ${claim.text} — Click to inspect analysis`}
            >
              {renderWithErrorSpan(seg, claim)}
              <span
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  marginLeft: '4px',
                  color: style.badgeColor,
                  background: 'rgba(0, 0, 0, 0.4)',
                  padding: '1px 5px',
                  borderRadius: '6px',
                  verticalAlign: 'baseline',
                  userSelect: 'none'
                }}
              >
                {style.label}
              </span>
            </mark>
          );
        })}
      </div>
    </div>
  );
}

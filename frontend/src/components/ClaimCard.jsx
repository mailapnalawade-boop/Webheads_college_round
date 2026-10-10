import React, { useState } from 'react';
import {
  CheckCircle2, XCircle, AlertTriangle, GitCompare,
  FileText, ChevronDown, ChevronUp, AlertOctagon, HelpCircle,
  Eye, Globe
} from 'lucide-react';

export default function ClaimCard({
  claim,
  index,
  isSelected,
  onSelect,
  onJumpToAnswer
}) {
  const [expanded, setExpanded] = useState(true);

  const getVerdictMeta = (verdict) => {
    switch (verdict) {
      case 'SUPPORTED':
        return {
          icon: <CheckCircle2 size={16} color="#10b981" />,
          color: '#10b981',
          bg: 'var(--status-supported-bg)',
          border: 'var(--status-supported-border)',
          label: 'SUPPORTED',
          summaryDesc: 'Available evidence substantiates this claim.'
        };
      case 'CONTRADICTED':
        return {
          icon: <XCircle size={16} color="#f43f5e" />,
          color: '#f43f5e',
          bg: 'var(--status-contradicted-bg)',
          border: 'var(--status-contradicted-border)',
          label: 'CONTRADICTED',
          summaryDesc: 'Reference evidence conflicts directly with this claim.'
        };
      case 'LOGICAL_INCONSISTENCY':
        return {
          icon: <GitCompare size={16} color="#c084fc" />,
          color: '#a855f7',
          bg: 'var(--status-inconsistent-bg)',
          border: 'var(--status-inconsistent-border)',
          label: 'LOGICAL INCONSISTENCY',
          summaryDesc: 'Claim conflicts with another assertion in the answer or lacks premise validity.'
        };
      case 'INSUFFICIENT_EVIDENCE':
      default:
        return {
          icon: <AlertTriangle size={16} color="#f59e0b" />,
          color: '#f59e0b',
          bg: 'var(--status-insufficient-bg)',
          border: 'var(--status-insufficient-border)',
          label: 'INSUFFICIENT EVIDENCE',
          summaryDesc: 'Available documents do not establish whether this claim is correct.'
        };
    }
  };

  const meta = getVerdictMeta(claim.verdict);
  const supportingList = claim.supporting_evidence || [];
  const contradictingList = claim.contradicting_evidence || [];
  const generalEvidence = claim.evidence || [];

  return (
    <div
      id={claim.claim_id}
      className={`glass-panel claim-card-target ${isSelected ? 'card-selected-pulse' : ''}`}
      onClick={onSelect}
      style={{
        padding: '20px 24px',
        marginBottom: '16px',
        border: isSelected ? `2px solid ${meta.color}` : '1px solid var(--border-color)',
        boxShadow: isSelected ? `0 0 24px ${meta.color}44` : 'none',
        transition: 'all 0.2s ease',
        cursor: 'pointer'
      }}
    >
      {/* Upper Bar: Claim Number, Verdict Badge, Uncertainty, and Jump Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* Claim Number */}
          <span style={{
            fontSize: '0.8rem',
            fontWeight: 800,
            color: '#a5b4fc',
            background: 'rgba(99, 102, 241, 0.15)',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            padding: '2px 8px',
            borderRadius: '6px'
          }}>
            Claim #{index !== undefined ? index + 1 : claim.claim_id.replace('claim_', '')}
          </span>

          {/* Primary Status Badge */}
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '16px',
            fontSize: '0.75rem',
            fontWeight: 700,
            background: meta.bg,
            border: `1px solid ${meta.border}`,
            color: meta.color
          }}>
            {meta.icon}
            {meta.label}
          </span>

          {/* Uncertainty Level Indicator */}
          <span style={{
            fontSize: '0.72rem',
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: '12px',
            background: claim.uncertainty_level === 'Low' ? 'rgba(16, 185, 129, 0.1)' : claim.uncertainty_level === 'Moderate' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(244, 63, 94, 0.1)',
            border: `1px solid ${claim.uncertainty_level === 'Low' ? 'rgba(16, 185, 129, 0.25)' : claim.uncertainty_level === 'Moderate' ? 'rgba(245, 158, 11, 0.25)' : 'rgba(244, 63, 94, 0.25)'}`,
            color: claim.uncertainty_level === 'Low' ? '#34d399' : claim.uncertainty_level === 'Moderate' ? '#fbbf24' : '#f87171'
          }}>
            {claim.uncertainty_level} Uncertainty
          </span>

          {/* Issue Flags */}
          {claim.flags?.internal_contradiction && (
            <span style={{ fontSize: '0.72rem', color: '#c084fc', background: 'rgba(168, 85, 247, 0.15)', border: '1px solid rgba(168, 85, 247, 0.3)', padding: '2px 8px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <AlertOctagon size={12} /> Internal Conflict
            </span>
          )}

          {claim.flags?.source_disagreement && (
            <span style={{ fontSize: '0.72rem', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.15)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '2px 8px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <HelpCircle size={12} /> Conflicting Sources
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (onJumpToAnswer) onJumpToAnswer(claim.claim_id);
            }}
            className="btn-secondary"
            style={{ padding: '4px 10px', fontSize: '0.75rem', gap: '4px' }}
            title="Locate this claim in the original answer"
          >
            <Eye size={12} /> Locate in Text
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: '4px' }}
            title={expanded ? 'Collapse Card' : 'Expand Card'}
          >
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
        </div>
      </div>

      {/* Claim Text */}
      <h4 style={{
        fontSize: '0.98rem',
        color: '#ffffff',
        fontWeight: 600,
        lineHeight: 1.45,
        margin: '12px 0 10px 0'
      }}>
        "{claim.text}"
      </h4>

      {/* Concise Explanation */}
      <div style={{
        background: 'rgba(0, 0, 0, 0.3)',
        padding: '12px 16px',
        borderRadius: '10px',
        borderLeft: `3px solid ${meta.color}`,
        fontSize: '0.86rem',
        color: '#e2e8f0',
        lineHeight: 1.5,
        marginBottom: expanded ? '14px' : '0'
      }}>
        {claim.explanation}
      </div>

      {/* Inconsistency Details note if applicable */}
      {claim.inconsistency_details && (
        <div style={{
          background: 'rgba(168, 85, 247, 0.1)',
          border: '1px solid rgba(168, 85, 247, 0.25)',
          borderRadius: '8px',
          padding: '8px 12px',
          fontSize: '0.8rem',
          color: '#e9d5ff',
          marginBottom: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <GitCompare size={14} color="#c084fc" />
          <span><strong>Logical Conflict: </strong>{claim.inconsistency_details}</span>
        </div>
      )}

      {/* Expandable Ground-Truth Evidence Inspection */}
      {expanded && (
        <div style={{ marginTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '12px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FileText size={14} color="#6366f1" />
            Verified Source Ground-Truth Evidence
          </div>

          {/* Contradicting Evidence Excerpts */}
          {contradictingList.length > 0 && (
            <div style={{ marginBottom: '10px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#f43f5e', display: 'inline-block', marginBottom: '6px' }}>
                Conflict / Contradicting Evidence ({contradictingList.length}):
              </span>
              {contradictingList.map((ev, idx) => (
                <div key={idx} style={{
                  background: 'rgba(244, 63, 94, 0.05)',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid rgba(244, 63, 94, 0.2)',
                  borderLeft: '3px solid #f43f5e',
                  marginBottom: '8px',
                  fontSize: '0.83rem'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', color: '#fda4af', fontWeight: 600, fontSize: '0.78rem' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {ev.is_external ? <Globe size={12} /> : <FileText size={12} />}
                      {ev.source_name} (Page {ev.page_number || 1})
                    </span>
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                      {ev.is_external ? 'External Source' : 'User Reference'}
                    </span>
                  </div>
                  <p style={{ color: '#ffffff', fontStyle: 'italic', margin: 0 }}>
                    "{ev.excerpt}"
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Supporting Evidence Excerpts */}
          {supportingList.length > 0 && (
            <div style={{ marginBottom: '10px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#10b981', display: 'inline-block', marginBottom: '6px' }}>
                Supporting Evidence ({supportingList.length}):
              </span>
              {supportingList.map((ev, idx) => (
                <div key={idx} style={{
                  background: 'rgba(16, 185, 129, 0.05)',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                  borderLeft: '3px solid #10b981',
                  marginBottom: '8px',
                  fontSize: '0.83rem'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', color: '#a7f3d0', fontWeight: 600, fontSize: '0.78rem' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {ev.is_external ? <Globe size={12} /> : <FileText size={12} />}
                      {ev.source_name} (Page {ev.page_number || 1})
                    </span>
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                      {ev.is_external ? 'External Source' : 'User Reference'}
                    </span>
                  </div>
                  <p style={{ color: '#ffffff', fontStyle: 'italic', margin: 0 }}>
                    "{ev.excerpt}"
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* If no categorized list but general evidence exists */}
          {supportingList.length === 0 && contradictingList.length === 0 && generalEvidence.length > 0 && (
            <div>
              {generalEvidence.map((ev, idx) => (
                <div key={idx} style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  marginBottom: '8px',
                  fontSize: '0.83rem'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', color: '#a5b4fc', fontWeight: 500, fontSize: '0.78rem' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {ev.is_external ? <Globe size={12} /> : <FileText size={12} />}
                      {ev.source_name} (Page {ev.page_number || 1})
                    </span>
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>
                      {ev.is_external ? 'External Web Source' : 'Uploaded Reference'}
                    </span>
                  </div>
                  <p style={{ color: '#d1d5db', fontStyle: 'italic', margin: 0 }}>
                    "{ev.excerpt}"
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* No Evidence Available */}
          {supportingList.length === 0 && contradictingList.length === 0 && generalEvidence.length === 0 && (
            <div style={{ fontSize: '0.82rem', color: 'var(--text-dim)', fontStyle: 'italic', padding: '6px 0' }}>
              No matching reference passages found in provided documents.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

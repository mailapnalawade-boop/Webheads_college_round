import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Download,
  Info,
  ChevronDown,
  ChevronUp,
  AlertOctagon
} from 'lucide-react';
import { formatDocumentNames } from '../utils/reportUtils';

export default function AuditOverview({
  summary,
  documents,
  claims,
  activeFilter,
  setActiveFilter,
  onExportPdf
}) {
  const [showFormula, setShowFormula] = useState(false);

  if (!summary) return null;

  const getCredibilityColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 50) return '#f59e0b';
    return '#f43f5e';
  };

  const getCredibilityLabel = (score) => {
    if (score >= 80) return 'High Reliability';
    if (score >= 50) return 'Moderate Reliability';
    return 'Low Reliability / Requires Review';
  };

  const credColor = getCredibilityColor(summary.credibility_score);
  const docName = formatDocumentNames(documents, claims);
  const issuesCount = (summary.contradicted_count || 0) + (summary.insufficient_evidence_count || 0);

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      
      {/* Top Header Bar: Document, Status, and Actions */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        borderBottom: '1px solid var(--border-color)',
        paddingBottom: '18px',
        marginBottom: '20px',
        flexWrap: 'wrap',
        gap: '14px'
      }}>
        {/* Document Info & Status */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', flexWrap: 'wrap' }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '3px 10px',
              borderRadius: '20px',
              fontSize: '0.75rem',
              fontWeight: 600,
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#10b981'
            }}>
              <CheckCircle2 size={12} /> Audit Complete
            </span>

            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.8rem',
              color: 'var(--text-muted)'
            }}>
              <FileText size={14} color="#818cf8" />
              <strong style={{ color: '#ffffff' }}>{docName}</strong>
            </span>
          </div>

          <h2 style={{ fontSize: '1.3rem', color: '#ffffff', margin: 0, fontWeight: 700 }}>
            Audit Summary & Reliability Overview
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px', margin: 0 }}>
            Analyzed {summary.total_claims} factual claims against {summary.sources_analyzed || (documents?.length || 1)} reference source documents.
          </p>
        </div>

        {/* Action Button: Export PDF */}
        <button
          className="btn-secondary"
          onClick={onExportPdf}
          style={{ padding: '9px 18px', fontSize: '0.85rem' }}
          title="Download verified audit report as PDF"
        >
          <Download size={15} /> Export PDF Audit Report
        </button>
      </div>

      {/* Main Stats Row: Gauge + Metric Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(240px, 300px) 1fr',
        gap: '20px',
        alignItems: 'stretch',
        marginBottom: '20px'
      }}>
        {/* Credibility Score Box */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--border-color)',
          borderRadius: '14px',
          padding: '18px 20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Credibility Score
            </span>
            <span style={{
              fontSize: '0.75rem',
              padding: '2px 8px',
              borderRadius: '10px',
              background: `${credColor}1a`,
              color: credColor,
              fontWeight: 600
            }}>
              {getCredibilityLabel(summary.credibility_score)}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', margin: '8px 0' }}>
            <span style={{ fontSize: '2.5rem', fontWeight: 800, color: credColor, lineHeight: 1 }}>
              {summary.credibility_score}%
            </span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>
              reliability index
            </span>
          </div>

          <p style={{ fontSize: '0.78rem', color: 'var(--text-dim)', margin: '0 0 10px 0', lineHeight: 1.4 }}>
            Weighted benchmark evaluating corroborated claims against detected contradictions.
          </p>

          {/* Toggle Formula Breakdown */}
          <button
            onClick={() => setShowFormula(!showFormula)}
            style={{
              background: 'none',
              border: 'none',
              color: '#818cf8',
              fontSize: '0.78rem',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: 0,
              fontWeight: 500,
              textAlign: 'left'
            }}
          >
            <Info size={13} />
            {showFormula ? 'Hide calculation formula' : 'How is this score calculated?'}
            {showFormula ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>

        {/* Counts Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '12px'
        }}>
          {/* Total Claims */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.02)',
            padding: '16px',
            borderRadius: '12px',
            border: '1px solid var(--border-color)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 500 }}>
              Total Claims
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#ffffff', lineHeight: 1 }}>
              {summary.total_claims}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '4px' }}>
              Extracted statements
            </div>
          </div>

          {/* Supported Claims */}
          <div style={{
            background: 'var(--status-supported-bg)',
            padding: '16px',
            borderRadius: '12px',
            border: '1px solid var(--status-supported-border)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}>
            <div style={{ fontSize: '0.75rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '6px', fontWeight: 600 }}>
              <CheckCircle2 size={14} /> Supported
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#10b981', lineHeight: 1 }}>
              {summary.supported_count}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'rgba(16, 185, 129, 0.8)', marginTop: '4px' }}>
              Corroborated by source
            </div>
          </div>

          {/* Contradicted Claims */}
          <div style={{
            background: 'var(--status-contradicted-bg)',
            padding: '16px',
            borderRadius: '12px',
            border: '1px solid var(--status-contradicted-border)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}>
            <div style={{ fontSize: '0.75rem', color: '#f43f5e', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '6px', fontWeight: 600 }}>
              <XCircle size={14} /> Contradicted
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f43f5e', lineHeight: 1 }}>
              {summary.contradicted_count}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'rgba(244, 63, 94, 0.8)', marginTop: '4px' }}>
              Direct conflicts
            </div>
          </div>

          {/* Unverified Claims */}
          <div style={{
            background: 'var(--status-insufficient-bg)',
            padding: '16px',
            borderRadius: '12px',
            border: '1px solid var(--status-insufficient-border)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}>
            <div style={{ fontSize: '0.75rem', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '6px', fontWeight: 600 }}>
              <AlertTriangle size={14} /> Unverified
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f59e0b', lineHeight: 1 }}>
              {summary.insufficient_evidence_count}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'rgba(245, 158, 11, 0.8)', marginTop: '4px' }}>
              Missing evidence
            </div>
          </div>

          {/* Logical Conflicts (if any) */}
          {summary.internal_contradictions_detected > 0 && (
            <div style={{
              background: 'rgba(192, 132, 252, 0.12)',
              padding: '16px',
              borderRadius: '12px',
              border: '1px solid rgba(192, 132, 252, 0.35)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center'
            }}>
              <div style={{ fontSize: '0.75rem', color: '#c084fc', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '6px', fontWeight: 600 }}>
                <AlertOctagon size={14} /> Self-Conflicts
              </div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#c084fc', lineHeight: 1 }}>
                {summary.internal_contradictions_detected}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'rgba(192, 132, 252, 0.8)', marginTop: '4px' }}>
                Internal discrepancies
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Expandable Scoring Formula & Explanation Box */}
      {showFormula && (
        <div style={{
          background: 'rgba(0, 0, 0, 0.3)',
          border: '1px solid var(--border-color)',
          borderRadius: '10px',
          padding: '16px',
          marginBottom: '20px',
          fontSize: '0.82rem',
          color: 'var(--text-muted)'
        }}>
          <div style={{ fontWeight: 600, color: '#ffffff', marginBottom: '6px' }}>
            Credibility Score Formulation
          </div>
          <p style={{ margin: '0 0 8px 0', lineHeight: 1.5 }}>
            Score is computed via defensible weighted grading: Supported claims contribute 1.0 pt (100%), Unverified claims contribute 0.5 pt (neutral), and Contradicted claims receive 0.0 pt (penalized).
          </p>
          <div style={{
            background: 'rgba(255, 255, 255, 0.03)',
            padding: '8px 12px',
            borderRadius: '6px',
            fontFamily: 'monospace',
            color: '#a5b4fc',
            marginBottom: '8px'
          }}>
            Formula: ({summary.supported_count} supported + 0.5 × {summary.insufficient_evidence_count} unverified) / {summary.total_claims} total × 100 = {summary.credibility_score}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            Weights: Supported = 1.0 | Unverified = 0.5 | Contradicted = 0.0
          </div>
        </div>
      )}

      {/* View Filter Pills */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        borderTop: '1px solid var(--border-color)',
        paddingTop: '16px',
        flexWrap: 'wrap'
      }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginRight: '4px', fontWeight: 600, textTransform: 'uppercase' }}>
          Filter View:
        </span>

        {[
          { key: 'ALL', label: `All Claims (${summary.total_claims})` },
          { key: 'ISSUES', label: `Issues Requiring Attention (${issuesCount})`, highlight: issuesCount > 0 },
          { key: 'CONTRADICTED', label: `Contradicted (${summary.contradicted_count})` },
          { key: 'INSUFFICIENT_EVIDENCE', label: `Unverified (${summary.insufficient_evidence_count})` },
          { key: 'SUPPORTED', label: `Supported (${summary.supported_count})` }
        ].map((tab) => {
          const isActive = activeFilter === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveFilter(tab.key)}
              style={{
                padding: '6px 12px',
                borderRadius: '8px',
                fontSize: '0.78rem',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                background: isActive
                  ? 'rgba(99, 102, 241, 0.25)'
                  : 'rgba(255, 255, 255, 0.04)',
                color: isActive ? '#a5b4fc' : 'var(--text-muted)',
                outline: isActive ? '1px solid rgba(99, 102, 241, 0.5)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

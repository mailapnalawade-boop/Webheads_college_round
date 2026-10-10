<<<<<<< HEAD
import React from 'react';
import AuditOverview from './AuditOverview';
=======
import React, { useState } from 'react';
import {
  CheckCircle2, XCircle, AlertTriangle, Shield, Download,
  GitCompare, ShieldAlert, FileText, Code, Info
} from 'lucide-react';

export default function SummaryDashboard({
  summary,
  activeFilter,
  setActiveFilter,
  onExportMarkdown,
  onExportJson,
  onExportPdf,
  modelInfo,
  verificationMode
}) {
  const [showFormula, setShowFormula] = useState(false);

  if (!summary) return null;

  const getCredibilityColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 50) return '#f59e0b';
    return '#f43f5e';
  };

  const credColor = getCredibilityColor(summary.credibility_score);
>>>>>>> ec6e633c716b8e29e61a630b74e1116960f129a3

export default function SummaryDashboard({
  summary,
  documents,
  claims,
  activeFilter,
  setActiveFilter,
  onExportPdf
}) {
  return (
<<<<<<< HEAD
    <AuditOverview
      summary={summary}
      documents={documents}
      claims={claims}
      activeFilter={activeFilter}
      setActiveFilter={setActiveFilter}
      onExportPdf={onExportPdf}
    />
=======
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      
      {/* Upper Metrics Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Credibility Gauge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            position: 'relative',
            width: '92px',
            height: '92px',
            borderRadius: '50%',
            background: `conic-gradient(${credColor} ${summary.credibility_score * 3.6}deg, rgba(255,255,255,0.08) 0deg)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 0 20px ${credColor}33`,
            flexShrink: 0
          }}>
            <div style={{
              width: '76px',
              height: '76px',
              borderRadius: '50%',
              background: '#0d1322',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <span style={{ fontSize: '1.45rem', fontWeight: 800, color: credColor, lineHeight: 1 }}>
                {summary.credibility_score}%
              </span>
              <span style={{ fontSize: '0.62rem', color: 'var(--text-dim)', letterSpacing: '0.05em', fontWeight: 700, marginTop: '2px' }}>
                CREDIBILITY
              </span>
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '1.25rem', color: '#ffffff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Shield size={22} color={credColor} />
                Audit Reliability Dashboard
              </h2>
              <button
                onClick={() => setShowFormula(!showFormula)}
                style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                title="View Credibility Formula Breakdown"
              >
                <Info size={16} />
              </button>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
              Audited {summary.total_claims} factual claims against {summary.sources_analyzed} reference source documents • {modelInfo || (verificationMode === 'llm_api' ? 'Cloud AI Verification' : 'Offline Deterministic Rules')}
            </p>
          </div>
        </div>

        {/* Export Report Actions */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            className="btn-secondary"
            onClick={onExportMarkdown}
            style={{ padding: '8px 14px', fontSize: '0.82rem' }}
            title="Download full audit report as Markdown"
          >
            <FileText size={14} /> Export Markdown
          </button>

          <button
            className="btn-secondary"
            onClick={onExportJson}
            style={{ padding: '8px 14px', fontSize: '0.82rem' }}
            title="Download audit results as JSON"
          >
            <Code size={14} /> Export JSON
          </button>

          <button
            className="btn-secondary"
            onClick={onExportPdf}
            style={{ padding: '8px 14px', fontSize: '0.82rem' }}
            title="Download audit report as PDF"
          >
            <Download size={14} /> Export PDF
          </button>
        </div>
      </div>

      {/* Credibility Formula Breakdown Box (collapsible) */}
      {showFormula && (
        <div style={{
          background: 'rgba(0, 0, 0, 0.4)',
          border: '1px solid var(--border-color)',
          borderRadius: '10px',
          padding: '12px 16px',
          marginBottom: '20px',
          fontSize: '0.82rem',
          color: 'var(--text-muted)'
        }}>
          <strong style={{ color: '#ffffff' }}>Mathematical Score Formula: </strong>
          <code>(Supported [1.0] + 0.5 * Insufficient [0.5]) / Total Claims * 100</code>
          <div style={{ marginTop: '4px', color: 'var(--text-dim)', fontSize: '0.78rem' }}>
            Contradicted claims (factual falsehoods) and logical inconsistencies receive 0.0 points. Unverified claims receive neutral 0.5 credit.
          </div>
        </div>
      )}

      {/* 6 Compact Metric Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: '12px',
        marginBottom: '20px'
      }}>
        {/* Total Claims */}
        <div
          onClick={() => setActiveFilter('ALL')}
          style={{
            background: activeFilter === 'ALL' ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.03)',
            padding: '14px 16px',
            borderRadius: '12px',
            border: `1px solid ${activeFilter === 'ALL' ? 'rgba(99, 102, 241, 0.5)' : 'var(--border-color)'}`,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Total Unique Claims</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff' }}>{summary.total_claims}</div>
        </div>

        {/* Supported */}
        <div
          onClick={() => setActiveFilter('SUPPORTED')}
          style={{
            background: 'var(--status-supported-bg)',
            padding: '14px 16px',
            borderRadius: '12px',
            border: `1px solid ${activeFilter === 'SUPPORTED' ? '#10b981' : 'var(--status-supported-border)'}`,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px', fontWeight: 600 }}>
            <CheckCircle2 size={14} /> Supported
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#10b981' }}>{summary.supported_count}</div>
        </div>

        {/* Contradicted */}
        <div
          onClick={() => setActiveFilter('CONTRADICTED')}
          style={{
            background: 'var(--status-contradicted-bg)',
            padding: '14px 16px',
            borderRadius: '12px',
            border: `1px solid ${activeFilter === 'CONTRADICTED' ? '#f43f5e' : 'var(--status-contradicted-border)'}`,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#f43f5e', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px', fontWeight: 600 }}>
            <XCircle size={14} /> Contradicted
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f43f5e' }}>{summary.contradicted_count}</div>
        </div>

        {/* Insufficient Evidence */}
        <div
          onClick={() => setActiveFilter('INSUFFICIENT_EVIDENCE')}
          style={{
            background: 'var(--status-insufficient-bg)',
            padding: '14px 16px',
            borderRadius: '12px',
            border: `1px solid ${activeFilter === 'INSUFFICIENT_EVIDENCE' ? '#f59e0b' : 'var(--status-insufficient-border)'}`,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px', fontWeight: 600 }}>
            <AlertTriangle size={14} /> Insufficient Evidence
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f59e0b' }}>{summary.insufficient_evidence_count}</div>
        </div>

        {/* Logical Inconsistencies */}
        <div
          onClick={() => setActiveFilter('LOGICAL_INCONSISTENCY')}
          style={{
            background: 'var(--status-inconsistent-bg)',
            padding: '14px 16px',
            borderRadius: '12px',
            border: `1px solid ${activeFilter === 'LOGICAL_INCONSISTENCY' ? '#a855f7' : 'var(--status-inconsistent-border)'}`,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#c084fc', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px', fontWeight: 600 }}>
            <GitCompare size={14} /> Logic Inconsistencies
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#c084fc' }}>
            {summary.logical_inconsistency_count}
          </div>
        </div>

        {/* Unsafe Recommendations */}
        <div
          style={{
            background: summary.unsafe_recommendations_count > 0 ? 'rgba(239, 68, 68, 0.12)' : 'rgba(255, 255, 255, 0.03)',
            padding: '14px 16px',
            borderRadius: '12px',
            border: `1px solid ${summary.unsafe_recommendations_count > 0 ? 'rgba(239, 68, 68, 0.35)' : 'var(--border-color)'}`
          }}
        >
          <div style={{ fontSize: '0.78rem', color: summary.unsafe_recommendations_count > 0 ? '#ef4444' : 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px', fontWeight: 600 }}>
            <ShieldAlert size={14} /> Unsafe Recommendations
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: summary.unsafe_recommendations_count > 0 ? '#ef4444' : '#ffffff' }}>
            {summary.unsafe_recommendations_count}
          </div>
        </div>
      </div>

      {/* 5 Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderTop: '1px solid var(--border-color)', paddingTop: '16px', flexWrap: 'wrap' }}>
        {[
          { key: 'ALL', label: `All Claims (${summary.total_claims})` },
          { key: 'SUPPORTED', label: `Supported (${summary.supported_count})` },
          { key: 'CONTRADICTED', label: `Contradicted (${summary.contradicted_count})` },
          { key: 'INSUFFICIENT_EVIDENCE', label: `Insufficient Evidence (${summary.insufficient_evidence_count})` },
          { key: 'LOGICAL_INCONSISTENCY', label: `Logic Inconsistency (${summary.logical_inconsistency_count})` }
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveFilter(tab.key)}
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              fontSize: '0.78rem',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              background: activeFilter === tab.key ? 'rgba(99, 102, 241, 0.25)' : 'rgba(255,255,255,0.04)',
              color: activeFilter === tab.key ? '#a5b4fc' : 'var(--text-muted)',
              outline: activeFilter === tab.key ? '1px solid rgba(99, 102, 241, 0.5)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
>>>>>>> ec6e633c716b8e29e61a630b74e1116960f129a3
  );
}

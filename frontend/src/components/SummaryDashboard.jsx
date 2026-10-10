import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Shield, Download, RefreshCw, AlertOctagon } from 'lucide-react';

export default function SummaryDashboard({ summary, activeFilter, setActiveFilter, onExportPdf }) {
  if (!summary) return null;

  const getCredibilityColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 50) return '#f59e0b';
    return '#f43f5e';
  };

  const credColor = getCredibilityColor(summary.credibility_score);

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      
      {/* Upper Metrics Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Credibility Gauge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            position: 'relative',
            width: '90px',
            height: '90px',
            borderRadius: '50%',
            background: `conic-gradient(${credColor} ${summary.credibility_score * 3.6}deg, rgba(255,255,255,0.08) 0deg)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 0 20px ${credColor}33`
          }}>
            <div style={{
              width: '74px',
              height: '74px',
              borderRadius: '50%',
              background: '#0d1322',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <span style={{ fontSize: '1.4rem', fontWeight: 800, color: credColor, lineHeight: 1 }}>
                {summary.credibility_score}%
              </span>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-dim)', uppercase: 'true', fontWeight: 600 }}>
                CREDIBILITY
              </span>
            </div>
          </div>

          <div>
            <h2 style={{ fontSize: '1.2rem', color: '#ffffff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Shield size={20} color={credColor} />
              Answer Reliability Audit Summary
            </h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Analyzed {summary.total_claims} factual claims against {summary.sources_analyzed} reference sources.
            </p>
          </div>
        </div>

        {/* PDF Export Button */}
        <button className="btn-secondary" onClick={onExportPdf} style={{ padding: '10px 18px' }}>
          <Download size={16} /> Export PDF Audit Report
        </button>
      </div>

      {/* Metric Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px', marginBottom: '20px' }}>
        
        {/* Total Claims */}
        <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '14px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Total Claims</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#ffffff' }}>{summary.total_claims}</div>
        </div>

        {/* Supported */}
        <div style={{ background: 'var(--status-supported-bg)', padding: '14px', borderRadius: '12px', border: '1px solid var(--status-supported-border)' }}>
          <div style={{ fontSize: '0.8rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
            <CheckCircle2 size={14} /> Supported
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#10b981' }}>{summary.supported_count}</div>
        </div>

        {/* Contradicted */}
        <div style={{ background: 'var(--status-contradicted-bg)', padding: '14px', borderRadius: '12px', border: '1px solid var(--status-contradicted-border)' }}>
          <div style={{ fontSize: '0.8rem', color: '#f43f5e', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
            <XCircle size={14} /> Contradicted
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f43f5e' }}>{summary.contradicted_count}</div>
        </div>

        {/* Insufficient Evidence */}
        <div style={{ background: 'var(--status-insufficient-bg)', padding: '14px', borderRadius: '12px', border: '1px solid var(--status-insufficient-border)' }}>
          <div style={{ fontSize: '0.8rem', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
            <AlertTriangle size={14} /> Unverified
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f59e0b' }}>{summary.insufficient_evidence_count}</div>
        </div>

        {/* Internal Discrepancies */}
        <div style={{ background: summary.internal_contradictions_detected > 0 ? 'rgba(244, 63, 94, 0.15)' : 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '12px', border: `1px solid ${summary.internal_contradictions_detected > 0 ? 'rgba(244, 63, 94, 0.4)' : 'var(--border-color)'}` }}>
          <div style={{ fontSize: '0.8rem', color: summary.internal_contradictions_detected > 0 ? '#f43f5e' : 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
            <AlertOctagon size={14} /> Self-Conflicts
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: summary.internal_contradictions_detected > 0 ? '#f43f5e' : '#ffffff' }}>
            {summary.internal_contradictions_detected}
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
        {['ALL', 'SUPPORTED', 'CONTRADICTED', 'INSUFFICIENT_EVIDENCE'].map((filter) => (
          <button
            key={filter}
            onClick={() => setActiveFilter(filter)}
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              fontSize: '0.8rem',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              background: activeFilter === filter ? 'rgba(99, 102, 241, 0.25)' : 'rgba(255,255,255,0.04)',
              color: activeFilter === filter ? '#a5b4fc' : 'var(--text-muted)',
              outline: activeFilter === filter ? '1px solid rgba(99, 102, 241, 0.5)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            {filter.replace('_', ' ')}
          </button>
        ))}
      </div>
    </div>
  );
}

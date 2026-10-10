import React from 'react';
import { ShieldAlert, ShieldCheck, ArrowRight, Info, CheckCircle2 } from 'lucide-react';

export default function SafetyRecommendationsSection({ safetyAnalysis }) {
  if (!safetyAnalysis) return null;

  const recs = safetyAnalysis.recommendations || [];
  const hasFlags = recs.length > 0;

  const getSeverityStyle = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return {
          bg: 'rgba(239, 68, 68, 0.15)',
          border: 'rgba(239, 68, 68, 0.4)',
          color: '#ef4444',
          label: 'CRITICAL HAZARD'
        };
      case 'high':
        return {
          bg: 'rgba(249, 115, 22, 0.15)',
          border: 'rgba(249, 115, 22, 0.4)',
          color: '#f97316',
          label: 'HIGH RISK'
        };
      case 'moderate':
        return {
          bg: 'rgba(245, 158, 11, 0.15)',
          border: 'rgba(245, 158, 11, 0.4)',
          color: '#f59e0b',
          label: 'MODERATE CONCERN'
        };
      case 'low':
      default:
        return {
          bg: 'rgba(59, 130, 246, 0.15)',
          border: 'rgba(59, 130, 246, 0.4)',
          color: '#60a5fa',
          label: 'LOW SENSITIVITY'
        };
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            background: hasFlags ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
            padding: '8px',
            borderRadius: '10px',
            border: `1px solid ${hasFlags ? 'rgba(239, 68, 68, 0.35)' : 'rgba(16, 185, 129, 0.35)'}`
          }}>
            {hasFlags ? <ShieldAlert size={20} color="#ef4444" /> : <ShieldCheck size={20} color="#10b981" />}
          </div>
          <div>
            <h3 style={{ fontSize: '1.1rem', color: '#ffffff', margin: 0 }}>
              Potentially Unsafe Recommendations
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
              Automated screening for clinical, financial, legal, and operational directives
            </p>
          </div>
        </div>

        <span style={{
          fontSize: '0.78rem',
          padding: '4px 10px',
          borderRadius: '16px',
          fontWeight: 600,
          background: hasFlags ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
          border: `1px solid ${hasFlags ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
          color: hasFlags ? '#ef4444' : '#10b981'
        }}>
          {hasFlags ? `${recs.length} Actionable Concern${recs.length > 1 ? 's' : ''} Flagged` : '0 Actionable Concerns Flagged'}
        </span>
      </div>

      {/* Flagged Items or Neutral Result */}
      {hasFlags ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {recs.map((rec, idx) => {
            const sev = getSeverityStyle(rec.severity);
            return (
              <div key={rec.recommendation_id || idx} style={{
                background: 'rgba(0, 0, 0, 0.35)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderLeft: `4px solid ${sev.color}`,
                borderRadius: '12px',
                padding: '18px 20px'
              }}>
                {/* Upper bar: Severity & Title */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
                  <span style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '12px',
                    background: sev.bg,
                    border: `1px solid ${sev.border}`,
                    color: sev.color
                  }}>
                    {sev.label}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    Flag #{idx + 1}
                  </span>
                </div>

                {/* Quoted Text */}
                <blockquote style={{
                  margin: '0 0 12px 0',
                  padding: '8px 14px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  borderLeft: '2px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: '4px',
                  fontStyle: 'italic',
                  fontSize: '0.9rem',
                  color: '#ffffff',
                  lineHeight: 1.5
                }}>
                  "{rec.text}"
                </blockquote>

                {/* Reason & Potential Risk */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', marginBottom: '12px' }}>
                  <div>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600, display: 'block', marginBottom: '2px' }}>
                      REASON FLAGGED
                    </span>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-main)' }}>
                      {rec.reason}
                    </span>
                  </div>

                  <div>
                    <span style={{ fontSize: '0.78rem', color: '#f87171', fontWeight: 600, display: 'block', marginBottom: '2px' }}>
                      POTENTIAL RISK
                    </span>
                    <span style={{ fontSize: '0.85rem', color: '#fca5a5' }}>
                      {rec.potential_risk}
                    </span>
                  </div>
                </div>

                {/* Safer Alternative */}
                {rec.safer_alternative && (
                  <div style={{
                    background: 'rgba(16, 185, 129, 0.08)',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    color: '#6ee7b7',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    marginBottom: '8px'
                  }}>
                    <ArrowRight size={16} style={{ marginTop: '2px', flexShrink: 0 }} />
                    <div>
                      <strong style={{ color: '#a7f3d0' }}>Recommended Safer Action: </strong>
                      {rec.safer_alternative}
                    </div>
                  </div>
                )}

                {/* Limitations / Evidence note */}
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Info size={12} />
                  <span>
                    {rec.relevant_limitations || 'Automated rule screening against uploaded reference protocol; not a licensed professional diagnosis.'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Neutral State (no false guarantees of safety) */
        <div style={{
          background: 'rgba(16, 185, 129, 0.05)',
          border: '1px solid rgba(16, 185, 129, 0.2)',
          borderRadius: '12px',
          padding: '18px 20px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px'
        }}>
          <CheckCircle2 size={20} color="#10b981" style={{ marginTop: '2px', flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: '0.9rem', color: '#a7f3d0', fontWeight: 600, marginBottom: '4px' }}>
              No potentially unsafe recommendations were flagged by the automated audit.
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0, lineHeight: 1.5 }}>
              The automated scan detected no hazardous medication discontinuations, dosage divergences, unqualified financial imperatives, or security bypass directives.
              <span style={{ display: 'block', marginTop: '4px', color: 'var(--text-dim)', fontSize: '0.75rem' }}>
                * Note: Automated evaluation does not substitute professional medical, legal, or financial consultation. Absence of flagged items does not constitute a definitive guarantee of clinical or operational safety.
              </span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

import React from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import IssueCard from './IssueCard';
import { deduplicateClaims } from '../utils/reportUtils';

export default function IssuesAttentionSection({
  claims,
  selectedClaimId,
  setSelectedClaimId
}) {
  // Filter for issues (Contradicted, Unverified, or Internal Contradiction)
  const rawIssues = claims.filter(
    (c) => c.verdict === 'CONTRADICTED' || c.verdict === 'INSUFFICIENT_EVIDENCE' || c.verdict === 'AMBIGUOUS' || c.flags?.internal_contradiction
  );

  // Sort: Contradicted & Internal Contradictions first, then Unverified
  const sortedIssues = [...rawIssues].sort((a, b) => {
    const scoreA = (a.flags?.internal_contradiction ? 3 : 0) + (a.verdict === 'CONTRADICTED' ? 2 : 1);
    const scoreB = (b.flags?.internal_contradiction ? 3 : 0) + (b.verdict === 'CONTRADICTED' ? 2 : 1);
    return scoreB - scoreA;
  });

  const issues = deduplicateClaims(sortedIssues);
  const contradictedCount = issues.filter(c => c.verdict === 'CONTRADICTED').length;
  const unverifiedCount = issues.filter(c => c.verdict === 'INSUFFICIENT_EVIDENCE' || c.verdict === 'AMBIGUOUS').length;

  if (issues.length === 0) {
    return (
      <div className="glass-panel" style={{
        padding: '24px',
        marginBottom: '24px',
        border: '1px solid rgba(16, 185, 129, 0.3)',
        background: 'rgba(16, 185, 129, 0.05)',
        display: 'flex',
        alignItems: 'center',
        gap: '14px'
      }}>
        <CheckCircle2 size={24} color="#10b981" style={{ flexShrink: 0 }} />
        <div>
          <h3 style={{ fontSize: '1.05rem', color: '#10b981', margin: 0, fontWeight: 600 }}>
            No Issues Requiring Attention
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
            All analyzed claims in the provided answer are verified and corroborated by the source documentation.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ marginBottom: '28px' }}>
      {/* Section Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '8px',
            background: 'rgba(244, 63, 94, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <AlertCircle size={16} color="#f43f5e" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: '#ffffff', margin: 0, fontWeight: 700 }}>
              Issues Requiring Attention ({issues.length})
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
              Prioritized review of contradicted ({contradictedCount}) and unverified ({unverifiedCount}) claims.
            </p>
          </div>
        </div>
      </div>

      {/* Issues Cards List */}
      <div>
        {issues.map((claim) => (
          <IssueCard
            key={claim.claim_id}
            claim={claim}
            isSelected={selectedClaimId === claim.claim_id}
            onSelect={() => setSelectedClaimId(claim.claim_id)}
          />
        ))}
      </div>
    </div>
  );
}

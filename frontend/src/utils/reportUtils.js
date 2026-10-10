/**
 * Utility functions for formatting Second Opinion audit reports.
 * Emphasizes concise, specific, and non-repetitive explanations.
 */

export function getIssueClassification(claim) {
  if (claim.flags?.internal_contradiction) {
    return {
      type: 'LOGICAL_INCONSISTENCY',
      label: 'Logical Inconsistency',
      badgeText: 'LOGICAL CONFLICT',
      color: '#c084fc',
      bg: 'rgba(192, 132, 252, 0.12)',
      border: 'rgba(192, 132, 252, 0.35)',
      description: 'Contradicts another statement within the same audited text.'
    };
  }

  switch (claim.verdict) {
    case 'CONTRADICTED':
      return {
        type: 'CONTRADICTED',
        label: 'Contradicted',
        badgeText: 'CONTRADICTED',
        color: '#f43f5e',
        bg: 'var(--status-contradicted-bg)',
        border: 'var(--status-contradicted-border)',
        description: 'Directly conflicts with verified facts in reference documents.'
      };
    case 'AMBIGUOUS':
      return {
        type: 'AMBIGUOUS',
        label: 'Ambiguous',
        badgeText: 'AMBIGUOUS',
        color: '#60a5fa',
        bg: 'var(--status-insufficient-bg)',
        border: 'var(--status-insufficient-border)',
        description: 'Evidence is partial or conflicting. This is not counted as an error.'
      };
    case 'INSUFFICIENT_EVIDENCE':
      return {
        type: 'UNVERIFIED',
        label: 'Unverified',
        badgeText: 'UNVERIFIED',
        color: '#f59e0b',
        bg: 'var(--status-insufficient-bg)',
        border: 'var(--status-insufficient-border)',
        description: 'Reference documents lack evidence to corroborate or refute this claim.'
      };
    case 'SUPPORTED':
    default:
      return {
        type: 'SUPPORTED',
        label: 'Supported',
        badgeText: 'SUPPORTED',
        color: '#10b981',
        bg: 'var(--status-supported-bg)',
        border: 'var(--status-supported-border)',
        description: 'Fully corroborated by source document evidence.'
      };
  }
}

export function getIssueTitle(claim) {
  if (claim.flags?.internal_contradiction) {
    return 'Internal Statement Conflict';
  }

  const exp = (claim.explanation || '').toLowerCase();

  if (claim.verdict === 'CONTRADICTED') {
    if (exp.includes('numerical') || exp.includes('discrepancy') || exp.includes('value(s)')) {
      return 'Numerical / Data Discrepancy';
    }
    if (exp.includes('reversed') || exp.includes('prioritiz') || exp.includes('preference') || exp.includes('directional')) {
      return 'Contradictory Recommendation';
    }
    if (exp.includes('polarity') || exp.includes('opposite') || exp.includes('affirmative')) {
      return 'Opposing Factual Statement';
    }
    return 'Factual Contradiction';
  }

  if (claim.verdict === 'INSUFFICIENT_EVIDENCE') {
    if (exp.includes('definition')) {
      return 'Unverified Definition';
    }
    if (exp.includes('action or event')) {
      return 'Unverified Action / Event';
    }
    if (!claim.evidence || claim.evidence.length === 0 || exp.includes('no relevant document')) {
      return 'Missing Source Verification';
    }
    return 'Unsubstantiated Claim';
  }

  return 'Corroborated Statement';
}

export function getConciseWhyItMatters(claim) {
  const raw = (claim.explanation || '').trim();

  // Clean fallback pattern: "Numerical discrepancy: Claim references value(s) [...] which conflicts with source evidence '...'"
  const numMatch = raw.match(/Numerical discrepancy:\s*Claim references value\(s\)\s*(\[.*?\]|\d+)/i);
  if (numMatch) {
    const vals = numMatch[1].replace(/[[\]']/g, '');
    return `The stated value (${vals}) directly contradicts the documented figures in the reference source.`;
  }

  // Clean fallback pattern: "Polarity contradiction: Claim is affirmative whereas reference source states the opposite."
  if (/polarity contradiction/i.test(raw)) {
    return 'The claim makes an affirmative statement, whereas the source document specifies the opposite.';
  }

  // Clean fallback pattern: "Reversed recommendation contradiction" or "Directional contradiction"
  if (/reversed recommendation|directional contradiction|evaluative contradiction/i.test(raw)) {
    return 'The claim inverts the priority or protocol mandated by the reference document.';
  }

  // Clean fallback pattern: "Internal ... contradiction: Claim X ... conflicts with Claim Y"
  if (/internal.*conflict|internal.*contradiction/i.test(raw)) {
    return 'This assertion is inconsistent with another claim made in the same response.';
  }

  // Clean fallback pattern: "No relevant document or reference context was found"
  if (/no relevant document/i.test(raw)) {
    return 'The provided reference documents do not mention or corroborate this statement.';
  }

  // Clean fallback pattern: "Source document '...' does not contain sufficient evidence"
  if (/does not contain sufficient evidence|lacks evidence/i.test(raw)) {
    return 'The source materials touch on related terminology but lack conclusive evidence for this specific assertion.';
  }

  // Clean fallback pattern: "Source document '...' directly supports this claim."
  if (/directly supports this claim/i.test(raw)) {
    return 'Directly verified by the source documentation.';
  }

  // General AI cleanup: remove robotic prefixes and repetitions
  let cleaned = raw
    .replace(/^Based on the provided (evidence|documents?),?\s*/i, '')
    .replace(/^According to the reference (evidence|documents?),?\s*/i, '')
    .replace(/^The source document (explicitly|directly)\s*/i, 'The source document ')
    .trim();

  // Avoid repeating the exact claim inside the explanation
  if (claim.text && cleaned.includes(`"${claim.text}"`)) {
    cleaned = cleaned.replace(`"${claim.text}"`, 'the stated claim');
  } else if (claim.text && cleaned.includes(`'${claim.text}'`)) {
    cleaned = cleaned.replace(`'${claim.text}'`, 'the stated claim');
  }

  // Keep to maximum 2 sentences
  const sentences = cleaned.split(/(?<=[.!?])\s+/);
  if (sentences.length > 2) {
    cleaned = sentences.slice(0, 2).join(' ');
  }

  return cleaned || 'Requires verification against reference source documentation.';
}

export function getSuggestedCorrection(claim) {
  if (claim.verdict === 'SUPPORTED') {
    return null;
  }

  const exp = (claim.explanation || '').toLowerCase();
  const topEvidence = claim.evidence && claim.evidence.length > 0 ? claim.evidence[0] : null;

  if (claim.flags?.internal_contradiction) {
    return 'Reconcile mutually conflicting statements across the text to maintain factual consistency.';
  }

  if (claim.verdict === 'CONTRADICTED') {
    if (exp.includes('numerical') || exp.includes('discrepancy') || exp.includes('value(s)')) {
      if (topEvidence?.source_name) {
        return `Update the figure to align with the verified value in ${topEvidence.source_name}.`;
      }
      return 'Correct the figure to match verified source data.';
    }

    if (exp.includes('reversed') || exp.includes('preference') || exp.includes('directional')) {
      return 'Align the recommended course of action with the protocol established in the reference source.';
    }

    if (exp.includes('polarity') || exp.includes('opposite')) {
      return 'Revise the statement to accurately reflect the negative or restrictive guidance in the reference source.';
    }

    if (topEvidence?.source_name) {
      return `Align statement with reference findings in ${topEvidence.source_name}.`;
    }
    return 'Revise statement to reflect documented source facts.';
  }

  // For unverified claims: omit correction unless there is a very clear next step
  // Per requirement 2: "Do not generate a recommendation for every claim. Omit it when no meaningful correction is needed."
  return null;
}

export function getShortExcerpt(text, maxLength = 130) {
  if (!text) return '';
  const clean = text.replace(/\s+/g, ' ').trim();
  if (clean.length <= maxLength) return clean;
  const truncated = clean.substring(0, maxLength);
  const lastSpace = truncated.lastIndexOf(' ');
  return (lastSpace > 60 ? truncated.substring(0, lastSpace) : truncated) + '...';
}

export function deduplicateClaims(claims) {
  if (!claims || !Array.isArray(claims)) return [];
  const seen = new Set();
  const deduped = [];

  for (const c of claims) {
    const key = `${c.verdict}_${(c.text || '').trim().toLowerCase()}`;
    if (!seen.has(key)) {
      seen.add(key);
      deduped.push(c);
    }
  }

  return deduped;
}

export function formatDocumentNames(documents, claims = []) {
  if (documents && documents.length > 0) {
    const names = documents.map(d => d.filename || 'Uploaded Document').filter(Boolean);
    if (names.length === 1) return names[0];
    if (names.length > 1) return `${names[0]} (+${names.length - 1} more)`;
  }

  if (claims && claims.length > 0) {
    const sourceNames = new Set();
    claims.forEach(c => {
      c.evidence?.forEach(e => {
        if (e.source_name) sourceNames.add(e.source_name);
      });
    });
    const arr = Array.from(sourceNames);
    if (arr.length === 1) return arr[0];
    if (arr.length > 1) return `${arr[0]} (+${arr.length - 1} more)`;
  }

  return 'Audited Document';
}

import { jsPDF } from 'jspdf';
import {
  getIssueClassification,
  getIssueTitle,
  getConciseWhyItMatters,
  getSuggestedCorrection,
  getShortExcerpt,
  formatDocumentNames,
  deduplicateClaims
} from './reportUtils.js';

export function exportAuditPdf(auditResult, documents = []) {
  if (!auditResult) return;

  const doc = new jsPDF({
    unit: 'mm',
    format: 'a4',
    orientation: 'portrait'
  });

  const pageWidth = 210;
  const pageHeight = 297;
  const margin = 14;
  const contentWidth = pageWidth - (margin * 2); // 182mm
  let y = margin;

  const checkPageBreak = (neededHeight) => {
    if (y + neededHeight > pageHeight - 16) {
      doc.addPage();
      y = margin;
      return true;
    }
    return false;
  };

  const docName = formatDocumentNames(documents, auditResult.claims);
  const summary = auditResult.summary;

  // --- 1. Header Banner ---
  doc.setFillColor(15, 23, 42); // Slate 900
  doc.rect(margin, y, contentWidth, 24, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.setTextColor(255, 255, 255);
  doc.text('SECOND OPINION — AUDIT REPORT', margin + 6, y + 8);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(148, 163, 184); // Slate 400
  doc.text(`Document: ${docName}`, margin + 6, y + 14);
  doc.text(`Audit ID: ${auditResult.audit_id}  |  Generated: ${new Date(auditResult.timestamp || Date.now()).toLocaleDateString()}`, margin + 6, y + 19);

  // Status Badge in Header
  doc.setFillColor(16, 185, 129); // Emerald
  doc.roundedRect(pageWidth - margin - 32, y + 6, 26, 6, 2, 2, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(255, 255, 255);
  doc.text('AUDIT COMPLETE', pageWidth - margin - 31, y + 10.2);

  y += 28;

  // --- 2. Executive Summary Metrics Box ---
  checkPageBreak(30);
  doc.setFillColor(248, 250, 252); // Light background
  doc.setDrawColor(226, 232, 240); // Slate 200
  doc.rect(margin, y, contentWidth, 22, 'FD');

  // Credibility score pill
  const credScore = summary.credibility_score;
  let scoreColor = [225, 29, 72]; // Rose
  if (credScore >= 80) scoreColor = [5, 150, 105]; // Green
  else if (credScore >= 50) scoreColor = [217, 119, 6]; // Amber

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(18);
  doc.setTextColor(scoreColor[0], scoreColor[1], scoreColor[2]);
  doc.text(`${credScore}%`, margin + 6, y + 12);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(100, 116, 139);
  doc.text('CREDIBILITY SCORE', margin + 6, y + 17);

  // Metric Columns
  const startX = margin + 50;
  const colWidth = (contentWidth - 50) / 4;

  const metrics = [
    { label: 'Total Claims', value: summary.total_claims, color: [30, 41, 59] },
    { label: 'Supported', value: summary.supported_count, color: [5, 150, 105] },
    { label: 'Contradicted', value: summary.contradicted_count, color: [225, 29, 72] },
    { label: 'Unverified', value: summary.insufficient_evidence_count, color: [217, 119, 6] }
  ];

  metrics.forEach((m, idx) => {
    const xPos = startX + (idx * colWidth);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    doc.setTextColor(m.color[0], m.color[1], m.color[2]);
    doc.text(String(m.value), xPos, y + 11);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(100, 116, 139);
    doc.text(m.label, xPos, y + 17);
  });

  y += 28;

  // --- 3. Issues Requiring Attention (Contradicted & Unverified claims) ---
  const allClaims = auditResult.claims || [];
  const rawIssues = allClaims.filter(
    (c) => c.verdict === 'CONTRADICTED' || c.verdict === 'INSUFFICIENT_EVIDENCE' || c.verdict === 'AMBIGUOUS' || c.flags?.internal_contradiction
  );

  // Sort Contradicted first, then Unverified
  const sortedIssues = [...rawIssues].sort((a, b) => {
    const scoreA = (a.flags?.internal_contradiction ? 3 : 0) + (a.verdict === 'CONTRADICTED' ? 2 : 1);
    const scoreB = (b.flags?.internal_contradiction ? 3 : 0) + (b.verdict === 'CONTRADICTED' ? 2 : 1);
    return scoreB - scoreA;
  });

  const issues = deduplicateClaims(sortedIssues);

  checkPageBreak(12);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(15, 23, 42);
  doc.text(`1. Issues Requiring Attention (${issues.length})`, margin, y);
  y += 5;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(100, 116, 139);
  doc.text('Review findings that conflict with or lack reference source corroboration.', margin, y);
  y += 6;

  if (issues.length === 0) {
    checkPageBreak(12);
    doc.setFillColor(240, 253, 244);
    doc.rect(margin, y, contentWidth, 10, 'F');
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8.5);
    doc.setTextColor(5, 150, 105);
    doc.text('No issues requiring attention. All claims were corroborated by source documentation.', margin + 4, y + 6.5);
    y += 14;
  } else {
    issues.forEach((issue, idx) => {
      const classification = getIssueClassification(issue);
      const title = getIssueTitle(issue);
      const whyItMatters = getConciseWhyItMatters(issue);
      const suggestedCorrection = getSuggestedCorrection(issue);
      const topEv = issue.evidence && issue.evidence.length > 0 ? issue.evidence[0] : null;

      // Estimate card height
      const claimLines = doc.splitTextToSize(`Claim: "${issue.text}"`, contentWidth - 8);
      const whyLines = doc.splitTextToSize(`Why it matters: ${whyItMatters}`, contentWidth - 8);
      const evText = topEv ? `Evidence (${topEv.source_name || 'Source'}, pg ${topEv.page_number || 1}): "${getShortExcerpt(topEv.excerpt, 140)}"` : 'Evidence: No verifying passage found in source documents.';
      const evLines = doc.splitTextToSize(evText, contentWidth - 8);
      const corrLines = suggestedCorrection ? doc.splitTextToSize(`Suggested correction: ${suggestedCorrection}`, contentWidth - 8) : [];

      const cardHeight = 12 + (claimLines.length * 4) + (whyLines.length * 3.8) + (evLines.length * 3.8) + (corrLines.length > 0 ? corrLines.length * 3.8 + 4 : 0);

      checkPageBreak(cardHeight + 4);

      // Card Background
      doc.setFillColor(255, 255, 255);
      doc.setDrawColor(226, 232, 240);
      doc.rect(margin, y, contentWidth, cardHeight, 'FD');

      // Left Accent Strip
      let accent = [225, 29, 72]; // Rose for Contradicted
      if (classification.type === 'UNVERIFIED') accent = [217, 119, 6];
      if (classification.type === 'LOGICAL_INCONSISTENCY') accent = [147, 51, 234];

      doc.setFillColor(accent[0], accent[1], accent[2]);
      doc.rect(margin, y, 2, cardHeight, 'F');

      let cardY = y + 5;

      // Issue Header & Badge
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8.5);
      doc.setTextColor(accent[0], accent[1], accent[2]);
      doc.text(`[${classification.badgeText}]`, margin + 5, cardY);

      doc.setTextColor(15, 23, 42);
      doc.text(`Issue ${idx + 1}: ${title}`, margin + 34, cardY);

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      doc.setTextColor(100, 116, 139);
      doc.text(`Confidence: ${Math.round((issue.confidence || 0.5) * 100)}%`, pageWidth - margin - 26, cardY);

      cardY += 5;

      // Claim Text
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.setTextColor(30, 41, 59);
      doc.text(claimLines, margin + 5, cardY);
      cardY += claimLines.length * 4;

      // Why it matters
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.8);
      doc.setTextColor(71, 85, 105);
      doc.text(whyLines, margin + 5, cardY);
      cardY += whyLines.length * 3.8;

      // Evidence
      doc.setFont('helvetica', 'italic');
      doc.setFontSize(7.5);
      doc.setTextColor(100, 116, 139);
      doc.text(evLines, margin + 5, cardY);
      cardY += evLines.length * 3.8;

      // Suggested Correction (if useful)
      if (suggestedCorrection) {
        cardY += 1;
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(7.5);
        doc.setTextColor(67, 56, 202); // Indigo
        doc.text(corrLines, margin + 5, cardY);
      }

      y += cardHeight + 4;
    });
  }

  y += 4;

  // --- 4. Supported Claims (Compact Grouped Section) ---
  const supportedClaims = deduplicateClaims(allClaims.filter((c) => c.verdict === 'SUPPORTED'));

  checkPageBreak(18);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(15, 23, 42);
  doc.text(`2. Supported Claims (${supportedClaims.length})`, margin, y);
  y += 5;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(100, 116, 139);
  doc.text('Statements verified and corroborated by the source documentation.', margin, y);
  y += 6;

  if (supportedClaims.length === 0) {
    checkPageBreak(10);
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(8);
    doc.setTextColor(100, 116, 139);
    doc.text('No supported claims identified in this audit.', margin, y);
    y += 8;
  } else {
    supportedClaims.forEach((claim, idx) => {
      const topEv = claim.evidence && claim.evidence.length > 0 ? claim.evidence[0] : null;
      const claimText = `${idx + 1}. "${claim.text}"`;
      const claimLines = doc.splitTextToSize(claimText, contentWidth - 42);
      const rowHeight = Math.max(8, claimLines.length * 4 + 3);

      checkPageBreak(rowHeight + 2);

      // Light row background
      doc.setFillColor(248, 250, 252);
      doc.rect(margin, y, contentWidth, rowHeight, 'F');

      // Checkmark icon indicator
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.setTextColor(5, 150, 105);
      doc.text('✓', margin + 3, y + 4.5);

      // Claim statement
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.8);
      doc.setTextColor(30, 41, 59);
      doc.text(claimLines, margin + 8, y + 4.5);

      // Source reference
      doc.setFont('helvetica', 'italic');
      doc.setFontSize(7);
      doc.setTextColor(100, 116, 139);
      const cite = topEv ? `${topEv.source_name || 'Doc'} (pg ${topEv.page_number || 1})` : 'Corroborated';
      doc.text(cite, pageWidth - margin - 34, y + 4.5);

      y += rowHeight + 2;
    });
  }

  y += 6;

  // --- 5. Audit Metadata & Methodology Section ---
  checkPageBreak(22);
  doc.setFillColor(241, 245, 249);
  doc.rect(margin, y, contentWidth, 18, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(30, 41, 59);
  doc.text('3. Audit Metadata & Methodology', margin + 4, y + 5);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(100, 116, 139);
  doc.text(`Scoring Formula: (Supported + 0.5 * Unverified) / Total * 100  |  Analyzed against ${summary.sources_analyzed || 1} reference document(s)`, margin + 4, y + 10);
  doc.text('Antigravity Second Opinion Engine — Verified with deterministic rule matrices and semantic cross-referencing.', margin + 4, y + 14.5);

  // --- Add Page Numbers to all pages ---
  const totalPages = doc.internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text(`Page ${i} of ${totalPages}`, pageWidth - margin - 18, pageHeight - 8);
    doc.text('Confidential — Second Opinion Audit Report', margin, pageHeight - 8);
  }

  doc.save(`Second_Opinion_Audit_${auditResult.audit_id}.pdf`);
}

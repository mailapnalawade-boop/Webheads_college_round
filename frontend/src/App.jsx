import React, { useState, useEffect } from 'react';
import jsPDF from 'jspdf';
import Header from './components/Header';
import InputSection from './components/InputSection';
import SummaryDashboard from './components/SummaryDashboard';
import ClaimHighlighter from './components/ClaimHighlighter';
import ClaimCard from './components/ClaimCard';
import { runAudit, getSampleData, getHealth } from './services/api';
import { AlertCircle } from 'lucide-react';

export default function App() {
  const [apiKey, setApiKey] = useState('');
  const [answerText, setAnswerText] = useState('');
  const [documents, setDocuments] = useState([]);
  const [options, setOptions] = useState({
    enable_web_search: false,
    force_deterministic_fallback: false,
    top_k_passages: 3
  });

  const [isLoading, setIsLoading] = useState(false);
  const [auditResult, setAuditResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [selectedClaimId, setSelectedClaimId] = useState(null);

  // Load sample dataset
  const handleLoadSample = async () => {
    try {
      const samples = await getSampleData();
      const medical = samples.medical_case;
      setAnswerText(medical.answer_text);
      setDocuments(medical.documents);
      setErrorMsg('');
    } catch (err) {
      setErrorMsg('Failed to fetch sample benchmark data.');
    }
  };

  // Run audit request
  const handleRunAudit = async () => {
    if (!answerText.trim()) return;

    setIsLoading(true);
    setErrorMsg('');
    try {
      const payload = {
        answer_text: answerText,
        documents: documents,
        options: options,
        api_key: apiKey || null
      };

      const result = await runAudit(payload);
      setAuditResult(result);
    } catch (err) {
      const detail = err.response?.data?.detail;
      let msg = 'Audit execution failed. Ensure backend server is running on port 8000.';
      if (typeof detail === 'string') {
        msg = detail;
      } else if (Array.isArray(detail)) {
        msg = detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
      } else if (err.message) {
        msg = err.message;
      }
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
    }
  };

  // Export PDF Report
  const handleExportPdf = () => {
    if (!auditResult) return;

    const doc = new jsPDF();
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(18);
    doc.text('Second Opinion — AI Answer Audit Report', 14, 20);

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(`Audit ID: ${auditResult.audit_id} | Date: ${new Date().toLocaleString()}`, 14, 28);
    doc.text(`Credibility Score: ${auditResult.summary.credibility_score}%`, 14, 34);
    doc.text(`Total Claims: ${auditResult.summary.total_claims} | Supported: ${auditResult.summary.supported_count} | Contradicted: ${auditResult.summary.contradicted_count} | Unverified: ${auditResult.summary.insufficient_evidence_count}`, 14, 40);

    doc.line(14, 44, 196, 44);

    let y = 52;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.text('Claim Level Breakdowns:', 14, y);
    y += 10;

    auditResult.claims.forEach((claim, idx) => {
      // Ensure page break if close to bottom
      if (y > 250) {
        doc.addPage();
        y = 20;
      }

      // 1. Claim Header & Verdict
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10);
      const headerText = `${idx + 1}. [${claim.verdict}] ${claim.text}`;
      const headerLines = doc.splitTextToSize(headerText, 175);
      doc.text(headerLines, 14, y);
      y += headerLines.length * 5 + 2;

      // 2. Explanation
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      const expText = `Explanation: ${claim.explanation}`;
      const expLines = doc.splitTextToSize(expText, 170);
      doc.text(expLines, 18, y);
      y += expLines.length * 4.5 + 2;

      // 3. Evidence Passages (if available)
      if (claim.evidence && claim.evidence.length > 0) {
        const topEv = claim.evidence[0];
        doc.setFont('helvetica', 'italic');
        const evText = `Source Evidence (${topEv.source_name}, pg ${topEv.page_number}): "${topEv.excerpt}"`;
        const evLines = doc.splitTextToSize(evText, 165);
        doc.text(evLines, 22, y);
        y += evLines.length * 4.5 + 4;
      } else {
        doc.setFont('helvetica', 'italic');
        doc.text(`Source Evidence: No relevant document evidence found.`, 22, y);
        y += 6;
      }

      y += 4; // Gap between claim cards
    });

    doc.save(`Second_Opinion_Audit_${auditResult.audit_id}.pdf`);
  };

  const filteredClaims = auditResult
    ? auditResult.claims.filter((c) => activeFilter === 'ALL' || c.verdict === activeFilter)
    : [];

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px 16px' }}>
      
      {/* Header */}
      <Header
        apiKey={apiKey}
        setApiKey={setApiKey}
        onLoadSample={handleLoadSample}
        isLiveMode={Boolean(apiKey)}
      />

      {/* Error Alert */}
      {errorMsg && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.15)',
          border: '1px solid rgba(244, 63, 94, 0.4)',
          borderRadius: '12px',
          padding: '14px 18px',
          marginBottom: '20px',
          color: '#f43f5e',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '0.9rem'
        }}>
          <AlertCircle size={20} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Input Setup Component */}
      <InputSection
        answerText={answerText}
        setAnswerText={setAnswerText}
        documents={documents}
        setDocuments={setDocuments}
        options={options}
        setOptions={setOptions}
        onRunAudit={handleRunAudit}
        isLoading={isLoading}
      />

      {/* Audit Results Dashboard & Claims */}
      {auditResult && (
        <div>
          {/* Summary Overview */}
          <SummaryDashboard
            summary={auditResult.summary}
            activeFilter={activeFilter}
            setActiveFilter={setActiveFilter}
            onExportPdf={handleExportPdf}
          />

          {/* Interactive Text Highlighter */}
          <ClaimHighlighter
            claims={auditResult.claims}
            originalText={auditResult.original_answer}
            selectedClaimId={selectedClaimId}
            setSelectedClaimId={setSelectedClaimId}
          />

          {/* Claims List */}
          <div style={{ marginTop: '24px' }}>
            <h3 style={{ fontSize: '1.1rem', color: '#ffffff', marginBottom: '16px' }}>
              Claim Evidence & Verification Breakdowns ({filteredClaims.length})
            </h3>

            {filteredClaims.map((claim) => (
              <ClaimCard
                key={claim.claim_id}
                claim={claim}
                isSelected={selectedClaimId === claim.claim_id}
                onSelect={() => setSelectedClaimId(claim.claim_id)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

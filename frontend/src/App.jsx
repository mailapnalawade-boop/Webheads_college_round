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
    doc.text(`Audit ID: ${auditResult.audit_id} | Date: ${new Date(auditResult.timestamp).toLocaleString()}`, 14, 28);
    doc.text(`Credibility Score: ${auditResult.summary.credibility_score}%`, 14, 34);
    doc.text(`Total Claims: ${auditResult.summary.total_claims} | Supported: ${auditResult.summary.supported_count} | Contradicted: ${auditResult.summary.contradicted_count} | Unverified: ${auditResult.summary.insufficient_evidence_count}`, 14, 40);

    doc.line(14, 44, 196, 44);

    let y = 52;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.text('Claim Level Breakdowns:', 14, y);
    y += 8;

    auditResult.claims.forEach((claim, idx) => {
      if (y > 270) {
        doc.addPage();
        y = 20;
      }
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10);
      doc.text(`${idx + 1}. [${claim.verdict}] ${claim.text}`, 14, y);
      y += 6;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.text(`Explanation: ${claim.explanation}`, 18, y, { maxWidth: 170 });
      y += 12;
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

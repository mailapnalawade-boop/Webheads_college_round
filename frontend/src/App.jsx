import React, { useState } from 'react';
import Header from './components/Header';
import InputSection from './components/InputSection';
import AuditOverview from './components/AuditOverview';
import ClaimHighlighter from './components/ClaimHighlighter';
import IssuesAttentionSection from './components/IssuesAttentionSection';
import SupportedClaimsSection from './components/SupportedClaimsSection';
import { exportAuditPdf } from './utils/pdfGenerator';
import { runAudit, getSampleData } from './services/api';
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

  // Load sample benchmark dataset
  const handleLoadSample = async () => {
    try {
      const samples = await getSampleData();
      const medical = samples.medical_case;
      setAnswerText(medical.answer_text);
      setDocuments(medical.documents);
      setErrorMsg('');
    } catch (err) {
      console.error(err);
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
      setActiveFilter('ALL');
      setSelectedClaimId(null);
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
    exportAuditPdf(auditResult, documents);
  };

  // Selection handler with auto-scroll
  const handleSelectClaim = (claimId) => {
    setSelectedClaimId(claimId);
    setTimeout(() => {
      const elem = document.getElementById(claimId);
      if (elem) {
        elem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }, 50);
  };

  const getFilteredIssuesClaims = () => {
    if (!auditResult) return [];
    if (activeFilter === 'CONTRADICTED') {
      return auditResult.claims.filter((c) => c.verdict === 'CONTRADICTED');
    }
    if (activeFilter === 'INSUFFICIENT_EVIDENCE') {
      return auditResult.claims.filter((c) => c.verdict === 'INSUFFICIENT_EVIDENCE');
    }
    return auditResult.claims;
  };

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
        <div style={{ marginTop: '24px' }}>
          
          {/* 1. Redesigned Audit Overview */}
          <AuditOverview
            summary={auditResult.summary}
            documents={documents}
            claims={auditResult.claims}
            activeFilter={activeFilter}
            setActiveFilter={setActiveFilter}
            onExportPdf={handleExportPdf}
          />

          {/* Interactive Text Highlighter */}
          <ClaimHighlighter
            claims={auditResult.claims}
            originalText={auditResult.original_answer}
            selectedClaimId={selectedClaimId}
            setSelectedClaimId={handleSelectClaim}
          />

          {/* 2. Prioritized Issues That Need Attention (Contradicted & Unverified first) */}
          {(activeFilter === 'ALL' || activeFilter === 'ISSUES' || activeFilter === 'CONTRADICTED' || activeFilter === 'INSUFFICIENT_EVIDENCE') && (
            <IssuesAttentionSection
              claims={getFilteredIssuesClaims()}
              selectedClaimId={selectedClaimId}
              setSelectedClaimId={handleSelectClaim}
            />
          )}

          {/* 3. Grouped Supported Claims (Collapsible, collapsed by default) */}
          {(activeFilter === 'ALL' || activeFilter === 'SUPPORTED') && (
            <SupportedClaimsSection
              claims={auditResult.claims}
              selectedClaimId={selectedClaimId}
              setSelectedClaimId={handleSelectClaim}
            />
          )}

        </div>
      )}
    </div>
  );
}

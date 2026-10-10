import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import InputSection from './components/InputSection';
import AuditOverview from './components/AuditOverview';
import ClaimHighlighter from './components/ClaimHighlighter';
import IssuesAttentionSection from './components/IssuesAttentionSection';
import SupportedClaimsSection from './components/SupportedClaimsSection';
import LogicalInconsistenciesSection from './components/LogicalInconsistenciesSection';
import SafetyRecommendationsSection from './components/SafetyRecommendationsSection';
import AuditLoadingOverlay from './components/AuditLoadingOverlay';
import DeveloperDiagnostics from './components/DeveloperDiagnostics';
import { exportAuditPdf } from './utils/pdfGenerator';
import { runAudit, getSampleData, getConfig } from './services/api';

export default function App() {
  const [apiKey, setApiKey] = useState('');
  const [answerText, setAnswerText] = useState('');
  const [documents, setDocuments] = useState([]);
  const [options, setOptions] = useState({
    enable_web_search: false,
    force_deterministic_fallback: false,
    verification_mode: 'auto',
    top_k_passages: 3,
    similarity_threshold: 0.25
  });

  const [serverConfig, setServerConfig] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [auditResult, setAuditResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [selectedClaimId, setSelectedClaimId] = useState(null);
  const [devMode, setDevMode] = useState(false);

  // Fetch backend configuration on mount
  useEffect(() => {
    getConfig()
      .then((cfg) => setServerConfig(cfg))
      .catch(() => setServerConfig({ has_gemini_api_key: false, active_mode: 'offline_deterministic' }));
  }, []);

  // Load sample dataset
  const handleLoadSample = async (sampleKey = 'medical_case') => {
    try {
      const samples = await getSampleData();
      const chosen = samples[sampleKey] || samples.medical_case;
      if (chosen) {
        setAnswerText(chosen.answer_text);
        setDocuments(chosen.documents);
        setErrorMsg('');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to fetch benchmark sample dataset from server.');
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
      let msg = 'Audit execution failed. Please verify server connectivity on port 8000.';
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

  const handleSwitchOfflineAndRetry = async () => {
    const offlineOpts = {
      ...options,
      verification_mode: 'offline',
      force_deterministic_fallback: true
    };
    setOptions(offlineOpts);
    setErrorMsg('');
    setIsLoading(true);

    try {
      const payload = {
        answer_text: answerText,
        documents: documents,
        options: offlineOpts,
        api_key: null
      };
      const result = await runAudit(payload);
      setAuditResult(result);
      setActiveFilter('ALL');
      setSelectedClaimId(null);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Offline audit execution failed.');
    } finally {
      setIsLoading(false);
    }
  };

  // Reciprocal navigation: Jump to sentence in original answer
  const handleJumpToAnswer = (claimId) => {
    setSelectedClaimId(claimId);
    const el = document.getElementById(`highlight-${claimId}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
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

  // Export Markdown Report
  const handleExportMarkdown = () => {
    if (!auditResult) return;

    const summary = auditResult.summary;
    const lines = [
      `# Second Opinion — AI Answer Audit Report`,
      `**Audit ID:** \`${auditResult.audit_id}\``,
      `**Date:** ${new Date(auditResult.timestamp).toUTCString()}`,
      `**Verification Mode:** ${auditResult.verification_mode}`,
      `**Model Info:** ${auditResult.model_info}`,
      `**Credibility Score:** ${summary.credibility_score}%`,
      ``,
      `---`,
      `## 1. Summary Metrics`,
      `| Metric | Count |`,
      `| :--- | :--- |`,
      `| **Total Claims Analyzed** | ${summary.total_claims} |`,
      `| **Supported Claims** | ${summary.supported_count} |`,
      `| **Contradicted / Incorrect Claims** | ${summary.contradicted_count} |`,
      `| **Insufficient Evidence Claims** | ${summary.insufficient_evidence_count} |`,
      `| **Logical Inconsistencies** | ${summary.logical_inconsistency_count || summary.internal_contradictions_detected || 0} |`,
      `| **Potentially Unsafe Recommendations** | ${summary.unsafe_recommendations_count || 0} |`,
      ``,
      `---`,
      `## 2. Original AI Answer`,
      `> ${auditResult.original_answer.replace(/\n/g, '\n> ')}`,
      ``,
      `---`,
      `## 3. Potentially Unsafe Recommendations`,
    ];

    const recs = auditResult.safety_analysis?.recommendations || [];
    if (recs.length === 0) {
      lines.push(`*${auditResult.safety_analysis?.summary || 'No potentially unsafe recommendations detected by automated analysis.'}*`);
    } else {
      recs.forEach((r, idx) => {
        lines.push(`### Recommendation ${idx + 1} [Severity: ${r.severity}]`);
        lines.push(`- **Flagged Text:** "${r.text}"`);
        lines.push(`- **Reason:** ${r.reason}`);
        lines.push(`- **Potential Risk:** ${r.potential_risk}`);
        if (r.safer_alternative) lines.push(`- **Safer Alternative:** ${r.safer_alternative}`);
        if (r.relevant_limitations) lines.push(`- **Limitations:** ${r.relevant_limitations}`);
        lines.push(``);
      });
    }

    lines.push(`---`);
    lines.push(`## 4. Logical Inconsistencies`);
    const conflicts = auditResult.logical_inconsistencies || [];
    if (conflicts.length === 0) {
      lines.push(`*No mutual internal contradictions or logical non-sequiturs detected.*`);
    } else {
      conflicts.forEach((c, idx) => {
        lines.push(`### Inconsistency ${idx + 1} (${c.inconsistency_type})`);
        lines.push(`- **Claim A [${c.claim_id_1}]:** "${c.claim_text_1}"`);
        if (c.claim_text_2) lines.push(`- **Claim B [${c.claim_id_2}]:** "${c.claim_text_2}"`);
        lines.push(`- **Explanation:** ${c.explanation}`);
        lines.push(``);
      });
    }

    lines.push(`---`);
    lines.push(`## 5. Claim-by-Claim Verification Analysis`);
    auditResult.claims.forEach((claim, idx) => {
      lines.push(`### Claim ${idx + 1}: [${claim.verdict}]`);
      lines.push(`> "${claim.text}"`);
      lines.push(`- **Primary Status:** ${claim.verdict}`);
      lines.push(`- **Model Certainty:** ${Math.round(claim.confidence * 100)}%`);
      lines.push(`- **Explanation:** ${claim.explanation}`);

      if (claim.contradicting_evidence?.length > 0) {
        lines.push(`- **Contradicting Evidence:**`);
        claim.contradicting_evidence.forEach((ev) => {
          lines.push(`  - *[${ev.source_name} (Page ${ev.page_number})]:* "${ev.excerpt}"`);
        });
      }

      if (claim.supporting_evidence?.length > 0) {
        lines.push(`- **Supporting Evidence:**`);
        claim.supporting_evidence.forEach((ev) => {
          lines.push(`  - *[${ev.source_name} (Page ${ev.page_number})]:* "${ev.excerpt}"`);
        });
      }
      lines.push(``);
    });

    lines.push(`---`);
    lines.push(`## 6. Audit Limitations`);
    lines.push(`*${auditResult.limitations || 'Automated audit evaluated strictly against supplied reference documents.'}*`);

    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Second_Opinion_Audit_${auditResult.audit_id}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Export JSON Report
  const handleExportJson = () => {
    if (!auditResult) return;
    const blob = new Blob([JSON.stringify(auditResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Second_Opinion_Audit_${auditResult.audit_id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Export PDF Report
  const handleExportPdf = () => {
    if (!auditResult) return;
    exportAuditPdf(auditResult, documents);
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
        serverConfig={serverConfig}
        apiKey={apiKey}
        setApiKey={setApiKey}
        devMode={devMode}
        setDevMode={setDevMode}
        onConfigUpdated={(cfg) => setServerConfig(cfg)}
      />

      {/* Input Section */}
      <InputSection
        answerText={answerText}
        setAnswerText={setAnswerText}
        documents={documents}
        setDocuments={setDocuments}
        options={options}
        setOptions={setOptions}
        onRunAudit={handleRunAudit}
        isLoading={isLoading}
        onLoadSample={handleLoadSample}
        serverConfig={serverConfig}
        apiKey={apiKey}
      />

      {/* Loading & Error Dedicated Overlay */}
      <AuditLoadingOverlay
        isLoading={isLoading}
        errorMsg={errorMsg}
        onRetry={handleRunAudit}
        onSwitchOfflineAndRetry={handleSwitchOfflineAndRetry}
        onDismissError={() => setErrorMsg('')}
      />

      {/* Audit Results Dashboard */}
      {auditResult && (
        <div style={{ marginTop: '24px' }}>
          
          {/* 1. Redesigned Audit Overview */}
          <AuditOverview
            summary={auditResult.summary}
            documents={documents}
            claims={auditResult.claims}
            activeFilter={activeFilter}
            setActiveFilter={setActiveFilter}
            onExportMarkdown={handleExportMarkdown}
            onExportJson={handleExportJson}
            onExportPdf={handleExportPdf}
            modelInfo={auditResult.model_info}
            verificationMode={auditResult.verification_mode}
          />

          {/* Interactive Text Highlighter with complete verbatim answer */}
          <ClaimHighlighter
            claims={auditResult.claims}
            originalText={auditResult.original_answer}
            selectedClaimId={selectedClaimId}
            setSelectedClaimId={handleSelectClaim}
            onSelectClaim={handleJumpToAnswer}
          />

          {/* Logical Inconsistencies Section (if any detected) */}
          {auditResult.logical_inconsistencies && auditResult.logical_inconsistencies.length > 0 && (
            <LogicalInconsistenciesSection
              logicalInconsistencies={auditResult.logical_inconsistencies}
              onSelectClaim={(id) => handleJumpToAnswer(id)}
            />
          )}

          {/* Potentially Unsafe Recommendations Section */}
          {auditResult.safety_analysis && auditResult.safety_analysis.recommendations?.length > 0 && (
            <SafetyRecommendationsSection
              safetyAnalysis={auditResult.safety_analysis}
            />
          )}

          {/* Developer Diagnostics (when Dev Mode is ON) */}
          {devMode && (
            <DeveloperDiagnostics auditResult={auditResult} />
          )}

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

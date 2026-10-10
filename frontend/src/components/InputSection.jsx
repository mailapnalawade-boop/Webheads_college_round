import React, { useState } from 'react';
import {
  FileUp, Play, FileText, Trash2, Sliders, ChevronDown, ChevronUp,
  Sparkles, Cpu, Plus
} from 'lucide-react';

export default function InputSection({
  answerText,
  setAnswerText,
  documents,
  setDocuments,
  options,
  setOptions,
  onRunAudit,
  isLoading,
  onLoadSample,
  serverConfig,
  apiKey
}) {
  const [docName, setDocName] = useState('');
  const [docText, setDocText] = useState('');
  const [showDocAdd, setShowDocAdd] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleAddTextDoc = () => {
    if (!docText.trim()) return;
    const name = docName.trim() || `Reference_Evidence_${documents.length + 1}.txt`;
    setDocuments([...documents, { filename: name, content: docText, content_type: 'text/plain' }]);
    setDocName('');
    setDocText('');
    setShowDocAdd(false);
  };

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    files.forEach((file) => {
      const reader = new FileReader();
      const fnLower = file.name.toLowerCase();

      if (file.type === 'application/pdf' || fnLower.endsWith('.pdf')) {
        reader.readAsDataURL(file);
        reader.onload = () => {
          setDocuments((prev) => [
            ...prev,
            {
              filename: file.name,
              content: reader.result,
              content_type: 'application/pdf'
            }
          ]);
        };
      } else if (fnLower.endsWith('.docx') || fnLower.endsWith('.doc')) {
        reader.readAsDataURL(file);
        reader.onload = () => {
          setDocuments((prev) => [
            ...prev,
            {
              filename: file.name,
              content: reader.result,
              content_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }
          ]);
        };
      } else {
        reader.readAsText(file);
        reader.onload = () => {
          setDocuments((prev) => [
            ...prev,
            {
              filename: file.name,
              content: reader.result,
              content_type: 'text/plain'
            }
          ]);
        };
      }
    });
  };

  const handleRemoveDoc = (index) => {
    setDocuments(documents.filter((_, idx) => idx !== index));
  };

  const wordCount = answerText.trim() ? answerText.trim().split(/\s+/).length : 0;

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      
      {/* Header bar: Section Title & Quick Benchmark Samples */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '1.15rem', color: '#ffffff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sliders size={20} color="#6366f1" />
            Audit Setup & Evidence Ingestion
          </h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Provide the AI response and ground-truth documents to verify factual claims
          </span>
        </div>

        {/* Quick Sample Benchmark Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontWeight: 600 }}>
            Sample Benchmarks:
          </span>
          <button
            className="btn-secondary"
            onClick={() => onLoadSample('medical_case')}
            style={{ padding: '4px 10px', fontSize: '0.75rem', borderRadius: '14px' }}
          >
            Clinical Case
          </button>
          <button
            className="btn-secondary"
            onClick={() => onLoadSample('financial_case')}
            style={{ padding: '4px 10px', fontSize: '0.75rem', borderRadius: '14px' }}
          >
            Financial Report
          </button>
          <button
            className="btn-secondary"
            onClick={() => onLoadSample('logical_conflict_case')}
            style={{ padding: '4px 10px', fontSize: '0.75rem', borderRadius: '14px' }}
          >
            Logic Conflict
          </button>
        </div>
      </div>

      {/* Main 2-Column Workflow */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        
        {/* Left Column: AI-Generated Answer Input */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              AI-Generated Answer to Audit *
            </label>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              {wordCount} words • {answerText.length} chars
            </span>
          </div>

          <textarea
            rows={8}
            value={answerText}
            onChange={(e) => setAnswerText(e.target.value)}
            disabled={isLoading}
            placeholder="Paste the AI-generated answer, clinical summary, financial report, or recommendations here..."
            style={{
              width: '100%',
              padding: '14px 16px',
              borderRadius: '12px',
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid var(--border-color)',
              color: '#ffffff',
              fontSize: '0.9rem',
              resize: 'vertical',
              fontFamily: 'inherit',
              outline: 'none',
              lineHeight: 1.6
            }}
          />
        </div>

        {/* Right Column: Reference Ground-Truth Documents */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              Reference Evidence Documents ({documents.length})
            </label>
            <input
              type="file"
              id="file-upload"
              accept=".pdf,.txt,.docx,.doc"
              multiple
              onChange={handleFileUpload}
              disabled={isLoading}
              style={{ display: 'none' }}
            />
            <label
              htmlFor="file-upload"
              className="btn-secondary"
              style={{ padding: '4px 10px', fontSize: '0.78rem', cursor: isLoading ? 'not-allowed' : 'pointer' }}
            >
              <FileUp size={14} /> Upload PDF/DOCX/TXT
            </label>
          </div>

          {/* Document List Box */}
          <div style={{
            background: 'rgba(0, 0, 0, 0.35)',
            borderRadius: '12px',
            border: '1px solid var(--border-color)',
            minHeight: '135px',
            maxHeight: '175px',
            overflowY: 'auto',
            padding: '10px',
            marginBottom: '10px'
          }}>
            {documents.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '24px 0', fontSize: '0.84rem' }}>
                <FileText size={22} style={{ opacity: 0.4, marginBottom: '6px' }} /><br />
                No reference documents added yet.<br />
                Upload guideline files or paste reference excerpts below.
              </div>
            ) : (
              documents.map((doc, idx) => (
                <div key={idx} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  background: 'rgba(255, 255, 255, 0.04)',
                  marginBottom: '6px',
                  fontSize: '0.85rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    <FileText size={16} color="#818cf8" />
                    <span style={{ color: '#ffffff', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '210px' }}>
                      {doc.filename}
                    </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', padding: '1px 6px', borderRadius: '4px', background: 'rgba(255,255,255,0.06)' }}>
                      {doc.content_type?.includes('pdf') ? 'PDF' : doc.content_type?.includes('word') ? 'DOCX' : 'TXT'}
                    </span>
                  </div>
                  <button
                    onClick={() => handleRemoveDoc(idx)}
                    disabled={isLoading}
                    style={{ background: 'none', border: 'none', color: '#f43f5e', cursor: 'pointer', opacity: 0.7 }}
                    title="Remove document"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Paste Raw Evidence Toggle */}
          {!showDocAdd ? (
            <button
              className="btn-secondary"
              style={{ width: '100%', justifyContent: 'center', fontSize: '0.8rem', padding: '6px 12px' }}
              onClick={() => setShowDocAdd(true)}
              disabled={isLoading}
            >
              <Plus size={14} /> Paste Reference Text Directly
            </button>
          ) : (
            <div style={{ background: 'rgba(0,0,0,0.5)', padding: '12px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <input
                type="text"
                placeholder="Document Title (e.g. Clinical_Guidelines.txt)"
                value={docName}
                onChange={(e) => setDocName(e.target.value)}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.8rem', marginBottom: '8px' }}
              />
              <textarea
                rows={3}
                placeholder="Paste reference text passage here..."
                value={docText}
                onChange={(e) => setDocText(e.target.value)}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.8rem', marginBottom: '8px' }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button className="btn-secondary" style={{ padding: '4px 10px', fontSize: '0.75rem' }} onClick={() => setShowDocAdd(false)}>Cancel</button>
                <button className="btn-primary" style={{ padding: '4px 14px', fontSize: '0.75rem' }} onClick={handleAddTextDoc}>Add Passage</button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Collapsible Advanced Settings Panel */}
      <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', padding: '4px 0' }}
        >
          {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          <span>Advanced Verification Settings</span>
        </button>

        {showAdvanced && (
          <div style={{
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: '10px',
            border: '1px solid var(--border-color)',
            padding: '16px',
            marginTop: '10px',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '16px'
          }}>
            {/* Mode Selection */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#ffffff', marginBottom: '6px' }}>
                Verification Mode
              </label>
              <select
                value={options.verification_mode || 'auto'}
                onChange={(e) => setOptions({
                  ...options,
                  verification_mode: e.target.value,
                  force_deterministic_fallback: e.target.value === 'offline'
                })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid var(--border-color)',
                  color: '#ffffff',
                  fontSize: '0.82rem'
                }}
              >
                <option value="auto">Automatic (Cloud AI if key configured, otherwise Offline)</option>
                <option value="llm">Strict Online Cloud LLM ({serverConfig?.default_model || 'Gemini 3.8 Flash'})</option>
                <option value="offline">Strict Offline Deterministic (Rules & BM25)</option>
              </select>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'block', marginTop: '4px' }}>
                Offline mode runs 100% locally without external API dependencies.
              </span>
            </div>

            {/* Web Search Fallback */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#ffffff', marginBottom: '6px' }}>
                Public Web Search Fallback
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={options.enable_web_search}
                  onChange={(e) => setOptions({ ...options, enable_web_search: e.target.checked })}
                  style={{ accentColor: '#6366f1' }}
                />
                <span>Include External Web Search (DuckDuckGo)</span>
              </label>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'block', marginTop: '4px' }}>
                Only queried when uploaded reference context is absent. External sources are clearly distinguished.
              </span>
            </div>

            {/* Top-K Passages */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#ffffff', marginBottom: '6px' }}>
                Evidence Retrieval Depth (Top-K Passages: {options.top_k_passages || 3})
              </label>
              <input
                type="range"
                min="1"
                max="5"
                value={options.top_k_passages || 3}
                onChange={(e) => setOptions({ ...options, top_k_passages: parseInt(e.target.value) })}
                style={{ width: '100%', accentColor: '#6366f1' }}
              />
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'block', marginTop: '4px' }}>
                Controls the number of most relevant excerpts retrieved per claim.
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Footer CTA & Engine Status */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: '18px',
        paddingTop: '16px',
        borderTop: '1px solid var(--border-color)',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        {/* Verification Engine Readiness */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem' }}>
          <span style={{ color: 'var(--text-dim)' }}>Engine:</span>
          {(serverConfig?.has_gemini_api_key || apiKey) && options.verification_mode !== 'offline' ? (
            <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}>
              <Sparkles size={14} /> Ready • {serverConfig?.default_model || 'Gemini 3.8 Flash'} Cloud Verification
            </span>
          ) : (
            <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 500 }}>
              <Cpu size={14} /> Ready • Offline Deterministic Rule & BM25 Engine
            </span>
          )}
        </div>

        {/* Audit Button */}
        <button
          className="btn-primary"
          onClick={onRunAudit}
          disabled={isLoading || !answerText.trim()}
          style={{ padding: '12px 32px', fontSize: '0.98rem' }}
        >
          <Play size={18} />
          <span>Audit Answer</span>
        </button>
      </div>
    </div>
  );
}

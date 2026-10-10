import React, { useState } from 'react';
import { FileUp, Search, Play, FileText, Trash2, Sliders, AlertCircle } from 'lucide-react';

export default function InputSection({
  answerText,
  setAnswerText,
  documents,
  setDocuments,
  options,
  setOptions,
  onRunAudit,
  isLoading
}) {
  const [docName, setDocName] = useState('');
  const [docText, setDocText] = useState('');
  const [showDocAdd, setShowDocAdd] = useState(false);

  const handleAddTextDoc = () => {
    if (!docText.strip || !docText.trim()) return;
    const name = docName.trim() || `Reference_Doc_${documents.length + 1}.txt`;
    setDocuments([...documents, { filename: name, content: docText, content_type: 'text/plain' }]);
    setDocName('');
    setDocText('');
    setShowDocAdd(false);
  };

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    files.forEach((file) => {
      const reader = new FileReader();
      if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
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

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      <h2 style={{ fontSize: '1.1rem', color: '#ffffff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Sliders size={20} color="#6366f1" />
        Input & Ground-Truth Context Setup
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        
        {/* Left Column: AI Answer Input */}
        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
            Pasted AI-Generated Answer to Audit *
          </label>
          <textarea
            rows={8}
            value={answerText}
            onChange={(e) => setAnswerText(e.target.value)}
            placeholder="Paste the AI-generated text, prescription, financial response, or summary here..."
            style={{
              width: '100%',
              padding: '12px 14px',
              borderRadius: '10px',
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid var(--border-color)',
              color: '#ffffff',
              fontSize: '0.9rem',
              resize: 'vertical',
              fontFamily: 'inherit',
              outline: 'none'
            }}
          />
        </div>

        {/* Right Column: Uploaded Ground-Truth Documents */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              Reference Ground-Truth Evidence Documents ({documents.length})
            </label>
            <input
              type="file"
              id="file-upload"
              accept=".pdf,.txt"
              multiple
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
            <label htmlFor="file-upload" className="btn-secondary" style={{ padding: '4px 10px', fontSize: '0.8rem', cursor: 'pointer' }}>
              <FileUp size={14} /> Upload PDF/TXT
            </label>
          </div>

          {/* Document List Box */}
          <div style={{
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: '10px',
            border: '1px solid var(--border-color)',
            minHeight: '130px',
            maxHeight: '170px',
            overflowY: 'auto',
            padding: '10px',
            marginBottom: '12px'
          }}>
            {documents.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '24px 0', fontSize: '0.85rem' }}>
                <FileText size={24} style={{ opacity: 0.5, marginBottom: '6px' }} /><br />
                No ground-truth evidence uploaded.<br />
                Upload PDF/TXT files or paste reference context below.
              </div>
            ) : (
              documents.map((doc, idx) => (
                <div key={idx} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  background: 'rgba(255, 255, 255, 0.04)',
                  marginBottom: '6px',
                  fontSize: '0.85rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    <FileText size={16} color="#6366f1" />
                    <span style={{ color: '#ffffff', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '200px' }}>
                      {doc.filename}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', padding: '1px 6px', borderRadius: '4px', background: 'rgba(255,255,255,0.06)' }}>
                      {doc.content_type === 'application/pdf' ? 'PDF' : 'TXT'}
                    </span>
                  </div>
                  <button
                    onClick={() => handleRemoveDoc(idx)}
                    style={{ background: 'none', border: 'none', color: '#f43f5e', cursor: 'pointer', opacity: 0.7 }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Quick Paste Text Reference Toggle */}
          {!showDocAdd ? (
            <button className="btn-secondary" style={{ width: '100%', justifyContent: 'center', fontSize: '0.8rem' }} onClick={() => setShowDocAdd(true)}>
              + Paste Raw Text Evidence
            </button>
          ) : (
            <div style={{ background: 'rgba(0,0,0,0.5)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <input
                type="text"
                placeholder="Document Title (e.g. Protocol.txt)"
                value={docName}
                onChange={(e) => setDocName(e.target.value)}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.8rem', marginBottom: '8px' }}
              />
              <textarea
                rows={3}
                placeholder="Paste reference text content..."
                value={docText}
                onChange={(e) => setDocText(e.target.value)}
                style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: '#fff', fontSize: '0.8rem', marginBottom: '8px' }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => setShowDocAdd(false)}>Cancel</button>
                <button className="btn-primary" style={{ padding: '4px 12px', fontSize: '0.75rem' }} onClick={handleAddTextDoc}>Add Document</button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Options & Action Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
        
        {/* Toggle Controls */}
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={options.enable_web_search}
              onChange={(e) => setOptions({ ...options, enable_web_search: e.target.checked })}
              style={{ accentColor: '#6366f1' }}
            />
            <Search size={14} /> Enable Public Web Search Fallback
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={options.force_deterministic_fallback}
              onChange={(e) => setOptions({ ...options, force_deterministic_fallback: e.target.checked })}
              style={{ accentColor: '#6366f1' }}
            />
            Force Offline BM25 Rule Engine
          </label>
        </div>

        {/* Audit CTA */}
        <button
          className="btn-primary"
          onClick={onRunAudit}
          disabled={isLoading || !answerText.trim()}
          style={{ padding: '12px 28px', fontSize: '0.95rem' }}
        >
          {isLoading ? (
            <span>Auditing Answer...</span>
          ) : (
            <>
              <Play size={18} />
              <span>Audit Answer Claims</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

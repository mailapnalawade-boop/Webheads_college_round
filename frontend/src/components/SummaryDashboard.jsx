import React from 'react';
import AuditOverview from './AuditOverview';

export default function SummaryDashboard({
  summary,
  documents,
  claims,
  activeFilter,
  setActiveFilter,
  onExportPdf
}) {
  return (
    <AuditOverview
      summary={summary}
      documents={documents}
      claims={claims}
      activeFilter={activeFilter}
      setActiveFilter={setActiveFilter}
      onExportPdf={onExportPdf}
    />
  );
}

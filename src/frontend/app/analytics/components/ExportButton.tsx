'use client';

import { useState } from 'react';
import { Button, CircularProgress } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';

interface ExportButtonProps {
  /** Function to retrieve the data rows to export. */
  getData: () => Promise<Record<string, unknown>[]> | Record<string, unknown>[];
  filename?: string;
  label?: string;
}

function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return '';
  const headers = Object.keys(rows[0]);
  const escape = (v: unknown) => {
    const s = String(v ?? '');
    return s.includes(',') || s.includes('"') || s.includes('\n')
      ? `"${s.replace(/"/g, '""')}"`
      : s;
  };
  const lines = [headers.map(escape).join(',')];
  for (const row of rows) {
    lines.push(headers.map((h) => escape(row[h])).join(','));
  }
  return lines.join('\n');
}

export default function ExportButton({
  getData,
  filename = 'analytics-export.csv',
  label = 'Export CSV',
}: ExportButtonProps) {
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      const rows = await getData();
      const csv = toCsv(rows);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  return (
    <Button
      variant="outlined"
      startIcon={exporting ? <CircularProgress size={16} /> : <DownloadIcon />}
      onClick={() => void handleExport()}
      disabled={exporting}
      data-testid="export-csv-button"
    >
      {label}
    </Button>
  );
}

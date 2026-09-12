import React from 'react';
import PropTypes from 'prop-types';
import { issueService } from '../../services/issueService';

/** Inline preview of an issued certificate: <img> for PNG, native <iframe> viewer for PDF. */
export default function CertPreview({ result }) {
  if (!result?.file_name) return null;
  const url = issueService.previewUrl(result.file_name);
  const isPdf = String(result.format || result.file_name).toLowerCase().endsWith('pdf');

  return (
    <div className="card">
      <div className="card-title">Certificate preview</div>
      <div style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--border)', background: '#fff' }}>
        {isPdf ? (
          <iframe title={`${result.cert_id} preview`} src={url} style={{ width: '100%', height: 480, border: 0 }} />
        ) : (
          <img src={url} alt={`Certificate ${result.cert_id}`} style={{ width: '100%', display: 'block' }} />
        )}
      </div>
      <p style={{ marginTop: 'var(--space-3)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
        The signed payload is hidden in the least significant bits of these pixels. Editing any visible value breaks the hash and is caught at Layer 1.
      </p>
    </div>
  );
}

CertPreview.propTypes = { result: PropTypes.object };

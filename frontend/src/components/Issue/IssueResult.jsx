import React from 'react';
import PropTypes from 'prop-types';
import { CheckCircle, Download, AlertTriangle, Copy } from 'lucide-react';
import toast from 'react-hot-toast';
import { issueService } from '../../services/issueService';

export default function IssueResult({ result }) {
  if (!result) return null;

  const copy = (text) => {
    navigator.clipboard?.writeText(text).then(() => toast.success('Copied'));
  };

  return (
    <div className="card" style={{ borderColor: 'var(--green-500)', boxShadow: 'var(--shadow-green)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
        <CheckCircle size={24} color="var(--green-400)" />
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xl)', fontWeight: 700 }}>{result.cert_id}</div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Issued, signed, embedded and registered in the ledger.</div>
        </div>
        <a href={issueService.downloadUrl(result.file_name)} className="btn btn-primary" style={{ marginLeft: 'auto' }} download>
          <Download size={16} /> Download {String(result.format || 'png').toUpperCase()}
        </a>
      </div>

      {result.anomaly_flag && (
        <div className="alert alert-amber" style={{ marginBottom: 'var(--space-4)' }}>
          <AlertTriangle size={18} color="var(--amber-400)" style={{ flexShrink: 0 }} />
          <div>
            <strong>Anomaly flagged for regulator review.</strong>
            <ul style={{ margin: '4px 0 0 16px', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
              {(result.anomaly?.reasons || [result.anomaly_reason]).map((r) => <li key={r}>{r}</li>)}
            </ul>
          </div>
        </div>
      )}

      <dl className="kv">
        <dt>SHA-256 hash</dt>
        <dd>
          {result.data_hash}
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => copy(result.data_hash)} title="Copy hash" style={{ marginLeft: 6 }}><Copy size={12} /></button>
        </dd>
        <dt>Issued at</dt>
        <dd>{result.issued_at}</dd>
        <dt>File</dt>
        <dd>{result.file_name}</dd>
      </dl>

      {result.payload && (
        <details style={{ marginTop: 'var(--space-4)' }}>
          <summary>Embedded steganographic payload</summary>
          <pre className="code" style={{ marginTop: 'var(--space-3)' }}>{JSON.stringify(result.payload, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}

IssueResult.propTypes = { result: PropTypes.object };

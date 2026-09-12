// frontend/src/components/Verify/VerifyResult.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import LayerStatus from './LayerStatus';
import StatusBadge from '../Common/StatusBadge';

export default function VerifyResult({ result }) {
  if (!result) return null;
  const isValid = result.final_result === 'VALID';
  const rec = result.ledger_record;

  return (
    <div style={{
      marginTop: 'var(--space-8)',
      padding: 'var(--space-8)',
      background: 'var(--bg-secondary)',
      borderRadius: 'var(--radius-lg)',
      border: `2px solid ${isValid ? 'var(--green-500)' : 'var(--red-400)'}`,
      boxShadow: isValid ? 'var(--shadow-green)' : 'var(--shadow-red)',
    }}>
      {/* Verdict Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap',
        marginBottom: 'var(--space-8)',
        padding: 'var(--space-6)',
        background: isValid ? 'var(--green-glow)' : 'var(--red-glow)',
        borderRadius: 'var(--radius-md)',
      }}>
        {isValid
          ? <CheckCircle size={32} color="var(--green-400)" />
          : <XCircle size={32} color="var(--red-400)" />}
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-2xl)', fontWeight: 700,
            color: isValid ? 'var(--green-400)' : 'var(--red-400)' }}>
            {result.final_result}
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
            Certificate ID: <span className="mono">{result.cert_id || 'Unknown'}</span>
            {result.file_name && <> · {result.file_name}</>}
            {result.claimed && <> · <StatusBadge status="claimed" /></>}
          </div>
        </div>
        {result.fraud_reason && (
          <div style={{ marginLeft: 'auto', maxWidth: 360, fontSize: 'var(--text-xs)',
            color: 'var(--red-400)', textAlign: 'right' }}>
            {result.fraud_reason}
          </div>
        )}
      </div>

      {/* Three Layer Results */}
      <h3 style={{ marginBottom: 'var(--space-4)', fontSize: 'var(--text-sm)',
        color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Verification Layers
      </h3>
      <LayerStatus
        number={1}
        name="Steganographic Integrity"
        passed={result.layers?.layer1_steganographic_integrity?.passed}
        detail={result.layers?.layer1_steganographic_integrity?.detail}
      />
      <LayerStatus
        number={2}
        name="Cryptographic Signature"
        passed={result.layers?.layer2_cryptographic_signature?.passed}
        detail={result.layers?.layer2_cryptographic_signature?.detail}
      />
      <LayerStatus
        number={3}
        name="Ledger / Registry Lookup"
        passed={result.layers?.layer3_ledger_lookup?.passed}
        detail={result.layers?.layer3_ledger_lookup?.detail}
      />

      {result.anomalies?.length > 0 && (
        <div className="alert alert-amber" style={{ marginTop: 'var(--space-4)' }}>
          <AlertTriangle size={18} color="var(--amber-400)" style={{ flexShrink: 0 }} />
          <div>
            <strong>Open issuance anomalies on this certificate</strong>
            <ul style={{ margin: '4px 0 0 16px', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
              {result.anomalies.map((a) => <li key={a.anomaly_id}>{a.anomaly_reason}</li>)}
            </ul>
          </div>
        </div>
      )}

      {rec && (
        <div style={{ marginTop: 'var(--space-6)' }}>
          <h3 style={{ marginBottom: 'var(--space-3)', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Ledger Record
          </h3>
          <dl className="kv">
            <dt>Status</dt><dd><StatusBadge status={rec.status} /></dd>
            <dt>Generator</dt><dd>{rec.generator_id}</dd>
            <dt>Source</dt><dd>{rec.source_type}</dd>
            <dt>Energy</dt><dd>{Number(rec.energy_kwh).toLocaleString()} kWh</dd>
            <dt>Generated</dt><dd>{rec.generation_date}</dd>
            <dt>Issuer</dt><dd>{rec.issuer_id}</dd>
            <dt>Issued at</dt><dd>{rec.issued_at}</dd>
            {rec.claimed_by && (<><dt>Claimed by</dt><dd>{rec.claimed_by} · {rec.claimed_at}</dd></>)}
          </dl>
        </div>
      )}

      {/* Extracted Data */}
      {result.extracted_data && (
        <details style={{ marginTop: 'var(--space-6)' }}>
          <summary>Extracted Certificate Data</summary>
          <pre className="code" style={{ marginTop: 'var(--space-3)' }}>
            {JSON.stringify(result.extracted_data, null, 2)}
          </pre>
        </details>
      )}
      {result.file_sha256 && (
        <p style={{ marginTop: 'var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
          Uploaded file SHA-256: <span className="mono">{result.file_sha256}</span>
        </p>
      )}
    </div>
  );
}

VerifyResult.propTypes = { result: PropTypes.object };

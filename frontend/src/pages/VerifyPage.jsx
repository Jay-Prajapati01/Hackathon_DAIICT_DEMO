import React from 'react';
import { useSelector } from 'react-redux';
import VerifyUpload from '../components/Verify/VerifyUpload';
import VerifyResult from '../components/Verify/VerifyResult';
import StatusBadge from '../components/Common/StatusBadge';

export default function VerifyPage() {
  const result = useSelector((s) => s.verify.result);
  const history = useSelector((s) => s.verify.history);

  return (
    <div className="page-grid">
      <div className="page-intro">
        <h3>Verify any REC in seconds</h3>
        <p>
          Upload a certificate file. REC Guard extracts the hidden payload (Layer 1), validates the issuer&apos;s RSA signature
          (Layer 2) and checks the shared ledger for registration and prior claims (Layer 3). A certificate is VALID only if all three agree.
        </p>
      </div>

      <VerifyUpload />
      <VerifyResult result={result} />

      {history.length > 1 && (
        <div className="card">
          <div className="card-title">Verified this session</div>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6, fontSize: 'var(--text-sm)' }}>
            {history.map((h, i) => (
              <li key={`${h.cert_id}-${i}`} style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <StatusBadge status={h.final_result} />
                <span className="mono" style={{ fontWeight: 600 }}>{h.cert_id || 'Unknown'}</span>
                <span style={{ color: 'var(--text-secondary)' }}>{h.file_name}</span>
                {h.fraud_reason && <span style={{ color: 'var(--red-400)', fontSize: 'var(--text-xs)' }}>{h.fraud_reason}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import IssueForm from '../components/Issue/IssueForm';
import IssueResult from '../components/Issue/IssueResult';
import CertPreview from '../components/Issue/CertPreview';
import { clearIssueResult } from '../store/issueSlice';

export default function IssuePage() {
  const dispatch = useDispatch();
  const result = useSelector((s) => s.issue.result);
  const history = useSelector((s) => s.issue.history);

  return (
    <div className="page-grid">
      <div className="page-intro">
        <h3>Issue a tamper-evident REC</h3>
        <p>
          The certificate data is hashed with SHA-256, the hash is signed with the issuer&apos;s RSA-2048 key, and the signed
          payload is hidden inside the certificate image with LSB steganography. The same event is written to the shared ledger.
        </p>
      </div>

      <div className="card">
        <div className="card-title">Certificate details</div>
        <IssueForm onSuccess={() => window.scrollTo({ top: 0, behavior: 'smooth' })} />
      </div>

      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 'var(--space-6)', alignItems: 'start' }}>
          <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
            <IssueResult result={result} />
            <button type="button" className="btn btn-ghost btn-sm" style={{ justifySelf: 'start' }} onClick={() => dispatch(clearIssueResult())}>Clear</button>
          </div>
          <CertPreview result={result} />
        </div>
      )}

      {history.length > 1 && (
        <div className="card">
          <div className="card-title">Issued this session</div>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6, fontSize: 'var(--text-sm)' }}>
            {history.map((h) => (
              <li key={h.cert_id} style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <span className="mono" style={{ fontWeight: 600 }}>{h.cert_id}</span>
                <span style={{ color: 'var(--text-secondary)' }}>{h.issued_at}</span>
                {h.anomaly_flag && <span className="badge badge-amber">Anomaly</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { ChevronDown, ChevronRight, Download, Ban, Handshake } from 'lucide-react';
import toast from 'react-hot-toast';
import { useSelector } from 'react-redux';
import StatusBadge from '../Common/StatusBadge';
import LoadingSpinner from '../Common/LoadingSpinner';
import { ledgerService } from '../../services/ledgerService';
import { issueService } from '../../services/issueService';
import { selectCanRegulate, selectIsAuthenticated } from '../../store/authSlice';

function fileName(path) {
  return path ? path.split(/[\\/]/).pop() : null;
}

export default function LedgerRow({ cert, onChanged }) {
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState(null);
  const [busy, setBusy] = useState(false);
  const authed = useSelector(selectIsAuthenticated);
  const canRegulate = useSelector(selectCanRegulate);
  const file = fileName(cert.cert_file_path);

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && history === null) {
      try {
        const h = await ledgerService.history(cert.cert_id);
        setHistory(h.verifications || []);
      } catch (e) {
        setHistory([]);
      }
    }
  };

  const claim = async () => {
    setBusy(true);
    try {
      await ledgerService.claim(cert.cert_id);
      toast.success(`${cert.cert_id} claimed`);
      onChanged?.();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  const revoke = async () => {
    setBusy(true);
    try {
      await ledgerService.revoke(cert.cert_id);
      toast.success(`${cert.cert_id} revoked`);
      onChanged?.();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <tr style={{ cursor: 'pointer' }} onClick={toggle}>
        <td style={{ width: 28, color: 'var(--text-secondary)' }}>{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</td>
        <td className="mono" style={{ fontWeight: 600 }}>{cert.cert_id}</td>
        <td>{cert.generator_id}</td>
        <td>{cert.source_type}</td>
        <td className="mono" style={{ textAlign: 'right' }}>{Number(cert.energy_kwh).toLocaleString()}</td>
        <td>{cert.generation_date}</td>
        <td>{cert.issuer_id}</td>
        <td><StatusBadge status={cert.status} /></td>
        <td style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{String(cert.issued_at).slice(0, 19).replace('T', ' ')}</td>
        <td onClick={(e) => e.stopPropagation()} style={{ whiteSpace: 'nowrap' }}>
          {file && (
            <a href={issueService.downloadUrl(file)} className="btn btn-ghost btn-sm" title="Download certificate" download>
              <Download size={14} />
            </a>
          )}
          {authed && cert.status === 'issued' && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={claim} disabled={busy} title="Claim">
              <Handshake size={14} />
            </button>
          )}
          {canRegulate && cert.status !== 'revoked' && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={revoke} disabled={busy} title="Revoke" style={{ color: 'var(--red-400)' }}>
              <Ban size={14} />
            </button>
          )}
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={10} style={{ background: 'var(--bg-primary)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-6)', padding: 'var(--space-2) 0' }}>
              <div>
                <div className="card-title">Registry record</div>
                <dl className="kv">
                  <dt>Data hash</dt><dd>{cert.data_hash}</dd>
                  <dt>Signature</dt><dd style={{ maxHeight: 60, overflow: 'hidden' }}>{cert.signature}</dd>
                  {cert.claimed_by && (<><dt>Claimed by</dt><dd>{cert.claimed_by}</dd><dt>Claimed at</dt><dd>{cert.claimed_at}</dd></>)}
                </dl>
              </div>
              <div>
                <div className="card-title">Verification history</div>
                {history === null ? <LoadingSpinner label="Loading…" /> : history.length === 0 ? (
                  <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>No verification attempts yet.</p>
                ) : (
                  <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {history.map((v) => (
                      <li key={v.log_id} style={{ fontSize: 'var(--text-xs)', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                        <StatusBadge status={v.final_result} />
                        <span style={{ color: 'var(--text-secondary)' }}>{String(v.verified_at).slice(0, 19).replace('T', ' ')}</span>
                        <span style={{ color: 'var(--text-muted)' }}>L1 {v.layer1_pass ? '✓' : '✗'} · L2 {v.layer2_pass ? '✓' : '✗'} · L3 {v.layer3_pass ? '✓' : '✗'}</span>
                        {v.fraud_reason && <span style={{ color: 'var(--red-400)' }}>{v.fraud_reason}</span>}
                        {v.verifier_id && <span style={{ color: 'var(--text-muted)' }}>by {v.verifier_id}</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

LedgerRow.propTypes = { cert: PropTypes.object.isRequired, onChanged: PropTypes.func };

import React, { useCallback, useState } from 'react';
import PropTypes from 'prop-types';
import { useDropzone } from 'react-dropzone';
import { useDispatch, useSelector } from 'react-redux';
import { UploadCloud, FileCheck2, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { verifyCertificate } from '../../store/verifySlice';
import { selectUser } from '../../store/authSlice';
import LoadingSpinner from '../Common/LoadingSpinner';

const ACCEPT = { 'image/png': ['.png'], 'image/jpeg': ['.jpg', '.jpeg'], 'application/pdf': ['.pdf'] };
const MAX_BYTES = 16 * 1024 * 1024;

export default function VerifyUpload({ onResult }) {
  const dispatch = useDispatch();
  const user = useSelector(selectUser);
  const status = useSelector((s) => s.verify.status);
  const loading = status === 'loading';
  const [file, setFile] = useState(null);
  const [claim, setClaim] = useState(false);
  const [claimedBy, setClaimedBy] = useState(user?.email || '');

  const onDrop = useCallback((accepted, rejected) => {
    if (rejected.length) {
      toast.error(rejected[0].errors?.[0]?.message || 'Unsupported file. Use PNG, JPG or PDF up to 16 MB.');
      return;
    }
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop, accept: ACCEPT, maxFiles: 1, maxSize: MAX_BYTES, multiple: false,
  });

  const submit = async () => {
    if (!file) return;
    if (claim && !claimedBy.trim()) {
      toast.error('Enter the buyer / entity ID that is claiming this certificate.');
      return;
    }
    const action = await dispatch(verifyCertificate({ file, claim, claimedBy: claimedBy.trim() }));
    if (verifyCertificate.fulfilled.match(action)) {
      const r = action.payload;
      if (r.final_result === 'VALID') toast.success(`VALID — ${r.cert_id}${r.claimed ? ' (claimed)' : ''}`);
      else toast.error(`FRAUD — ${r.fraud_reason}`, { duration: 7000 });
      onResult?.(r);
    } else {
      toast.error(`Verification failed: ${action.payload?.message || 'unknown error'}`);
    }
  };

  return (
    <div className="card">
      <div className="card-title">Upload suspect certificate</div>
      {!file ? (
        <div {...getRootProps({ className: `dropzone${isDragActive ? ' active' : ''}${isDragReject ? ' reject' : ''}` })}>
          <input {...getInputProps()} />
          <UploadCloud size={36} color="var(--green-400)" style={{ marginBottom: 12 }} />
          <div style={{ fontWeight: 600 }}>{isDragActive ? 'Drop it here' : 'Drag & drop a certificate, or click to browse'}</div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: 6 }}>PNG, JPG or PDF · up to 16 MB · nothing is stored after verification</div>
        </div>
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: 'var(--space-4)', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
          <FileCheck2 size={22} color="var(--green-400)" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{(file.size / 1024).toFixed(1)} KB · {file.type || 'unknown type'}</div>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setFile(null)} disabled={loading} aria-label="Remove file"><X size={14} /></button>
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-4)', alignItems: 'flex-end', marginTop: 'var(--space-6)' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--text-sm)', cursor: 'pointer' }}>
          <input type="checkbox" checked={claim} onChange={(e) => setClaim(e.target.checked)} disabled={loading} />
          Claim this certificate if valid
        </label>
        {claim && (
          <div style={{ flex: '1 1 240px' }}>
            <label className="label" htmlFor="claimed_by">Claiming entity (buyer ID)</label>
            <input id="claimed_by" className="field" placeholder="BUYER-Acme-Corp" value={claimedBy} onChange={(e) => setClaimedBy(e.target.value)} disabled={loading} />
          </div>
        )}
        <button type="button" className="btn btn-primary" onClick={submit} disabled={!file || loading} style={{ marginLeft: 'auto', padding: '12px 24px' }}>
          {loading ? <LoadingSpinner label="Running 3-layer check..." style={{ color: '#fff' }} /> : 'Verify Certificate'}
        </button>
      </div>
    </div>
  );
}

VerifyUpload.propTypes = { onResult: PropTypes.func };

import React from 'react';
import PropTypes from 'prop-types';
import { formatDistanceToNow } from 'date-fns';
import StatusBadge from '../Common/StatusBadge';

function ago(iso) {
  try {
    return formatDistanceToNow(new Date(iso), { addSuffix: true });
  } catch {
    return iso;
  }
}

/** Latest verification attempts (valid and fraudulent) from the audit log. */
export default function RecentActivity({ verifications = [] }) {
  return (
    <div className="card">
      <div className="card-title">Recent verification activity</div>
      {verifications.length === 0 ? (
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>No verification attempts logged yet.</p>
      ) : (
        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column' }}>
          {verifications.map((v) => (
            <li key={v.log_id} style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-start', padding: '10px 0', borderBottom: '1px solid var(--border)', fontSize: 'var(--text-sm)' }}>
              <StatusBadge status={v.final_result} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="mono" style={{ fontWeight: 600 }}>{v.cert_id}</div>
                <div style={{ fontSize: 'var(--text-xs)', color: v.fraud_reason ? 'var(--red-400)' : 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {v.fraud_reason || 'All three layers passed'}
                </div>
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', whiteSpace: 'nowrap', textAlign: 'right' }}>
                {ago(v.verified_at)}
                {v.verifier_id && <div>{v.verifier_id}</div>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

RecentActivity.propTypes = { verifications: PropTypes.array };

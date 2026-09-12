import React, { useCallback, useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { Award, Zap, ShieldAlert, ShieldCheck, AlertTriangle, Handshake, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import StatCard from '../components/Dashboard/StatCard';
import FraudChart from '../components/Dashboard/FraudChart';
import RecentActivity from '../components/Dashboard/RecentActivity';
import StatusBadge from '../components/Common/StatusBadge';
import LoadingSpinner from '../components/Common/LoadingSpinner';
import { ledgerService } from '../services/ledgerService';
import { selectCanRegulate } from '../store/authSlice';

function fmtKwh(v) {
  const n = Number(v || 0);
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)} GWh`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)} MWh`;
  return `${n.toLocaleString()} kWh`;
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const canRegulate = useSelector(selectCanRegulate);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await ledgerService.dashboard(14));
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const resolve = async (id) => {
    try {
      await ledgerService.resolveAnomaly(id);
      toast.success('Anomaly resolved');
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (loading && !data) return <LoadingSpinner size="lg" label="Loading dashboard…" />;
  if (error && !data) {
    return (
      <div className="alert alert-red">
        <ShieldAlert size={18} />
        <div>
          <strong>Could not reach the REC Guard API.</strong>
          <div style={{ fontSize: 'var(--text-xs)', marginTop: 4 }}>{error} — is the backend running on the configured VITE_API_URL?</div>
        </div>
      </div>
    );
  }

  const s = data.stats || {};
  const fraudRate = s.total_verifications ? Math.round((s.fraud_attempts_detected / s.total_verifications) * 100) : 0;

  return (
    <div className="page-grid">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
        <div className="page-intro" style={{ marginBottom: 0 }}>
          <h3>System overview</h3>
          <p>Every issuance, verification attempt and anomaly across the shared ledger. Fraud is detected by construction: hash, signature and registry must all agree.</p>
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={load} disabled={loading}><RefreshCw size={14} /> Refresh</button>
      </div>

      <div className="stat-grid">
        <StatCard label="Certificates" value={s.total_certificates ?? 0} hint={`${s.issued ?? 0} issued · ${s.claimed ?? 0} claimed · ${s.revoked ?? 0} revoked`} icon={Award} color="var(--blue-400)" />
        <StatCard label="Energy registered" value={fmtKwh(s.total_kwh_registered)} hint="Sum of all certified generation" icon={Zap} color="var(--green-400)" />
        <StatCard label="Valid verifications" value={s.valid_verifications ?? 0} hint={`${s.total_verifications ?? 0} total attempts`} icon={ShieldCheck} color="var(--green-400)" />
        <StatCard label="Fraud detected" value={s.fraud_attempts_detected ?? 0} hint={`${fraudRate}% of verification attempts`} icon={ShieldAlert} color="var(--red-400)" />
        <StatCard label="Open anomalies" value={s.open_anomalies ?? 0} hint="Flagged at issuance for review" icon={AlertTriangle} color="var(--amber-400)" />
      </div>

      <FraudChart daily={data.daily_activity} fraudByLayer={data.fraud_by_layer} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 'var(--space-6)' }}>
        <RecentActivity verifications={data.recent_verifications} />

        <div style={{ display: 'grid', gap: 'var(--space-6)', alignContent: 'start' }}>
          <div className="card">
            <div className="card-title">Open anomalies</div>
            {(data.open_anomalies || []).length === 0 ? (
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>No open anomalies.</p>
            ) : (
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {data.open_anomalies.map((a) => (
                  <li key={a.anomaly_id} className="alert alert-amber" style={{ padding: 'var(--space-3)' }}>
                    <AlertTriangle size={16} color="var(--amber-400)" style={{ flexShrink: 0, marginTop: 2 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="mono" style={{ fontWeight: 600, fontSize: 'var(--text-xs)' }}>{a.cert_id} · score {Number(a.anomaly_score).toFixed(3)}</div>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{a.anomaly_reason}</div>
                    </div>
                    {canRegulate && <button type="button" className="btn btn-secondary btn-sm" onClick={() => resolve(a.anomaly_id)}>Resolve</button>}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card">
            <div className="card-title">By energy source</div>
            {(data.by_source || []).length === 0 ? (
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Nothing issued yet. <Link to="/issue">Issue the first certificate.</Link></p>
            ) : (
              <table className="table">
                <thead><tr><th>Source</th><th style={{ textAlign: 'right' }}>Certificates</th><th style={{ textAlign: 'right' }}>Energy</th></tr></thead>
                <tbody>
                  {data.by_source.map((r) => (
                    <tr key={r.source_type}><td>{r.source_type}</td><td className="mono" style={{ textAlign: 'right' }}>{r.count}</td><td className="mono" style={{ textAlign: 'right' }}>{fmtKwh(r.total_kwh)}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <div className="card-title">Latest certificates</div>
            {(data.recent_certificates || []).length === 0 ? (
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>None yet.</p>
            ) : (
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 'var(--text-sm)' }}>
                {data.recent_certificates.slice(0, 6).map((c) => (
                  <li key={c.cert_id} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
                    <span className="mono" style={{ fontWeight: 600 }}>{c.cert_id}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{c.source_type} · {Number(c.energy_kwh).toLocaleString()} kWh</span>
                    <StatusBadge status={c.status} />
                  </li>
                ))}
              </ul>
            )}
            <Link to="/ledger" className="btn btn-ghost btn-sm" style={{ marginTop: 'var(--space-3)' }}><Handshake size={14} /> Open full ledger</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

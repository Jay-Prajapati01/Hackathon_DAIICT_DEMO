import React, { useCallback, useEffect, useState } from 'react';
import { Search, RefreshCw } from 'lucide-react';
import { ledgerService } from '../../services/ledgerService';
import LedgerRow from './LedgerRow';
import LoadingSpinner from '../Common/LoadingSpinner';

const SOURCES = ['', 'Wind', 'Solar', 'Hydro', 'Biomass', 'Geothermal', 'Tidal', 'Other'];
const STATUSES = ['', 'issued', 'claimed', 'revoked'];
const PAGE = 25;

export default function LedgerTable() {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const [source, setSource] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ledgerService.list({ limit: PAGE, offset, search: query || undefined, status: status || undefined, source_type: source || undefined });
      setRows(data.certificates || []);
      setTotal(data.total ?? data.count ?? 0);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [offset, query, status, source]);

  useEffect(() => { load(); }, [load]);

  const submitSearch = (e) => {
    e.preventDefault();
    setOffset(0);
    setQuery(search.trim());
  };

  const pages = Math.max(1, Math.ceil(total / PAGE));
  const page = Math.floor(offset / PAGE) + 1;

  return (
    <div className="card">
      <form onSubmit={submitSearch} style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
        <div style={{ position: 'relative', flex: '1 1 260px' }}>
          <Search size={16} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
          <input className="field" style={{ paddingLeft: 36 }} placeholder="Search certificate, generator, issuer or buyer…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <select className="field" style={{ width: 160 }} value={status} onChange={(e) => { setOffset(0); setStatus(e.target.value); }}>
          {STATUSES.map((s) => <option key={s} value={s}>{s ? s[0].toUpperCase() + s.slice(1) : 'All statuses'}</option>)}
        </select>
        <select className="field" style={{ width: 160 }} value={source} onChange={(e) => { setOffset(0); setSource(e.target.value); }}>
          {SOURCES.map((s) => <option key={s} value={s}>{s || 'All sources'}</option>)}
        </select>
        <button type="submit" className="btn btn-secondary">Search</button>
        <button type="button" className="btn btn-ghost" onClick={load} title="Refresh"><RefreshCw size={16} /></button>
      </form>

      {error && <div className="alert alert-red" style={{ marginBottom: 'var(--space-4)' }}>{error}</div>}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th />
              <th>Certificate ID</th>
              <th>Generator</th>
              <th>Source</th>
              <th style={{ textAlign: 'right' }}>kWh</th>
              <th>Generated</th>
              <th>Issuer</th>
              <th>Status</th>
              <th>Issued (UTC)</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={10} style={{ textAlign: 'center', padding: 'var(--space-8)' }}><LoadingSpinner label="Loading ledger…" /></td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={10} style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--text-secondary)' }}>No certificates match.</td></tr>
            ) : rows.map((c) => <LedgerRow key={c.cert_id} cert={c} onChanged={load} />)}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
        <span>{total.toLocaleString()} certificate{total === 1 ? '' : 's'}</span>
        <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button type="button" className="btn btn-secondary btn-sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Prev</button>
          Page {page} / {pages}
          <button type="button" className="btn btn-secondary btn-sm" disabled={page >= pages} onClick={() => setOffset(offset + PAGE)}>Next</button>
        </span>
      </div>
    </div>
  );
}

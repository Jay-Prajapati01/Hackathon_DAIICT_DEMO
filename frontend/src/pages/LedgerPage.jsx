import React from 'react';
import LedgerTable from '../components/Ledger/LedgerTable';

export default function LedgerPage() {
  return (
    <div className="page-grid">
      <div className="page-intro">
        <h3>Shared REC ledger</h3>
        <p>
          The single source of truth for every issued certificate. Expand a row to see its registry hash and the full
          verification history. Signed-in buyers can claim certificates; regulators can revoke them.
        </p>
      </div>
      <LedgerTable />
    </div>
  );
}

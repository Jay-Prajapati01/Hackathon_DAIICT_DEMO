import React from 'react';

export default function Footer() {
  const version = import.meta.env.VITE_APP_VERSION || '1.0.0';
  return (
    <footer className="footer">
      <span>REC Guard v{version} — Team Exodus · Renewable Energy Intelligence</span>
      <span>SHA-256 · RSA-2048 PSS · LSB steganography · Shared ledger</span>
    </footer>
  );
}

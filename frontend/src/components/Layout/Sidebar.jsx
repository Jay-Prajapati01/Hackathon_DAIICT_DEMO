import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FilePlus2, ShieldCheck, Database, Shield } from 'lucide-react';

const NAV = [
  { to: '/', label: 'Dashboard', Icon: LayoutDashboard, end: true },
  { to: '/issue', label: 'Issue Certificate', Icon: FilePlus2 },
  { to: '/verify', label: 'Verify Certificate', Icon: ShieldCheck },
  { to: '/ledger', label: 'REC Ledger', Icon: Database },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span style={{ display: 'grid', placeItems: 'center', width: 36, height: 36, borderRadius: 8, background: 'var(--green-500)' }}>
          <Shield size={20} color="#fff" />
        </span>
        <h1>
          REC Guard
          <span>Certificate Integrity</span>
        </h1>
      </div>
      {NAV.map(({ to, label, Icon, end }) => (
        <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <Icon size={18} />
          {label}
        </NavLink>
      ))}
      <div className="sidebar-foot">
        Three-layer verification
        <br />
        Steg · Signature · Ledger
      </div>
    </aside>
  );
}

import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { LogIn, LogOut, UserCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { logout, selectUser } from '../../store/authSlice';

const TITLES = {
  '/': ['Regulator Dashboard', 'System-wide issuance, verification and fraud activity'],
  '/issue': ['Issue Certificate', 'Module 1 — hash, sign, embed and register a new REC'],
  '/verify': ['Verify Certificate', 'Module 2 — three-layer fraud detection on any PDF/PNG'],
  '/ledger': ['REC Ledger', 'Shared, append-only registry of every issued certificate'],
};

export default function Header() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const user = useSelector(selectUser);
  const [title, subtitle] = TITLES[pathname] || ['REC Guard', ''];

  const onLogout = () => {
    dispatch(logout());
    toast.success('Signed out');
    navigate('/');
  };

  return (
    <header className="header">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        {user ? (
          <>
            <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
              <UserCircle2 size={18} />
              <span>
                <strong style={{ color: 'var(--text-primary)' }}>{user.email}</strong>
                <span className="badge badge-muted" style={{ marginLeft: 8 }}>{user.role}</span>
              </span>
            </span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={onLogout}>
              <LogOut size={14} /> Sign out
            </button>
          </>
        ) : (
          <Link to="/login" className="btn btn-secondary btn-sm">
            <LogIn size={14} /> Sign in
          </Link>
        )}
      </div>
    </header>
  );
}

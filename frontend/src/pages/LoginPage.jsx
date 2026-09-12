import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { Shield } from 'lucide-react';
import toast from 'react-hot-toast';
import { login, register as registerUser } from '../store/authSlice';
import LoadingSpinner from '../components/Common/LoadingSpinner';

const ROLES = [
  ['auditor', 'Independent Auditor'],
  ['buyer', 'Corporate REC Buyer'],
  ['issuer', 'Certificate Issuing Body'],
  ['regulator', 'Renewable Energy Regulator'],
];

export default function LoginPage() {
  const [mode, setMode] = useState('login');
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const status = useSelector((s) => s.auth.status);
  const loading = status === 'loading';
  const { register, handleSubmit, formState: { errors } } = useForm({ defaultValues: { role: 'auditor' } });

  const onSubmit = async (data) => {
    const action = await dispatch(mode === 'login' ? login(data) : registerUser(data));
    if (action.meta.requestStatus === 'fulfilled') {
      toast.success(mode === 'login' ? `Welcome back, ${action.payload.user.email}` : 'Account created');
      navigate('/');
    } else {
      const err = action.payload || {};
      toast.error(`${err.message}${err.details ? ` — ${err.details.join(' ')}` : ''}`);
    }
  };

  return (
    <div className="login-shell">
      <div className="card login-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 'var(--space-6)' }}>
          <span style={{ display: 'grid', placeItems: 'center', width: 40, height: 40, borderRadius: 8, background: 'var(--green-500)' }}><Shield size={22} color="#fff" /></span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 'var(--text-lg)' }}>REC Guard</div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{mode === 'login' ? 'Sign in to claim, issue and audit' : 'Create an account'}</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 4, marginBottom: 'var(--space-6)', background: 'var(--bg-tertiary)', padding: 4, borderRadius: 'var(--radius-md)' }}>
          {['login', 'register'].map((m) => (
            <button key={m} type="button" onClick={() => setMode(m)} className="btn btn-sm" style={{ flex: 1, background: mode === m ? 'var(--bg-secondary)' : 'transparent', color: mode === m ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
              {m === 'login' ? 'Sign in' : 'Register'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'grid', gap: 'var(--space-4)' }}>
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input id="email" type="email" className="field" placeholder="you@organisation.com" autoComplete="email" {...register('email', { required: 'Email is required' })} />
            {errors.email && <span className="error-text">{errors.email.message}</span>}
          </div>
          <div>
            <label className="label" htmlFor="password">Password</label>
            <input id="password" type="password" className="field" placeholder="••••••••" autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              {...register('password', { required: 'Password is required', minLength: { value: 8, message: 'At least 8 characters' } })} />
            {errors.password && <span className="error-text">{errors.password.message}</span>}
          </div>
          {mode === 'register' && (
            <>
              <div>
                <label className="label" htmlFor="role">Role</label>
                <select id="role" className="field" {...register('role')}>
                  {ROLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="organisation">Organisation</label>
                <input id="organisation" className="field" placeholder="Acme Corp" {...register('organisation')} />
              </div>
            </>
          )}
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ padding: '12px' }}>
            {loading ? <LoadingSpinner label="Please wait…" style={{ color: '#fff' }} /> : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <p style={{ marginTop: 'var(--space-6)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', textAlign: 'center' }}>
          Verification is public — <Link to="/verify">verify a certificate without signing in</Link>.
        </p>
      </div>
    </div>
  );
}

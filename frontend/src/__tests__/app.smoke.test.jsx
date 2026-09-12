import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';

vi.mock('../services/api', async () => {
  const { route, LOGIN } = await import('./mockApi');
  const calls = [];
  const api = {
    get: vi.fn(async (url, cfg) => { calls.push(['GET', url, cfg]); return { data: route('GET', url) }; }),
    post: vi.fn(async (url, body, cfg) => { calls.push(['POST', url, body, cfg]); return { data: route('POST', url) }; }),
    __calls: calls,
    __LOGIN: LOGIN,
  };
  return { default: api, api, API_BASE: 'http://api.test', TOKEN_KEY: 'rec_guard_token', USER_KEY: 'rec_guard_user', fileUrl: (p) => `http://api.test${p}` };
});

import api from '../services/api';
import issueReducer from '../store/issueSlice';
import verifyReducer from '../store/verifySlice';
import authReducer from '../store/authSlice';
import { AppRoutes } from '../App';
import { FRAUD_RESULT } from './mockApi';

function makeStore(preloaded) {
  return configureStore({
    reducer: { issue: issueReducer, verify: verifyReducer, auth: authReducer },
    middleware: (g) => g({ serializableCheck: false }),
    preloadedState: preloaded,
  });
}

function renderAt(path, store = makeStore()) {
  return { store, ...render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </Provider>,
  ) };
}

beforeEach(() => {
  api.__calls.length = 0;
  api.get.mockClear();
  api.post.mockClear();
  localStorage.clear();
});

describe('Dashboard page', () => {
  it('renders stats, charts data and recent activity from /api/admin/dashboard', async () => {
    renderAt('/');
    expect(await screen.findByText('System overview')).toBeInTheDocument();
    expect(api.get).toHaveBeenCalledWith('/api/admin/dashboard', expect.anything());
    expect(screen.getByText('Fraud detected').closest('.stat-card')).toHaveTextContent('4');
    expect(screen.getByText('Energy registered').closest('.stat-card')).toHaveTextContent('9.00 GWh');
    expect(screen.getByText(/No steganographic payload detected/)).toBeInTheDocument();
    expect(screen.getByText(/exceeds the plausible single-certificate ceiling/)).toBeInTheDocument();
    // regulator-only resolve button hidden for anonymous users
    expect(screen.queryByRole('button', { name: 'Resolve' })).not.toBeInTheDocument();
  });

  it('shows the resolve control to regulators', async () => {
    const store = makeStore({ auth: { token: 't', user: { email: 'reg@x', role: 'regulator' }, status: 'idle', error: null } });
    renderAt('/', store);
    expect(await screen.findByRole('button', { name: 'Resolve' })).toBeInTheDocument();
  });
});

describe('Issue page', () => {
  it('submits the form and shows the issued certificate with an anomaly warning', async () => {
    renderAt('/issue');
    fireEvent.change(screen.getByLabelText('Generator ID'), { target: { value: 'WF-A-01' } });
    fireEvent.change(screen.getByLabelText('Energy Generated (kWh)'), { target: { value: '100' } });
    fireEvent.change(screen.getByLabelText('Generation Date'), { target: { value: '2026-03-01' } });
    fireEvent.change(screen.getByLabelText('Issuer ID'), { target: { value: 'ISSUER-GreenCert-04' } });
    fireEvent.click(screen.getByRole('button', { name: 'Issue REC Certificate' }));

    expect(await screen.findByText('REC-WND-2026-0091')).toBeInTheDocument();
    const [, url, body] = api.__calls.find((c) => c[1] === '/api/issue');
    expect(url).toBe('/api/issue');
    expect(body).toMatchObject({ generator_id: 'WF-A-01', source_type: 'Wind', energy_kwh: 100, generation_date: '2026-03-01', issuer_id: 'ISSUER-GreenCert-04', format: 'png', cert_id: null });
    expect(screen.getByText('Anomaly flagged for regulator review.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Download PNG/ })).toHaveAttribute('href', 'http://api.test/api/certificate/REC-WND-2026-0091.png');
    expect(screen.getByAltText('Certificate REC-WND-2026-0091')).toHaveAttribute('src', 'http://api.test/api/certificate/REC-WND-2026-0091.png/preview');
  });

  it('blocks submission when required fields are missing', async () => {
    renderAt('/issue');
    fireEvent.click(screen.getByRole('button', { name: 'Issue REC Certificate' }));
    expect(await screen.findByText('Generator ID is required')).toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
  });
});

describe('Verify page', () => {
  it('uploads a file, calls /api/verify as multipart and renders a VALID verdict', async () => {
    renderAt('/verify');
    const input = document.querySelector('input[type="file"]');
    const file = new File([new Uint8Array([137, 80, 78, 71])], 'cert.png', { type: 'image/png' });
    fireEvent.change(input, { target: { files: [file] } });
    expect(await screen.findByText('cert.png')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Verify Certificate' }));

    expect(await screen.findByText('VALID')).toBeInTheDocument();
    const call = api.__calls.find((c) => c[1] === '/api/verify');
    expect(call[2]).toBeInstanceOf(FormData);
    expect(call[2].get('file')).toBe(file);
    expect(call[2].get('claim')).toBeNull();
    expect(screen.getAllByText('PASS')).toHaveLength(3);
    expect(screen.getByText('Ledger Record')).toBeInTheDocument();
  });

  it('sends claim fields and renders a FRAUD verdict with failed and skipped layers', async () => {
    api.post.mockImplementationOnce(async (url, body) => { api.__calls.push(['POST', url, body]); return { data: FRAUD_RESULT }; });
    renderAt('/verify');
    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [new File(['x'], 'suspect.pdf', { type: 'application/pdf' })] } });
    await screen.findByText('suspect.pdf');
    fireEvent.click(screen.getByLabelText('Claim this certificate if valid'));
    fireEvent.change(screen.getByLabelText('Claiming entity (buyer ID)'), { target: { value: 'BUYER-Acme-Corp' } });
    fireEvent.click(screen.getByRole('button', { name: 'Verify Certificate' }));

    expect(await screen.findByText('FRAUD')).toBeInTheDocument();
    const call = api.__calls.find((c) => c[1] === '/api/verify');
    expect(call[2].get('claim')).toBe('true');
    expect(call[2].get('claimed_by')).toBe('BUYER-Acme-Corp');
    expect(screen.getByText('FAIL')).toBeInTheDocument();
    expect(screen.getByText('SKIPPED')).toBeInTheDocument();
    expect(screen.getAllByText(/LAYER_1_FAIL/).length).toBeGreaterThan(0);
  });
});

describe('Ledger page', () => {
  it('lists certificates, filters, and expands a row to show verification history', async () => {
    renderAt('/ledger');
    expect(await screen.findByText('REC-WND-2026-0091')).toBeInTheDocument();
    expect(screen.getByText('REC-SLR-2026-0034')).toBeInTheDocument();
    expect(screen.getByText('2 certificates')).toBeInTheDocument();

    fireEvent.change(screen.getByDisplayValue('All sources'), { target: { value: 'Solar' } });
    await waitFor(() => expect(api.get).toHaveBeenLastCalledWith('/api/ledger', { params: expect.objectContaining({ source_type: 'Solar' }) }));

    fireEvent.change(screen.getByPlaceholderText(/Search certificate/), { target: { value: 'WF-A' } });
    fireEvent.click(screen.getByRole('button', { name: 'Search' }));
    await waitFor(() => expect(api.get).toHaveBeenLastCalledWith('/api/ledger', { params: expect.objectContaining({ search: 'WF-A' }) }));

    fireEvent.click(screen.getByText('REC-WND-2026-0091'));
    expect(await screen.findByText('Verification history')).toBeInTheDocument();
    expect(api.get).toHaveBeenCalledWith('/api/ledger/REC-WND-2026-0091/history');
    expect(await screen.findByText(/No steganographic payload detected/)).toBeInTheDocument();
  });

  it('hides claim/revoke actions for anonymous users and shows them for regulators', async () => {
    const anon = renderAt('/ledger');
    await screen.findByText('REC-WND-2026-0091');
    expect(screen.queryByTitle('Claim')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Revoke')).not.toBeInTheDocument();
    anon.unmount();

    const store = makeStore({ auth: { token: 't', user: { email: 'reg@x', role: 'regulator' }, status: 'idle', error: null } });
    renderAt('/ledger', store);
    const row = (await screen.findByText('REC-WND-2026-0091')).closest('tr');
    expect(within(row).getByTitle('Claim')).toBeInTheDocument();
    expect(within(row).getByTitle('Revoke')).toBeInTheDocument();
    // claimed certificates cannot be claimed again, but can still be revoked
    const claimedRow = screen.getByText('REC-SLR-2026-0034').closest('tr');
    expect(within(claimedRow).queryByTitle('Claim')).not.toBeInTheDocument();
    expect(within(claimedRow).getByTitle('Revoke')).toBeInTheDocument();
  });
});

describe('Login page', () => {
  it('logs in, persists the token and shows the user in the header', async () => {
    const { store } = renderAt('/login');
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'admin@recguard.io' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'changeme1' } });
    fireEvent.click(document.querySelector('form button[type="submit"]'));

    await waitFor(() => expect(store.getState().auth.token).toBe('token-123'));
    expect(api.post).toHaveBeenCalledWith('/api/auth/login', { email: 'admin@recguard.io', password: 'changeme1' });
    expect(localStorage.getItem('rec_guard_token')).toBe('token-123');
    // redirected to dashboard with the signed-in header
    expect(await screen.findByText('admin@recguard.io')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Sign out/ }));
    await waitFor(() => expect(store.getState().auth.token).toBeNull());
    expect(localStorage.getItem('rec_guard_token')).toBeNull();
  });

  it('switches to registration and sends role + organisation', async () => {
    renderAt('/login');
    fireEvent.click(screen.getByRole('button', { name: 'Register' }));
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'buyer@acme.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'buyer' } });
    fireEvent.change(screen.getByLabelText('Organisation'), { target: { value: 'Acme' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/api/auth/register', { email: 'buyer@acme.com', password: 'password123', role: 'buyer', organisation: 'Acme' }));
  });
});

describe('Routing', () => {
  it('redirects unknown paths to the dashboard', async () => {
    renderAt('/nope');
    expect(await screen.findByText('System overview')).toBeInTheDocument();
  });
});

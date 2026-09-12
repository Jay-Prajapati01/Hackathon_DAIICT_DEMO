/**
 * Canned backend responses for the frontend smoke tests.
 * Mirrors the real Flask API shapes (see backend/routes).
 */
export const ISSUED = {
  success: true,
  cert_id: 'REC-WND-2026-0091',
  data_hash: 'c9f0f895fb98ab9159f51fd0297e236d570bfa2c72a43571f1e5c68d96e9f2a3',
  issued_at: '2026-03-02T10:15:00+00:00',
  format: 'png',
  file_name: 'REC-WND-2026-0091.png',
  download_url: '/api/certificate/REC-WND-2026-0091.png',
  preview_url: '/api/certificate/REC-WND-2026-0091.png/preview',
  anomaly_flag: true,
  anomaly_reason: '9,000,000 kWh exceeds the plausible single-certificate ceiling for Wind (2,500,000 kWh).',
  anomaly: { is_anomaly: true, reasons: ['9,000,000 kWh exceeds the plausible single-certificate ceiling for Wind (2,500,000 kWh).'] },
  payload: { cert_id: 'REC-WND-2026-0091', energy_kwh: 100 },
};

export const VALID_RESULT = {
  success: true,
  cert_id: 'REC-WND-2026-0091',
  final_result: 'VALID',
  is_valid: true,
  layers: {
    layer1_steganographic_integrity: { passed: true, detail: 'Hash integrity confirmed.' },
    layer2_cryptographic_signature: { passed: true, detail: 'RSA-2048 signature is valid.' },
    layer3_ledger_lookup: { passed: true, detail: "Certificate 'REC-WND-2026-0091' is registered, valid, and not yet claimed." },
  },
  fraud_reason: null,
  extracted_data: { cert_id: 'REC-WND-2026-0091', energy_kwh: 100 },
  ledger_record: { status: 'issued', generator_id: 'WF-A-01', source_type: 'Wind', energy_kwh: 100, generation_date: '2026-03-01', issuer_id: 'ISSUER-GreenCert-04', issued_at: '2026-03-02T10:15:00+00:00' },
  claimed: false,
  anomalies: [],
  file_sha256: 'ab'.repeat(32),
};

export const FRAUD_RESULT = {
  ...VALID_RESULT,
  final_result: 'FRAUD',
  is_valid: false,
  layers: {
    layer1_steganographic_integrity: { passed: false, detail: 'HASH MISMATCH. The visible certificate data has been altered after issuance.' },
    layer2_cryptographic_signature: { passed: true, detail: 'RSA-2048 signature is valid.' },
    layer3_ledger_lookup: { passed: false, detail: 'Skipped — Layer 1 failed (hash mismatch).' },
  },
  fraud_reason: 'LAYER_1_FAIL: Data hash mismatch — certificate was tampered.',
  ledger_record: null,
};

export const LEDGER = {
  success: true,
  total: 2,
  count: 2,
  limit: 25,
  offset: 0,
  certificates: [
    { cert_id: 'REC-WND-2026-0091', generator_id: 'WF-A-01', source_type: 'Wind', energy_kwh: 100, generation_date: '2026-03-01', issuer_id: 'ISSUER-GreenCert-04', status: 'issued', issued_at: '2026-03-02T10:15:00+00:00', data_hash: 'c9'.repeat(32), signature: 'sig', cert_file_path: '/x/REC-WND-2026-0091.png' },
    { cert_id: 'REC-SLR-2026-0034', generator_id: 'SP-C-01', source_type: 'Solar', energy_kwh: 1000, generation_date: '2026-02-15', issuer_id: 'ISSUER-SolarAuth-01', status: 'claimed', claimed_by: 'BUYER-Acme-Corp', claimed_at: '2026-03-03T00:00:00+00:00', issued_at: '2026-02-16T10:15:00+00:00', data_hash: 'aa'.repeat(32), signature: 'sig', cert_file_path: '/x/REC-SLR-2026-0034.pdf' },
  ],
};

export const DASHBOARD = {
  success: true,
  stats: { total_certificates: 3, issued: 1, claimed: 1, revoked: 1, total_kwh_registered: 9001100, total_verifications: 6, valid_verifications: 2, fraud_attempts_detected: 4, open_anomalies: 1 },
  by_source: [{ source_type: 'Wind', count: 2, total_kwh: 9000100 }, { source_type: 'Solar', count: 1, total_kwh: 1000 }],
  fraud_by_layer: [{ layer: 'Layer 3 — Ledger', count: 2 }, { layer: 'Layer 1 — Steg Integrity', count: 2 }],
  daily_activity: [{ day: '2026-09-12', issued: 3, valid: 2, fraud: 4 }],
  recent_verifications: [
    { log_id: 2, cert_id: 'UNKNOWN', verified_at: '2026-09-12T08:00:00+00:00', final_result: 'FRAUD', fraud_reason: 'LAYER_1_FAIL: No steganographic payload detected.' },
    { log_id: 1, cert_id: 'REC-WND-2026-0091', verified_at: '2026-09-12T07:59:00+00:00', final_result: 'VALID', fraud_reason: null, verifier_id: 'buyer@acme.com' },
  ],
  recent_certificates: LEDGER.certificates,
  open_anomalies: [{ anomaly_id: 1, cert_id: 'REC-WND-2026-1473', anomaly_score: -1, anomaly_reason: 'exceeds the plausible single-certificate ceiling' }],
};

export const LOGIN = {
  success: true,
  access_token: 'token-123',
  expires_in: 3600,
  user: { user_id: 1, email: 'admin@recguard.io', role: 'admin', organisation: 'REC Guard', created_at: '2026-01-01' },
};

/** Route a mocked request to a canned response by method + URL. */
export function route(method, url) {
  if (url.startsWith('/api/admin/dashboard')) return DASHBOARD;
  if (url.startsWith('/api/ledger/stats')) return DASHBOARD.stats;
  if (url.match(/^\/api\/ledger\/[^/]+\/history/)) return { success: true, verifications: DASHBOARD.recent_verifications };
  if (url.startsWith('/api/ledger')) return LEDGER;
  if (url === '/api/issue') return ISSUED;
  if (url === '/api/verify') return VALID_RESULT;
  if (url === '/api/auth/login') return LOGIN;
  if (url === '/api/auth/register') return LOGIN;
  throw new Error(`Unmocked ${method} ${url}`);
}

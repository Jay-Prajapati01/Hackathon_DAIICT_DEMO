// frontend/src/components/Issue/IssueForm.jsx
import React from 'react';
import PropTypes from 'prop-types';
import { useForm } from 'react-hook-form';
import { useDispatch, useSelector } from 'react-redux';
import toast from 'react-hot-toast';
import { issueCertificate } from '../../store/issueSlice';
import { selectUser } from '../../store/authSlice';
import LoadingSpinner from '../Common/LoadingSpinner';

const SOURCE_TYPES = ['Wind', 'Solar', 'Hydro', 'Biomass', 'Geothermal', 'Tidal', 'Other'];

export default function IssueForm({ onSuccess }) {
  const dispatch = useDispatch();
  const status = useSelector((s) => s.issue.status);
  const user = useSelector(selectUser);
  const loading = status === 'loading';
  const today = new Date().toISOString().slice(0, 10);

  const { register, handleSubmit, formState: { errors }, reset } = useForm({
    defaultValues: { source_type: 'Wind', format: 'png', issuer_id: user?.email || '' },
  });

  const onSubmit = async (data) => {
    const action = await dispatch(
      issueCertificate({
        generator_id: data.generator_id.trim(),
        source_type: data.source_type,
        energy_kwh: parseFloat(data.energy_kwh),
        generation_date: data.generation_date,
        issuer_id: data.issuer_id.trim(),
        cert_id: data.cert_id?.trim() || null,
        format: data.format || 'png',
      }),
    );

    if (issueCertificate.fulfilled.match(action)) {
      const result = action.payload;
      toast.success(`Certificate issued: ${result.cert_id}`);
      if (result.anomaly_flag) {
        toast(`Anomaly flagged: ${result.anomaly_reason}`, { icon: '⚠️', duration: 7000 });
      }
      onSuccess?.(result);
      reset({ source_type: data.source_type, format: data.format, issuer_id: data.issuer_id });
    } else {
      const err = action.payload || {};
      const detail = Array.isArray(err.details) ? err.details.join(' ') : '';
      toast.error(`Issuance failed: ${err.message}${detail ? ` — ${detail}` : ''}`, { duration: 7000 });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--space-4)' }}>
        <div>
          <label className="label" htmlFor="generator_id">Generator ID</label>
          <input id="generator_id" className="field" placeholder="WF-A-01" autoComplete="off"
            {...register('generator_id', { required: 'Generator ID is required' })} />
          {errors.generator_id && <span className="error-text">{errors.generator_id.message}</span>}
        </div>

        <div>
          <label className="label" htmlFor="source_type">Source Type</label>
          <select id="source_type" className="field" {...register('source_type', { required: true })}>
            {SOURCE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>

        <div>
          <label className="label" htmlFor="energy_kwh">Energy Generated (kWh)</label>
          <input id="energy_kwh" type="number" step="0.001" min="0.001" className="field" placeholder="100.0"
            {...register('energy_kwh', { required: 'Energy is required', min: { value: 0.001, message: 'Must be > 0' } })} />
          {errors.energy_kwh && <span className="error-text">{errors.energy_kwh.message}</span>}
        </div>

        <div>
          <label className="label" htmlFor="generation_date">Generation Date</label>
          <input id="generation_date" type="date" className="field" max={today}
            {...register('generation_date', { required: 'Date is required' })} />
          {errors.generation_date && <span className="error-text">{errors.generation_date.message}</span>}
        </div>

        <div>
          <label className="label" htmlFor="issuer_id">Issuer ID</label>
          <input id="issuer_id" className="field" placeholder="ISSUER-GreenCert-04" autoComplete="off"
            {...register('issuer_id', { required: 'Issuer ID is required' })} />
          {errors.issuer_id && <span className="error-text">{errors.issuer_id.message}</span>}
        </div>

        <div>
          <label className="label" htmlFor="format">Output Format</label>
          <select id="format" className="field" {...register('format')}>
            <option value="png">PNG (Recommended)</option>
            <option value="pdf">PDF</option>
          </select>
        </div>

        <div style={{ gridColumn: '1 / -1' }}>
          <label className="label" htmlFor="cert_id">Certificate ID <span style={{ color: 'var(--text-muted)' }}>(optional — auto-generated as REC-SRC-YYYY-NNNN)</span></label>
          <input id="cert_id" className="field mono" placeholder="REC-WND-2026-0091" autoComplete="off"
            {...register('cert_id', { pattern: { value: /^[A-Z0-9][A-Z0-9\-_]{2,63}$/, message: 'Uppercase letters, digits and hyphens only' } })} />
          {errors.cert_id && <span className="error-text">{errors.cert_id.message}</span>}
        </div>
      </div>

      <button type="submit" disabled={loading} className="btn btn-primary" style={{ alignSelf: 'flex-start', padding: '12px 24px' }}>
        {loading ? <LoadingSpinner label="Issuing Certificate..." style={{ color: '#fff' }} /> : 'Issue REC Certificate'}
      </button>
    </form>
  );
}

IssueForm.propTypes = { onSuccess: PropTypes.func };

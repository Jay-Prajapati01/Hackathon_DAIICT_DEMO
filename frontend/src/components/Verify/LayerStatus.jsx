import React from 'react';
import PropTypes from 'prop-types';
import { CheckCircle, XCircle, MinusCircle } from 'lucide-react';

/** One verification layer card (pass / fail / skipped). */
export default function LayerStatus({ number, name, passed, detail }) {
  const skipped = !passed && /^skipped/i.test(detail || '');
  const color = passed ? 'var(--green-400)' : skipped ? 'var(--text-secondary)' : 'var(--red-400)';
  const Icon = passed ? CheckCircle : skipped ? MinusCircle : XCircle;
  const border = passed ? 'var(--green-500)' : skipped ? 'var(--border)' : 'var(--red-400)';

  return (
    <div style={{
      padding: 'var(--space-4) var(--space-6)',
      background: 'var(--bg-tertiary)',
      borderRadius: 'var(--radius-md)',
      border: `1px solid ${border}`,
      marginBottom: 'var(--space-3)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
        <Icon size={18} color={color} />
        <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color }}>
          Layer {number} — {name}
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: 'var(--text-xs)',
          padding: '2px 8px',
          borderRadius: 12,
          background: passed ? 'var(--green-glow)' : skipped ? 'var(--bg-secondary)' : 'var(--red-glow)',
          color,
          fontWeight: 700,
        }}>
          {passed ? 'PASS' : skipped ? 'SKIPPED' : 'FAIL'}
        </span>
      </div>
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.5, wordBreak: 'break-word' }}>
        {detail}
      </p>
    </div>
  );
}

LayerStatus.propTypes = {
  number: PropTypes.number.isRequired,
  name: PropTypes.string.isRequired,
  passed: PropTypes.bool,
  detail: PropTypes.string,
};

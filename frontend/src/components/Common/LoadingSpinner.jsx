import React from 'react';
import PropTypes from 'prop-types';

export default function LoadingSpinner({ size = 'sm', label, style }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, color: 'var(--text-secondary)', ...style }}>
      <span className={`spinner ${size === 'lg' ? 'spinner-lg' : ''}`} />
      {label && <span style={{ fontSize: 'var(--text-sm)' }}>{label}</span>}
    </span>
  );
}

LoadingSpinner.propTypes = { size: PropTypes.oneOf(['sm', 'lg']), label: PropTypes.string, style: PropTypes.object };

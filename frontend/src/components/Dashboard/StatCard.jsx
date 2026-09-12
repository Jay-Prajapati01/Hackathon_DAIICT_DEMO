import React from 'react';
import PropTypes from 'prop-types';

export default function StatCard({ label, value, hint, icon: Icon, color = 'var(--text-primary)' }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{Icon && <Icon size={14} color={color} />}{label}</span>
      <span className="stat-value" style={{ color }}>{value}</span>
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  );
}

StatCard.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  hint: PropTypes.string,
  icon: PropTypes.elementType,
  color: PropTypes.string,
};

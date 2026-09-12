import React from 'react';
import PropTypes from 'prop-types';
import { CheckCircle, XCircle, AlertTriangle, Clock, Ban } from 'lucide-react';

const MAP = {
  issued: { cls: 'badge-blue', Icon: Clock, label: 'Issued' },
  claimed: { cls: 'badge-green', Icon: CheckCircle, label: 'Claimed' },
  revoked: { cls: 'badge-red', Icon: Ban, label: 'Revoked' },
  VALID: { cls: 'badge-green', Icon: CheckCircle, label: 'Valid' },
  FRAUD: { cls: 'badge-red', Icon: XCircle, label: 'Fraud' },
  PASS: { cls: 'badge-green', Icon: CheckCircle, label: 'Pass' },
  FAIL: { cls: 'badge-red', Icon: XCircle, label: 'Fail' },
  ANOMALY: { cls: 'badge-amber', Icon: AlertTriangle, label: 'Anomaly' },
};

export default function StatusBadge({ status, label, icon = true }) {
  const entry = MAP[status] || { cls: 'badge-muted', Icon: null, label: status };
  const Icon = icon ? entry.Icon : null;
  return (
    <span className={`badge ${entry.cls}`}>
      {Icon && <Icon size={12} />}
      {label || entry.label}
    </span>
  );
}

StatusBadge.propTypes = {
  status: PropTypes.string,
  label: PropTypes.string,
  icon: PropTypes.bool,
};

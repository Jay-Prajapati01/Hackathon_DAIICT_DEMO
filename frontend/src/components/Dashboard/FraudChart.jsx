import React from 'react';
import PropTypes from 'prop-types';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const GREEN = '#3FB950';
const RED = '#F85149';
const BLUE = '#388BFD';
const AMBER = '#D29922';
const PIE_COLORS = [RED, AMBER, BLUE, '#8B949E'];

function Empty({ text }) {
  return <div style={{ height: 240, display: 'grid', placeItems: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>{text}</div>;
}
Empty.propTypes = { text: PropTypes.string };

/** Daily issuance vs. valid/fraud verifications + fraud-by-layer breakdown. */
export default function FraudChart({ daily = [], fraudByLayer = [] }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-6)' }}>
      <div className="card">
        <div className="card-title">Activity by day</div>
        {daily.length === 0 ? <Empty text="No activity yet — issue or verify a certificate." /> : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={daily} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid stroke="#30363D" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" tick={{ fill: '#8B949E', fontSize: 11 }} tickFormatter={(d) => d.slice(5)} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#8B949E', fontSize: 11 }} allowDecimals={false} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
              <Legend wrapperStyle={{ fontSize: 12, color: '#8B949E' }} />
              <Bar dataKey="issued" name="Issued" fill={BLUE} radius={[3, 3, 0, 0]} />
              <Bar dataKey="valid" name="Valid" fill={GREEN} radius={[3, 3, 0, 0]} />
              <Bar dataKey="fraud" name="Fraud" fill={RED} radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
      <div className="card">
        <div className="card-title">Fraud caught by layer</div>
        {fraudByLayer.length === 0 ? <Empty text="No fraud attempts detected yet." /> : (
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={fraudByLayer} dataKey="count" nameKey="layer" innerRadius={55} outerRadius={90} paddingAngle={3} stroke="none">
                {fraudByLayer.map((entry, i) => <Cell key={entry.layer} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12, color: '#8B949E' }} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

FraudChart.propTypes = { daily: PropTypes.array, fraudByLayer: PropTypes.array };

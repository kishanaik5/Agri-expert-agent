import React from 'react';
import { Leaf, ShieldAlert, MapPin, Droplet, Sliders, CheckCircle2 } from 'lucide-react';

export default function KpiBar({ cropsCount = 164 }) {
  return (
    <section className="kpi-bar">
      <div className="kpi-container">
        <div className="kpi-metrics-group">
          <div className="kpi-item">
            <Leaf style={{ width: 14, height: 14, color: 'var(--primary)' }} />
            <span>Crops Mapped:</span>
            <span className="kpi-value">{cropsCount} Species</span>
          </div>
          <div className="kpi-item">
            <ShieldAlert style={{ width: 14, height: 14, color: 'var(--warning)' }} />
            <span>Disease & Pest Profiles:</span>
            <span className="kpi-value">3,083 Protocols</span>
          </div>
          <div className="kpi-item">
            <MapPin style={{ width: 14, height: 14, color: 'var(--blue)' }} />
            <span>PIN Codes Mapped:</span>
            <span className="kpi-value">19,486 PINs (15 Zones)</span>
          </div>
          <div className="kpi-item">
            <Droplet style={{ width: 14, height: 14, color: 'var(--info)' }} />
            <span>District Groundwater:</span>
            <span className="kpi-value">1,347 Outlooks</span>
          </div>
          <div className="kpi-item">
            <Sliders style={{ width: 14, height: 14, color: '#a855f7' }} />
            <span>Suitability Model:</span>
            <span className="kpi-value">6-Factor Weighted</span>
          </div>
        </div>

        <div className="status-badge live" style={{ fontSize: '0.6875rem' }}>
          <CheckCircle2 style={{ width: 13, height: 13 }} />
          <span>Agronomist Verified Data</span>
        </div>
      </div>
    </section>
  );
}

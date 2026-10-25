import React, { useState, useEffect } from 'react';
import { Calendar, Bug, ShieldAlert, Thermometer, Droplets, Sun, Info } from 'lucide-react';

export default function PhenologyCalendar({ crops }) {
  const [selectedCrop, setSelectedCrop] = useState('Rice (Paddy)');
  const [stages, setStages] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchPhenology();
  }, [selectedCrop]);

  const fetchPhenology = async () => {
    if (!selectedCrop) return;
    setLoading(true);

    const q = `
      query CropStages($name: String!) {
        cropDetails(name: $name) {
          name
          category
          stages {
            mainStage
            subStage
            startDay
            endDay
            optimalTempC
            relHumidityPct
            soilMoisturePct
            uvIndex
            irrigationMm
            susceptiblePests
            pestRiskFactors
            pestManagement
            susceptibleDiseases
            diseaseRiskFactors
            diseaseManagement
          }
        }
      }
    `;

    try {
      const res = await fetch('/graphql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, variables: { name: selectedCrop } })
      });
      const json = await res.json();
      setStages(json?.data?.cropDetails?.stages || []);
    } catch (err) {
      console.error('Failed to load phenology:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="filter-card">
        <div className="filter-grid" style={{ gridTemplateColumns: '280px auto 1fr' }}>
          <div className="form-group">
            <label className="form-label">Select Crop Species (89 Indexed):</label>
            <select 
              className="form-select"
              value={selectedCrop}
              onChange={e => setSelectedCrop(e.target.value)}
            >
              <option value="">-- Choose Crop --</option>
              {crops.map((c, i) => (
                <option key={i} value={c.name}>{c.name}</option>
              ))}
            </select>
          </div>

          <button 
            className="btn btn-primary"
            onClick={fetchPhenology}
            style={{ height: '38px', alignSelf: 'flex-end' }}
          >
            <Calendar style={{ width: 15, height: 15 }} />
            <span>Load Calendar</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted-fg)' }}>
          <div>Loading phenological calendar & environmental limits...</div>
        </div>
      ) : stages.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted-fg)', backgroundColor: 'var(--card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
          <Info style={{ width: 32, height: 32, margin: '0 auto 0.5rem auto' }} />
          <div style={{ fontWeight: 600 }}>Phenological calendar not indexed for {selectedCrop}.</div>
          <div style={{ fontSize: '0.8125rem' }}>Try selecting Rice, Cotton, Soybean, Wheat, Mustard, Sugarcane, or Tomato.</div>
        </div>
      ) : (
        <div className="phenology-timeline-wrapper">
          {stages.map((s, idx) => (
            <div key={idx} className="phenology-stage-card">
              <div className="phenology-stage-header">
                <div className="phenology-stage-title">
                  <span className="step-day-badge">Phase {idx + 1}</span>
                  <span>{s.mainStage}: {s.subStage}</span>
                </div>
                <span className="step-days-pill">
                  <Calendar style={{ width: 12, height: 12 }} />
                  <span>Day {s.startDay} – {s.endDay}</span>
                </span>
              </div>

              {/* Environmental Limits */}
              <div className="env-limits-grid">
                <div className="env-metric-item">
                  <span className="env-metric-label">Optimal Temp</span>
                  <span className="env-metric-value">{s.optimalTempC ? `${s.optimalTempC}°C` : '—'}</span>
                </div>
                <div className="env-metric-item">
                  <span className="env-metric-label">Rel. Humidity</span>
                  <span className="env-metric-value">{s.relHumidityPct ? `${s.relHumidityPct}%` : '—'}</span>
                </div>
                <div className="env-metric-item">
                  <span className="env-metric-label">Soil Moisture</span>
                  <span className="env-metric-value">{s.soilMoisturePct || '—'}</span>
                </div>
                <div className="env-metric-item">
                  <span className="env-metric-label">Irrigation</span>
                  <span className="env-metric-value">{s.irrigationMm ? `${s.irrigationMm} mm` : '—'}</span>
                </div>
              </div>

              {/* Pests & Diseases */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem', fontSize: '0.8125rem' }}>
                {s.susceptiblePests && (
                  <div style={{ backgroundColor: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: 'var(--radius-sm)', padding: '0.75rem' }}>
                    <div style={{ fontWeight: 700, color: 'var(--warning)', marginBottom: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Bug style={{ width: 14, height: 14 }} />
                      <span>Susceptible Pests</span>
                    </div>
                    <div>{s.susceptiblePests}</div>
                    {s.pestManagement && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--muted-fg)', marginTop: '0.3rem' }}>
                        <em>IPM: {s.pestManagement.substring(0, 160)}...</em>
                      </div>
                    )}
                  </div>
                )}

                {s.susceptibleDiseases && (
                  <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: 'var(--radius-sm)', padding: '0.75rem' }}>
                    <div style={{ fontWeight: 700, color: 'var(--destructive)', marginBottom: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <ShieldAlert style={{ width: 14, height: 14 }} />
                      <span>Susceptible Pathogens</span>
                    </div>
                    <div>{s.susceptibleDiseases}</div>
                    {s.diseaseManagement && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--muted-fg)', marginTop: '0.3rem' }}>
                        <em>Treatment: {s.diseaseManagement.substring(0, 160)}...</em>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

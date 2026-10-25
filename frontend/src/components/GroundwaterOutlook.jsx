import React, { useState, useEffect } from 'react';
import { Droplet, Search, AlertTriangle, ShieldCheck, TrendingDown, Gauge, RefreshCw, MessageSquare } from 'lucide-react';

export default function GroundwaterOutlook({ onAskCopilotPrompt }) {
  const [pincode, setPincode] = useState('587111');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const samplePincodes = [
    { pin: '587111', district: 'Bagalkote (Karnataka)', tag: 'Deficit' },
    { pin: '141004', district: 'Ludhiana (Punjab)', tag: 'Overexploited' },
    { pin: '500001', district: 'Hyderabad (Telangana)', tag: 'Critical' },
    { pin: '411001', district: 'Pune (Maharashtra)', tag: 'Moderate' },
    { pin: '302001', district: 'Jaipur (Rajasthan)', tag: 'Arid' },
    { pin: '600001', district: 'Chennai (Tamil Nadu)', tag: 'Coastal' }
  ];

  useEffect(() => {
    fetchOutlook(pincode);
  }, []);

  const fetchOutlook = async (pin) => {
    const p = pin || pincode;
    if (!p) return;
    setLoading(true);
    setError(null);

    const q = `
      query PincodeWater($pin: String!) {
        pincodeOutlook(pincode: $pin) {
          pincode
          district
          waterOutlookTag
          reservoirLevelCurrent
          monsoonForecast
          waterRisk
          cropsToGrow
          cropsToAvoid
          whatThisMeans
          waterBudgetMm
          zoneId
        }
      }
    `;

    try {
      const res = await fetch('/graphql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, variables: { pin: p } })
      });
      const json = await res.json();
      if (json?.data?.pincodeOutlook) {
        setData(json.data.pincodeOutlook);
      } else {
        setError('No groundwater telemetry available for PIN code ' + p);
      }
    } catch (err) {
      setError(err.message || 'Failed to query groundwater database');
    } finally {
      setLoading(false);
    }
  };

  const getOutlookColor = (tag) => {
    const t = (tag || '').toLowerCase();
    if (t.includes('critical') || t.includes('deficit') || t.includes('severe') || t.includes('overexploit')) {
      return 'var(--destructive)';
    }
    if (t.includes('moderate') || t.includes('watch') || t.includes('alert')) {
      return 'var(--warning)';
    }
    return 'var(--primary)';
  };

  return (
    <div>
      {/* Search Header */}
      <div className="filter-card">
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ flex: '1 1 240px' }}>
            <label className="form-label">
              <Droplet style={{ width: 13, height: 13, color: 'var(--info)' }} />
              <span>Enter 6-Digit PIN Code:</span>
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="form-input"
                maxLength={6}
                value={pincode}
                onChange={e => setPincode(e.target.value)}
                placeholder="e.g. 587111"
                onKeyDown={e => { if (e.key === 'Enter') fetchOutlook(pincode); }}
              />
              <Search style={{ position: 'absolute', right: 12, top: 11, width: 16, height: 16, color: 'var(--muted-fg)' }} />
            </div>
          </div>

          <button
            className="btn btn-primary"
            onClick={() => fetchOutlook(pincode)}
            disabled={loading || !pincode}
          >
            {loading ? <RefreshCw className="spin" style={{ width: 14, height: 14 }} /> : <Search style={{ width: 14, height: 14 }} />}
            <span>Query Water Outlook</span>
          </button>
        </div>

        {/* Quick PIN Presets */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.875rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--muted-fg)', fontWeight: 600 }}>Quick Profiles:</span>
          {samplePincodes.map(item => (
            <button
              key={item.pin}
              type="button"
              className="preset-pill"
              onClick={() => {
                setPincode(item.pin);
                fetchOutlook(item.pin);
              }}
            >
              <strong>{item.pin}</strong> - {item.district}
            </button>
          ))}
        </div>
      </div>

      {/* Results Display */}
      {error && (
        <div className="alert-card alert-warning" style={{ margin: '1rem 0' }}>
          <AlertTriangle style={{ width: 18, height: 18, flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) minmax(340px, 1.3fr)', gap: '1.25rem', marginTop: '1.25rem' }}>
          
          {/* Hydro Status Card */}
          <div className="doctor-card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <span className="step-day-badge" style={{ backgroundColor: 'rgba(56, 189, 248, 0.15)', color: 'var(--info)', borderColor: 'var(--info)' }}>
                  Agro Zone {data.zoneId || 'Regional'}
                </span>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: '0.35rem', color: 'var(--fg)' }}>
                  District: {data.district}
                </h3>
                <div style={{ fontSize: '0.8125rem', color: 'var(--muted-fg)' }}>PIN Code: {data.pincode}</div>
              </div>
              <div 
                className="status-badge" 
                style={{ 
                  borderColor: getOutlookColor(data.waterOutlookTag), 
                  color: getOutlookColor(data.waterOutlookTag),
                  fontSize: '0.75rem',
                  padding: '0.35rem 0.65rem'
                }}
              >
                {data.waterOutlookTag || 'NORMAL'}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', margin: '1rem 0' }}>
              <div style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--input)', border: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.6875rem', color: 'var(--muted-fg)', textTransform: 'uppercase' }}>Reservoir Storage</div>
                <div style={{ fontSize: '1.125rem', fontWeight: 800, color: 'var(--fg)', marginTop: '0.2rem' }}>
                  {data.reservoirLevelCurrent || 'Normal'}
                </div>
              </div>
              <div style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--input)', border: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.6875rem', color: 'var(--muted-fg)', textTransform: 'uppercase' }}>Monsoon Forecast</div>
                <div style={{ fontSize: '1.125rem', fontWeight: 800, color: 'var(--fg)', marginTop: '0.2rem' }}>
                  {data.monsoonForecast || 'Expected'}
                </div>
              </div>
            </div>

            {data.waterBudgetMm && (
              <div style={{ padding: '0.75rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--muted)', fontSize: '0.8125rem', marginBottom: '1rem' }}>
                <span style={{ color: 'var(--muted-fg)' }}>Estimated Irrigation Budget: </span>
                <strong style={{ color: 'var(--primary)' }}>{data.waterBudgetMm} mm / season</strong>
              </div>
            )}

            <div style={{ fontSize: '0.8125rem', lineHeight: 1.6, color: 'var(--fg)', backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '0.875rem' }}>
              <div style={{ fontWeight: 600, color: 'var(--warning)', display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.35rem' }}>
                <AlertTriangle style={{ width: 14, height: 14 }} />
                <span>Agronomic Advisory:</span>
              </div>
              {data.whatThisMeans || data.waterRisk || 'Manage surface runoff and schedule drip irrigation cycles.'}
            </div>

            <button
              className="btn btn-outline btn-sm"
              style={{ width: '100%', marginTop: '1rem' }}
              onClick={() => onAskCopilotPrompt && onAskCopilotPrompt(`Show groundwater status, reservoir levels, and crops to avoid for pincode ${data.pincode}`)}
            >
              <MessageSquare style={{ width: 14, height: 14 }} />
              <span>Ask Copilot for {data.district} Water Strategy</span>
            </button>
          </div>

          {/* Recommended vs Discouraged Crops */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            
            {/* Crops to Grow */}
            <div className="doctor-card" style={{ padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', color: 'var(--primary)' }}>
                <ShieldCheck style={{ width: 18, height: 18 }} />
                <h4 style={{ fontSize: '0.9375rem', fontWeight: 700 }}>Recommended Water-Efficient Crops</h4>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--muted-fg)', marginBottom: '0.75rem' }}>
                Selected for low water footprint and drought resilience under current aquifer levels:
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {(data.cropsToGrow || ['Pearl Millet', 'Sorghum', 'Chickpea', 'Mustard', 'Pigeon Pea']).map((c, i) => (
                  <span
                    key={i}
                    style={{
                      padding: '0.35rem 0.75rem',
                      borderRadius: 16,
                      backgroundColor: 'rgba(16, 185, 129, 0.12)',
                      border: '1px solid rgba(16, 185, 129, 0.35)',
                      color: 'var(--primary)',
                      fontSize: '0.8125rem',
                      fontWeight: 600
                    }}
                  >
                    ✓ {c}
                  </span>
                ))}
              </div>
            </div>

            {/* Crops to Avoid */}
            <div className="doctor-card" style={{ padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', color: 'var(--destructive)' }}>
                <TrendingDown style={{ width: 18, height: 18 }} />
                <h4 style={{ fontSize: '0.9375rem', fontWeight: 700 }}>High-Water Crops to Avoid / Restrict</h4>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--muted-fg)', marginBottom: '0.75rem' }}>
                Water-intensive crops posing catastrophic yield collapse or aquifer depletion:
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {(data.cropsToAvoid || ['Sugarcane', 'Paddy Rice (Boro)', 'Banana', 'Watermelon']).map((c, i) => (
                  <span
                    key={i}
                    style={{
                      padding: '0.35rem 0.75rem',
                      borderRadius: 16,
                      backgroundColor: 'rgba(239, 68, 68, 0.12)',
                      border: '1px solid rgba(239, 68, 68, 0.35)',
                      color: 'var(--destructive)',
                      fontSize: '0.8125rem',
                      fontWeight: 600
                    }}
                  >
                    ✕ {c}
                  </span>
                ))}
              </div>
            </div>

          </div>

        </div>
      )}
    </div>
  );
}

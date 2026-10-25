import React, { useState, useEffect } from 'react';
import { Sliders, MapPin, BarChart3, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';

export default function SuitabilityWizard() {
  const [pin, setPin] = useState('141004');
  const [season, setSeason] = useState('KHARIF');
  const [soilClass, setSoilClass] = useState(2);
  const [waterMethod, setWaterMethod] = useState('SURFACE');
  const [budgetBucket, setBudgetBucket] = useState('B2');
  const [previousCrop, setPreviousCrop] = useState('Fallow');
  
  const [recs, setRecs] = useState([]);
  const [groundwater, setGroundwater] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    calculateSuitability();
  }, []);

  const calculateSuitability = async () => {
    setLoading(true);
    const q = `
      query RecWizard($pin: String!, $s: String, $soil: Int, $w: String, $b: String, $prev: String) {
        zoneRecommendations(
          pincode: $pin,
          season: $s,
          soilClass: $soil,
          waterMethod: $w,
          budgetBucket: $b,
          previousCrop: $prev,
          limit: 12
        ) {
          crop
          category
          family
          zoneId
          zoneScore
          seasonScore
          waterScore
          soilScore
          budgetScore
          rotationScore
          totalScore
          matchPercentage
          waterOutlookWarning
        }
        pincodeOutlook(pincode: $pin) {
          district
          waterOutlookTag
          waterRisk
          reservoirLevelCurrent
          cropsToGrow
          cropsToAvoid
          whatThisMeans
        }
      }
    `;

    try {
      const res = await fetch('/graphql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          variables: {
            pin,
            s: season,
            soil: parseInt(soilClass, 10),
            w: waterMethod,
            b: budgetBucket,
            prev: previousCrop
          }
        })
      });
      const json = await res.json();
      setRecs(json?.data?.zoneRecommendations || []);
      setGroundwater(json?.data?.pincodeOutlook || null);
    } catch (err) {
      console.error('Failed to calculate suitability:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderMiniBar = (score, max = 2) => {
    const pct = Math.min(100, Math.max(0, (score / max) * 100));
    return (
      <div className="factor-mini-bar">
        <div className="factor-bar-bg">
          <div className="factor-bar-fill" style={{ width: `${pct}%` }} />
        </div>
        <span>{score.toFixed(1)}</span>
      </div>
    );
  };

  return (
    <div>
      {/* Configuration Header Card */}
      <div className="filter-card">
        <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--fg)' }}>
          <Sliders style={{ width: 18, height: 18, color: 'var(--primary)' }} />
          <span>6-Factor Regional Suitability Matrix (Zone 2.0, Season 2.0, Water 2.0, Soil 1.5, Budget 1.5, Rotation 1.0)</span>
        </div>

        <div className="filter-grid" style={{ gridTemplateColumns: '130px 150px 170px 160px 150px 150px auto' }}>
          <div className="form-group">
            <label className="form-label">PIN Code:</label>
            <input 
              type="text" 
              className="form-input" 
              value={pin}
              maxLength={6}
              onChange={e => setPin(e.target.value)}
              style={{ height: '38px' }}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Crop Season:</label>
            <select className="form-select" value={season} onChange={e => setSeason(e.target.value)}>
              <option value="KHARIF">Kharif (Monsoon)</option>
              <option value="RABI">Rabi (Winter)</option>
              <option value="ZAID">Zaid (Summer)</option>
              <option value="LONGTERM">Annual / Longterm</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Soil Classification:</label>
            <select className="form-select" value={soilClass} onChange={e => setSoilClass(e.target.value)}>
              <option value="1">Class 1: Clayey Soil</option>
              <option value="2">Class 2: Black Soil</option>
              <option value="3">Class 3: Loamy Soil</option>
              <option value="4">Class 4: Sandy Loam</option>
              <option value="5">Class 5: Sandy Soil</option>
              <option value="6">Class 6: Red Soil</option>
              <option value="7">Class 7: Alluvial Soil</option>
              <option value="8">Class 8: Laterite Soil</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Irrigation Method:</label>
            <select className="form-select" value={waterMethod} onChange={e => setWaterMethod(e.target.value)}>
              <option value="RAINFED">Rainfed (Dryland)</option>
              <option value="SURFACE">Surface / Canal</option>
              <option value="DRIP">Drip Irrigation</option>
              <option value="SPRINKLER">Sprinkler</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Budget Capacity:</label>
            <select className="form-select" value={budgetBucket} onChange={e => setBudgetBucket(e.target.value)}>
              <option value="B1">B1: Subsistence / Low</option>
              <option value="B2">B2: Moderate Budget</option>
              <option value="B3">B3: High Commercial</option>
              <option value="B4">B4: Enterprise Scale</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Previous Crop:</label>
            <input 
              type="text" 
              className="form-input" 
              value={previousCrop}
              onChange={e => setPreviousCrop(e.target.value)}
              placeholder="e.g. Fallow, Wheat"
              style={{ height: '38px' }}
            />
          </div>

          <button 
            className="btn btn-primary"
            onClick={calculateSuitability}
            style={{ height: '38px' }}
            disabled={loading}
          >
            <BarChart3 style={{ width: 15, height: 15 }} />
            <span>Calculate</span>
          </button>
        </div>

        {/* Quick PINs */}
        <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--muted-fg)' }}>Quick Test PINs:</span>
          {[
            { pin: '141004', label: '141004 (Punjab - Trans-Gangetic)' },
            { pin: '587111', label: '587111 (Bagalkote - Low Water)' },
            { pin: '522001', label: '522001 (Guntur - Coastal Andhra)' },
            { pin: '440001', label: '440001 (Nagpur - Black Soil)' }
          ].map(qp => (
            <button
              key={qp.pin}
              className="btn btn-ghost btn-sm"
              onClick={() => { setPin(qp.pin); }}
              style={{ fontSize: '0.75rem', padding: '0.15rem 0.5rem', height: '24px' }}
            >
              {qp.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results Container */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted-fg)' }}>
          <RefreshCw className="spin" style={{ width: 28, height: 28, margin: '0 auto 0.5rem auto', color: 'var(--primary)' }} />
          <div>Evaluating 6-factor matrix over 104 crop species...</div>
        </div>
      ) : (
        <div>
          {/* Groundwater Header Banner */}
          {groundwater && (
            <div className="suitability-header-card">
              <div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--fg)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <MapPin style={{ width: 16, height: 16, color: 'var(--blue)' }} />
                  <span>District: {groundwater.district} ({pin}) — Agro-Zone {recs[0]?.zoneId || '3'}</span>
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--muted-fg)', marginTop: '0.2rem' }}>
                  Reservoir: <strong>{groundwater.reservoirLevelCurrent || 'Normal'}</strong> | Water Risk: <strong>{groundwater.waterRisk || 'Low'}</strong>
                </div>
              </div>

              <span 
                className="status-badge"
                style={{ 
                  color: groundwater.waterOutlookTag.toLowerCase().includes('low') ? '#ef4444' : '#10b981',
                  borderColor: groundwater.waterOutlookTag.toLowerCase().includes('low') ? 'rgba(239, 68, 68, 0.4)' : 'rgba(16, 185, 129, 0.4)'
                }}
              >
                {groundwater.waterOutlookTag}
              </span>
            </div>
          )}

          {/* Suitability Table */}
          <div className="suitability-table-wrapper">
            <table className="suitability-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Crop Species</th>
                  <th>Category / Family</th>
                  <th>Overall Match %</th>
                  <th>Zone Fit (2.0)</th>
                  <th>Season (2.0)</th>
                  <th>Water (2.0)</th>
                  <th>Soil (1.5)</th>
                  <th>Budget (1.5)</th>
                  <th>Rotation (1.0)</th>
                  <th>District Directive</th>
                </tr>
              </thead>
              <tbody>
                {recs.map((r, idx) => {
                  const match = r.matchPercentage || 0;
                  const matchClass = match >= 80 ? 'high' : (match >= 65 ? 'medium' : 'low');
                  const warn = r.waterOutlookWarning || 'Approved';
                  const isWarn = warn.includes('Risk') || warn.includes('High');

                  return (
                    <tr key={idx}>
                      <td><strong>#{idx + 1}</strong></td>
                      <td><strong style={{ color: 'var(--fg)' }}>{r.crop}</strong></td>
                      <td>{r.category || 'Crop'} <span style={{ fontSize: '0.7rem', color: 'var(--muted-fg)' }}>({r.family || ''})</span></td>
                      <td>
                        <span className={`match-badge ${matchClass}`}>
                          {match.toFixed(1)}%
                        </span>
                      </td>
                      <td>{renderMiniBar(r.zoneScore, 2)}</td>
                      <td>{renderMiniBar(r.seasonScore, 2)}</td>
                      <td>{renderMiniBar(r.waterScore, 2)}</td>
                      <td>{renderMiniBar(r.soilScore, 2)}</td>
                      <td>{renderMiniBar(r.budgetScore, 2)}</td>
                      <td>{renderMiniBar(r.rotationScore, 2)}</td>
                      <td>
                        {isWarn ? (
                          <span className="gw-pill" style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', fontWeight: 600 }}>
                            ⚠️ Restricted
                          </span>
                        ) : (
                          <span className="gw-pill" style={{ backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#10b981', fontWeight: 600 }}>
                            ✅ Approved
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

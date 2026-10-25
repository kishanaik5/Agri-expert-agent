import React, { useState, useEffect } from 'react';
import { Search, Stethoscope, MessageSquare, ShieldCheck, Bug, AlertCircle } from 'lucide-react';

export default function CropDoctor({ crops, onAskCopilotPrompt }) {
  const [selectedCrop, setSelectedCrop] = useState('Cotton');
  const [category, setCategory] = useState('');
  const [symptom, setSymptom] = useState('');
  const [diseases, setDiseases] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchDiseases();
  }, [selectedCrop, category]);

  const fetchDiseases = async () => {
    setLoading(true);
    const q = `
      query DoctorQuery($crop: String, $sym: String) {
        diseases(cropName: $crop, symptom: $sym) {
          crop
          disease
          pathogen
          treatments
          stages {
            stageNumber
            stageName
            spreadPercentage
            revenueLossRangeDisplay
            maxRevenueLossMaxPerAcre
            treatmentSteps {
              day
              title
              desc
            }
          }
        }
      }
    `;

    try {
      const res = await fetch('/graphql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, variables: { crop: selectedCrop || null, sym: symptom || null } })
      });
      const json = await res.json();
      setDiseases(json?.data?.diseases || []);
    } catch (err) {
      console.error('Failed to load diseases:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Filter Card */}
      <div className="filter-card">
        <div className="filter-grid" style={{ gridTemplateColumns: '260px 180px 1fr auto' }}>
          <div className="form-group">
            <label className="form-label">Target Crop Species (164 Mapped):</label>
            <select 
              className="form-select"
              value={selectedCrop}
              onChange={e => setSelectedCrop(e.target.value)}
            >
              <option value="">-- All Master Crops --</option>
              {crops.map((c, i) => (
                <option key={i} value={c.name}>
                  {c.name} {c.nameHin ? `(${c.nameHin})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Category Filter:</label>
            <select 
              className="form-select"
              value={category}
              onChange={e => setCategory(e.target.value)}
            >
              <option value="">All Categories</option>
              <option value="Field Crop">Field Crops</option>
              <option value="Vegetable">Vegetables</option>
              <option value="Fruit">Fruits</option>
              <option value="Spices">Spices & Condiments</option>
              <option value="Pulses">Pulses & Legumes</option>
              <option value="Oilseeds">Oilseeds</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Filter Symptom, Pathogen, or Keyword:</label>
            <input 
              type="text"
              className="form-input"
              style={{ height: '38px' }}
              placeholder="e.g. blight, rust, rot, mildew, wilt, alternaria..."
              value={symptom}
              onChange={e => setSymptom(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') fetchDiseases(); }}
            />
          </div>

          <button 
            className="btn btn-primary"
            onClick={fetchDiseases}
            style={{ height: '38px' }}
          >
            <Search style={{ width: 15, height: 15 }} />
            <span>Search Graph</span>
          </button>
        </div>
      </div>

      {/* Disease Cards Grid */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted-fg)' }}>
          <div>Querying multi-stage disease ontology...</div>
        </div>
      ) : diseases.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--muted-fg)', backgroundColor: 'var(--card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
          <ShieldCheck style={{ width: 36, height: 36, color: 'var(--primary)', marginBottom: '0.75rem' }} />
          <div style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--fg)' }}>No Disease Records Found</div>
          <div style={{ fontSize: '0.8125rem', marginTop: '0.25rem' }}>Try searching another keyword or selecting a different crop.</div>
        </div>
      ) : (
        <div className="disease-grid">
          {diseases.map((d, idx) => {
            const stages = d.stages || [];
            return (
              <div key={idx} className="inspector-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
                    <span className="step-days-pill">{d.crop}</span>
                    <span className="status-badge" style={{ fontSize: '0.65rem' }}>Verified</span>
                  </div>

                  <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--fg)' }}>{d.disease}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--muted-fg)', fontStyle: 'italic', marginTop: '0.15rem' }}>
                    Causal: {d.pathogen || 'Biotic / Fungal Stress'}
                  </div>

                  {/* Stages List */}
                  {stages.length > 0 && (
                    <div style={{ marginTop: '0.75rem', paddingTop: '0.6rem', borderTop: '1px solid var(--border)' }}>
                      <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: 'var(--muted-fg)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                        Progression Stages ({stages.length} Recorded):
                      </div>
                      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                        {stages.map((s, si) => (
                          <span key={si} className="gw-pill" style={{ fontSize: '0.6875rem' }}>
                            <strong>S{s.stageNumber}:</strong> {s.stageName} {s.revenueLossRangeDisplay ? `• ${s.revenueLossRangeDisplay}` : ''}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Treatments */}
                  {d.treatments && d.treatments.length > 0 && (
                    <ul style={{ listStyle: 'disc', marginLeft: '1.25rem', fontSize: '0.75rem', color: 'var(--muted-fg)', lineHeight: 1.5, marginTop: '0.6rem' }}>
                      {d.treatments.slice(0, 2).map((t, ti) => (
                        <li key={ti}>{t}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end' }}>
                  <button 
                    className="btn btn-outline btn-sm"
                    onClick={() => onAskCopilotPrompt(`Give complete treatment plan and Day 1, 2, 5 checklist for ${d.crop} and ${d.disease}`)}
                    style={{ fontSize: '0.75rem', height: '28px' }}
                  >
                    <MessageSquare style={{ width: 12, height: 12 }} />
                    <span>Get Full Action Plan</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

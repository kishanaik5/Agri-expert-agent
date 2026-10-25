import React, { useState } from 'react';
import { X, ShieldCheck, Zap, Sliders, AlertCircle, RefreshCw } from 'lucide-react';

export default function RateLimitModal({ isOpen, onClose, rateLimitData, onTierChange, loading }) {
  if (!isOpen) return null;

  const [selectedTier, setSelectedTier] = useState(rateLimitData?.tier || 'standard');
  const [saving, setSaving] = useState(false);

  const tiers = [
    {
      id: 'standard',
      name: 'Standard Farmer Tier',
      limit: '10 queries / min',
      burst: '3 burst queries',
      desc: 'Ideal for single-user field inquiries, standard diagnosis, and resource protection.'
    },
    {
      id: 'agronomist',
      name: 'KVK Field Agronomist Tier',
      limit: '60 queries / min',
      burst: '10 burst queries',
      desc: 'Higher throughput for rapid multi-plot assessments, extension centers, and field trials.'
    },
    {
      id: 'enterprise',
      name: 'Enterprise Research Tier',
      limit: '300 queries / min',
      burst: '30 burst queries',
      desc: 'Unthrottled pipeline throughput for automated diagnostics, batch scans, and R&D pipelines.'
    }
  ];

  const handleApply = async () => {
    setSaving(true);
    await onTierChange(selectedTier);
    setSaving(false);
    onClose();
  };

  const remaining = rateLimitData?.remaining ?? 10;
  const limit = rateLimitData?.limit ?? 10;
  const pct = Math.min(100, Math.max(0, (remaining / limit) * 100));

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '1rem' }}>
            <Sliders style={{ width: 18, height: 18, color: 'var(--primary)' }} />
            <span>Rate Limiting & Throughput Settings</span>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>
            <X style={{ width: 16, height: 16 }} />
          </button>
        </div>

        <div className="modal-body">
          {/* Current Quota Gauge */}
          <div style={{ padding: '0.875rem 1rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--input)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem', fontSize: '0.8125rem' }}>
              <span style={{ color: 'var(--muted-fg)' }}>Current Token Quota:</span>
              <strong style={{ color: remaining <= 2 ? 'var(--destructive)' : 'var(--primary)' }}>
                {remaining} / {limit} requests remaining
              </strong>
            </div>
            <div style={{ width: '100%', height: 8, backgroundColor: 'var(--border)', borderRadius: 4, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${pct}%`,
                  height: '100%',
                  backgroundColor: remaining <= 2 ? 'var(--destructive)' : 'var(--primary)',
                  transition: 'width 0.3s ease'
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6875rem', color: 'var(--muted-fg)', marginTop: '0.35rem' }}>
              <span>Algorithm: Token Bucket</span>
              <span>Client IP: {rateLimitData?.client_id || '127.0.0.1'}</span>
            </div>
          </div>

          <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--fg)', marginTop: '0.25rem' }}>
            Select Active Rate Limit Policy:
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
            {tiers.map(t => {
              const isActive = selectedTier === t.id;
              return (
                <div
                  key={t.id}
                  className={`tier-option-card ${isActive ? 'active' : ''}`}
                  onClick={() => setSelectedTier(t.id)}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                      <strong style={{ fontSize: '0.875rem', color: 'var(--fg)' }}>{t.name}</strong>
                      <span className="step-day-badge" style={{ fontSize: '0.625rem' }}>{t.limit}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--muted-fg)' }}>{t.desc}</div>
                  </div>
                  {isActive && <ShieldCheck style={{ width: 18, height: 18, color: 'var(--primary)', flexShrink: 0 }} />}
                </div>
              );
            })}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--muted-fg)', backgroundColor: 'var(--muted)', padding: '0.6rem 0.8rem', borderRadius: 'var(--radius-sm)' }}>
            <AlertCircle style={{ width: 15, height: 15, color: 'var(--warning)', flexShrink: 0 }} />
            <span>Responses return <code>X-RateLimit-Remaining</code> and <code>Retry-After</code> headers.</span>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-outline btn-sm" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleApply} disabled={saving}>
            {saving ? <RefreshCw className="spin" style={{ width: 14, height: 14 }} /> : null}
            <span>Apply Rate Limit Policy</span>
          </button>
        </div>
      </div>
    </div>
  );
}

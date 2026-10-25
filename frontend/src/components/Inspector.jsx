import React from 'react';
import { Activity, AlertTriangle, Sliders, ShieldCheck, Clock, Gauge } from 'lucide-react';

export default function Inspector({ 
  telemetry, 
  activeCondition, 
  rateLimitStatus, 
  onOpenRateLimitModal 
}) {
  const remaining = rateLimitStatus?.remaining ?? 10;
  const limit = rateLimitStatus?.limit ?? 10;
  const tier = rateLimitStatus?.tier || 'standard';

  return (
    <aside className="inspector-panel">
      {/* 1. Query Telemetry Card */}
      <div className="inspector-card">
        <div className="inspector-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--primary)' }}>
            <Activity style={{ width: 14, height: 14 }} />
            <span>Query Telemetry</span>
          </div>
          <span className="status-badge" style={{ padding: '0.15rem 0.45rem', fontSize: '0.7rem' }}>
            {telemetry?.status || 'Idle'}
          </span>
        </div>

        <div className="inspector-row">
          <span className="inspector-label">Identified Crop:</span>
          <span className="inspector-value">{telemetry?.crop || '—'}</span>
        </div>

        <div className="inspector-row">
          <span className="inspector-label">Diagnostic Confidence:</span>
          <span className="inspector-value" style={{ color: 'var(--primary)', fontWeight: 700 }}>
            {telemetry?.confidence ? `${Math.round(telemetry.confidence * 100)}%` : '—'}
          </span>
        </div>

        <div className="inspector-row">
          <span className="inspector-label">Detected Intent:</span>
          <span className="inspector-value">{telemetry?.intent ? telemetry.intent.replace('_', ' ').toUpperCase() : '—'}</span>
        </div>

        <div className="inspector-row">
          <span className="inspector-label">Reasoning Engine:</span>
          <span className="inspector-value" style={{ fontSize: '0.75rem' }}>LangGraph + Gemini</span>
        </div>

        <div className="inspector-row">
          <span className="inspector-label">API Latency:</span>
          <span className="inspector-value">{telemetry?.latency ? `${telemetry.latency}ms` : '—'}</span>
        </div>
      </div>

      {/* 2. Rate Limiting Live Quota Card */}
      <div className="inspector-card" style={{ borderColor: 'rgba(16, 185, 129, 0.3)' }}>
        <div className="inspector-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--primary)' }}>
            <Gauge style={{ width: 14, height: 14 }} />
            <span>Rate Limiting Quota</span>
          </div>
          <button 
            className="btn btn-ghost btn-sm" 
            onClick={onOpenRateLimitModal}
            style={{ height: '20px', padding: '0 0.35rem', fontSize: '0.65rem' }}
          >
            Options
          </button>
        </div>

        <div className="inspector-row">
          <span className="inspector-label">Active Policy:</span>
          <span className="inspector-value" style={{ textTransform: 'capitalize' }}>{tier}</span>
        </div>

        <div className="inspector-row">
          <span className="inspector-label">Remaining Tokens:</span>
          <span className="inspector-value" style={{ color: remaining <= 2 ? 'var(--destructive)' : 'var(--primary)' }}>
            {remaining} / {limit} requests
          </span>
        </div>

        <div className="inspector-row">
          <span className="inspector-label">Window Reset:</span>
          <span className="inspector-value">Rolling 60s</span>
        </div>
      </div>

      {/* 3. Matched Condition Card */}
      {activeCondition && (
        <div className="inspector-card">
          <div className="inspector-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--warning)' }}>
              <AlertTriangle style={{ width: 14, height: 14 }} />
              <span>Matched Condition</span>
            </div>
          </div>

          <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--fg)' }}>
            {activeCondition.disease || 'Condition'}
          </div>
          {activeCondition.pathogen && (
            <div style={{ fontSize: '0.75rem', color: 'var(--muted-fg)', fontStyle: 'italic', marginBottom: '0.35rem' }}>
              {activeCondition.pathogen}
            </div>
          )}

          {activeCondition.stage && (
            <div className="inspector-row">
              <span className="inspector-label">Stage Phase:</span>
              <span className="inspector-value">{activeCondition.stage}</span>
            </div>
          )}

          {activeCondition.revenueLoss && (
            <div className="inspector-row">
              <span className="inspector-label">Revenue Risk:</span>
              <span className="inspector-value" style={{ color: 'var(--destructive)' }}>
                {activeCondition.revenueLoss}
              </span>
            </div>
          )}
        </div>
      )}

      {/* 4. Tips */}
      <div className="inspector-card">
        <div className="inspector-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Sliders style={{ width: 14, height: 14 }} />
            <span>Agronomic Guidelines</span>
          </div>
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--muted-fg)', lineHeight: 1.5 }}>
          • <strong>Multi-criteria queries</strong>: Try mentioning symptoms, PIN codes, seasons, or soil types.
        </p>
        <p style={{ fontSize: '0.75rem', color: 'var(--muted-fg)', lineHeight: 1.5 }}>
          • <strong>Intervention Checklist</strong>: Click items in the action plan to track field application progress.
        </p>
      </div>
    </aside>
  );
}

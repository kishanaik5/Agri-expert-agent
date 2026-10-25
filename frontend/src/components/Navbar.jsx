import React from 'react';
import { Sprout, Sparkles, Database, Terminal, Sun, Moon, Gauge } from 'lucide-react';

export default function Navbar({ isLight, onToggleTheme, rateLimitData, onOpenRateLimitModal }) {
  const remaining = rateLimitData?.remaining ?? 10;
  const limit = rateLimitData?.limit ?? 10;
  const tier = rateLimitData?.tier || 'standard';

  const quotaColor = remaining <= 2 ? '#ef4444' : (remaining <= 5 ? '#f59e0b' : '#10b981');

  return (
    <header className="header-navbar">
      <div className="header-container">
        
        {/* Brand */}
        <div className="brand-section">
          <div className="brand-icon-wrapper">
            <Sprout style={{ width: 22, height: 22 }} />
          </div>
          <div className="brand-titles">
            <div className="brand-name">
              AgriCopilot<span style={{ color: 'var(--primary)' }}>.ai</span>
              <span className="brand-tag">React JS Edition</span>
            </div>
            <span className="brand-subtitle">Multimodal Agricultural Decision Intelligence</span>
          </div>
        </div>

        {/* Live Infrastructure Status & Rate Limit Quota */}
        <div className="header-status-strip">
          <div className="status-badge live">
            <span className="status-dot pulse" />
            <span>FastAPI: Active</span>
          </div>

          <div className="status-badge live">
            <Sparkles style={{ width: 13, height: 13, color: 'var(--primary)' }} />
            <span>Gemini 2.5 Flash</span>
          </div>

          {/* Rate Limiting Option Badge */}
          <div 
            className="status-badge clickable" 
            onClick={onOpenRateLimitModal}
            title="Configure Rate Limiting & View Quota"
            style={{ borderColor: quotaColor, color: quotaColor }}
          >
            <Gauge style={{ width: 13, height: 13 }} />
            <span>Quota: {remaining}/{limit} ({tier})</span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="header-actions">
          <a href="/graphql" target="_blank" rel="noreferrer" className="btn btn-outline btn-sm">
            <Terminal style={{ width: 14, height: 14 }} />
            <span>GraphiQL</span>
          </a>
          <button 
            className="btn btn-ghost btn-sm" 
            onClick={onToggleTheme} 
            title="Toggle Light/Dark Theme"
          >
            {isLight ? <Moon style={{ width: 16, height: 16 }} /> : <Sun style={{ width: 16, height: 16 }} />}
          </button>
        </div>

      </div>
    </header>
  );
}

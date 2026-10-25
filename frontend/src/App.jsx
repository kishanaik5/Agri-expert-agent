import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  Stethoscope, 
  Sliders, 
  Calendar, 
  Droplet, 
  AlertTriangle, 
  Clock, 
  CheckCircle2, 
  X,
  Gauge
} from 'lucide-react';

import Navbar from './components/Navbar';
import KpiBar from './components/KpiBar';
import PresetBar from './components/PresetBar';
import CopilotChat from './components/CopilotChat';
import Inspector from './components/Inspector';
import CropDoctor from './components/CropDoctor';
import SuitabilityWizard from './components/SuitabilityWizard';
import PhenologyCalendar from './components/PhenologyCalendar';
import GroundwaterOutlook from './components/GroundwaterOutlook';
import RateLimitModal from './components/RateLimitModal';

import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [isLight, setIsLight] = useState(false);
  const [crops, setCrops] = useState([]);
  
  // Rate Limiting State
  const [rateLimitData, setRateLimitData] = useState({
    client_id: '127.0.0.1',
    tier: 'standard',
    limit: 10,
    remaining: 10,
    reset_seconds: 60
  });
  const [isRateLimitModalOpen, setIsRateLimitModalOpen] = useState(false);
  const [rateLimitAlert, setRateLimitAlert] = useState(null); // { retryAfter, tier }
  const [cooldownSeconds, setCooldownSeconds] = useState(0);

  // Inspector & Query Telemetry State
  const [telemetry, setTelemetry] = useState({
    status: 'Ready',
    crop: '—',
    confidence: null,
    intent: '—',
    latency: null
  });
  const [activeCondition, setActiveCondition] = useState(null);

  // Cross-component prompt trigger (e.g. clicking preset or doctor prompt)
  const [currentPrompt, setCurrentPrompt] = useState('');

  // Initial Data Load
  useEffect(() => {
    fetchInitialRateLimit();
    fetchAllCrops();
  }, []);

  // Theme effect
  useEffect(() => {
    if (isLight) {
      document.body.classList.add('light-theme');
    } else {
      document.body.classList.remove('light-theme');
    }
  }, [isLight]);

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const interval = setInterval(() => {
      setCooldownSeconds(prev => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldownSeconds]);

  // Rate limit 429 alert countdown
  useEffect(() => {
    if (!rateLimitAlert || rateLimitAlert.retryAfter <= 0) return;
    const interval = setInterval(() => {
      setRateLimitAlert(prev => {
        if (!prev || prev.retryAfter <= 1) {
          return null;
        }
        return { ...prev, retryAfter: prev.retryAfter - 1 };
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [rateLimitAlert]);

  const fetchInitialRateLimit = async () => {
    try {
      const res = await fetch('/api/ratelimit/status');
      if (res.ok) {
        const json = await res.json();
        setRateLimitData(json);
      }
    } catch (e) {
      console.warn('Rate limit endpoint not accessible:', e);
    }
  };

  const fetchAllCrops = async () => {
    try {
      const res = await fetch('/graphql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: `query GetAllCrops { crops { name category family } }`
        })
      });
      const json = await res.json();
      if (json?.data?.crops) {
        setCrops(json.data.crops);
      }
    } catch (e) {
      console.warn('Failed to fetch crops list:', e);
    }
  };

  const handleTierChange = async (newTier) => {
    try {
      const res = await fetch('/api/ratelimit/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tier: newTier })
      });
      if (res.ok) {
        const json = await res.json();
        setRateLimitData(json);
        setRateLimitAlert(null); // clear alert when tier changes
      }
    } catch (err) {
      console.error('Failed to update rate limit tier:', err);
    }
  };

  const handleQueryCompleted = (copilotData, latencyMs, updatedRateLimits) => {
    if (updatedRateLimits) {
      setRateLimitData(prev => ({
        ...prev,
        ...updatedRateLimits
      }));
    }

    if (copilotData) {
      setTelemetry({
        status: 'Success',
        crop: copilotData.crop || 'Cross-Crop Ontology',
        confidence: copilotData.confidenceScore || 0.95,
        intent: copilotData.intent || 'Advisory',
        latency: latencyMs
      });

      if (copilotData.stages && copilotData.stages.length > 0) {
        const stg = copilotData.stages[0];
        setActiveCondition({
          disease: copilotData.diagnosis || 'Pathogen Infestation',
          stage: stg.stageName,
          revenueLoss: stg.revenueLossRangeDisplay || '₹8,000 - ₹24,000 / acre'
        });
      } else if (copilotData.diagnosis) {
        setActiveCondition({
          disease: copilotData.diagnosis,
          stage: 'Active',
          revenueLoss: copilotData.financialImpact?.stageRevenueLossDisplay || 'High Risk'
        });
      }
    }
  };

  const handleRateLimitHit = (retryAfterSeconds, limit, remaining, tier) => {
    setRateLimitAlert({
      retryAfter: retryAfterSeconds,
      tier: tier || rateLimitData.tier
    });
    setRateLimitData(prev => ({
      ...prev,
      remaining: 0,
      limit: limit ? parseInt(limit, 10) : prev.limit,
      tier: tier || prev.tier
    }));
  };

  const handleStartCooldown = (cooldownMs = 1500) => {
    setCooldownSeconds(Math.ceil(cooldownMs / 1000));
  };

  const handleSelectPrompt = (promptText) => {
    setActiveTab('chat');
    setCurrentPrompt(promptText);
  };

  return (
    <div className="app-container">
      {/* 1. Header Navigation */}
      <Navbar
        isLight={isLight}
        onToggleTheme={() => setIsLight(prev => !prev)}
        rateLimitData={rateLimitData}
        onOpenRateLimitModal={() => setIsRateLimitModalOpen(true)}
      />

      {/* 2. Platform KPI Metrics Strip */}
      <KpiBar cropsCount={crops.length > 0 ? crops.length : 164} />

      {/* Rate Limit Active Throttle Warning Banner */}
      {rateLimitAlert && (
        <div className="rate-limit-banner">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <AlertTriangle style={{ width: 18, height: 18, color: 'var(--destructive)', flexShrink: 0 }} />
            <div>
              <strong>HTTP 429 Rate Limit Active:</strong> Request quota exhausted for tier{' '}
              <code>{rateLimitAlert.tier}</code>. Cool down active for{' '}
              <span className="cooldown-pill">
                <Clock style={{ width: 12, height: 12 }} />
                {rateLimitAlert.retryAfter}s
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => setIsRateLimitModalOpen(true)}
            >
              <Gauge style={{ width: 13, height: 13 }} />
              <span>Upgrade / Switch Tier</span>
            </button>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setRateLimitAlert(null)}
            >
              <X style={{ width: 15, height: 15 }} />
            </button>
          </div>
        </div>
      )}

      {/* Client Cooldown Banner */}
      {cooldownSeconds > 0 && !rateLimitAlert && (
        <div style={{
          maxWidth: 1440,
          margin: '0.4rem auto 0 auto',
          padding: '0.35rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.75rem',
          color: 'var(--muted-fg)'
        }}>
          <span className="status-dot pulse" style={{ backgroundColor: 'var(--warning)' }} />
          <span>Throttling client burst: Ready in {cooldownSeconds}s...</span>
        </div>
      )}

      {/* 3. Scenario Prompts Strip */}
      <PresetBar onSelectPrompt={handleSelectPrompt} />

      {/* 4. Tab Navigation Strip */}
      <div className="tabs-navigation-wrapper">
        <div className="tabs-list">
          <button
            className={`tabs-trigger ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <Bot style={{ width: 16, height: 16 }} />
            <span>Decision Copilot</span>
          </button>

          <button
            className={`tabs-trigger ${activeTab === 'doctor' ? 'active' : ''}`}
            onClick={() => setActiveTab('doctor')}
          >
            <Stethoscope style={{ width: 16, height: 16 }} />
            <span>Crop Doctor (3,083 Diseases)</span>
          </button>

          <button
            className={`tabs-trigger ${activeTab === 'recommendation' ? 'active' : ''}`}
            onClick={() => setActiveTab('recommendation')}
          >
            <Sliders style={{ width: 16, height: 16 }} />
            <span>6-Factor Suitability Wizard</span>
          </button>

          <button
            className={`tabs-trigger ${activeTab === 'phenology' ? 'active' : ''}`}
            onClick={() => setActiveTab('phenology')}
          >
            <Calendar style={{ width: 16, height: 16 }} />
            <span>Phenology Milestones & IPM</span>
          </button>

          <button
            className={`tabs-trigger ${activeTab === 'groundwater' ? 'active' : ''}`}
            onClick={() => setActiveTab('groundwater')}
          >
            <Droplet style={{ width: 16, height: 16 }} />
            <span>District Groundwater Outlook</span>
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--muted-fg)' }}>
          <CheckCircle2 style={{ width: 14, height: 14, color: 'var(--primary)' }} />
          <span>Graph & NLP Synced</span>
        </div>
      </div>

      {/* 5. Main Content Area */}
      <main className="main-wrapper">
        {activeTab === 'chat' && (
          <div className="chat-layout-grid">
            <CopilotChat
              currentQueryPrompt={currentPrompt}
              onQueryCompleted={handleQueryCompleted}
              rateLimitStatus={rateLimitData}
              onRateLimitHit={handleRateLimitHit}
              cooldownActive={cooldownSeconds > 0}
              onStartCooldown={handleStartCooldown}
            />
            <Inspector
              telemetry={telemetry}
              activeCondition={activeCondition}
              rateLimitStatus={rateLimitData}
              onOpenRateLimitModal={() => setIsRateLimitModalOpen(true)}
            />
          </div>
        )}

        {activeTab === 'doctor' && (
          <CropDoctor
            crops={crops}
            onAskCopilotPrompt={handleSelectPrompt}
          />
        )}

        {activeTab === 'recommendation' && (
          <SuitabilityWizard />
        )}

        {activeTab === 'phenology' && (
          <PhenologyCalendar
            crops={crops}
          />
        )}

        {activeTab === 'groundwater' && (
          <GroundwaterOutlook
            onAskCopilotPrompt={handleSelectPrompt}
          />
        )}
      </main>

      {/* Rate Limiting Configuration Modal */}
      <RateLimitModal
        isOpen={isRateLimitModalOpen}
        onClose={() => setIsRateLimitModalOpen(false)}
        rateLimitData={rateLimitData}
        onTierChange={handleTierChange}
      />
    </div>
  );
}

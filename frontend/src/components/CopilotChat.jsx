import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Copy, Check, TrendingDown, Clock, Droplet, Activity, AlertTriangle, ShieldCheck } from 'lucide-react';
import { marked } from 'marked';

export default function CopilotChat({ 
  onQueryCompleted, 
  currentQueryPrompt, 
  rateLimitStatus, 
  onRateLimitHit,
  cooldownActive,
  onStartCooldown
}) {
  const [messages, setMessages] = useState([
    {
      id: 'init',
      sender: 'bot',
      text: `### 🌱 Welcome to AgriCopilot Decision Copilot (React Edition)

Connected to **164 master crop ontologies**, **3,083 multi-stage disease & pest protocols**, and **19,486 Indian regional agro-climatic zones**.

Select a scenario above or enter any agronomy question below for:
* **Multi-Stage Infection Progression & Canopy Spread**
* **Day-by-Day Field Intervention Checklists (Day 1 / 2 / 5)**
* **Financial Economic Loss Estimates per Acre**
* **6-Factor Suitability & District Groundwater Directives**`,
      time: 'Just now',
      copilotData: null
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [checkedSteps, setCheckedSteps] = useState({});

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    if (currentQueryPrompt) {
      setInput(currentQueryPrompt);
      sendMessage(currentQueryPrompt);
    }
  }, [currentQueryPrompt]);

  const toggleCheckStep = (stepKey) => {
    setCheckedSteps(prev => ({
      ...prev,
      [stepKey]: !prev[stepKey]
    }));
  };

  const copyText = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const sendMessage = async (textToSend) => {
    const q = textToSend || input.trim();
    if (!q || loading) return;

    // Check client-side cooldown
    if (cooldownActive) {
      return;
    }

    setInput('');
    const timeNow = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Append user message
    const userMsgId = 'user-' + Date.now();
    setMessages(prev => [...prev, {
      id: userMsgId,
      sender: 'user',
      text: q,
      time: timeNow
    }]);

    setLoading(true);
    const startTime = performance.now();

    const graphqlQuery = `
      query AskCopilot($q: String!) {
        askCopilot(query: $q) {
          intent
          crop
          symptoms
          diagnosis
          confidenceScore
          advisory
          stages {
            stageNumber
            stageName
            earlyInterventionMessage
            spreadPercentage
            etaForNextStageInDays
            revenueLossRangeDisplay
            maxRevenueLossMaxPerAcre
            minYieldLossPct
            maxYieldLossPct
            treatmentSteps {
              day
              step
              title
              desc
            }
          }
          treatmentPlan {
            day
            step
            title
            desc
          }
          financialImpact {
            stageRevenueLossDisplay
            maxRevenueLossMaxPerAcre
            minYieldLossPct
            maxYieldLossPct
          }
          spraySafety {
            status
            recommendedWindow
            windRisk
            fungalRisk
            advisoryMessage
          }
          groundwaterAlert {
            pincode
            district
            waterOutlookTag
            reservoirLevelCurrent
            monsoonForecast
            waterRisk
            cropsToGrow
            cropsToAvoid
          }
        }
      }
    `;

    try {
      const response = await fetch('/graphql', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Client-Tier': rateLimitStatus?.tier || 'standard'
        },
        body: JSON.stringify({ query: graphqlQuery, variables: { q } })
      });

      // Extract Rate-Limit Headers
      const limitH = response.headers.get('x-ratelimit-limit');
      const remH = response.headers.get('x-ratelimit-remaining');
      const resetH = response.headers.get('x-ratelimit-reset');
      const tierH = response.headers.get('x-ratelimit-tier');

      if (response.status === 429) {
        const errJson = await response.json();
        const retryAfter = errJson.retry_after_seconds || 60;
        if (onRateLimitHit) {
          onRateLimitHit(retryAfter, limitH, remH, tierH);
        }
        setMessages(prev => [...prev, {
          id: 'bot-' + Date.now(),
          sender: 'bot',
          text: `⚠️ **Rate Limit Exceeded (HTTP 429)**: You have exhausted requests for tier \`${tierH || 'standard'}\`. Please wait **${retryAfter}s** before dispatching further agronomic queries.`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          copilotData: null
        }]);
        setLoading(false);
        return;
      }

      const json = await response.json();
      const elapsedMs = Math.round(performance.now() - startTime);

      if (onStartCooldown) {
        onStartCooldown(1500); // 1.5s client-side cooldown
      }

      const copilotData = json?.data?.askCopilot;
      const botText = copilotData?.advisory || copilotData?.diagnosis || 'No response returned from reasoning graph.';

      setMessages(prev => [...prev, {
        id: 'bot-' + Date.now(),
        sender: 'bot',
        text: botText,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        copilotData: copilotData
      }]);

      if (onQueryCompleted) {
        onQueryCompleted(copilotData, elapsedMs, {
          limit: limitH ? parseInt(limitH, 10) : 10,
          remaining: remH ? parseInt(remH, 10) : 9,
          reset: resetH ? parseInt(resetH, 10) : 60,
          tier: tierH || 'standard'
        });
      }

    } catch (err) {
      setMessages(prev => [...prev, {
        id: 'bot-' + Date.now(),
        sender: 'bot',
        text: `⚠️ **Network / API Failure**: ${err.message}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        copilotData: null
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-panel">
      {/* Messages Stream */}
      <div className="chat-messages">
        {messages.map(m => {
          const isBot = m.sender === 'bot';
          const htmlContent = marked.parse(m.text || '');
          const data = m.copilotData;

          return (
            <div key={m.id} className={`message ${isBot ? 'bot-message' : 'user-message'}`}>
              <div className="message-avatar">
                {isBot ? <Bot style={{ width: 16, height: 16 }} /> : <User style={{ width: 16, height: 16 }} />}
              </div>

              <div className="message-content-wrapper">
                <div className="message-meta" style={{ justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                    <span style={{ fontWeight: 600, color: 'var(--fg)' }}>
                      {isBot ? 'AgriCopilot AI' : 'Field Agronomist'}
                    </span>
                    <span>{m.time}</span>
                  </div>

                  {isBot && (
                    <button 
                      className="btn btn-ghost btn-sm" 
                      onClick={() => copyText(m.id, m.text)}
                      title="Copy response markdown"
                      style={{ height: '22px', padding: '0 0.4rem', fontSize: '0.7rem' }}
                    >
                      {copiedId === m.id ? (
                        <>
                          <Check style={{ width: 12, height: 12, color: 'var(--primary)' }} />
                          <span style={{ color: 'var(--primary)' }}>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy style={{ width: 12, height: 12 }} />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  )}
                </div>

                <div className="message-bubble">
                  {/* Markdown rendered body */}
                  <div className="markdown-body" dangerouslySetInnerHTML={{ __html: htmlContent }} />

                  {/* Interactive Visual Cards (if rich data available) */}
                  {data && (
                    <div className="diag-widget-card">
                      <div className="diag-widget-header">
                        <div className="diag-widget-title">
                          <Activity style={{ width: 16, height: 16, color: 'var(--primary)' }} />
                          <span>Interactive Protocol Cards (Knowledge Graph Grounded)</span>
                        </div>
                        <span className="status-badge live" style={{ fontSize: '0.6875rem' }}>Verified</span>
                      </div>

                      <div className="diag-widget-body">
                        {/* 1. Stage Progression Tracker */}
                        {data.stages && data.stages.length > 0 && (
                          <div>
                            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--muted-fg)', textTransform: 'uppercase', marginBottom: '0.4rem', letterSpacing: '0.05em' }}>
                              Infection Phase Progression & Canopy Spread
                            </div>
                            <div className="progression-track">
                              {data.stages.map((stg, i) => {
                                const isCurrent = i === 1 || (data.stages.length === 1 && i === 0);
                                const isPassed = i < 1;
                                const nodeClass = isCurrent ? 'active' : (isPassed ? 'passed' : '');

                                return (
                                  <div key={stg.stageNumber} className={`stage-node ${nodeClass}`}>
                                    <div className="stage-circle">{stg.stageNumber}</div>
                                    <div className="stage-node-label">{stg.stageName}</div>
                                    <div style={{ fontSize: '0.625rem', color: 'var(--muted-fg)' }}>{stg.spreadPercentage}</div>
                                    {stg.revenueLossRangeDisplay && (
                                      <div style={{ fontSize: '0.625rem', color: 'var(--destructive)', fontWeight: 600 }}>
                                        {stg.revenueLossRangeDisplay}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {/* 2. Interactive Field Intervention Checklist */}
                        {data.treatmentPlan && data.treatmentPlan.length > 0 && (
                          <div>
                            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--muted-fg)', textTransform: 'uppercase', marginBottom: '0.4rem', letterSpacing: '0.05em' }}>
                              Field Action Checklist (Click to track progress)
                            </div>
                            <div className="intervention-timeline-list">
                              {data.treatmentPlan.map((step, idx) => {
                                const key = `${m.id}-step-${idx}`;
                                const isDone = !!checkedSteps[key];

                                return (
                                  <div 
                                    key={idx} 
                                    className="timeline-step-item"
                                    onClick={() => toggleCheckStep(key)}
                                    style={{ 
                                      cursor: 'pointer',
                                      opacity: isDone ? 0.65 : 1,
                                      borderColor: isDone ? 'var(--primary)' : 'var(--border)'
                                    }}
                                  >
                                    <span 
                                      className="step-day-badge" 
                                      style={{ backgroundColor: isDone ? 'var(--primary)' : 'var(--secondary)' }}
                                    >
                                      {step.day || `Step ${idx + 1}`}
                                    </span>
                                    <div className="step-content-box">
                                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                        <div className="step-content-title" style={{ textDecoration: isDone ? 'line-through' : 'none' }}>
                                          {step.title}
                                        </div>
                                        {isDone && <Check style={{ width: 14, height: 14, color: 'var(--primary)' }} />}
                                      </div>
                                      <div className="step-content-desc">{step.desc}</div>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {/* 3. Metric Badges (Revenue, Spray, Groundwater) */}
                        <div className="metric-strip-grid">
                          {data.financialImpact?.stageRevenueLossDisplay && (
                            <div className="metric-pill-card danger">
                              <TrendingDown style={{ width: 18, height: 18, color: '#ef4444' }} />
                              <div>
                                <div className="metric-pill-val" style={{ color: '#ef4444' }}>
                                  {data.financialImpact.stageRevenueLossDisplay}
                                </div>
                                <div className="metric-pill-sub">Current Stage Loss / Acre</div>
                              </div>
                            </div>
                          )}

                          {data.spraySafety && (
                            <div className="metric-pill-card success">
                              <Clock style={{ width: 18, height: 18, color: '#10b981' }} />
                              <div>
                                <div className="metric-pill-val" style={{ color: '#10b981' }}>
                                  {data.spraySafety.recommendedWindow || '6:00 – 9:00 AM'}
                                </div>
                                <div className="metric-pill-sub">Safe Spray Window</div>
                              </div>
                            </div>
                          )}

                          {data.groundwaterAlert && (
                            <div className="metric-pill-card info">
                              <Droplet style={{ width: 18, height: 18, color: '#06b6d4' }} />
                              <div>
                                <div className="metric-pill-val" style={{ color: '#06b6d4' }}>
                                  {data.groundwaterAlert.waterOutlookTag}
                                </div>
                                <div className="metric-pill-sub">{data.groundwaterAlert.district} ({data.groundwaterAlert.pincode})</div>
                              </div>
                            </div>
                          )}
                        </div>

                      </div>
                    </div>
                  )}

                </div>
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="message bot-message">
            <div className="message-avatar">
              <Bot style={{ width: 16, height: 16 }} />
            </div>
            <div className="message-content-wrapper">
              <div className="message-meta">
                <span style={{ fontWeight: 600, color: 'var(--fg)' }}>AgriCopilot AI</span>
                <span>Reasoning multi-hop graph...</span>
              </div>
              <div className="message-bubble" style={{ color: 'var(--muted-fg)', fontStyle: 'italic' }}>
                Executing entity parsing & knowledge graph traversal...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div className="chat-input-box">
        <form 
          className="chat-form" 
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
        >
          <input
            type="text"
            className="form-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask any crop, symptom, chemical dosage, 6-factor suitability, or PIN code water query..."
            disabled={loading || cooldownActive}
          />
          <button 
            type="submit" 
            className="btn btn-primary" 
            disabled={loading || !input.trim() || cooldownActive}
          >
            <Send style={{ width: 15, height: 15 }} />
            <span>{cooldownActive ? 'Cooldown...' : 'Ask Copilot'}</span>
          </button>
        </form>
      </div>
    </div>
  );
}

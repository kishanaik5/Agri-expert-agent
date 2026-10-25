// AgriCopilot Frontend Application Logic
// Connects to FastAPI Strawberry GraphQL backend at /graphql

document.addEventListener('DOMContentLoaded', () => {
  initIcons();
  initThemeToggle();
  initNavigation();
  loadCropSelectors();
  initChat();
  initDoctor();
  initRecommendationWizard();
  initPhenology();
  initGroundwater();
  checkBackendHealth();
});

function initIcons() {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

/* =========================================================================
   1. GRAPHQL CLIENT HELPER
   ========================================================================= */
async function fetchGraphQL(query, variables = {}) {
  try {
    const response = await fetch('/graphql', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ query, variables }),
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
    }

    const json = await response.json();
    if (json.errors && json.errors.length > 0) {
      console.warn('GraphQL returned errors:', json.errors);
    }
    return json.data;
  } catch (err) {
    console.error('GraphQL fetch failure:', err);
    throw err;
  }
}

/* =========================================================================
   2. THEME TOGGLE (Dark / Light)
   ========================================================================= */
function initThemeToggle() {
  const btnTheme = document.getElementById('btn-theme-toggle');
  const themeIcon = document.getElementById('theme-icon');
  
  const savedTheme = localStorage.getItem('agri_theme');
  if (savedTheme === 'light') {
    document.body.classList.add('light-theme');
    if (themeIcon) themeIcon.setAttribute('data-lucide', 'moon');
  }

  if (btnTheme) {
    btnTheme.addEventListener('click', () => {
      const isLight = document.body.classList.toggle('light-theme');
      localStorage.setItem('agri_theme', isLight ? 'light' : 'dark');
      if (themeIcon) {
        themeIcon.setAttribute('data-lucide', isLight ? 'moon' : 'sun');
      }
      initIcons();
    });
  }
}

/* =========================================================================
   3. NAVIGATION TABS
   ========================================================================= */
function initNavigation() {
  const tabTriggers = document.querySelectorAll('.tabs-trigger');
  const tabContents = document.querySelectorAll('.tab-content');

  tabTriggers.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');

      tabTriggers.forEach(t => t.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetSection = document.getElementById(targetId);
      if (targetSection) {
        targetSection.classList.add('active');
      }
      initIcons();
    });
  });

  // Clear Chat / New Session
  const btnClearChat = document.getElementById('btn-clear-chat');
  if (btnClearChat) {
    btnClearChat.addEventListener('click', () => {
      const tabBtnChat = document.getElementById('tab-btn-chat');
      if (tabBtnChat) tabBtnChat.click();

      const messagesContainer = document.getElementById('chat-messages');
      if (messagesContainer) {
        messagesContainer.innerHTML = `
          <div class="message bot-message">
            <div class="message-avatar">
              <i data-lucide="bot" style="width: 16px; height: 16px;"></i>
            </div>
            <div class="message-content-wrapper">
              <div class="message-meta">
                <span style="font-weight: 600; color: hsl(var(--foreground));">AgriCopilot AI</span>
                <span>Just now</span>
              </div>
              <div class="message-bubble">
                <p>New session initialized. Select a scenario above or enter your agronomic query to test knowledge graph inference.</p>
              </div>
            </div>
          </div>
        `;
        initIcons();
      }

      resetInspector();
      const userInput = document.getElementById('user-input');
      if (userInput) userInput.focus();
    });
  }
}

function resetInspector() {
  const cropEl = document.getElementById('inspector-crop');
  const confEl = document.getElementById('inspector-confidence');
  const intEl = document.getElementById('inspector-intent');
  const latEl = document.getElementById('inspector-latency');
  const badgeEl = document.getElementById('inspector-status-badge');
  const activeCard = document.getElementById('inspector-card-active');

  if (cropEl) cropEl.textContent = '—';
  if (confEl) confEl.textContent = '—';
  if (intEl) intEl.textContent = '—';
  if (latEl) latEl.textContent = '—';
  if (activeCard) activeCard.style.display = 'none';
  if (badgeEl) {
    badgeEl.textContent = 'Idle';
    badgeEl.style.color = 'hsl(var(--muted-foreground))';
  }
}

/* =========================================================================
   4. DYNAMIC CROP SELECTORS LOADER
   ========================================================================= */
let allMasterCrops = [];

async function loadCropSelectors() {
  const doctorSelect = document.getElementById('doctor-crop-select');
  const phenologySelect = document.getElementById('phenology-crop-select');

  try {
    const q = `
      query {
        crops(limit: 200) {
          name
          nameHin
          category
        }
      }
    `;
    const data = await fetchGraphQL(q);
    if (data && data.crops) {
      allMasterCrops = data.crops;
      
      const kpiCrops = document.getElementById('kpi-crops');
      if (kpiCrops) kpiCrops.textContent = `${allMasterCrops.length} Species`;

      let optionsHtml = '<option value="">-- Choose Crop Species --</option>';
      allMasterCrops.forEach(c => {
        const hinText = c.nameHin ? ` (${c.nameHin})` : '';
        optionsHtml += `<option value="${escapeHtml(c.name)}">${escapeHtml(c.name)}${hinText}</option>`;
      });

      if (doctorSelect) {
        doctorSelect.innerHTML = optionsHtml;
        doctorSelect.value = "Cotton";
      }
      if (phenologySelect) {
        phenologySelect.innerHTML = optionsHtml;
        phenologySelect.value = "Rice (Paddy)";
      }

      // Trigger initial loads
      triggerInitialDoctorQuery();
    }
  } catch (err) {
    console.error("Failed to load crop master list:", err);
  }
}

/* =========================================================================
   5. AI ADVISORY COPILOT (CHAT STREAM & VISUAL DIAGNOSTIC CARDS)
   ========================================================================= */
function initChat() {
  const chatForm = document.getElementById('chat-form');
  const userInput = document.getElementById('user-input');
  const messagesContainer = document.getElementById('chat-messages');
  const presetPills = document.querySelectorAll('.preset-pill');

  presetPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const prompt = pill.getAttribute('data-prompt');
      if (prompt) {
        const tabBtnChat = document.getElementById('tab-btn-chat');
        if (tabBtnChat) tabBtnChat.click();
        
        if (userInput) userInput.value = prompt;
        sendMessage(prompt);
      }
    });
  });

  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = userInput.value.trim();
      if (!text) return;
      sendMessage(text);
    });
  }

  async function sendMessage(question) {
    userInput.value = '';
    appendUserMessage(question);

    const startTime = performance.now();
    const badgeEl = document.getElementById('inspector-status-badge');
    if (badgeEl) {
      badgeEl.textContent = 'Processing...';
      badgeEl.style.color = 'hsl(var(--primary))';
    }

    const typingId = appendTypingIndicator();
    scrollToBottom();

    try {
      const query = `
        query AskAdvisory($q: String!) {
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

      const data = await fetchGraphQL(query, { q: question });
      const elapsedMs = Math.round(performance.now() - startTime);

      removeTypingIndicator(typingId);

      const copilotData = data && data.askCopilot ? data.askCopilot : null;
      const markdownText = copilotData && copilotData.advisory 
        ? copilotData.advisory 
        : (copilotData && copilotData.diagnosis ? `### Diagnosis\n${copilotData.diagnosis}` : "No specific protocol matched in the graph. Try refining the crop or symptom name.");

      // Update Inspector Panel
      updateInspector(copilotData, elapsedMs);

      // Render Bot Message with embedded interactive widgets
      appendBotMessage(markdownText, copilotData);
    } catch (err) {
      removeTypingIndicator(typingId);
      appendBotMessage(`⚠️ **Agent Error**: Unable to query LangGraph advisory engine. (${err.message})`, null);
      if (badgeEl) {
        badgeEl.textContent = 'Error';
        badgeEl.style.color = 'hsl(var(--destructive))';
      }
    }

    scrollToBottom();
    initIcons();
  }

  function appendUserMessage(text) {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user-message';
    msgDiv.innerHTML = `
      <div class="message-avatar">
        <i data-lucide="user" style="width: 16px; height: 16px;"></i>
      </div>
      <div class="message-content-wrapper">
        <div class="message-meta">
          <span style="font-weight: 600; color: hsl(var(--foreground));">Agronomist</span>
          <span>${timeStr}</span>
        </div>
        <div class="message-bubble">
          <p>${escapeHtml(text)}</p>
        </div>
      </div>
    `;
    messagesContainer.appendChild(msgDiv);
    initIcons();
  }

  function appendBotMessage(markdownText, copilotData) {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';

    let renderedHtml = markdownText;
    if (window.marked && typeof window.marked.parse === 'function') {
      renderedHtml = window.marked.parse(markdownText);
    } else {
      renderedHtml = `<p>${escapeHtml(markdownText)}</p>`;
    }

    // Build Interactive Visual Cards Widget
    let widgetsHtml = '';
    if (copilotData) {
      widgetsHtml = renderInteractiveWidgetsHtml(copilotData);
    }

    const messageId = 'bot-msg-' + Date.now();
    msgDiv.id = messageId;
    msgDiv.innerHTML = `
      <div class="message-avatar">
        <i data-lucide="bot" style="width: 16px; height: 16px;"></i>
      </div>
      <div class="message-content-wrapper" style="width: 100%;">
        <div class="message-meta" style="justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-weight: 600; color: hsl(var(--foreground));">AgriCopilot AI</span>
            <span>${timeStr}</span>
          </div>
          <button class="btn btn-ghost btn-sm btn-copy-msg" data-text="${escapeHtml(markdownText)}" style="height: 1.5rem; padding: 0 0.4rem; font-size: 0.7rem;" title="Copy advisory markdown">
            <i data-lucide="copy" style="width: 12px; height: 12px;"></i>
            <span>Copy</span>
          </button>
        </div>
        <div class="message-bubble">
          ${renderedHtml}
          ${widgetsHtml}
        </div>
      </div>
    `;
    messagesContainer.appendChild(msgDiv);

    // Setup Copy Handler
    const copyBtn = msgDiv.querySelector('.btn-copy-msg');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(markdownText).then(() => {
          copyBtn.innerHTML = '<i data-lucide="check" style="width: 12px; height: 12px; color: hsl(var(--primary));"></i> <span style="color: hsl(var(--primary));">Copied</span>';
          initIcons();
          setTimeout(() => {
            copyBtn.innerHTML = '<i data-lucide="copy" style="width: 12px; height: 12px;"></i> <span>Copy</span>';
            initIcons();
          }, 2000);
        });
      });
    }

    initIcons();
  }

  function appendTypingIndicator() {
    const id = 'typing-' + Date.now();
    const typingDiv = document.createElement('div');
    typingDiv.id = id;
    typingDiv.className = 'message bot-message';
    typingDiv.innerHTML = `
      <div class="message-avatar">
        <i data-lucide="bot" style="width: 16px; height: 16px;"></i>
      </div>
      <div class="message-content-wrapper">
        <div class="message-meta">
          <span style="font-weight: 600; color: hsl(var(--foreground));">AgriCopilot AI</span>
          <span>Traversing knowledge graph & reasoning...</span>
        </div>
        <div class="message-bubble">
          <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    `;
    messagesContainer.appendChild(typingDiv);
    initIcons();
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }
}

/* =========================================================================
   6. RENDER INTERACTIVE DIAGNOSTIC WIDGETS
   ========================================================================= */
function renderInteractiveWidgetsHtml(data) {
  const stages = data.stages || [];
  const treatmentPlan = data.treatmentPlan || [];
  const fi = data.financialImpact;
  const ss = data.spraySafety;
  const gw = data.groundwaterAlert;

  if (stages.length === 0 && treatmentPlan.length === 0 && !fi && !gw) {
    return '';
  }

  let html = `<div class="diag-widget-card">`;
  
  // Widget Header
  html += `
    <div class="diag-widget-header">
      <div class="diag-widget-title">
        <i data-lucide="activity" style="width: 16px; height: 16px; color: hsl(var(--primary));"></i>
        <span>Interactive Agronomic Protocol Cards</span>
      </div>
      <span class="status-badge live" style="font-size: 0.6875rem;">Connected KB</span>
    </div>
    <div class="diag-widget-body">
  `;

  // 1. Stage Progression Bar (if multi-stage disease)
  if (stages.length > 0) {
    html += `
      <div>
        <div style="font-size: 0.75rem; font-weight: 700; color: hsl(var(--muted-foreground)); text-transform: uppercase; margin-bottom: 0.5rem; letter-spacing: 0.05em;">
          Disease Stage Progression & Canopy Spread
        </div>
        <div class="progression-track">
    `;

    stages.forEach((stg, i) => {
      const isCurrent = i === 1 || (stages.length === 1 && i === 0);
      const isPassed = i < 1;
      const nodeClass = isCurrent ? 'active' : (isPassed ? 'passed' : '');
      const revText = stg.revenueLossRangeDisplay ? `<div style="font-size: 0.625rem; color: #ef4444; font-weight: 600;">${stg.revenueLossRangeDisplay}</div>` : '';
      
      html += `
        <div class="stage-node ${nodeClass}">
          <div class="stage-circle">${stg.stageNumber}</div>
          <div class="stage-node-label">${escapeHtml(stg.stageName)}</div>
          <div style="font-size: 0.625rem; color: hsl(var(--muted-foreground));">${stg.spreadPercentage || ''}</div>
          ${revText}
        </div>
      `;
    });

    html += `</div></div>`;
  }

  // 2. Day-by-Day Intervention Checklist
  if (treatmentPlan.length > 0) {
    html += `
      <div>
        <div style="font-size: 0.75rem; font-weight: 700; color: hsl(var(--muted-foreground)); text-transform: uppercase; margin-bottom: 0.5rem; letter-spacing: 0.05em;">
          Field Intervention Checklist (Day-wise Action Plan)
        </div>
        <div class="intervention-timeline-list">
    `;

    treatmentPlan.forEach((step, idx) => {
      html += `
        <div class="timeline-step-item">
          <span class="step-day-badge">${escapeHtml(step.day || 'Day ' + (idx + 1))}</span>
          <div class="step-content-box">
            <div class="step-content-title">${escapeHtml(step.title)}</div>
            <div class="step-content-desc">${escapeHtml(step.desc)}</div>
          </div>
        </div>
      `;
    });

    html += `</div></div>`;
  }

  // 3. Metric Badges Strip (Revenue Loss, Safe Spray, Groundwater)
  html += `<div class="metric-strip-grid">`;

  if (fi && (fi.stageRevenueLossDisplay || fi.maxRevenueLossMaxPerAcre)) {
    const disp = fi.stageRevenueLossDisplay || `Up to ₹${fi.maxRevenueLossMaxPerAcre?.toLocaleString('en-IN')}`;
    html += `
      <div class="metric-pill-card danger">
        <i data-lucide="trending-down" style="width: 18px; height: 18px; color: #ef4444;"></i>
        <div>
          <div class="metric-pill-val" style="color: #ef4444;">${escapeHtml(disp)}</div>
          <div class="metric-pill-sub">Economic Loss / Acre</div>
        </div>
      </div>
    `;
  }

  if (ss) {
    html += `
      <div class="metric-pill-card success">
        <i data-lucide="clock" style="width: 18px; height: 18px; color: #10b981;"></i>
        <div>
          <div class="metric-pill-val" style="color: #10b981;">${escapeHtml(ss.recommendedWindow || '6:00 - 9:00 AM')}</div>
          <div class="metric-pill-sub">Safe Spraying Window</div>
        </div>
      </div>
    `;
  }

  if (gw) {
    html += `
      <div class="metric-pill-card info">
        <i data-lucide="droplet" style="width: 18px; height: 18px; color: #06b6d4;"></i>
        <div>
          <div class="metric-pill-val" style="color: #06b6d4;">${escapeHtml(gw.waterOutlookTag)}</div>
          <div class="metric-pill-sub">${escapeHtml(gw.district)} (${escapeHtml(gw.pincode)})</div>
        </div>
      </div>
    `;
  }

  html += `</div>`; // end metric-strip-grid
  html += `</div></div>`; // end diag-widget-body & diag-widget-card

  return html;
}

function updateInspector(copilotData, elapsedMs) {
  const cropEl = document.getElementById('inspector-crop');
  const confEl = document.getElementById('inspector-confidence');
  const intEl = document.getElementById('inspector-intent');
  const latEl = document.getElementById('inspector-latency');
  const badgeEl = document.getElementById('inspector-status-badge');
  const activeCard = document.getElementById('inspector-card-active');

  if (cropEl) cropEl.textContent = copilotData?.crop || 'Auto-Detected';
  if (confEl) {
    const score = copilotData?.confidenceScore ?? 0.92;
    confEl.textContent = `${Math.round(score * 100)}%`;
  }
  if (intEl) {
    intEl.textContent = (copilotData?.intent || 'treatment_plan').replace('_', ' ').toUpperCase();
  }
  if (latEl) latEl.textContent = `${elapsedMs}ms`;
  if (badgeEl) {
    badgeEl.textContent = 'Active';
    badgeEl.style.color = 'hsl(var(--primary))';
  }

  // Active condition card
  if (activeCard && copilotData?.stages && copilotData.stages.length > 0) {
    activeCard.style.display = 'block';
    const stg = copilotData.stages[0];
    const dNameEl = document.getElementById('inspector-disease-name');
    const sNameEl = document.getElementById('inspector-stage-name');
    const rLossEl = document.getElementById('inspector-rev-loss');

    if (dNameEl) dNameEl.textContent = copilotData.diagnosis.split('**')[1] || 'Identified Condition';
    if (sNameEl) sNameEl.textContent = `Stage ${stg.stageNumber}: ${stg.stageName}`;
    if (rLossEl) rLossEl.textContent = stg.revenueLossRangeDisplay || '₹558 - ₹1,116';
  }
}

/* =========================================================================
   7. TAB 2: CROP DOCTOR CATALOG
   ========================================================================= */
function initDoctor() {
  const cropSelect = document.getElementById('doctor-crop-select');
  const catSelect = document.getElementById('doctor-category-filter');
  const symptomInput = document.getElementById('doctor-symptom-input');
  const btnSearch = document.getElementById('btn-search-doctor');
  const resultsContainer = document.getElementById('doctor-results');

  if (btnSearch) {
    btnSearch.addEventListener('click', doDoctorQuery);
  }
  if (cropSelect) {
    cropSelect.addEventListener('change', doDoctorQuery);
  }
  if (symptomInput) {
    symptomInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') doDoctorQuery();
    });
  }

  async function doDoctorQuery() {
    const crop = cropSelect ? cropSelect.value : '';
    const symptom = symptomInput ? symptomInput.value.trim() : '';

    if (!resultsContainer) return;
    resultsContainer.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: hsl(var(--muted-foreground));">
        <i data-lucide="loader-2" class="spin" style="width: 24px; height: 24px; margin-bottom: 0.5rem;"></i>
        <div>Querying multi-stage disease ontology...</div>
      </div>
    `;
    initIcons();

    try {
      const q = `
        query SearchDoctor($crop: String, $sym: String) {
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
              earlyInterventionMessage
              treatmentSteps {
                day
                title
                desc
              }
            }
          }
        }
      `;

      const data = await fetchGraphQL(q, { crop: crop || null, sym: symptom || null });
      const diseases = data?.diseases || [];

      if (diseases.length === 0) {
        resultsContainer.innerHTML = `
          <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: hsl(var(--muted-foreground)); background-color: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius);">
            <i data-lucide="shield-check" style="width: 36px; height: 36px; color: hsl(var(--primary)); margin-bottom: 0.75rem;"></i>
            <div style="font-weight: 600; font-size: 1rem; color: hsl(var(--foreground));">No Diseases Found</div>
            <div style="font-size: 0.8125rem; margin-top: 0.25rem;">No disease records match '${escapeHtml(symptom || crop)}' in the knowledge graph.</div>
          </div>
        `;
        initIcons();
        return;
      }

      let html = '';
      diseases.forEach(d => {
        const sci = d.pathogen ? `<em>${escapeHtml(d.pathogen)}</em>` : 'Biotic Stress';
        const stages = d.stages || [];

        // Build stages HTML
        let stagesHtml = '';
        if (stages.length > 0) {
          stagesHtml = `
            <div style="margin-top: 0.75rem; border-top: 1px solid hsl(var(--border)); padding-top: 0.75rem;">
              <div style="font-size: 0.6875rem; font-weight: 700; color: hsl(var(--muted-foreground)); text-transform: uppercase; margin-bottom: 0.4rem;">
                Progression Stages (${stages.length} Phases Recorded):
              </div>
              <div style="display: flex; gap: 0.35rem; flex-wrap: wrap;">
          `;
          stages.forEach(s => {
            const revBadge = s.revenueLossRangeDisplay ? ` • ${s.revenueLossRangeDisplay}` : '';
            stagesHtml += `
              <span class="gw-pill" style="font-size: 0.6875rem;">
                <strong>S${s.stageNumber}:</strong> ${escapeHtml(s.stageName)}${revBadge}
              </span>
            `;
          });
          stagesHtml += `</div></div>`;
        }

        // Treatments list
        let trtHtml = '';
        if (d.treatments && d.treatments.length > 0) {
          trtHtml = `<ul style="list-style: disc; margin-left: 1.25rem; font-size: 0.75rem; color: hsl(var(--muted-foreground)); line-height: 1.5; margin-top: 0.5rem;">`;
          d.treatments.slice(0, 3).forEach(t => {
            trtHtml += `<li>${escapeHtml(t)}</li>`;
          });
          trtHtml += `</ul>`;
        }

        html += `
          <div class="shadcn-card" style="padding: 1.25rem; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span class="step-days-pill">${escapeHtml(d.crop)}</span>
                <span class="status-badge" style="font-size: 0.6875rem;">Verified</span>
              </div>
              <div style="font-size: 1rem; font-weight: 700; color: hsl(var(--foreground));">${escapeHtml(d.disease)}</div>
              <div style="font-size: 0.75rem; color: hsl(var(--muted-foreground)); margin-top: 0.15rem;">Causal: ${sci}</div>
              ${stagesHtml}
              ${trtHtml}
            </div>
            <div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid hsl(var(--border)); display: flex; justify-content: space-between; align-items: center;">
              <button class="btn btn-outline btn-sm btn-ask-this-disease" data-crop="${escapeHtml(d.crop)}" data-disease="${escapeHtml(d.disease)}" style="font-size: 0.75rem; height: 1.75rem;">
                <i data-lucide="message-square" style="width: 12px; height: 12px;"></i>
                <span>Get Full Action Plan</span>
              </button>
            </div>
          </div>
        `;
      });

      resultsContainer.innerHTML = html;
      initIcons();

      // Hook click on "Get Full Action Plan"
      resultsContainer.querySelectorAll('.btn-ask-this-disease').forEach(btn => {
        btn.addEventListener('click', () => {
          const c = btn.getAttribute('data-crop');
          const dis = btn.getAttribute('data-disease');
          const prompt = `Give complete treatment plan and Day 1, 2, 5 checklist for ${c} and ${dis}`;
          
          const tabBtnChat = document.getElementById('tab-btn-chat');
          if (tabBtnChat) tabBtnChat.click();
          
          const inputEl = document.getElementById('user-input');
          if (inputEl) inputEl.value = prompt;
          const chatForm = document.getElementById('chat-form');
          if (chatForm) chatForm.dispatchEvent(new Event('submit'));
        });
      });

    } catch (err) {
      resultsContainer.innerHTML = `<div style="grid-column: 1 / -1; color: hsl(var(--destructive)); padding: 1.5rem;">Failed to fetch disease catalog: ${err.message}</div>`;
    }
  }
}

function triggerInitialDoctorQuery() {
  const btnSearch = document.getElementById('btn-search-doctor');
  if (btnSearch) btnSearch.click();
}

/* =========================================================================
   8. TAB 3: 6-FACTOR REGIONAL SUITABILITY WIZARD
   ========================================================================= */
function initRecommendationWizard() {
  const pinInput = document.getElementById('rec-pincode-input');
  const seasonSelect = document.getElementById('rec-season-select');
  const soilSelect = document.getElementById('rec-soil-select');
  const waterSelect = document.getElementById('rec-water-select');
  const budgetSelect = document.getElementById('rec-budget-select');
  const prevInput = document.getElementById('rec-prev-crop');
  const btnCalc = document.getElementById('btn-calc-suitability');
  const container = document.getElementById('suitability-results-container');
  const quickPins = document.querySelectorAll('.quick-pin-btn');

  quickPins.forEach(btn => {
    btn.addEventListener('click', () => {
      const pin = btn.getAttribute('data-pin');
      if (pin && pinInput) {
        pinInput.value = pin;
        if (btnCalc) btnCalc.click();
      }
    });
  });

  if (btnCalc) {
    btnCalc.addEventListener('click', runSuitabilityCalculation);
  }

  async function runSuitabilityCalculation() {
    const pin = pinInput ? pinInput.value.trim() : '141004';
    const season = seasonSelect ? seasonSelect.value : 'KHARIF';
    const soil = soilSelect ? parseInt(soilSelect.value, 10) : 2;
    const water = waterSelect ? waterSelect.value : 'SURFACE';
    const budget = budgetSelect ? budgetSelect.value : 'B2';
    const prev = prevInput ? prevInput.value.trim() : 'Fallow';

    if (!container) return;
    container.innerHTML = `
      <div style="text-align: center; padding: 2.5rem; color: hsl(var(--muted-foreground)); background-color: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius);">
        <i data-lucide="loader-2" class="spin" style="width: 28px; height: 28px; margin-bottom: 0.5rem; color: hsl(var(--primary));"></i>
        <div>Executing 6-Factor Multi-Criteria Matrix Calculation...</div>
        <div style="font-size: 0.75rem; margin-top: 0.25rem;">Zone (2.0) • Season (2.0) • Water (2.0) • Soil (1.5) • Budget (1.5) • Rotation (1.0)</div>
      </div>
    `;
    initIcons();

    try {
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

      const data = await fetchGraphQL(q, {
        pin: pin,
        s: season,
        soil: soil,
        w: water,
        b: budget,
        prev: prev
      });

      const recs = data?.zoneRecommendations || [];
      const gw = data?.pincodeOutlook;

      let html = '';

      // Groundwater Header Card
      if (gw) {
        const isLow = gw.waterOutlookTag.toLowerCase().includes('low');
        const badgeColor = isLow ? '#ef4444' : '#10b981';
        html += `
          <div class="suitability-header-card">
            <div>
              <div style="font-size: 1rem; font-weight: 700; color: hsl(var(--foreground)); display: flex; align-items: center; gap: 0.5rem;">
                <i data-lucide="map-pin" style="width: 16px; height: 16px; color: #3b82f6;"></i>
                <span>District: ${escapeHtml(gw.district)} (${escapeHtml(pin)}) — Agro-Zone ${recs[0]?.zoneId || '3'}</span>
              </div>
              <div style="font-size: 0.8125rem; color: hsl(var(--muted-foreground)); margin-top: 0.25rem;">
                Reservoir Status: <strong>${escapeHtml(gw.reservoirLevelCurrent || 'Normal')}</strong> | Water Risk: <strong>${escapeHtml(gw.waterRisk || 'Low')}</strong>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <span class="status-badge" style="background-color: ${badgeColor}22; color: ${badgeColor}; border: 1px solid ${badgeColor}55;">
                ${escapeHtml(gw.waterOutlookTag)}
              </span>
            </div>
          </div>
        `;
      }

      // Suitability Table
      html += `
        <div class="suitability-table-wrapper">
          <table class="suitability-table">
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
      `;

      recs.forEach((r, idx) => {
        const match = r.matchPercentage || 0;
        const matchClass = match >= 80 ? 'high' : (match >= 65 ? 'medium' : 'low');
        const warn = r.waterOutlookWarning || 'Approved';
        const isWarn = warn.includes('Risk') || warn.includes('High');
        const warnBadge = isWarn 
          ? `<span class="gw-pill" style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; font-weight: 600;">⚠️ Restricted</span>`
          : `<span class="gw-pill" style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; font-weight: 600;">✅ Recommended</span>`;

        html += `
          <tr>
            <td><strong>#${idx + 1}</strong></td>
            <td><strong style="color: hsl(var(--foreground));">${escapeHtml(r.crop)}</strong></td>
            <td>${escapeHtml(r.category || 'Field Crop')} <span style="font-size: 0.7rem; color: hsl(var(--muted-foreground));">(${escapeHtml(r.family || '')})</span></td>
            <td>
              <span class="match-badge ${matchClass}">
                ${match.toFixed(1)}%
              </span>
            </td>
            <td>${renderMiniBar(r.zoneScore, 2)}</td>
            <td>${renderMiniBar(r.seasonScore, 2)}</td>
            <td>${renderMiniBar(r.waterScore, 2)}</td>
            <td>${renderMiniBar(r.soilScore, 2)}</td>
            <td>${renderMiniBar(r.budgetScore, 2)}</td>
            <td>${renderMiniBar(r.rotationScore, 2)}</td>
            <td>${warnBadge}</td>
          </tr>
        `;
      });

      html += `</tbody></table></div>`;
      container.innerHTML = html;
      initIcons();
    } catch (err) {
      container.innerHTML = `<div style="color: hsl(var(--destructive)); padding: 1.5rem;">Calculation Error: ${err.message}</div>`;
    }
  }

  function renderMiniBar(score, max = 2) {
    const pct = Math.min(100, Math.max(0, (score / max) * 100));
    return `
      <div class="factor-mini-bar">
        <div class="factor-bar-bg">
          <div class="factor-bar-fill" style="width: ${pct}%;"></div>
        </div>
        <span>${score.toFixed(1)}</span>
      </div>
    `;
  }
}

/* =========================================================================
   9. TAB 4: PHENOLOGICAL GROWTH STAGES & CROP CALENDAR
   ========================================================================= */
function initPhenology() {
  const cropSelect = document.getElementById('phenology-crop-select');
  const btnLoad = document.getElementById('btn-load-phenology');
  const container = document.getElementById('phenology-container');

  if (btnLoad) {
    btnLoad.addEventListener('click', loadPhenologySchedule);
  }
  if (cropSelect) {
    cropSelect.addEventListener('change', loadPhenologySchedule);
  }

  async function loadPhenologySchedule() {
    const crop = cropSelect ? cropSelect.value : 'Rice (Paddy)';
    if (!crop || !container) return;

    container.innerHTML = `
      <div style="text-align: center; padding: 2.5rem; color: hsl(var(--muted-foreground)); background-color: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius);">
        <i data-lucide="loader-2" class="spin" style="width: 28px; height: 28px; margin-bottom: 0.5rem; color: hsl(var(--primary));"></i>
        <div>Retrieving phenological schedule & environmental limits for ${escapeHtml(crop)}...</div>
      </div>
    `;
    initIcons();

    try {
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

      const data = await fetchGraphQL(q, { name: crop });
      const stages = data?.cropDetails?.stages || [];

      if (stages.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; padding: 3rem; color: hsl(var(--muted-foreground)); background-color: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius);">
            <i data-lucide="info" style="width: 32px; height: 32px; margin-bottom: 0.5rem;"></i>
            <div style="font-weight: 600;">Phenological calendar not indexed for ${escapeHtml(crop)}.</div>
            <div style="font-size: 0.8125rem;">Try selecting Rice, Cotton, Soybean, Wheat, Mustard, Sugarcane, or Tomato.</div>
          </div>
        `;
        initIcons();
        return;
      }

      let html = `<div class="phenology-timeline-wrapper">`;
      stages.forEach((s, idx) => {
        const temp = s.optimalTempC ? `${escapeHtml(s.optimalTempC)}°C` : '—';
        const hum = s.relHumidityPct ? `${escapeHtml(s.relHumidityPct)}%` : '—';
        const moist = s.soilMoisturePct ? `${escapeHtml(s.soilMoisturePct)}` : '—';
        const irrig = s.irrigationMm ? `${escapeHtml(s.irrigationMm)} mm` : '—';

        html += `
          <div class="phenology-stage-card">
            <div class="phenology-stage-header">
              <div class="phenology-stage-title">
                <span class="step-day-badge">Stage ${idx + 1}</span>
                <span>${escapeHtml(s.mainStage)}: ${escapeHtml(s.subStage)}</span>
              </div>
              <span class="step-days-pill">
                <i data-lucide="calendar" style="width: 12px; height: 12px;"></i>
                <span>Day ${s.startDay} – ${s.endDay}</span>
              </span>
            </div>

            <div class="env-limits-grid">
              <div class="env-metric-item">
                <span class="env-metric-label">Optimal Temp</span>
                <span class="env-metric-value">${temp}</span>
              </div>
              <div class="env-metric-item">
                <span class="env-metric-label">Rel. Humidity</span>
                <span class="env-metric-value">${hum}</span>
              </div>
              <div class="env-metric-item">
                <span class="env-metric-label">Soil Moisture</span>
                <span class="env-metric-value">${moist}</span>
              </div>
              <div class="env-metric-item">
                <span class="env-metric-label">Irrigation</span>
                <span class="env-metric-value">${irrig}</span>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 0.75rem; font-size: 0.8125rem;">
              ${s.susceptiblePests ? `
                <div style="background-color: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: var(--radius-sm); padding: 0.75rem;">
                  <div style="font-weight: 700; color: #f59e0b; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.35rem;">
                    <i data-lucide="bug" style="width: 14px; height: 14px;"></i>
                    <span>Susceptible Pests</span>
                  </div>
                  <div>${escapeHtml(s.susceptiblePests)}</div>
                  ${s.pestManagement ? `<div style="font-size: 0.75rem; color: hsl(var(--muted-foreground)); margin-top: 0.35rem;"><em>IPM: ${escapeHtml(s.pestManagement.substring(0, 160))}...</em></div>` : ''}
                </div>
              ` : ''}

              ${s.susceptibleDiseases ? `
                <div style="background-color: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: var(--radius-sm); padding: 0.75rem;">
                  <div style="font-weight: 700; color: #ef4444; margin-bottom: 0.25rem; display: flex; align-items: center; gap: 0.35rem;">
                    <i data-lucide="shield-alert" style="width: 14px; height: 14px;"></i>
                    <span>Susceptible Pathogens</span>
                  </div>
                  <div>${escapeHtml(s.susceptibleDiseases)}</div>
                  ${s.diseaseManagement ? `<div style="font-size: 0.75rem; color: hsl(var(--muted-foreground)); margin-top: 0.35rem;"><em>Treatment: ${escapeHtml(s.diseaseManagement.substring(0, 160))}...</em></div>` : ''}
                </div>
              ` : ''}
            </div>
          </div>
        `;
      });

      html += `</div>`;
      container.innerHTML = html;
      initIcons();
    } catch (err) {
      container.innerHTML = `<div style="color: hsl(var(--destructive)); padding: 1.5rem;">Failed to load phenology: ${err.message}</div>`;
    }
  }
}

/* =========================================================================
   10. TAB 5: DISTRICT GROUNDWATER & SEASON OUTLOOK
   ========================================================================= */
function initGroundwater() {
  const pinInput = document.getElementById('gw-pincode-input');
  const btnSearch = document.getElementById('btn-search-gw');
  const container = document.getElementById('groundwater-container');

  if (btnSearch) {
    btnSearch.addEventListener('click', searchGroundwater);
  }
  if (pinInput) {
    pinInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') searchGroundwater();
    });
  }

  async function searchGroundwater() {
    const pin = pinInput ? pinInput.value.trim() : '587111';
    if (!container) return;

    container.innerHTML = `
      <div style="text-align: center; padding: 2.5rem; color: hsl(var(--muted-foreground)); background-color: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius);">
        <i data-lucide="loader-2" class="spin" style="width: 28px; height: 28px; margin-bottom: 0.5rem; color: #06b6d4;"></i>
        <div>Fetching groundwater reserve & monsoon outlook for PIN ${escapeHtml(pin)}...</div>
      </div>
    `;
    initIcons();

    try {
      const q = `
        query GroundwaterQuery($pin: String!) {
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
          }
        }
      `;

      const data = await fetchGraphQL(q, { pin: pin });
      const gw = data?.pincodeOutlook;

      if (!gw) {
        container.innerHTML = `
          <div style="text-align: center; padding: 3rem; color: hsl(var(--muted-foreground)); background-color: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius);">
            <i data-lucide="alert-circle" style="width: 32px; height: 32px; color: #f59e0b; margin-bottom: 0.5rem;"></i>
            <div style="font-weight: 600; color: hsl(var(--foreground));">PIN Code ${escapeHtml(pin)} not indexed in district water records.</div>
            <div style="font-size: 0.8125rem; margin-top: 0.25rem;">Try testing with Bagalkote PINs: <code>587111</code>, <code>587201</code>, <code>587101</code>.</div>
          </div>
        `;
        initIcons();
        return;
      }

      const isLow = gw.waterOutlookTag.toLowerCase().includes('low');
      const tagColor = isLow ? '#ef4444' : '#10b981';

      let growPills = '';
      (gw.cropsToGrow || []).forEach(c => {
        growPills += `<span class="gw-pill" style="border: 1px solid #10b98155; background-color: rgba(16, 185, 129, 0.1); color: #10b981; font-weight: 600;">${escapeHtml(c)}</span>`;
      });

      let avoidPills = '';
      (gw.cropsToAvoid || []).forEach(c => {
        avoidPills += `<span class="gw-pill" style="border: 1px solid #ef444455; background-color: rgba(239, 68, 68, 0.1); color: #ef4444; font-weight: 600;">${escapeHtml(c)}</span>`;
      });

      const html = `
        <div class="groundwater-hero-card">
          <div class="gw-status-banner">
            <div>
              <div style="font-size: 1.25rem; font-weight: 800; color: hsl(var(--foreground));">
                ${escapeHtml(gw.district)} District — PIN ${escapeHtml(gw.pincode)}
              </div>
              <div style="font-size: 0.8125rem; color: hsl(var(--muted-foreground)); margin-top: 0.25rem;">
                Reservoir Level: <strong>${escapeHtml(gw.reservoirLevelCurrent || 'N/A')}</strong> | Monsoon Forecast vs Normal: <strong>${escapeHtml(gw.monsoonForecast || 'Normal')}</strong>
              </div>
            </div>
            <span class="status-badge" style="background-color: ${tagColor}22; color: ${tagColor}; border: 1px solid ${tagColor}55; font-size: 0.8125rem; padding: 0.35rem 0.75rem;">
              ${escapeHtml(gw.waterOutlookTag)}
            </span>
          </div>

          <div class="gw-crops-grid">
            <div class="gw-crops-col grow">
              <div class="gw-crops-title" style="color: #10b981;">
                <i data-lucide="check-circle" style="width: 16px; height: 16px;"></i>
                <span>Recommended Water-Efficient Crops (Water Need in mm)</span>
              </div>
              <div class="gw-pill-list">${growPills || 'None specified'}</div>
            </div>

            <div class="gw-crops-col avoid">
              <div class="gw-crops-title" style="color: #ef4444;">
                <i data-lucide="x-circle" style="width: 16px; height: 16px;"></i>
                <span>High-Water Crops to Avoid / Restrict (Water Need in mm)</span>
              </div>
              <div class="gw-pill-list">${avoidPills || 'None restricted'}</div>
            </div>
          </div>

          ${gw.whatThisMeans ? `
            <div style="padding: 1rem; background-color: hsl(var(--muted) / 0.5); border-radius: var(--radius-sm); border: 1px solid hsl(var(--border)); font-size: 0.8125rem; line-height: 1.5;">
              <strong style="color: hsl(var(--foreground));">What This Means for Local Farmers:</strong>
              <div style="color: hsl(var(--muted-foreground)); margin-top: 0.25rem;">${escapeHtml(gw.whatThisMeans)}</div>
            </div>
          ` : ''}
        </div>
      `;

      container.innerHTML = html;
      initIcons();
    } catch (err) {
      container.innerHTML = `<div style="color: hsl(var(--destructive)); padding: 1.5rem;">Failed to fetch groundwater data: ${err.message}</div>`;
    }
  }

  // Initial lookup
  searchGroundwater();
}

/* =========================================================================
   11. BACKEND HEALTH CHECK
   ========================================================================= */
async function checkBackendHealth() {
  const backendStatusText = document.getElementById('backend-status-text');
  try {
    const res = await fetch('/api/status');
    const json = await res.json();
    if (json.status === 'healthy' && backendStatusText) {
      backendStatusText.textContent = 'FastAPI: Active';
    }
  } catch (err) {
    if (backendStatusText) backendStatusText.textContent = 'Backend: Offline';
  }
}

/* =========================================================================
   12. UTILITIES
   ========================================================================= */
function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

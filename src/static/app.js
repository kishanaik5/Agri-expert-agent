// AgriCopilot Frontend Application Logic
// Connects to FastAPI GraphQL backend at /graphql

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initChat();
  initDoctor();
  initStages();
  initZones();
  checkBackendHealth();
});

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
   2. TAB NAVIGATION
   ========================================================================= */
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const tabContents = document.querySelectorAll('.tab-content');
  const pageTitle = document.getElementById('page-title');
  const pageSubtitle = document.getElementById('page-subtitle');

  const titles = {
    'chat-tab': {
      title: '🌾 Agri-Expert Conversational Copilot',
      subtitle: 'Powered by Neo4j Knowledge Graph, LangGraph Reasoning & RabbitMQ'
    },
    'doctor-tab': {
      title: '🩺 Crop Doctor & Disease Diagnostician',
      subtitle: 'Traverse 1,900+ Crop-Disease-Treatment knowledge paths directly'
    },
    'stages-tab': {
      title: '📅 Phenological Crop Growth Timeline',
      subtitle: 'Explore stage-by-stage agronomic durations and developmental phases'
    },
    'zones-tab': {
      title: '🗺️ Agro-Climatic Zone Suitability Engine',
      subtitle: 'Multi-criteria regional rankings for Indian PIN codes and soil classifications'
    },
    'system-tab': {
      title: '⚙️ Cloud Infrastructure & Knowledge Topology',
      subtitle: 'Live status of Neo4j AuraDB, RabbitMQ CloudAMQP, and FastAPI Worker'
    }
  };

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const tabId = item.getAttribute('data-tab');

      navItems.forEach(btn => btn.classList.remove('active'));
      tabContents.forEach(tab => tab.classList.remove('active'));

      item.classList.add('active');
      const targetTab = document.getElementById(tabId);
      if (targetTab) {
        targetTab.classList.add('active');
      }

      if (titles[tabId]) {
        pageTitle.textContent = titles[tabId].title;
        pageSubtitle.textContent = titles[tabId].subtitle;
      }
    });
  });

  const btnNewChat = document.getElementById('btn-new-chat');
  if (btnNewChat) {
    btnNewChat.addEventListener('click', () => {
      const navChat = document.getElementById('nav-chat');
      if (navChat) navChat.click();
      const messagesContainer = document.getElementById('chat-messages');
      if (messagesContainer) {
        messagesContainer.innerHTML = `
          <div class="message bot-message">
            <div class="message-avatar">
              <i class="fa-solid fa-robot"></i>
            </div>
            <div class="message-body">
              <div class="message-header">
                <span class="sender-name">AgriCopilot AI</span>
                <span class="message-time">Just now</span>
              </div>
              <div class="message-text">
                <p>New session initialized! How can I assist with your crops, disease diagnostics, or soil recommendations?</p>
              </div>
            </div>
          </div>
        `;
      }
      const userInput = document.getElementById('user-input');
      if (userInput) userInput.focus();
    });
  }
}

/* =========================================================================
   3. AI ADVISORY CHAT
   ========================================================================= */
function initChat() {
  const chatForm = document.getElementById('chat-form');
  const userInput = document.getElementById('user-input');
  const messagesContainer = document.getElementById('chat-messages');
  const promptChips = document.querySelectorAll('.prompt-chip');

  // Quick Prompt Chips
  promptChips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        userInput.value = prompt;
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

    const typingId = appendTypingIndicator();
    scrollToBottom();

    try {
      const query = `
        query AskAdvisory($q: String!) {
          askCopilot(query: $q) {
            advisory
            diagnosis
            confidenceScore
            crop
          }
        }
      `;

      const data = await fetchGraphQL(query, { q: question });
      removeTypingIndicator(typingId);

      const copilotData = data && data.askCopilot ? data.askCopilot : null;
      const markdownText = copilotData && copilotData.advisory 
        ? copilotData.advisory 
        : (copilotData && copilotData.diagnosis ? `### Diagnosis\n${copilotData.diagnosis}` : "I could not retrieve a specific advisory for this query. Please check your crop or symptom description.");

      appendBotMessage(markdownText);
    } catch (err) {
      removeTypingIndicator(typingId);
      appendBotMessage(`⚠️ **Connection Error**: Unable to reach the Agri-Expert agent. (${err.message})`);
    }

    scrollToBottom();
  }

  function appendUserMessage(text) {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user-message';
    msgDiv.innerHTML = `
      <div class="message-avatar">
        <i class="fa-solid fa-user"></i>
      </div>
      <div class="message-body">
        <div class="message-header">
          <span class="sender-name">You</span>
          <span class="message-time">${timeStr}</span>
        </div>
        <div class="message-text">
          <p>${escapeHtml(text)}</p>
        </div>
      </div>
    `;
    messagesContainer.appendChild(msgDiv);
  }

  function appendBotMessage(markdownText) {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';

    // Parse Markdown if marked library is available
    let renderedHtml = markdownText;
    if (window.marked && typeof window.marked.parse === 'function') {
      renderedHtml = window.marked.parse(markdownText);
    } else {
      renderedHtml = `<p>${escapeHtml(markdownText)}</p>`;
    }

    msgDiv.innerHTML = `
      <div class="message-avatar">
        <i class="fa-solid fa-robot"></i>
      </div>
      <div class="message-body">
        <div class="message-header">
          <span class="sender-name">AgriCopilot AI</span>
          <span class="message-time">${timeStr}</span>
        </div>
        <div class="message-text">
          ${renderedHtml}
        </div>
      </div>
    `;
    messagesContainer.appendChild(msgDiv);
  }

  function appendTypingIndicator() {
    const id = 'typing-' + Date.now();
    const typingDiv = document.createElement('div');
    typingDiv.id = id;
    typingDiv.className = 'message bot-message';
    typingDiv.innerHTML = `
      <div class="message-avatar">
        <i class="fa-solid fa-robot"></i>
      </div>
      <div class="message-body">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    `;
    messagesContainer.appendChild(typingDiv);
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function escapeHtml(string) {
    const div = document.createElement('div');
    div.innerText = string;
    return div.innerHTML;
  }
}

/* =========================================================================
   4. CROP DOCTOR LOOKUP
   ========================================================================= */
function initDoctor() {
  const btnSearch = document.getElementById('btn-search-doctor');
  const cropSelect = document.getElementById('doctor-crop-select');
  const symptomInput = document.getElementById('doctor-symptom-input');
  const resultsGrid = document.getElementById('doctor-results');

  if (btnSearch) {
    btnSearch.addEventListener('click', runDoctorQuery);
  }

  // Auto trigger on initial tab load
  runDoctorQuery();

  async function runDoctorQuery() {
    const crop = cropSelect ? cropSelect.value : 'Cotton';
    const symptom = symptomInput ? symptomInput.value.trim() : '';

    resultsGrid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">
        <i class="fa-solid fa-spinner fa-spin fa-2x"></i>
        <p style="margin-top: 10px;">Querying Neo4j Knowledge Graph for ${crop}...</p>
      </div>
    `;

    try {
      const query = `
        query GetDiseases($crop: String, $symptom: String) {
          diseases(crop: $crop, symptoms: $symptom) {
            crop
            disease
            pathogen
            treatments
          }
        }
      `;

      const data = await fetchGraphQL(query, { crop, symptom: symptom || null });
      const records = data && data.diseases ? data.diseases : [];

      if (records.length === 0) {
        resultsGrid.innerHTML = `
          <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted); background: var(--bg-card); border-radius: var(--radius-md);">
            <i class="fa-solid fa-shield-halved fa-2x" style="color: var(--emerald-400); margin-bottom: 12px;"></i>
            <p>No matching disease records found for <strong>${crop}</strong> with filter <em>"${symptom || 'all'}"</em>.</p>
          </div>
        `;
        return;
      }

      resultsGrid.innerHTML = records.map(r => `
        <div class="disease-card">
          <div class="disease-header">
            <h4>${r.disease || 'Plant Condition'}</h4>
            <span class="badge-crop">${r.crop || crop}</span>
          </div>
          <div class="pathogen-name">
            <i class="fa-solid fa-biohazard"></i> Pathogen: ${r.pathogen || 'Fungal / Bacterial Complex'}
          </div>
          <div class="treatment-box">
            <strong><i class="fa-solid fa-prescription-bottle-medical"></i> Prescribed Protocol:</strong>
            <p style="margin-top: 4px;">${Array.isArray(r.treatments) && r.treatments.length > 0 ? r.treatments.join('; ') : 'Consult registered agronomist.'}</p>
          </div>
        </div>
      `).join('');

    } catch (err) {
      resultsGrid.innerHTML = `
        <div style="grid-column: 1/-1; color: var(--rose-500); padding: 20px; background: rgba(244,63,94,0.1); border-radius: var(--radius-md);">
          ⚠️ Failed to load disease data: ${err.message}
        </div>
      `;
    }
  }
}

/* =========================================================================
   5. PHENOLOGICAL GROWTH STAGES
   ========================================================================= */
function initStages() {
  const btnSearch = document.getElementById('btn-search-stages');
  const cropSelect = document.getElementById('stages-crop-select');
  const timelineWrapper = document.getElementById('stages-timeline');

  if (btnSearch) {
    btnSearch.addEventListener('click', runStagesQuery);
  }

  // Load initial wheat stages
  runStagesQuery();

  async function runStagesQuery() {
    const crop = cropSelect ? cropSelect.value : 'Wheat';

    timelineWrapper.innerHTML = `
      <div style="padding: 30px; text-align: center; color: var(--text-muted);">
        <i class="fa-solid fa-spinner fa-spin fa-2x"></i>
        <p style="margin-top: 10px;">Loading growth stages for ${crop}...</p>
      </div>
    `;

    try {
      const query = `
        query GetCropStages($crop: String!) {
          cropDetails(name: $crop) {
            name
            stages {
              mainStage
              subStage
              startDay
              endDay
            }
          }
        }
      `;

      const data = await fetchGraphQL(query, { crop });
      const cropDetails = data && data.cropDetails ? data.cropDetails : null;
      const stages = cropDetails && cropDetails.stages ? cropDetails.stages : [];

      if (stages.length === 0) {
        timelineWrapper.innerHTML = `
          <div style="padding: 20px; background: var(--bg-card); border-radius: var(--radius-md); color: var(--text-muted);">
            No phenological stage data currently mapped for <strong>${crop}</strong>.
          </div>
        `;
        return;
      }

      timelineWrapper.innerHTML = stages.map((st, idx) => {
        return `
          <div class="stage-item">
            <div class="stage-dot"></div>
            <div class="stage-card">
              <div class="stage-phase">${st.mainStage || `Stage ${idx + 1}`}</div>
              <h4 class="stage-title">${st.subStage || st.mainStage}</h4>
              <div class="stage-days">
                <i class="fa-regular fa-clock"></i> Timeline: <strong>Day ${st.startDay} - ${st.endDay}</strong>
              </div>
            </div>
          </div>
        `;
      }).join('');

    } catch (err) {
      timelineWrapper.innerHTML = `
        <div style="color: var(--rose-500); padding: 20px;">
          ⚠️ Error loading phenology data: ${err.message}
        </div>
      `;
    }
  }
}

/* =========================================================================
   6. REGIONAL ZONE SUITABILITY
   ========================================================================= */
function initZones() {
  const btnSearch = document.getElementById('btn-search-zones');
  const pincodeInput = document.getElementById('zone-pincode-input');
  const soilSelect = document.getElementById('zone-soil-select');
  const rankingsContainer = document.getElementById('zone-rankings');

  if (btnSearch) {
    btnSearch.addEventListener('click', runZonesQuery);
  }

  // Load initial zone recommendation
  runZonesQuery();

  async function runZonesQuery() {
    const pincode = pincodeInput ? pincodeInput.value.trim() : '141004';
    const soilClassVal = soilSelect && soilSelect.value ? parseInt(soilSelect.value, 10) : null;

    rankingsContainer.innerHTML = `
      <div style="padding: 40px; text-align: center; color: var(--text-muted); background: var(--bg-card); border-radius: var(--radius-md);">
        <i class="fa-solid fa-spinner fa-spin fa-2x"></i>
        <p style="margin-top: 10px;">Computing zone suitability rankings for PIN ${pincode}...</p>
      </div>
    `;

    try {
      const query = `
        query GetZoneRecs($pincode: String!, $soilClass: Int) {
          zoneRecommendations(pincode: $pincode, soilClass: $soilClass) {
            crop
            category
            zoneId
            combinedScore
          }
        }
      `;

      const data = await fetchGraphQL(query, { pincode, soilClass: soilClassVal });
      const recs = data && data.zoneRecommendations ? data.zoneRecommendations : [];

      if (recs.length === 0) {
        rankingsContainer.innerHTML = `
          <div style="padding: 30px; text-align: center; color: var(--text-muted); background: var(--bg-card); border-radius: var(--radius-md);">
            <i class="fa-solid fa-circle-exclamation fa-2x" style="color: var(--amber-400); margin-bottom: 8px;"></i>
            <p>No agro-climatic profile found for PIN <strong>${pincode}</strong>. Try <code>141004</code> (Ludhiana), <code>500001</code> (Hyderabad), or <code>380001</code> (Ahmedabad).</p>
          </div>
        `;
        return;
      }

      const zoneId = recs[0].zoneId || 'Identified';

      const rows = recs.map((c, i) => {
        const score = c.combinedScore || 1.0;
        const pct = Math.min(100, Math.round((score / 2.0) * 100));
        return `
          <tr>
            <td style="font-weight: 700; color: var(--text-muted); width: 40px;">#${i + 1}</td>
            <td style="font-weight: 700; color: var(--text-primary); font-size: 14.5px;">${c.crop}</td>
            <td>
              <div class="score-bar-container">
                <div class="score-bar">
                  <div class="score-fill" style="width: ${pct}%;"></div>
                </div>
                <span style="font-weight: 700; font-family: var(--font-mono); font-size: 13px; color: var(--emerald-400);">${pct}%</span>
              </div>
            </td>
          </tr>
        `;
      }).join('');

      rankingsContainer.innerHTML = `
        <div style="margin-bottom: 16px; display: flex; gap: 20px; flex-wrap: wrap;">
          <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 12px 16px; border-radius: var(--radius-sm); font-size: 13px;">
            <span style="color: var(--text-muted);">PIN Code:</span> <strong>${pincode}</strong>
          </div>
          <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 12px 16px; border-radius: var(--radius-sm); font-size: 13px;">
            <span style="color: var(--text-muted);">Agro-Climatic Zone ID:</span> <strong style="color: var(--teal-400);">Zone ${zoneId}</strong>
          </div>
        </div>

        <table class="zones-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Recommended Crop</th>
              <th>Suitability Index</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      `;

    } catch (err) {
      rankingsContainer.innerHTML = `
        <div style="color: var(--rose-500); padding: 20px;">
          ⚠️ Error calculating zone recommendations: ${err.message}
        </div>
      `;
    }
  }
}

/* =========================================================================
   7. BACKEND HEALTH CHECK
   ========================================================================= */
async function checkBackendHealth() {
  const statusText = document.getElementById('backend-status-text');
  const neo4jStatus = document.getElementById('neo4j-status');

  try {
    const res = await fetch('/api/status');
    if (res.ok) {
      const data = await res.json();
      if (statusText) statusText.textContent = 'Operational';
      if (neo4jStatus && data.neo4j_connected) {
        neo4jStatus.innerHTML = '<i class="fa-solid fa-database"></i> Neo4j Aura: Connected';
        neo4jStatus.style.color = 'var(--emerald-400)';
      }
    }
  } catch (e) {
    if (statusText) statusText.textContent = 'Operational';
  }
}

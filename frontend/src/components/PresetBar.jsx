import React from 'react';
import { Sparkles } from 'lucide-react';

export default function PresetBar({ onSelectPrompt }) {
  const presets = [
    {
      label: '🌿 Cotton Leaf Blight Protocol',
      prompt: 'Give complete treatment plan for cotton crop and leaf blight disease with Day 1, 2, 5 checklist and revenue loss per acre'
    },
    {
      label: '🌾 Wheat Yellow Rust (141004)',
      prompt: 'What should I spray on wheat for yellow stripe rust in pincode 141004?'
    },
    {
      label: '🗺️ Ludhiana 6-Factor Suitability',
      prompt: 'Calculate best suited crops for PIN code 141004 in black soil during Kharif season with surface irrigation'
    },
    {
      label: '💧 Bagalkote Water Outlook (587111)',
      prompt: 'Show groundwater status, reservoir levels, and crops to avoid for pincode 587111'
    },
    {
      label: '🌾 Rice Growth Stages & Pests',
      prompt: 'Provide full phenological growth stages, critical moisture milestones, and vulnerable pests for rice'
    },
    {
      label: '🌱 Mustard Powdery Mildew',
      prompt: 'How to treat powdery mildew on mustard with biological and chemical remedies?'
    }
  ];

  return (
    <div className="presets-banner">
      <div className="presets-label">
        <Sparkles style={{ width: 14, height: 14, color: 'var(--primary)' }} />
        <span>Scenarios:</span>
      </div>
      <div className="preset-pills-list">
        {presets.map((p, idx) => (
          <button
            key={idx}
            className="preset-pill"
            onClick={() => onSelectPrompt(p.prompt)}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}

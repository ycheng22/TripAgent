import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PlanService, PresetScenario, SSEEvent } from './plan.service';
import { TimelineComponent } from './timeline/timeline.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, TimelineComponent],
  template: `
    <div class="page-wrap">
      <!-- HEADER -->
      <header class="app-header">
        <div class="header-inner">
          <div class="brand">
            <span class="brand-icon">&#x1F9ED;</span>
            <div>
              <h1 class="brand-title">TripAgent</h1>
              <p class="brand-subtitle">Precision Travel Planning with Deterministic Safety & Budget Enforcement</p>
            </div>
          </div>
          <div class="model-badge-group">
            <span class="badge badge-ai">&#x26A1; Default AI: Gemini 3.5 Flash Lite</span>
            <span class="badge badge-db">&#x1F5C4; Database: Neon PostgreSQL</span>
          </div>
        </div>
      </header>

      <main class="container">
        <!-- HERO / INFO BANNER -->
        <div class="info-card">
          <div class="info-icon">&#x1F4A1;</div>
          <div class="info-text">
            <strong>Production AI Architecture:</strong>
            Select any of the <strong>20 precomputed benchmark scenarios</strong> below to replay authentic evaluation runs directly from our <strong>Neon PostgreSQL database</strong> (0 tokens consumed, instant & free). Or enter a custom trip request to trigger live AI generation with strict rate limiting (5 calls / 10 mins).
          </div>
        </div>

        <!-- RATE LIMIT BANNER -->
        <div class="rate-limit-banner" *ngIf="rateLimitMessage">
          <span class="warning-icon">&#x26A0;</span>
          <div>
            <strong>Rate Limit Enforced</strong>
            <p>{{ rateLimitMessage }}</p>
          </div>
          <button class="btn-dismiss" (click)="rateLimitMessage = null">&times;</button>
        </div>

        <!-- 20 PRESETS SECTION -->
        <section class="presets-section">
          <div class="section-header">
            <div>
              <h2 class="section-title">20 Curated Evaluation Scenarios</h2>
              <p class="section-desc">Click any scenario to replay the full reasoning, validation, and replanning loop from Neon DB:</p>
            </div>
            <div class="category-filters">
              <button 
                class="filter-pill" 
                [class.active]="selectedCategory === 'ALL'" 
                (click)="selectedCategory = 'ALL'">
                All ({{ presets.length }})
              </button>
              <button 
                class="filter-pill" 
                *ngFor="let cat of categories" 
                [class.active]="selectedCategory === cat" 
                (click)="selectedCategory = cat">
                {{ cat }}
              </button>
            </div>
          </div>

          <div class="presets-grid">
            <div 
              class="preset-card" 
              *ngFor="let p of filteredPresets"
              [class.selected]="selectedPresetId === p.id"
              (click)="selectPreset(p)">
              <div class="preset-card-top">
                <span class="category-tag">{{ p.category }}</span>
                <span class="feasibility-badge" [ngClass]="p.expected_feasibility">
                  {{ p.expected_feasibility === 'feasible' ? '✔ Feasible' : '⛔ Infeasible' }}
                </span>
              </div>
              <h3 class="preset-title">{{ p.title }}</h3>
              <p class="preset-prompt">"{{ p.request_text }}"</p>
              <div class="preset-meta">
                <span class="meta-item">&#x1F4C5; {{ p.days }}d</span>
                <span class="meta-item">&#x1F4B6; €{{ p.budget_eur }}</span>
                <span class="meta-item">&#x1F465; {{ p.party_size }}p</span>
                <span class="meta-item cost" *ngIf="p.total_cost > 0">&#x2714; €{{ p.total_cost }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- INPUT FORM -->
        <section class="planning-box" id="planning-box">
          <h3 class="box-title">Trip Request Prompt</h3>
          <div class="input-form">
            <textarea 
              [(ngModel)]="requestText" 
              rows="3" 
              placeholder="Enter trip request (e.g. A romantic weekend in Paris. 2 days, 1000 EUR budget)"></textarea>
            
            <div class="form-actions">
              <span class="rate-note">
                <span class="rate-dot"></span>
                Rate Limit: 5 live AI calls / 10m &bull; Presets bypass rate limit
              </span>
              <button 
                class="btn-plan" 
                (click)="startPlan()" 
                [disabled]="isPlanning || !requestText.trim()">
                <span *ngIf="!isPlanning">&#x1F680; Plan Trip</span>
                <span *ngIf="isPlanning">&#x23F3; Planning in Progress...</span>
              </button>
            </div>
          </div>
        </section>

        <!-- TIMELINE COMPONENT -->
        <app-timeline [events]="events" [isPlanning]="isPlanning"></app-timeline>
      </main>
    </div>
  `,
  styles: [`
    .page-wrap {
      min-height: 100vh;
      background: #f8fafc;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
    }
    .app-header {
      background: #ffffff;
      border-bottom: 1px solid #e2e8f0;
      padding: 18px 24px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }
    .header-inner {
      max-width: 1100px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .brand-icon {
      font-size: 2.2rem;
    }
    .brand-title {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #0f172a;
    }
    .brand-subtitle {
      margin: 2px 0 0 0;
      font-size: 0.85rem;
      color: #64748b;
    }
    .model-badge-group {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .badge {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 20px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .badge-ai {
      background: #eff6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
    }
    .badge-db {
      background: #ecfdf5;
      color: #047857;
      border: 1px solid #a7f3d0;
    }
    .container {
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px 20px 60px 20px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }
    .info-card {
      display: flex;
      gap: 14px;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 14px 18px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      align-items: flex-start;
    }
    .info-icon {
      font-size: 1.4rem;
    }
    .info-text {
      font-size: 0.9rem;
      color: #334155;
      line-height: 1.5;
    }
    .rate-limit-banner {
      display: flex;
      align-items: center;
      gap: 12px;
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 8px;
      padding: 12px 16px;
      color: #991b1b;
      font-size: 0.9rem;
    }
    .btn-dismiss {
      margin-left: auto;
      background: none;
      border: none;
      font-size: 1.3rem;
      color: #991b1b;
      cursor: pointer;
    }
    .presets-section {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 12px;
    }
    .section-title {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 700;
      color: #0f172a;
    }
    .section-desc {
      margin: 4px 0 0 0;
      font-size: 0.85rem;
      color: #64748b;
    }
    .category-filters {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .filter-pill {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 16px;
      padding: 4px 12px;
      font-size: 0.8rem;
      color: #475569;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .filter-pill:hover {
      background: #f1f5f9;
      color: #0f172a;
    }
    .filter-pill.active {
      background: #2563eb;
      color: white;
      border-color: #2563eb;
    }
    .presets-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 14px;
      max-height: 480px;
      overflow-y: auto;
      padding: 4px 4px 10px 4px;
    }
    .preset-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 14px;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      flex-direction: column;
      gap: 8px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }
    .preset-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
      border-color: #93c5fd;
    }
    .preset-card.selected {
      border-color: #2563eb;
      background: #f0f7ff;
    }
    .preset-card-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .category-tag {
      font-size: 0.7rem;
      font-weight: 700;
      color: #0369a1;
      background: #e0f2fe;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .feasibility-badge {
      font-size: 0.7rem;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .feasibility-badge.feasible {
      background: #dcfce7;
      color: #15803d;
    }
    .feasibility-badge.infeasible {
      background: #fee2e2;
      color: #b91c1c;
    }
    .preset-title {
      margin: 0;
      font-size: 0.95rem;
      font-weight: 700;
      color: #1e293b;
    }
    .preset-prompt {
      margin: 0;
      font-size: 0.8rem;
      color: #64748b;
      line-height: 1.35;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .preset-meta {
      display: flex;
      gap: 8px;
      font-size: 0.75rem;
      color: #475569;
      font-weight: 500;
      margin-top: auto;
      border-top: 1px solid #f1f5f9;
      padding-top: 6px;
    }
    .meta-item.cost {
      margin-left: auto;
      color: #059669;
      font-weight: 700;
    }
    .planning-box {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 18px 20px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .box-title {
      margin: 0 0 10px 0;
      font-size: 1rem;
      font-weight: 700;
      color: #1e293b;
    }
    .input-form {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    textarea {
      width: 100%;
      box-sizing: border-box;
      padding: 12px 14px;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      font-size: 0.95rem;
      font-family: inherit;
      resize: vertical;
      transition: border-color 0.15s;
    }
    textarea:focus {
      outline: none;
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    .form-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .rate-note {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8rem;
      color: #64748b;
    }
    .rate-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
    }
    .btn-plan {
      padding: 10px 22px;
      background: #2563eb;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s ease;
    }
    .btn-plan:hover:not(:disabled) {
      background: #1d4ed8;
    }
    .btn-plan:disabled {
      background: #94a3b8;
      cursor: not-allowed;
    }
  `]
})
export class AppComponent implements OnInit {
  requestText = 'A romantic weekend in Paris. 2 days, 1000 EUR budget.';
  isPlanning = false;
  events: SSEEvent[] = [];
  presets: PresetScenario[] = [];
  selectedCategory = 'ALL';
  selectedPresetId: string | null = 'scenario_ai_01';
  rateLimitMessage: string | null = null;

  constructor(private planService: PlanService) {}

  ngOnInit() {
    this.loadPresets();
  }

  loadPresets() {
    this.planService.getPresets().subscribe({
      next: (data) => {
        this.presets = data;
        if (this.presets.length > 0 && !this.requestText) {
          this.requestText = this.presets[0].request_text;
          this.selectedPresetId = this.presets[0].id;
        }
      },
      error: (err) => console.error('Failed to load presets:', err)
    });
  }

  get categories(): string[] {
    const set = new Set<string>();
    for (const p of this.presets) {
      if (p.category) set.add(p.category);
    }
    return Array.from(set);
  }

  get filteredPresets(): PresetScenario[] {
    if (this.selectedCategory === 'ALL') {
      return this.presets;
    }
    return this.presets.filter(p => p.category === this.selectedCategory);
  }

  selectPreset(preset: PresetScenario) {
    this.selectedPresetId = preset.id;
    this.requestText = preset.request_text;
    this.rateLimitMessage = null;
    
    // Automatically execute the preset plan
    this.startPlan();

    // Smooth scroll down to timeline
    const elem = document.getElementById('planning-box');
    if (elem) {
      elem.scrollIntoView({ behavior: 'smooth' });
    }
  }

  startPlan() {
    this.events = [];
    this.isPlanning = true;
    this.rateLimitMessage = null;

    // Intelligently extract days and budget from user prompt if present
    const daysMatch = this.requestText.match(/(\d+)\s*days?/i);
    const days = daysMatch ? parseInt(daysMatch[1], 10) : 2;

    const budgetMatch = this.requestText.match(/(?:€|eur\s*)(\d+)|(\d+)\s*(?:€|eur)|budget\s+(?:is\s+)?(?:eur\s+)?(\d+)/i);
    const budget = budgetMatch ? parseFloat(budgetMatch[1] || budgetMatch[2] || budgetMatch[3]) : 1000.0;

    const isCouple = /couple|romantic|two people|2 people/i.test(this.requestText);

    const req = {
      request_text: this.requestText,
      constraints: [],
      party_size: isCouple ? 2 : 1,
      budget: budget,
      days: days
    };
    
    this.planService.planTrip(req).subscribe({
      next: (ev) => {
        this.events.push(ev);
        if (ev.event_type === 'rate_limit_exceeded') {
          this.rateLimitMessage = ev.payload?.detail || 'Rate limit reached: Maximum 5 live AI generation calls allowed every 10 minutes.';
          this.isPlanning = false;
        }
        if (ev.event_type === 'finalised' || ev.event_type === 'infeasible' || ev.event_type === 'aborted') {
          this.isPlanning = false;
        }
      },
      error: (err) => {
        console.error('SSE Error:', err);
        this.isPlanning = false;
      },
      complete: () => {
        this.isPlanning = false;
      }
    });
  }
}

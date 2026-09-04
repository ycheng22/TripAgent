import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PlanService, SSEEvent } from './plan.service';
import { TimelineComponent } from './timeline/timeline.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, TimelineComponent],
  template: `
    <div class="container">
      <h1>TripAgent Planner</h1>
      <div class="input-form">
        <textarea [(ngModel)]="requestText" rows="4" cols="50" placeholder="Enter trip request (e.g. 5 days / €1200 / two people / no long-distance coaches)"></textarea>
        <button (click)="startPlan()" [disabled]="isPlanning">Plan Trip</button>
      </div>
      
      <app-timeline [events]="events"></app-timeline>
    </div>
  `,
  styles: [`
    .container { max-width: 800px; margin: 0 auto; padding: 20px; font-family: sans-serif; }
    .input-form { margin-bottom: 20px; display: flex; flex-direction: column; gap: 10px; }
    button { padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
    button:disabled { background: #ccc; }
  `]
})
export class AppComponent {
  requestText = '5 days / €1200 / two people / no long-distance coaches';
  isPlanning = false;
  events: SSEEvent[] = [];

  constructor(private planService: PlanService) {}

  startPlan() {
    this.events = [];
    this.isPlanning = true;
    
    // We mock the other fields since the UI just takes text for now
    const req = {
      request_text: this.requestText,
      constraints: [],
      party_size: 2,
      budget: 1200.0,
      days: 5
    };
    
    this.planService.planTrip(req).subscribe({
      next: (ev) => {
        this.events.push(ev);
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

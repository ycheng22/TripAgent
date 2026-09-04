import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SSEEvent } from '../plan.service';
import { ApprovalService } from '../approval.service';

@Component({
  selector: 'app-timeline',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './timeline.component.html',
  styleUrls: ['./timeline.component.css']
})
export class TimelineComponent {
  @Input() events: SSEEvent[] = [];

  constructor(private approvalService: ApprovalService) {}

  approveAction(actionId: string) {
    this.approvalService.approve(actionId).subscribe({
      next: () => console.log('Approved', actionId),
      error: err => console.error(err)
    });
  }

  rejectAction(actionId: string) {
    this.approvalService.reject(actionId, "User rejected").subscribe({
      next: () => console.log('Rejected', actionId),
      error: err => console.error(err)
    });
  }
}

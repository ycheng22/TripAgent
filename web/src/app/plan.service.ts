import { Injectable, NgZone } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

export interface SSEEvent {
  event_type: string;
  payload: any;
  timestamp: string;
}

@Injectable({
  providedIn: 'root'
})
export class PlanService {
  constructor(private zone: NgZone) {}

  planTrip(request: any): Observable<SSEEvent> {
    return new Observable<SSEEvent>(observer => {
      fetch(`${environment.apiBaseUrl}/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      }).then(response => {
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        
        let buffer = '';

        const read = () => {
          reader?.read().then(({ done, value }) => {
            if (done) {
              this.zone.run(() => observer.complete());
              return;
            }
            
            buffer += decoder.decode(value, { stream: true });
            
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // Keep the incomplete line in the buffer
            
            for (const chunk of lines) {
              const eventMatch = chunk.match(/event:\s*(.+)/);
              const dataMatch = chunk.match(/data:\s*(.+)/);
              
              if (eventMatch && dataMatch) {
                const evType = eventMatch[1].trim();
                const payload = JSON.parse(dataMatch[1].trim());
                this.zone.run(() => {
                  observer.next({ event_type: evType, payload, timestamp: new Date().toISOString() });
                });
              }
            }
            read();
          }).catch(err => {
            this.zone.run(() => observer.error(err));
          });
        };
        
        read();
      }).catch(err => {
        this.zone.run(() => observer.error(err));
      });
    });
  }
}

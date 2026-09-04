import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApprovalService {
  constructor(private http: HttpClient) {}

  listApprovals(): Observable<any> {
    return this.http.get(`${environment.apiBaseUrl}/approvals`);
  }

  approve(actionId: string): Observable<any> {
    return this.http.post(`${environment.apiBaseUrl}/approvals/${actionId}/approve`, {});
  }

  reject(actionId: string, reason: string): Observable<any> {
    return this.http.post(`${environment.apiBaseUrl}/approvals/${actionId}/reject`, { reason });
  }
}

import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

interface Message {
  question: string;
  requete_sql: string;
  reponse_sql: string;
}

@Component({
  selector: 'app-sql-chat',
  standalone: true,
  templateUrl: './sql-chat.component.html',
  styleUrls: ['./sql-chat.component.css'],
  imports: [CommonModule, FormsModule]
})
export class SqlChatComponent implements OnInit {
  question = '';
  messages: Message[] = [];
  loading = false;
  selectedDb = '';
  databases: string[] = [];

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.http.get<string[]>('http://localhost:8020/list_databases').subscribe({
      next: (res) => {
        this.databases = res;
        if (res.length > 0) this.selectedDb = res[0];
      },
      error: (err) => {
        console.error('Erreur récupération bases:', err);
      }
    });
  }

  poserQuestion() {
    const q = this.question.trim();
    if (!q || !this.selectedDb) return;
    this.loading = true;

    this.http.post<any>('http://localhost:8020/pose_question', {
      question: q,
      database: this.selectedDb
    }).subscribe({
      next: (res) => {
        this.messages.push({
          question: q,
          requete_sql: res.requete_sql || "",       // affiche la requête si elle est présente
          reponse_sql: res.reponse_finale || ""     // réponse textuelle synthétisée
        });
        this.question = '';
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.loading = false;
      }
    });
  }
}

import { Component } from '@angular/core';
import { SqlChatComponent } from './sql-chat/sql-chat.component';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, SqlChatComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  protected title = 'chatbot-app';
}
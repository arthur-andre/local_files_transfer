import { provideRouter } from '@angular/router';
import { AppComponent } from './app.component';

export const appConfig = {
  providers: [
    provideRouter([
      {
        path: '',
        component: AppComponent
      }
    ])
  ]
};

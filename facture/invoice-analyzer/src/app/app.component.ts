import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import * as pdfjsLib from 'pdfjs-dist';

(pdfjsLib as any).GlobalWorkerOptions.workerSrc =
  `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js`;

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule], 
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  result: any = null;
  highlightKey: string = '';
  selectedFile: File | null = null;

  readonly champsFixes: string[] = [
    "entreprise",
    "tva_intracommunautaire",
    "SIRET/SIREN",
    "numero_facture_ou_piece",
    "date",
    "montant_TTC",
    "montant_Hors_Taxe",
    "montant_TVA"
  ];

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0] || null;

    if (this.selectedFile) {
      const reader = new FileReader();

      reader.onload = async () => {
        const typedarray = new Uint8Array(reader.result as ArrayBuffer);
        const pdf = await pdfjsLib.getDocument({ data: typedarray }).promise;
        const page = await pdf.getPage(1);
        const canvas: any = document.getElementById('pdfCanvas');
        const context = canvas.getContext('2d');
        const viewport = page.getViewport({ scale: 1.5 });

        canvas.height = viewport.height;
        canvas.width = viewport.width;

        await page.render({ canvasContext: context, viewport }).promise;
      };

      reader.readAsArrayBuffer(this.selectedFile);
    }
  }

//   async analyzePDF() {
//     if (!this.selectedFile) return;

//     const formData = new FormData();
//     formData.append('file', this.selectedFile);

//     const response = await fetch('https://TON_ENDPOINT_RUNPOD/upload', {
//       method: 'POST',
//       body: formData
//     });

//     const full = await response.json();
//     this.result = full.result;
//   }
  async analyzePDF() {
    if (!this.selectedFile) return;

    console.log("🔍 Simulation d'appel backend…");

    // Simulation manuelle d'un résultat de LLM
    this.result = {
        entreprise: "EDF",
        tva_intracommunautaire: "FR123456789",
        "SIRET/SIREN": "73282932000074",
        numero_facture_ou_piece: "FAC-2025-0042",
        date: "2025-06-27",
        montant_TTC: "249,60 €",
        montant_Hors_Taxe: "208,00 €",
        montant_TVA: "41,60 €"
    };
    }

  async analyzePDF_2() {
    if (!this.selectedFile) return;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    try {
        const response = await fetch('https://TON_ENDPOINT_RUNPOD/upload', {
        method: 'POST',
        body: formData
        });

        const full = await response.json();

        if (!response.ok) {
        throw new Error(full?.error || 'Erreur inconnue');
        }

        this.result = full.result;
        console.log("✅ Résultat reçu :", this.result);
    } catch (error) {
        console.error("❌ Erreur d'analyse :", error);
        this.result = null;
        alert("Erreur lors de l'analyse du PDF : " + error);
    }
    }

  highlight(champ: string) {
    this.highlightKey = champ;
  }

  clearHighlight() {
    this.highlightKey = '';
  }

  drawHighlight(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D) {
    ctx.strokeStyle = 'red';
    ctx.lineWidth = 2;
    ctx.strokeRect(100, 150, 200, 30); // Exemple fictif
  }
}

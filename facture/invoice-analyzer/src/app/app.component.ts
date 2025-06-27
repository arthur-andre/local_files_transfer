import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import * as pdfjsLib from 'pdfjs-dist';

(pdfjsLib as any).GlobalWorkerOptions.workerSrc =
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';

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
  private currentRenderTask: any = null;  // 👈 ici
  pdfDoc: any = null;
  ctx: CanvasRenderingContext2D | null = null;
  canvas: HTMLCanvasElement | null = null;
  pageRendered = false;
  positions: any = {};
  

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
        this.pdfDoc = await pdfjsLib.getDocument({ data: typedarray }).promise;
        const page = await this.pdfDoc.getPage(1);

        this.canvas = document.getElementById('pdfCanvas') as HTMLCanvasElement;
        this.ctx = this.canvas.getContext('2d');
        const viewport = page.getViewport({ scale: 1.5 });

        this.canvas.height = viewport.height;
        this.canvas.width = viewport.width;

        await page.render({ canvasContext: this.ctx!, viewport }).promise;
        this.pageRendered = true;
      };
      reader.readAsArrayBuffer(this.selectedFile);
    }
  }

  async analyzePDF() {
    if (!this.selectedFile) return;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData
      });

      const full = await response.json();

      if (!response.ok) {
        throw new Error(full?.error || 'Erreur inconnue');
      }

      this.result = full.result.result;
      this.positions = full.result.positions;
      console.log("✅ Résultat reçu :", this.result);
    } catch (error) {
      console.error("❌ Erreur d'analyse :", error);
      this.result = null;
      alert("Erreur lors de l'analyse du PDF : " + error);
    }
  }

  highlight(champ: string) {
    this.highlightKey = champ;

    if (!this.pageRendered || !this.ctx || !this.canvas || !this.positions?.[champ]) return;

    const scale = 1.5;
    const { x0, x1, top, bottom } = this.positions[champ];

    const x = x0 * scale;
    const y = top * scale;
    const width = (x1 - x0) * scale;
    const height = (bottom - top) * scale;

    this.pdfDoc.getPage(1).then((page: any) => {
        const viewport = page.getViewport({ scale });

        // Si un rendu précédent est actif, on l’annule
        if (this.currentRenderTask) {
        this.currentRenderTask.cancel();
        }

        // Nouveau rendu
        const renderTask = page.render({ canvasContext: this.ctx!, viewport });
        this.currentRenderTask = renderTask;

        renderTask.promise.then(() => {
        this.ctx!.fillStyle = 'rgba(216, 191, 216, 0.4)'; // Highlight
        this.ctx!.fillRect(x, y, width, height);
        }).catch((err: any) => {
        if (err?.name !== 'RenderingCancelledException') {
            console.error("Erreur de rendu PDF :", err);
        }
        });
    });
    }


  clearHighlight() {
    this.highlightKey = '';
    if (!this.pageRendered || !this.ctx || !this.canvas) return;

    this.pdfDoc.getPage(1).then((page: any) => {
      const viewport = page.getViewport({ scale: 1.5 });
      page.render({ canvasContext: this.ctx!, viewport });
    });
  }
}

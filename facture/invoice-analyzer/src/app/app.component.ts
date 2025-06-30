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

  pdfDoc: any = null;
  ctx: CanvasRenderingContext2D | null = null;
  canvas: HTMLCanvasElement | null = null;
  pageRendered = false;
  positions: Record<string, any> = {};
  private currentRenderTask: any = null;
  fixedHighlightKey: string = '';
  loading: boolean = false;

  readonly champsFixes: string[] = [
    "entreprise",
    "téléphone",
    "adresse",
    "tva_intracommunautaire",
    "SIRET/SIREN",
    "numero_facture_ou_piece",
    "date",
    "montant_HT",
    "montant_TVA",
    "montant_TTC"
  ];

  readonly champLabels: Record<string, string> = {
    entreprise: "🏢 Entreprise",
    téléphone: "📞 Téléphone",
    adresse: "📍 Adresse",
    tva_intracommunautaire: "🧾 TVA intracommunautaire",
    "SIRET/SIREN": "🆔 SIRET / SIREN",
    numero_facture_ou_piece: "📄 Numéro de facture",
    date: "📅 Date",
    montant_HT: "💰 Montant HT",
    montant_TVA: "💸 Montant TVA",
    montant_TTC: "💵 Montant TTC"
  };

  readonly scale = 0.95;

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0] || null;

    if (this.selectedFile) {
      this.pageRendered = false;
      this.result = null;
      this.positions = {};
      this.highlightKey = '';
      this.fixedHighlightKey = '';


      const reader = new FileReader();
      reader.onload = async () => {
        const typedarray = new Uint8Array(reader.result as ArrayBuffer);
        this.pdfDoc = await pdfjsLib.getDocument({ data: typedarray }).promise;
        const page = await this.pdfDoc.getPage(1);

        this.canvas = document.getElementById('pdfCanvas') as HTMLCanvasElement;
        this.ctx = this.canvas.getContext('2d');

        const viewport = page.getViewport({ scale: this.scale });

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
    this.loading = true;

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
      console.log("📍 Positions des champs :", this.positions);
    } catch (error) {
      console.error("❌ Erreur d'analyse :", error);
      this.result = null;
      alert("Erreur lors de l'analyse du PDF : " + error);
    }
    this.loading = false;
    this.highlightKey = ''; // Réinitialise la clé de surbrillance après l'analyse
  }

  highlight(champ: string) {
    if (this.fixedHighlightKey) return;
    this.highlightKey = champ;

    if (!this.pageRendered || !this.ctx || !this.canvas || !this.positions?.[champ]) return;

    const { x0, x1, top, bottom } = this.positions[champ];

    const x = x0 * this.scale;
    const y = top * this.scale;
    const width = (x1 - x0) * this.scale;
    const height = (bottom - top) * this.scale;

    this.pdfDoc.getPage(1).then((page: any) => {
      const viewport = page.getViewport({ scale: this.scale });

      if (this.currentRenderTask) {
        this.currentRenderTask.cancel();
      }

      const renderTask = page.render({ canvasContext: this.ctx!, viewport });
      this.currentRenderTask = renderTask;

      renderTask.promise.then(() => {
        this.ctx!.fillStyle = 'rgba(255, 99, 132, 0.35)'; // Rouge doux semi-transparent
        console.log(`🔍 Mise en évidence du champ "${champ}" à (${x}, ${y}) avec une taille de (${width}x${height})`);
        this.ctx!.fillRect(x, y, width, height);
      }).catch((err: any) => {
        if (err?.name !== 'RenderingCancelledException') {
          console.error("Erreur de rendu PDF :", err);
        }
      });
    });
  }

  private _drawHighlightFor(champ: string) {
    if (!this.pageRendered || !this.ctx || !this.canvas || !this.positions?.[champ]) return;

    const { x0, x1, top, bottom } = this.positions[champ];

    const x = x0 * this.scale;
    const y = top * this.scale;
    const width = (x1 - x0) * this.scale;
    const height = (bottom - top) * this.scale;

    this.pdfDoc.getPage(1).then((page: any) => {
      const viewport = page.getViewport({ scale: this.scale });

      if (this.currentRenderTask) this.currentRenderTask.cancel();

      const renderTask = page.render({ canvasContext: this.ctx!, viewport });
      this.currentRenderTask = renderTask;

      renderTask.promise.then(() => {
        this.ctx!.fillStyle = 'rgba(255, 230, 100, 0.4)';
        this.ctx!.fillRect(x, y, width, height);
      }).catch((err: any) => {
        if (err?.name !== 'RenderingCancelledException') {
          console.error("Erreur de rendu PDF :", err);
        }
      });
    });
  }

  private _redrawPage() {
    this.pdfDoc.getPage(1).then((page: any) => {
      const viewport = page.getViewport({ scale: this.scale });
      page.render({ canvasContext: this.ctx!, viewport });
    });
  }


  toggleFixedHighlight(champ: string) {
    if (this.fixedHighlightKey === champ) {
      // Désactive
      this.fixedHighlightKey = '';
      this.highlightKey = '';
      this._redrawPage();
    } else {
      // Active
      this.fixedHighlightKey = champ;
      this.highlightKey = champ;
      this._drawHighlightFor(champ);
    }
  }

  clearHighlight() {
    if (this.fixedHighlightKey) return;
    this.highlightKey = '';
    if (!this.pageRendered || !this.ctx || !this.canvas) return;

    this.pdfDoc.getPage(1).then((page: any) => {
      const viewport = page.getViewport({ scale: this.scale });
      page.render({ canvasContext: this.ctx!, viewport });
    });
  }
}
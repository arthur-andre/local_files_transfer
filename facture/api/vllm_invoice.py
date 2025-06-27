import os
import pdfplumber
import warnings
import requests
import re
import argparse
import time
import json

warnings.filterwarnings("ignore", category=UserWarning, module="pdfplumber")



def filtrer_reponse_json(reponse):
    """
    Extrait le premier JSON (objet ou liste) valide d'une chaîne, même si le bloc ```json est mal fermé.
    """
    # Supprime les éventuels ```json et ``` non fermés proprement
    reponse = re.sub(r"```(?:json)?", "", reponse).strip()

    # Recherche toutes les sous-chaînes commençant par { ou [
    candidats = re.findall(r'({[\s\S]*?}|\[[\s\S]*?\])', reponse)

    for bloc in candidats:
        try:
            return json.loads(bloc)
        except json.JSONDecodeError:
            continue

    return None


def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file"""
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n\n"
    return full_text

def enlever_caracteres_speciaux(texte):
    """Nettoyage des caractères spéciaux"""
    pattern = r'[^a-zA-Z0-9\s€$.,:;!?%()\-_/]'
    return re.sub(pattern, '', texte)

def convert_to_docling(text):
    """Structure DOCLING"""
    lines = text.split("\n")
    docling = {"header": [], "body": [], "footer": []}
    section = "header"
    for line in lines:
        if "Total" in line or "TVA" in line:
            section = "footer"
        elif any(keyword in line for keyword in ["Article", "Quantité", "Prix"]):
            section = "body"
        docling[section].append(line.strip())
    return docling

def docling_to_markdown(docling):
    """Convertit la structure DOCLING en prompt Markdown adapté"""
    markdown = (
        "# Voici une facture. Réponds uniquement avec un JSON strictement conforme au format ci-dessous, sans aucun mot en dehors du JSON. Si une information est manquante, mets la valeur à null.\n\n"
        "FORMAT ATTENDU :\n"
        "{{\n"
        "  \"entreprise\": None \"\",\n"
        "  \"tva_intracommunautaire\": None\"\",\n"
        "  \"SIRET/SIREN\": None\"\",\n"
        "  \"numero_facture_ou_piece\": None\"\",\n"
        "  \"date\": None\"\",\n"
        "  \"montant_TTC \": None\"\",\n"
        "  \"montant_Hors_Taxe \": None\"\",\n"
        "  \"montant_TVA\": None\"\"\n"
        "}}\n\n"
        "Voici le contenu OCR extrait :\n\n"
    )
    if docling["header"]:
        markdown += "## En-tête\n\n" + "\n".join(docling["header"]) + "\n\n"

    if docling["body"]:
        markdown += (
            "### Détails des articles\n\n"
            "| Article | Quantité | Prix Unitaire | Total |\n"
            "|---------|----------|----------------|-------|\n"
        )
        for line in docling["body"]:
            parts = line.split()
            if len(parts) >= 4:
                markdown += f"| {' '.join(parts[:-3])} | {parts[-3]} | {parts[-2]} | {parts[-1]} |\n"
        markdown += "\n"

    if docling["footer"]:
        markdown += "### Pied de page\n\n" + "\n".join(docling["footer"]) + "\n\n"

    return markdown

def query_vllm(model, prompt):
    """Appel VLLM local via /v1/completions"""
    url = "http://127.0.0.1:8000/v1/completions"
    headers = {"Content-Type": "application/json"}

    data = {
        "model": model,
        "prompt": prompt,
        "max_tokens": 512,
        "temperature": 0
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["text"].strip()

def main(pdf_path, model="/workspace/models/mistral-7b-instruct"):
    text = extract_text_from_pdf(pdf_path)
    text = enlever_caracteres_speciaux(text)
    docling = convert_to_docling(text)
    markdown = docling_to_markdown(docling)

    print("Prompt envoyé au modèle :\n", markdown)

    start_time = time.perf_counter()
    response = query_vllm(model, markdown)
    elapsed_time = time.perf_counter() - start_time

    print("\nRéponse du LLM :\n", response)
    print(f"\nTemps de réponse du modèle : {elapsed_time:.3f} secondes")

    return filtrer_reponse_json(response)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Processus d'extraction de données depuis une facture PDF.")
    parser.add_argument("pdf_path", type=str, help="Chemin vers le fichier PDF")
    parser.add_argument("--model", type=str, default="/workspace/models/mistral-7b-instruct", help="Chemin vers le modèle local")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Erreur : le fichier {args.pdf_path} n'existe pas.")
        exit(1)

    main(args.pdf_path, args.model)
import os
import pdfplumber
import warnings
import requests
import re
import argparse
import time

warnings.filterwarnings("ignore", category=UserWarning, module="pdfplumber")

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file"""
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n\n"
    return full_text

def enlever_caracteres_speciaux(texte):
    """Nettoyage des caract  res sp  ciaux"""
    pattern = r'[^a-zA-Z0-9\s ^b $.,:;!?%()\-_/                              ]'
    texte_nettoye = re.sub(pattern, '', texte)
    return texte_nettoye

def convert_to_docling(text):
    """Structure DOCLING"""
    lines = text.split("\n")
    docling = {"header": [], "body": [], "footer": []}
    section = "header"
    for line in lines:
        if "Total" in line or "TVA" in line:
            section = "footer"
        elif any(keyword in line for keyword in ["Article", "Quantit  ", "Prix"]):
            section = "body"
        docling[section].append(line.strip())
    return docling

def docling_to_markdown(docling):
    """ Converts DOCLING structure to Markdown adapted to new extraction fields """
    markdown = (
        "# Voici une facture, R  ponds moi uniquement avec cette structure json :\n"
        "{{\n"
        "  \"entreprise\": None \"\",\n"
        "  \"tva_intracommunautaire\": None\"\",\n"
        "  \"SIRET/SIREN\": None\"\",\n"
        "  \"numero_facture_ou_piece\": None\"\",\n"
        "  \"date\": None\"\",\n"
        "  \"montant_TTC \": None\"\",\n"
        "  \"montant_TVA\": None\"\"\n"
        "}}\n\n"
        "Voici le contenu OCR extrait :\n\n"
    )
    if docling["header"]:
        markdown += "## En-t  te\n\n" + "\n".join(docling["header"]) + "\n\n"

    if docling["body"]:
        markdown += "### D  tails des articles\n\n" \
                    "| Article | Quantit   | Prix Unitaire | Total |\n" \
                    "|---------|----------|--------------|-------|\n"
        for line in docling["body"]:
            parts = line.split()
            if len(parts) >= 4:
                markdown += f"| {' '.join(parts[:-3])} | {parts[-3]} | {parts[-2]} | {parts[-1]} |\n"
        markdown += "\n"

    if docling["footer"]:
        markdown += "### Pied de page\n\n" + "\n".join(docling["footer"]) + "\n\n"

    return markdown

def query_vllm(model, prompt):
    """Appel VLLM local en mode /v1/completions"""
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
    result = response.json()
    return result["choices"][0]["text"].strip()


def main(pdf_path, model="/workspace/models/mistral-7b-instruct"):
    text = extract_text_from_pdf(pdf_path)
    text = enlever_caracteres_speciaux(text)
    docling = convert_to_docling(text)
    markdown = docling_to_markdown(docling)

    print("Prompt envoy   au mod  le :\n", markdown)

    start_time = time.perf_counter()
    response = query_vllm(model, markdown)
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time

    print("\nLLM Response:\n", response)
    print(f"\nTemps de r  ponse du mod  le : {elapsed_time:.3f} secondes")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a PDF file and extract structured data.")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to process")
    parser.add_argument("--model", type=str, default="/workspace/models/mistral-7b-instruct", help="LLM model to use")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Error: The file {args.pdf_path} does not exist.")
        exit(1)

    main(args.pdf_path, args.model)

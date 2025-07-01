import os
import pdfplumber
import warnings
import requests
import re
import argparse
import json

warnings.filterwarnings("ignore", category=UserWarning, module="pdfplumber")

def extract_text_from_pdf(pdf_path):
    """ Extracts text from a PDF file """
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n\n"
    return full_text

def enlever_caracteres_speciaux(texte):
    """
    Enlève les caractères spéciaux d'un texte en conservant les lettres, chiffres et espaces.
    """
    pattern = r'[^a-zA-Z0-9\s€$.,:;!?%()\-_/éèàùçâêîôûëïüöñ]'
    texte_nettoye = re.sub(pattern, '', texte)
    return texte_nettoye

def convert_to_docling(text):
    """ Converts raw text to a DOCLING structure """
    lines = text.split("\n")
    docling = {
        "header": [],
        "body": [],
        "footer": []
    }

    section = "header"

    for line in lines:
        if "Total" in line or "TVA" in line:
            section = "footer"
        elif any(keyword in line for keyword in ["Article", "Quantité", "Prix"]):
            section = "body"
        docling[section].append(line.strip())

    return docling

def docling_to_markdown(docling):
    """ Converts DOCLING structure to Markdown """
    markdown = "# Voici une facture, Réponds moi avec cette structure :\n{{\n    \"entreprise\": \"\",\n    \"numero_facture_ou_piece\": \"\",\n    \"date\": \"\",\n    \"montant_TTC \": \"\",\n  \"montant_TVA\": \"\",\n  \"nom_client\": \"\",\n  \"code_client\": \"\"\n}}\n\n Voici le contenu OCR extrait :\n\n"

    if docling["header"]:
        markdown += "## En-tête\n\n" + "\n".join(docling["header"]) + "\n\n"

    if docling["body"]:
        markdown += "### Détails des articles\n\n"
        markdown += "| Article | Quantité | Prix Unitaire | Total |\n"
        markdown += "|---------|----------|--------------|-------|\n"
        for line in docling["body"]:
            parts = line.split()
            if len(parts) >= 4:
                markdown += f"| {' '.join(parts[:-3])} | {parts[-3]} | {parts[-2]} | {parts[-1]} |\n"
        markdown += "\n"

    if docling["footer"]:
        markdown += "### Pied de page\n\n" + "\n".join(docling["footer"]) + "\n\n"

    return markdown

def query_vllm(model, prompt):
    url = "http://127.0.0.1:8000/v1/chat/completions"  # vLLM API local
    headers = {"Content-Type": "application/json"}

    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Tu es un expert en extraction de données de factures OCR."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 512,
        "temperature": 0
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"]

def main(pdf_path, model='mistralai/Mistral-7B-Instruct-v0.2'):
    text = extract_text_from_pdf(pdf_path)
    text = enlever_caracteres_speciaux(text)
    docling = convert_to_docling(text)
    markdown = docling_to_markdown(docling)

    print("Prompt envoyé au modèle :\n")
    print(markdown)
    
    response = query_vllm(model, markdown)
    print("\nLLM Response:\n", response)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a PDF file and extract structured data.")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to process")
    parser.add_argument("--model", type=str, default="mistralai/Mistral-7B-Instruct-v0.2", help="LLM model to use (default: Mistral-7B-Instruct-v0.2)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: The file {args.pdf_path} does not exist.")
        exit(1)
    
    main(args.pdf_path, args.model)
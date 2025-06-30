import os
import pdfplumber
import warnings
import requests
import re
import argparse
import time
import json

warnings.filterwarnings("ignore", category=UserWarning, module="pdfplumber")



def nettoyer_montant(val):
    """
    Nettoie un montant en supprimant les caractères non numériques sauf ',' et '.'.
    Convertit une chaîne du type '2 100,00 €' ou '350,00' en float.
    """
    if not isinstance(val, str):
        return None
    # Garde uniquement chiffres, virgule, point
    val = re.sub(r"[^\d,\.]", "", val)
    # Si le format est européen avec virgule comme séparateur décimal
    if val.count(',') == 1 and (val.count('.') == 0 or val.find(',') > val.find('.')):
        val = val.replace(',', '.')
    try:
        return float(val)
    except ValueError:
        return None

def filtrer_reponse_json(reponse):
    """
    Extrait le premier JSON (objet ou liste) valide d'une chaîne, même si le bloc ```json est mal fermé.
    Nettoie les montants TTC et TVA si présents, et ajoute montant_HT = montant_TTC - montant_TVA si possible.
    """
    reponse = re.sub(r"```(?:json)?", "", reponse).strip()
    candidats = re.findall(r'({[\s\S]*?}|\[[\s\S]*?\])', reponse)

    for bloc in candidats:
        try:
            data = json.loads(bloc)

            if isinstance(data, dict):
                ttc = nettoyer_montant(data.get("montant_TTC", None))
                data["montant_TTC"] = ttc  # Assure que c'est un float ou None
                tva = nettoyer_montant(data.get("montant_TVA", None))
                data["montant_TVA"] = tva  # Assure que c'est un float ou None
                if ttc is not None and tva is not None:
                    data["montant_HT"] = round(ttc - tva, 2)
                else:
                    data["montant_HT"] = None

            return data
        except json.JSONDecodeError:
            continue

    return None

def trouver_positions_champs(pdf_path, champs_dict):
    """
    Pour chaque champ du dictionnaire (ex: {"entreprise": "EDF"}), cherche la position du texte dans le PDF.
    Retourne un dictionnaire : champ → position sur la première page (x0, x1, top, bottom).
    """
    positions = {}

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]  # pour aller plus loin : boucle sur pages

        words = page.extract_words()
        for key, valeur in champs_dict.items():
            if not valeur:
                continue

            valeur_simplifiee = str(valeur).lower().strip().split()[0] if valeur else ""
            print(f"Recherche de '{valeur_simplifiee}' pour le champ '{key}'")

            for mot in words:
                mot_simplifie = mot['text'].lower().strip()
                print("mot_simplifie:", mot_simplifie)
                if valeur_simplifiee in mot_simplifie:
                    positions[key] = {
                        "x0": mot["x0"],
                        "x1": mot["x1"],
                        "top": mot["top"],
                        "bottom": mot["bottom"]
                    }
                    break  # premier match trouvé = suffit

    return positions


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
        "  \"téléphone\": None \"\",\n"
        "  \"adresse\": None \"\",\n"
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
    url = "http://127.0.0.1:8010/v1/completions"
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
    champs = filtrer_reponse_json(response)
    coords = trouver_positions_champs(pdf_path, champs)

    return {
        "result": champs,
        "positions": coords
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Processus d'extraction de données depuis une facture PDF.")
    parser.add_argument("--pdf_path", type=str, default="/workspace/local_files_transfer/facture_client.pdf", help="Chemin vers le fichier PDF")
    parser.add_argument("--model", type=str, default="/workspace/models/mistral-7b-instruct", help="Chemin vers le modèle local")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Erreur : le fichier {args.pdf_path} n'existe pas.")
        exit(1)

    main(args.pdf_path, args.model)
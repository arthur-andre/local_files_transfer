import os
import pdfplumber
import warnings
import requests
import re
import argparse
import time
import json
from decimal import Decimal, InvalidOperation
from collections import defaultdict

warnings.filterwarnings("ignore", category=UserWarning, module="pdfplumber")



def nettoyer_montant(val):
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val)), '.'

    if not isinstance(val, str):
        return None, None

    val_nettoye = re.sub(r"[^\d,\.]", "", val)

    if val_nettoye.count(',') == 1 and (val_nettoye.count('.') == 0 or val_nettoye.find(',') > val_nettoye.find('.')):
        val_converti = val_nettoye.replace(',', '.')
        separateur = ','
    else:
        val_converti = val_nettoye
        separateur = '.'

    try:
        return Decimal(val_converti), separateur
    except InvalidOperation:
        print(f"[WARNING] Impossible de parser '{val}' → '{val_converti}'")
        return None, None

def formater_montant(val_decimal, separateur):
    if val_decimal is None or separateur not in {',', '.'}:
        return None
    s = str(val_decimal)  # préserve les décimales exactes, même inutiles
    s.replace('.', separateur)
    print(f"[DEBUG] Formattage du montant '{s}' avec séparateur '{separateur}'")
    return s 

def filtrer_reponse_json(reponse):
    reponse = re.sub(r"```(?:json)?", "", reponse).strip()
    candidats = re.findall(r'({[\s\S]*?}|\[[\s\S]*?\])', reponse)

    for bloc in candidats:
        try:
            data = json.loads(bloc)

            if isinstance(data, dict):
                montant_TTC, sep_TTC = nettoyer_montant(data.get("montant_TTC", None))
                montant_TVA, sep_TVA = nettoyer_montant(data.get("montant_TVA", None))
                separateur = sep_TTC or sep_TVA

                if montant_TTC is not None:
                    data["montant_TTC"] = formater_montant(montant_TTC, separateur)
                if montant_TVA is not None:
                    data["montant_TVA"] = formater_montant(montant_TVA, separateur)

                if montant_TTC is not None and montant_TVA is not None:
                    montant_HT = montant_TTC - montant_TVA
                    data["montant_HT"] = formater_montant(montant_HT, separateur)
                else:
                    data["montant_HT"] = None

            return data
        except json.JSONDecodeError:
            print(f"Erreur de décodage JSON pour le bloc : {bloc}")
            continue

    return None

def generer_variantes_montant(val):
    if not isinstance(val, str):
        return []

    val = val.strip().replace("€", "").replace(" ", "")
    variantes = set()

    try:
        d = Decimal(val.replace(",", "."))
        str_dot = str(d)
        str_comma = str_dot.replace(".", ",")

        variantes.update([str_dot, str_comma])

        int_part, _, frac_part = str_dot.partition(".")
        grouped = "{:,}".format(int(int_part)).replace(",", " ")
        if frac_part:
            variantes.update([f"{grouped},{frac_part}", f"{grouped}.{frac_part}"])
        else:
            variantes.add(grouped)

        if d == d.to_integral():
            variantes.add(str(int(d)))
    except InvalidOperation:
        variantes.add(val)

    return [v.replace(" ", "") for v in variantes]  # standardisation

def get_lines(words, y_tolerance=3):
    lignes = defaultdict(list)
    for mot in words:
        top_key = round(mot["top"] / y_tolerance) * y_tolerance
        lignes[top_key].append(mot)
    return [sorted(l, key=lambda w: w["x0"]) for l in lignes.values()]

def trouver_positions_champs(pdf_path, champs_dict):
    positions = {}

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        lignes = get_lines(words)

        for key, val in champs_dict.items():
            if not val:
                continue

            if key.startswith("montant_"):
                variantes = generer_variantes_montant(val)
            else:
                variantes = [val.strip().lower().replace(" ", "")]

            print(f"[{key}] Variantes recherchées : {variantes}")
            positions[key] = []

            for ligne in lignes:
                n = len(ligne)
                # fenêtre glissante de 1 à 5 mots
                for i in range(n):
                    for j in range(i+1, min(i+6, n+1)):
                        mots_window = ligne[i:j]
                        texte_concat = "".join([w["text"] for w in mots_window]).lower().replace(" ", "")
                        if texte_concat in variantes:
                            x0 = mots_window[0]["x0"]
                            x1 = mots_window[-1]["x1"]
                            top = min(w["top"] for w in mots_window)
                            bottom = max(w["bottom"] for w in mots_window)
                            positions[key].append({
                                "x0": x0,
                                "x1": x1,
                                "top": top,
                                "bottom": bottom
                            })
                            break  # trouvé, on sort cette fenêtre

    return positions

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file"""
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n\n"
    return full_text

def enlever_caracteres_speciaux(texte):
    """Nettoyage des caractères spéciaux, en conservant les accents"""
    pattern = r"[^a-zA-Z0-9\s€$.,:;!?%()\-_/àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ]"
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
        "# Voici une facture. Réponds uniquement avec un JSON strictement conforme au format ci-dessous, sans aucun mot en dehors du JSON et avec exactement les bons champs. Si une information est manquante, mets la valeur à null.\n\n"
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
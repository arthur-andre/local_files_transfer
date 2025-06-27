FROM python:3.10-slim

# Dossiers utiles
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Dépendances système minimales
RUN apt update && apt install -y gcc libpoppler-cpp-dev pkg-config python3-dev

# Installation des librairies Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ajout du code
COPY . .

# Variables d'environnement pour les caches
ENV VLLM_CACHE_DIR=/workspace/vllm_cache \
    TORCH_HOME=/workspace/torch_cache \
    HF_HOME=/workspace/hf_cache \
    XDG_CACHE_HOME=/workspace/xdg_cache

# Lancement de l'API avec Uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

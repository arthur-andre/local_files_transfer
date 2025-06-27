from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import shutil
import os
import uvicorn
from vllm_invoice import main as vllm_main

app = FastAPI()

# Autoriser CORS pour ton frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔒 en prod, utilise ["http://localhost:4200"] par exemple
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_invoice(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        print(f"[INFO] Fichier reçu : {file.filename}")
        os.environ["MODEL_PATH"] = "/workspace/models/mistral-7b-instruct"
        response = vllm_main(tmp_path)

        os.remove(tmp_path)

        return JSONResponse(content={"success": True, "result": response})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
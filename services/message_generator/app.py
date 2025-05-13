# services/message_generator/app.py

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from langchain import PromptTemplate

# Importa moduli cache
from .cache_utils import get_cached_message, cache_message, get_cache_stats

# --------------- Configuration -----------------
PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()   # . "groq"
BASE_URL = os.getenv("OPENAI_API_BASE") or None          # https://api.groq.com/openai/v1
API_KEY  = os.getenv("OPENAI_API_KEY")                   # 

if PROVIDER in {"openai", "groq", "together", "fireworks"} and not API_KEY:
    raise RuntimeError("OPENAI_API_KEY mancante per il provider scelto")

# --------------- Prompt Template -----------------
PROMPT_TMPL = """Sei un sistema di advertising che crea un messaggio conciso e coinvolgente.
Utente:
- Età: {age}
- Professione: {profession}
- Interessi: {interests}

Negozio:
- Nome: {name}
- Categoria: {category}
- Descrizione aggiuntiva: {description}

Condizioni:
- L'utente è a pochi metri dal negozio.
- Il messaggio deve essere breve (max 30 parole) e invogliare l'utente a fermarsi.

Genera il messaggio in italiano:"""
template = PromptTemplate(
    input_variables=["age", "profession", "interests", "name", "category", "description"],
    template=PROMPT_TMPL,
)

# --------------- LLM Invocation -----------------
def call_llm(prompt: str) -> str:
    if PROVIDER in {"openai", "groq", "together", "fireworks"}:
        # modelli di produzione Groq Cloud supportati: gemma2-9b-it
        model_name = "gpt-4o-mini" if PROVIDER == "openai" else "gemma2-9b-it"
        llm = ChatOpenAI(
            model=model_name,
            temperature=0.7,
            openai_api_key=API_KEY,
            openai_api_base=BASE_URL,
        )
        return llm([HumanMessage(content=prompt)]).content.strip()

    raise RuntimeError(f"Provider LLM non supportato: {PROVIDER}")

# --------------- FastAPI App -----------------
class User(BaseModel):
    age: int
    profession: str
    interests: str

class POI(BaseModel):
    name: str
    category: str
    description: str = ""

class GenerateRequest(BaseModel):
    user: User
    poi: POI

class GenerateResponse(BaseModel):
    message: str
    cached: bool = False

app = FastAPI(title="NearYou Message Generator")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/cache/stats")
async def cache_stats():
    """Endopoint per verificare statistiche cache."""
    return get_cache_stats()

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    try:
        # Converti oggetti Pydantic in dict per le funzioni cache
        user_params = req.user.dict()
        poi_params = req.poi.dict()
        
        # Controlla cache
        cached_message = get_cached_message(user_params, poi_params)
        if cached_message:
            return GenerateResponse(message=cached_message, cached=True)
        
        # Se non in cache, genera nuovo messaggio
        prompt_text = template.format(
            age=req.user.age,
            profession=req.user.profession,
            interests=req.user.interests,
            name=req.poi.name,
            category=req.poi.category,
            description=req.poi.description,
        )
        result = call_llm(prompt_text)
        
        # Salva in cache
        cache_message(user_params, poi_params, result)
        
        return GenerateResponse(message=result, cached=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
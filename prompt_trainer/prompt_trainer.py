import os
import requests
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from passlib.context import CryptContext
from dotenv import load_dotenv
import sys
sys.path.append('..')

# Load environment variables from the .env file
load_dotenv()
from auth_service import verify_user_and_get_role

# --- CONFIGURATION ---
DB_URL = os.getenv("DB_URL")

# Fetching Azure configurations from environment
GPT4_CHAT_URL = os.getenv("GPT4_CHAT_URL")
GPT4_API_KEY = os.getenv("GPT4_API_KEY")

# Whisper configs (Make sure to add these to your .env)
WHISPER_URL = os.getenv("WHISPER_URL")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

class LoginRequest(BaseModel):
    username: str
    password: str

# --- DB POOL ---
pool = ConnectionPool(conninfo=DB_URL, min_size=1, max_size=10, open=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HELPER FUNCTIONS ---
def verify_password(plain_password, hashed_password):
    try:
        if not plain_password or not hashed_password: return False
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def call_azure_whisper(audio_bytes, filename, content_type):
    if not WHISPER_URL or not WHISPER_API_KEY:
        raise Exception("Whisper URL or API Key is missing from environment variables.")
        
    headers = { "api-key": WHISPER_API_KEY }
    files = { "file": (filename, audio_bytes, content_type) }
    response = requests.post(WHISPER_URL, headers=headers, files=files)
    if response.status_code != 200:
        raise Exception(f"Whisper API Error: {response.text}")
    return response.json()["text"]

def call_azure_chat(messages):
    if not GPT4_CHAT_URL or not GPT4_API_KEY:
        raise Exception("GPT-4 Chat URL or API Key is missing from environment variables.")
        
    headers = { "api-key": GPT4_API_KEY, "Content-Type": "application/json" }
    payload = { "messages": messages, "temperature": 0.7, "max_tokens": 16000 }
    response = requests.post(GPT4_CHAT_URL, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Chat API Error: {response.text}")
    return response.json()["choices"][0]["message"]["content"]

def save_new_version(org_id: int, product_id: int, text: str):
    """Calculates max version PER PRODUCT and inserts new row."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT MAX(version) as max_ver FROM multiturn_chat.prompts WHERE product_id = %s", (product_id,))
            result = cur.fetchone()
            next_ver = (result['max_ver'] + 1) if result and result['max_ver'] else 1
            
            cur.execute("""
                INSERT INTO multiturn_chat.prompts 
                (org_id, product_id, prompt_text, version, is_production)
                VALUES (%s, %s, %s, %s, FALSE)
                RETURNING id, version
            """, (org_id, product_id, text, next_ver))
            
            new_row = cur.fetchone()
            conn.commit()
            return new_row

# --- ROUTES (ALL PREFIXED WITH /prompts) ---

@app.post("/prompts/login")
def login(creds: LoginRequest):
    is_valid, user_data = verify_user_and_get_role(creds.username, creds.password, pool)

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check admin permission
    if not user_data['isadmin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    return {
        "message": "Login successful",
        "org_id": user_data['org'],
        "username": user_data['username'],
        "isadmin": True
    }

@app.get("/prompts/orgs/{org_id}/products")
def get_products(org_id: int):
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT id, product_name 
                FROM multiturn_chat.products 
                WHERE org_id = %s 
                ORDER BY product_name ASC
            """, (org_id,))
            return cur.fetchall()

@app.get("/prompts/products/{product_id}/prompts")
def get_product_prompts(product_id: int):
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT id, org_id, product_id, prompt_text, version, is_production, created_at 
                FROM multiturn_chat.prompts 
                WHERE product_id = %s 
                ORDER BY version DESC
            """, (product_id,))
            return cur.fetchall()

@app.post("/prompts/products/{product_id}/promote/{prompt_id}")
def set_production_prompt(product_id: int, prompt_id: int):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE multiturn_chat.prompts SET is_production = FALSE WHERE product_id = %s", (product_id,))
            cur.execute("UPDATE multiturn_chat.prompts SET is_production = TRUE WHERE id = %s", (prompt_id,))
            if cur.rowcount == 0:
                conn.rollback()
                raise HTTPException(status_code=404, detail="Prompt not found")
            conn.commit()
    return {"message": "Updated production prompt"}

@app.post("/prompts/products/{product_id}/manual-update")
def manual_update(product_id: int, org_id: int = Form(...), prompt_text: str = Form(...)):
    save_new_version(org_id, product_id, prompt_text)
    return {"message": "Saved"}

@app.post("/prompts/products/{product_id}/voice-update")
async def voice_update(
    product_id: int,
    org_id: int = Form(...),
    file: UploadFile = File(...), 
    current_prompt_id: int = Form(...)
):
    try:
        audio_content = await file.read()
        user_instruction = call_azure_whisper(audio_content, file.filename, file.content_type)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {str(e)}")

    old_text = ""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT prompt_text FROM multiturn_chat.prompts WHERE id = %s", (current_prompt_id,))
            row = cur.fetchone()
            if not row: raise HTTPException(status_code=404, detail="Base prompt not found")
            old_text = row[0]

    messages = [
        {"role": "system", "content": "You are an expert Prompt Engineer. Update the prompt based on the user's voice instructions. Output only the new prompt text."},
        {"role": "user", "content": f"Existing Prompt: {old_text}\nUser Instructions: {user_instruction}"}
    ]

    try:
        new_prompt_text = call_azure_chat(messages)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM processing failed: {str(e)}")

    new_version_data = save_new_version(org_id, product_id, new_prompt_text)

    return {
        "transcription": user_instruction,
        "new_prompt": new_prompt_text,
        "version": new_version_data['version']
    }
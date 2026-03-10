import os
import json
import re
import psycopg
from psycopg_pool import ConnectionPool
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AzureOpenAI
import secrets
from passlib.context import CryptContext
import asyncio
import websockets
from concurrent.futures import ThreadPoolExecutor
from auth_service import verify_user_and_get_role
from dotenv import load_dotenv  # Added missing import for load_dotenv

# --- Azure Imports ---
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

# --- NEW: AWS Imports ---
import boto3
from botocore.credentials import Credentials
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from botocore.exceptions import ClientError

app = FastAPI()
rag_router = APIRouter(prefix="/rag", tags=["RAG"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# CONFIGURATION
# ==========================================

# Load environment variables from the .env file
load_dotenv()

# --- Configuration loaded from Environment Variables ---
STORAGE_ACCOUNT_NAME = os.getenv("STORAGE_ACCOUNT_NAME")
STORAGE_ACCOUNT_KEY = os.getenv("STORAGE_ACCOUNT_KEY")

AZURE_OPENAI_ENDPOINT_REALTIME = os.getenv("AZURE_OPENAI_ENDPOINT_REALTIME")
AZURE_OPENAI_ENDPOINT_REALTIME_KEY = os.getenv("AZURE_OPENAI_ENDPOINT_REALTIME_KEY")

SEARCH_SERVICE_ENDPOINT = os.getenv("SEARCH_SERVICE_ENDPOINT")
SEARCH_ADMIN_KEY = os.getenv("SEARCH_ADMIN_KEY")

AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")
AOAI_KEY = os.getenv("AOAI_KEY")
EMBEDDING_DEPLOYMENT = os.getenv("EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

DB_URL = os.getenv("DB_URL")

GPT4_CHAT_URL = os.getenv("GPT4_CHAT_URL")
GPT4_API_KEY = os.getenv("GPT4_API_KEY")

# --- NEW: AWS Configuration ---
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY =  os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY") # Fixed: missing closing parenthesis and quote
AWS_OPENSEARCH_ENDPOINT = os.getenv("AWS_OPENSEARCH_ENDPOINT")
AWS_EMBEDDING_MODEL = os.getenv("AWS_EMBEDDING_MODEL")
AWS_LLM_MODEL = os.getenv("AWS_LLM_MODEL")

# Initialize AWS Clients with explicit credentials
s3_client = boto3.client(
    's3', 
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

bedrock_client = boto3.client(
    'bedrock-runtime', 
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

# --- Database Connection ---
pool = ConnectionPool(conninfo=DB_URL, min_size=1, max_size=10) # Fixed: removed redundant db_url assignment
executor = ThreadPoolExecutor(max_workers=3)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# ==========================================
# MODELS
# ==========================================
class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    message: str

class LoginRequest(BaseModel):
    username: str
    password: str

# ==========================================
# DATABASE HELPERS
# ==========================================

def get_db_connection():
    return pool.connection()

def verify_user_credentials(username, password):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM multiturn_chat.users WHERE username = %s", (username,))
            result = cur.fetchone()
            if result:
                return pwd_context.verify(password, result[0])
    return False

def get_user_org(username):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT org FROM multiturn_chat.users WHERE username = %s", (username,))
            result = cur.fetchone()
            return result[0] if result else None
        
def get_user_profile(username):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT profile FROM multiturn_chat.users WHERE username = %s", (username,))
            result = cur.fetchone()
            return result[0] if result else None

def get_org_config(org_id):
    """Fetches organization routing details including cloud provider."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT search_index_name, storage_container, cloud_provider 
                FROM multiturn_chat.organizations 
                WHERE id = %s
            """, (org_id,))
            result = cur.fetchone()
            if result:
                return {
                    "index_name": result[0],
                    "storage_container": result[1],
                    "cloud_provider": (result[2] or "azure").lower()
                }
            return None

def get_chat_history(session_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role, content 
                FROM multiturn_chat.conversation_turns 
                WHERE session_id = %s 
                ORDER BY created_at ASC
            """, (session_id,))
            return cur.fetchall()

def save_turn(session_id, role, content, artifacts=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO multiturn_chat.conversation_turns (session_id, role, content, artifacts)
                VALUES (%s, %s, %s, %s)
            """, (session_id, role, content, json.dumps(artifacts) if artifacts else '{}'))
        conn.commit()

def save_conversation_data(session_id, org_id, data_type, json_data, product_name=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO multiturn_chat.conversation_data 
                (session_id, org_id, product_name, data_type, data_payload)
                VALUES (%s, %s, %s, %s, %s)
            """, (session_id, org_id, product_name, data_type, json.dumps(json_data)))
        conn.commit()

async def save_turn_async(session_id, role, content, artifacts=None):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, save_turn, session_id, role, content, artifacts)

def ensure_session_exists(session_id, user_id, message_hint):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT session_id FROM multiturn_chat.conversation_sessions WHERE session_id = %s", (session_id,))
            exists = cur.fetchone()
            if not exists:
                title = (message_hint[:30] + '...') if len(message_hint) > 30 else message_hint
                cur.execute("""
                    INSERT INTO multiturn_chat.conversation_sessions (session_id, user_id, title)
                    VALUES (%s, %s, %s)
                """, (session_id, user_id, title))
            else:
                cur.execute("UPDATE multiturn_chat.conversation_sessions SET last_active_at = CURRENT_TIMESTAMP WHERE session_id = %s", (session_id,))
        conn.commit()

# ==========================================
# CLOUD ROUTING HELPERS (RAG & LLM)
# ==========================================

def get_secure_blob_url(base_url: str, provider: str, container: str = None) -> str:
    if not base_url or base_url == "Unknown Source":
        return base_url

    if provider == "aws":
        try:
            object_key = base_url.replace(f"s3://{container}/", "") if base_url.startswith("s3://") else base_url
            return s3_client.generate_presigned_url(
                'get_object', Params={'Bucket': container, 'Key': object_key}, ExpiresIn=3600
            )
        except ClientError as e:
            print(f"[DEBUG RAG] ERROR generating S3 presigned URL: {e}")
            return base_url
    else:
        try:
            parsed_url = urlparse(base_url)
            path_parts = parsed_url.path.lstrip('/').split('/', 1)
            if len(path_parts) != 2: return base_url
            
            sas_token = generate_blob_sas(
                account_name=STORAGE_ACCOUNT_NAME,
                container_name=path_parts[0],
                blob_name=path_parts[1],
                account_key=STORAGE_ACCOUNT_KEY,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            return f"{base_url}?{sas_token}"
        except Exception as e:
            print(f"[DEBUG RAG] ERROR generating SAS token: {e}")
            return base_url

def generate_embeddings(text: str, provider: str):
    if provider == "aws":
        try:
            body = json.dumps({"inputText": text})
            response = bedrock_client.invoke_model(
                body=body, modelId=AWS_EMBEDDING_MODEL, accept='application/json', contentType='application/json'
            )
            return json.loads(response.get('body').read()).get('embedding')
        except Exception as e:
            print(f"AWS Embedding generation failed: {e}")
            return None
    else:
        try:
            client = AzureOpenAI(api_key=AOAI_KEY, api_version="2023-05-15", azure_endpoint=AOAI_ENDPOINT)
            response = client.embeddings.create(input=[text], model=EMBEDDING_DEPLOYMENT)
            return response.data[0].embedding
        except Exception as e:
            print(f"Azure Embedding generation failed: {e}")
            return None

def search_vector_store(query: str, index_name: str, provider: str):
    query_vector = generate_embeddings(query, provider)
    if not query_vector: return []

    if provider == "aws":
        try:
            credentials = Credentials(AWS_ACCESS_KEY, AWS_SECRET_KEY)
            auth = AWSV4SignerAuth(credentials, AWS_REGION, 'aoss')
            
            os_client = OpenSearch(
                hosts=[{'host': AWS_OPENSEARCH_ENDPOINT.replace("https://", ""), 'port': 443}],
                http_auth=auth, use_ssl=True, verify_certs=True, connection_class=RequestsHttpConnection
            )
            
            os_query = {
                "size": 3,
                "query": {"knn": {"snippet_vector": {"vector": query_vector, "k": 3}}},
                "_source": ["snippet", "blob_url"]
            }
            response = os_client.search(body=os_query, index=index_name)
            
            return [{"content": hit['_source'].get("snippet"), "source": hit['_source'].get("blob_url", "Unknown Source")} for hit in response['hits']['hits']]
        except Exception as e:
            print(f"[DEBUG RAG] EXCEPTION AWS OpenSearch: {e}")
            return []
    else:
        try:
            search_client = SearchClient(endpoint=SEARCH_SERVICE_ENDPOINT, index_name=index_name, credential=AzureKeyCredential(SEARCH_ADMIN_KEY))
            vector_query = VectorizedQuery(vector=query_vector, k=3, fields="snippet_vector")
            results = search_client.search(search_text=query, vector_queries=[vector_query], select=["snippet", "blob_url"], top=3)
            return [{"content": r.get("snippet"), "source": r.get("blob_url", "Unknown Source")} for r in results]
        except Exception as e:
            print(f"[DEBUG RAG] EXCEPTION Azure Search: {e}")
            return []

def multiturn_call_llm(messages: list, provider: str):    
    if provider == "aws":
        try:
            system_prompts = [{"text": m["content"]} for m in messages if m["role"] == "system"]
            chat_messages = [{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages if m["role"] != "system"]
            
            response = bedrock_client.converse(
                modelId=AWS_LLM_MODEL,
                messages=chat_messages,
                system=system_prompts,
                inferenceConfig={"maxTokens": 2000, "temperature": 0}
            )
            return {"choices": [{"message": {"content": response['output']['message']['content'][0]['text']}}]}
        except Exception as e:
            print(f"AWS Bedrock LLM Error: {e}")
            return {"choices": [{"message": {"content": "I'm sorry, I encountered an error with AWS Bedrock."}}]}
    else:
        # Fixed: Removed hardcoded URL and key, mapping directly to configuration variables
        url = GPT4_CHAT_URL
        headers = {"api-key": GPT4_API_KEY, "Content-Type": "application/json"}
        payload = {"messages": messages, "max_tokens": 2000, "temperature": 0}
        response = requests.post(url, headers=headers, json=payload)
        return response.json()

# ==========================================
# PROMPT LOGIC
# ==========================================

def get_session_category(session_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT category FROM multiturn_chat.conversation_sessions WHERE session_id = %s", (session_id,))
            res = cur.fetchone()
            return res[0] if res else None

def update_session_category(session_id, category):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE multiturn_chat.conversation_sessions SET category = %s WHERE session_id = %s", (category, session_id))
        conn.commit()

def fetch_prompt_from_db(org_id, product_name):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT p.prompt_text 
                FROM multiturn_chat.prompts p
                JOIN multiturn_chat.products prod ON p.product_id = prod.id
                WHERE p.org_id = %s AND prod.product_name = %s AND p.is_production = true
                LIMIT 1
            """
            cur.execute(query, (org_id, product_name))
            res = cur.fetchone()
            return res[0] if res else None

def get_org_details(org_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM multiturn_chat.organizations WHERE id = %s", (org_id,))
            org_row = cur.fetchone()
            company_name = org_row[0] if org_row else "Our Finance Company"

            cur.execute("SELECT product_name FROM multiturn_chat.products WHERE org_id = %s AND product_name != 'main'", (org_id,))
            products = [row[0] for row in cur.fetchall()]
            
            return {"company_name": company_name, "products": products}

def load_system_prompt(session_id, org_id):
    category = get_session_category(session_id)
    prompt_text = None
    
    if category:
        prompt_text = fetch_prompt_from_db(org_id, category)
            
    if not prompt_text: prompt_text = fetch_prompt_from_db(org_id, "main")
    if not prompt_text: return "You are a helpful assistant."

    config = get_org_details(org_id)
    product_list_str = ", ".join([p for p in config["products"]]) 
    
    final_prompt = prompt_text.replace("{{COMPANY_NAME}}", config["company_name"])
    final_prompt = final_prompt.replace("{{PRODUCT_LIST}}", product_list_str)
    
    return final_prompt.replace("\n", " \\n ")

def extract_json_from_response(text):
    json_match = re.search(r"```\w*\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not json_match:
        json_match = re.search(r"(\{.*\})$", text, re.DOTALL)
        
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            clean_text = text.replace(json_match.group(0), "").strip()
            return re.sub(r"```\s*$", "", clean_text).strip(), data
        except json.JSONDecodeError:
            pass
    return text, None

# ==========================================
# ENDPOINTS
# ==========================================

@app.post("/aulogin")
async def login_endpoint(req: LoginRequest):
    is_valid, user_data = verify_user_and_get_role(req.username, req.password, pool)
    if not is_valid: raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "status": "success", "user_id": user_data['username'],
        "session_id": secrets.token_hex(16), "isadmin": user_data['isadmin'], "org": user_data['org']
    }

@app.get("/sessions")
async def get_sessions(user_id: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT session_id, title, last_active_at, category 
                FROM multiturn_chat.conversation_sessions 
                WHERE user_id = %s ORDER BY last_active_at DESC
            """, (user_id,))
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

@app.get("/history")
async def get_history(session_id: str):
    return {"history": [{"role": role, "content": content} for role, content in get_chat_history(session_id)]}

@app.post("/chat_auth")
async def chat_endpoint(req: ChatRequest):
    org_id = get_user_org(req.user_id)
    if org_id is None: raise HTTPException(status_code=403, detail="User organization not found")

    org_config = get_org_config(org_id)
    provider = org_config["cloud_provider"] if org_config else "azure"

    ensure_session_exists(req.session_id, req.user_id, req.message)
    save_turn(req.session_id, "user", req.message)

    messages = [{"role": "system", "content": load_system_prompt(req.session_id, org_id)}]
    for turn in get_chat_history(req.session_id):
        messages.append({"role": turn[0], "content": turn[1]})

    response_dict = multiturn_call_llm(messages, provider)
    try: raw_reply = response_dict["choices"][0]["message"]["content"]
    except KeyError: raw_reply = "I'm sorry, I encountered an error."

    user_reply, json_data = extract_json_from_response(raw_reply)
    current_category = get_session_category(req.session_id)
    
    if json_data:
        if "product_discovery" in json_data:
            identified_product = json_data["product_discovery"].get("identified_product")
            if identified_product in get_org_details(org_id)["products"]:
                save_conversation_data(req.session_id, org_id, "meta_handoff", json_data, identified_product)
                update_session_category(req.session_id, identified_product)
                current_category = identified_product
        elif "lead_summary" in json_data:
            save_conversation_data(req.session_id, org_id, "lead_capture", json_data, current_category)

    save_turn(req.session_id, "assistant", user_reply)
    return {"reply": user_reply, "category": current_category or "identifying", "debug_data": json_data}

@app.get("/org/{org_id}")
async def get_organization_info(org_id: int):
    try: return {"org_name": get_org_details(org_id).get("company_name", "Unknown Organization")}
    except Exception: raise HTTPException(status_code=500, detail="DB error")

# --- RAG Endpoints ---

@rag_router.post("/chat")
async def rag_chat_endpoint(req: ChatRequest):
    org_id = get_user_org(req.user_id)
    if org_id is None: raise HTTPException(status_code=403, detail="User organization not found")

    org_config = get_org_config(org_id)
    provider = org_config["cloud_provider"] if org_config else "azure"
    index_name = org_config["index_name"] if org_config else None
    container_name = org_config["storage_container"] if org_config else None

    ensure_session_exists(req.session_id, req.user_id, req.message)
    save_turn(req.session_id, "user", req.message)

    docs = []
    if index_name:
        raw_docs = search_vector_store(req.message, index_name, provider)
        for d in raw_docs:
            secure_url = get_secure_blob_url(d["source"], provider, container_name)
            docs.append({"content": d["content"], "source": secure_url})

    context_str = "\n\n### RELEVANT COMPANY DOCUMENTS ###\n" + "".join([f"Source ({d['source']}): {d['content']}\n\n" for d in docs]) if docs else ""
    
    base_system_content = load_system_prompt(req.session_id, org_id)
    user_profile = get_user_profile(req.user_id)
    if user_profile: base_system_content = base_system_content.replace("{{USER_PROFILE}}", user_profile)  
        
    system_content = base_system_content.replace("{{RAG_CONTEXT}}", context_str) if "{{RAG_CONTEXT}}" in base_system_content else base_system_content + context_str

    messages = [{"role": "system", "content": system_content}]
    for turn in get_chat_history(req.session_id): messages.append({"role": turn[0], "content": turn[1]})

    response_dict = multiturn_call_llm(messages, provider)
    try: raw_reply = response_dict["choices"][0]["message"]["content"]
    except KeyError: raw_reply = "I'm sorry, I encountered an error."

    user_reply, json_data = extract_json_from_response(raw_reply)
    current_category = get_session_category(req.session_id)
    
    if json_data:
        if "product_discovery" in json_data:
            identified_product = json_data["product_discovery"].get("identified_product")
            if identified_product in get_org_details(org_id)["products"]:
                save_conversation_data(req.session_id, org_id, "meta_handoff", json_data, identified_product)
                update_session_category(req.session_id, identified_product)
                current_category = identified_product
        elif "lead_summary" in json_data:
            save_conversation_data(req.session_id, org_id, "lead_capture", json_data, current_category)

    artifacts = {"rag_mode": True, "search_query": req.message, "search_results": docs}
    save_turn(req.session_id, "assistant", user_reply, artifacts)
    
    return {"reply": user_reply, "category": current_category or "identifying", "artifacts": artifacts, "debug_data": json_data}

# --- Websocket Endpoint ---
@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket, session_id: str, user_id: str):
    await websocket.accept()
    await asyncio.get_running_loop().run_in_executor(executor, ensure_session_exists, session_id, user_id, "Realtime Voice Session")
    
    # Fixed: Removed hardcoded org_id = 1. Now fetching dynamically via get_user_org helper.
    loop = asyncio.get_running_loop()
    org_id = await loop.run_in_executor(executor, get_user_org, user_id)
    
    if not org_id:
        await websocket.close(code=1008, reason="User organization not found")
        return

    system_instructions = await loop.run_in_executor(executor, load_system_prompt, session_id, org_id)
    azure_headers = {"api-key": AZURE_OPENAI_ENDPOINT_REALTIME_KEY, "Content-Type": "application/json"}

    try:
        async with websockets.connect(AZURE_OPENAI_ENDPOINT_REALTIME, additional_headers=azure_headers) as azure_ws:
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["audio", "text"], "instructions": system_instructions, "voice": "alloy",
                    "input_audio_format": "pcm16", "output_audio_format": "pcm16",
                    "turn_detection": {"type": "server_vad"}, "input_audio_transcription": {"model": "whisper-1"}
                }
            }
            await azure_ws.send(json.dumps(session_config))

            async def client_to_azure():
                try:
                    while True:
                        msg = json.loads(await websocket.receive_text())
                        if msg.get("type") in ["input_audio_buffer.append", "response.cancel"]: await azure_ws.send(json.dumps(msg))
                except Exception: pass

            async def azure_to_client():
                try:
                    async for message in azure_ws:
                        msg_json = json.loads(message)
                        event_type = msg_json.get("type")
                        await websocket.send_text(message)

                        if event_type == "input_audio_buffer.speech_started": await azure_ws.send(json.dumps({"type": "response.cancel"}))
                        if event_type == "conversation.item.input_audio_transcription.completed" and msg_json.get("transcript"):
                            await save_turn_async(session_id, "user", msg_json.get("transcript"))
                        if event_type == "response.audio_transcript.done" and msg_json.get("transcript"):
                            await save_turn_async(session_id, "assistant", msg_json.get("transcript"))
                except Exception as e: print(f"Azure WS Error: {e}")

            await asyncio.gather(client_to_azure(), azure_to_client())
    except Exception as e:
        print(f"Connection Error: {e}")
        await websocket.close()

app.include_router(rag_router)

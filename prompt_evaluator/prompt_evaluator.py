import os
import json
import requests
import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from passlib.context import CryptContext
from typing import List, Optional
import sys

sys.path.append('..')

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv()

# --- CONFIGURATION ---
DB_URL = os.getenv("DB_URL")
LLM_API_KEY = os.getenv("GPT4_API_KEY")
LLM_CHAT_URL = os.getenv("GPT4_CHAT_URL")

if not all([DB_URL, LLM_API_KEY, LLM_CHAT_URL]):
    raise ValueError("Missing required environment variables. Check your .env file.")

# --- AUTH SETUP ---
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    try:
        if not plain_password or not hashed_password: return False
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

# --- DATABASE POOL ---
pool = ConnectionPool(conninfo=DB_URL, min_size=1, max_size=10, open=False)

# --- LIFESPAN (Table Creation) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    with pool.connection() as conn:
        # 1. Users & Prompts
        conn.execute("""
            CREATE TABLE IF NOT EXISTS multiturn_chat.users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE,
                password_hash TEXT,
                org INTEGER,
                isadmin BOOLEAN DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS multiturn_chat.prompts (
                id SERIAL PRIMARY KEY,
                org_id INTEGER NOT NULL,
                product_id INTEGER,  -- Ensure this exists for product filtering
                prompt_text TEXT NOT NULL,
                version INTEGER NOT NULL,
                is_production BOOLEAN DEFAULT FALSE,
                business_scenario TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR DEFAULT NULL
            );
        """)
        
        # 2. Test Cases & Results
        conn.execute("""
            CREATE TABLE IF NOT EXISTS multiturn_chat.test_cases (
                id SERIAL PRIMARY KEY,
                prompt_id INTEGER REFERENCES multiturn_chat.prompts(id),
                type VARCHAR(20),
                goal TEXT,
                initial_query TEXT
            );
            CREATE TABLE IF NOT EXISTS multiturn_chat.test_results (
                id SERIAL PRIMARY KEY,
                test_case_id INTEGER REFERENCES multiturn_chat.test_cases(id),
                transcript_json TEXT,
                score FLOAT,
                reasoning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Evaluation Rubrics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS multiturn_chat.evaluation_rubrics (
                id SERIAL PRIMARY KEY,
                prompt_id INTEGER REFERENCES multiturn_chat.prompts(id) UNIQUE, 
                criteria_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Default Admin (admin/admin123)
        default_hash = pwd_context.hash("admin123")
        conn.execute("""
            INSERT INTO multiturn_chat.users (username, password_hash, org, isadmin)
            VALUES ('admin', %s, 1, TRUE)
            ON CONFLICT (username) DO NOTHING
        """, (default_hash,))
    yield
    pool.close()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- DATA MODELS ---
class LoginRequest(BaseModel):
    username: str
    password: str

class GenerateRequest(BaseModel):
    force_new: bool = False
    
class UpdateScenarioRequest(BaseModel):
    business_scenario: str

class TestCaseModel(BaseModel):
    id: Optional[int] = None
    goal: str
    initial_query: str
    type: str = "single"

class SaveTestsRequest(BaseModel):
    test_cases: List[TestCaseModel]
    
class OptimizeRequest(BaseModel):
    ignore_divergence: bool = False

class SaveVersionRequest(BaseModel):
    prompt_text: str

# --- LLM HELPER ---
def call_llm(messages, model="", json_mode=False):
    # Note: If your Azure OpenAI setup uses 'api-key' instead of 'Bearer', 
    # change "Authorization": f"Bearer {LLM_API_KEY}" to "api-key": LLM_API_KEY
    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.7}
    if json_mode: payload["response_format"] = {"type": "json_object"}
    
    try:
        resp = requests.post(LLM_CHAT_URL, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"LLM Error: {e}")
        return "{}" if json_mode else "Error"

# --- ROUTES ---

@app.post("/evaluator/login")
def login(creds: LoginRequest):
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT user_id, username, password_hash, org, isadmin FROM multiturn_chat.users WHERE username = %s", (creds.username,))
            user = cur.fetchone()
            if not user or not verify_password(creds.password, user['password_hash']):
                raise HTTPException(401, "Invalid credentials")
            if not user['isadmin']: raise HTTPException(403, "Admin only")
            return {"org_id": user['org'], "username": user['username']}

@app.get("/evaluator/orgs/{org_id}/products")
def get_products(org_id: int):
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id, product_name FROM multiturn_chat.products WHERE org_id = %s", (org_id,))
            return cur.fetchall()

@app.get("/evaluator/products/{product_id}/prompts")
def get_prompts_by_product(product_id: int):
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT id, version, is_production, created_at, prompt_text, business_scenario 
                FROM multiturn_chat.prompts 
                WHERE product_id = %s 
                ORDER BY version DESC
            """, (product_id,))
            return cur.fetchall()

@app.get("/evaluator/prompts/{prompt_id}/testcases")
def get_test_cases(prompt_id: int):
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM multiturn_chat.test_cases WHERE prompt_id = %s ORDER BY id ASC", (prompt_id,))
            cases = cur.fetchall()
            
            for case in cases:
                cur.execute("""
                    SELECT score, reasoning, transcript_json 
                    FROM multiturn_chat.test_results 
                    WHERE test_case_id = %s ORDER BY created_at DESC LIMIT 1
                """, (case['id'],))
                res = cur.fetchone()
                if res:
                    case.update(res)

            cur.execute("SELECT criteria_json FROM multiturn_chat.evaluation_rubrics WHERE prompt_id = %s", (prompt_id,))
            rubric_row = cur.fetchone()
            rubric = json.loads(rubric_row['criteria_json']) if rubric_row else None
            
            return {"test_cases": cases, "rubric": rubric}

# --- 1. UPDATE SCENARIO ---
@app.post("/evaluator/prompts/{prompt_id}/update_scenario")
def update_scenario_endpoint(prompt_id: int, req: UpdateScenarioRequest):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE multiturn_chat.prompts SET business_scenario = %s WHERE id = %s", 
                (req.business_scenario, prompt_id)
            )
            if cur.rowcount == 0:
                raise HTTPException(404, "Prompt not found")
            conn.commit()
            return {"status": "updated"}

# --- 2. SAVE MANUAL CHANGES ---
@app.post("/evaluator/prompts/{prompt_id}/save_testcases")
def save_testcases_endpoint(prompt_id: int, req: SaveTestsRequest):
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            for tc in req.test_cases:
                if tc.id:
                    cur.execute("""
                        UPDATE multiturn_chat.test_cases 
                        SET goal = %s, initial_query = %s, type = %s 
                        WHERE id = %s AND prompt_id = %s
                    """, (tc.goal, tc.initial_query, tc.type, tc.id, prompt_id))
                else:
                    cur.execute("""
                        INSERT INTO multiturn_chat.test_cases (prompt_id, goal, initial_query, type)
                        VALUES (%s, %s, %s, %s)
                    """, (prompt_id, tc.goal, tc.initial_query, tc.type))
            conn.commit()
            return {"status": "saved"}

# --- 3. GENERATE TESTS ---
@app.post("/evaluator/prompts/{prompt_id}/generate_tests")
def generate_tests_endpoint(prompt_id: int, req: GenerateRequest):
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT business_scenario, prompt_text FROM multiturn_chat.prompts WHERE id = %s", (prompt_id,))
            row = cur.fetchone()
            if not row: raise HTTPException(404, "Prompt not found")
            
            # Rubric check
            cur.execute("SELECT criteria_json FROM multiturn_chat.evaluation_rubrics WHERE prompt_id = %s", (prompt_id,))
            rubric_row = cur.fetchone()
            if not rubric_row:
                rubric_prompt = f"Create a grading rubric (3-4 metrics) for: {row['business_scenario']}. JSON: {{ 'metrics': [ {{ 'name': '...', 'weight': 0.3, 'desc': '...' }} ] }}"
                rubric_json = call_llm([{"role": "user", "content": rubric_prompt}], json_mode=True)
                cur.execute("INSERT INTO multiturn_chat.evaluation_rubrics (prompt_id, criteria_json) VALUES (%s, %s)", (prompt_id, rubric_json))
                rubric = json.loads(rubric_json)
            else:
                rubric = json.loads(rubric_row['criteria_json'])

            # Generate via LLM
            llm_prompt = f"Generate 5 test cases for scenario: '{row['business_scenario']}'. JSON: {{ 'cases': [ {{ 'type': 'single/multi', 'goal': '...', 'initial_query': '...' }} ] }}"
            data_str = call_llm([{"role": "user", "content": llm_prompt}], json_mode=True)
            data = json.loads(data_str)

            if req.force_new: 
                cur.execute("""
                    DELETE FROM multiturn_chat.test_results 
                    WHERE test_case_id IN (SELECT id FROM multiturn_chat.test_cases WHERE prompt_id = %s)
                """, (prompt_id,))
                
                cur.execute("DELETE FROM multiturn_chat.test_cases WHERE prompt_id = %s", (prompt_id,))
            
            saved_cases = []
            for c in data.get('cases', []):
                cur.execute("""
                    INSERT INTO multiturn_chat.test_cases (prompt_id, type, goal, initial_query) 
                    VALUES (%s, %s, %s, %s) RETURNING id, type, goal, initial_query
                """, (prompt_id, c['type'], c['goal'], c['initial_query']))
                saved_cases.append(cur.fetchone())           
            conn.commit()
            return {"status": "created", "test_cases": saved_cases, "rubric": rubric}

# --- 4. RUN EVALUATION ---
@app.post("/evaluator/prompts/{prompt_id}/run_evaluation")
def run_evaluation_endpoint(prompt_id: int, req: GenerateRequest):
    print(f"DEBUG: Starting Evaluation for Prompt ID: {prompt_id}") 
    
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT prompt_text, business_scenario FROM multiturn_chat.prompts WHERE id = %s", (prompt_id,))
            p_data = cur.fetchone()
            if not p_data: raise HTTPException(404, "Prompt not found")

            cur.execute("SELECT * FROM multiturn_chat.test_cases WHERE prompt_id = %s ORDER BY id ASC", (prompt_id,))
            test_cases = cur.fetchall()
            if not test_cases: raise HTTPException(400, "No tests found.")

            cur.execute("SELECT criteria_json FROM multiturn_chat.evaluation_rubrics WHERE prompt_id = %s", (prompt_id,))
            rubric_row = cur.fetchone()
            rubric = json.loads(rubric_row['criteria_json']) if rubric_row else {}

            results_summary = []
            
            for case in test_cases:
                print(f"DEBUG: Processing Case {case['id']} ({case['type']})")
                
                transcript = [{"role": "user", "content": case['initial_query']}]
                bot_reply = call_llm([{"role": "system", "content": p_data['prompt_text']}] + transcript)
                transcript.append({"role": "assistant", "content": bot_reply})
                
                if case['type'] == 'multi':
                    MAX_TURNS = 4 
                    for turn in range(MAX_TURNS):
                        history_str = "\n".join([f"{'User' if m['role']=='user' else 'Bot'}: {m['content']}" for m in transcript])
                        
                        sim_prompt = f"""
                        You are simulating a customer.
                        GOAL: "{case['goal']}"
                        CONTEXT:
                        {history_str}
                        
                        INSTRUCTIONS:
                        - Reply to the Bot as the Customer.
                        - Be brief and natural. Do NOT be an AI.
                        - If goal is met, output: [STOP]
                        """
                        user_reply = call_llm([{"role": "user", "content": sim_prompt}])
                        
                        if "[STOP]" in user_reply.upper(): break
                        
                        transcript.append({"role": "user", "content": user_reply})
                        bot_reply_2 = call_llm([{"role": "system", "content": p_data['prompt_text']}] + transcript)
                        transcript.append({"role": "assistant", "content": bot_reply_2})

                # Grading
                eval_prompt = f"""
                Grade this chat based on: {json.dumps(rubric.get('metrics', []))}.
                Transcript: {json.dumps(transcript)}
                Return JSON: {{ "score": 85, "reasoning": "..." }}
                """
                eval_res = json.loads(call_llm([{"role": "user", "content": eval_prompt}], json_mode=True))
                
                # Save Result
                cur.execute("""
                    INSERT INTO multiturn_chat.test_results (test_case_id, transcript_json, score, reasoning) 
                    VALUES (%s, %s, %s, %s)
                """, (case['id'], json.dumps(transcript), eval_res.get('score', 0), eval_res.get('reasoning', '')))
                
                results_summary.append({
                    "id": case['id'], 
                    "goal": case['goal'], 
                    "type": case['type'],
                    "score": eval_res.get('score', 0), 
                    "reasoning": eval_res.get('reasoning', ''),
                    "transcript_json": transcript 
                })
            
            conn.commit()
            avg = sum(r['score'] for r in results_summary) / len(results_summary) if results_summary else 0
            return {"overall_score": avg, "results": results_summary, "rubric": rubric}

# --- Routes for Prompt Optimization ---
@app.post("/evaluator/prompts/{prompt_id}/optimize")
def optimize_prompt_endpoint(prompt_id: int, req: OptimizeRequest):
    """Feeds test failures to the LLM to rewrite the prompt, with a divergence guardrail."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # 1. Fetch current context
            cur.execute("SELECT prompt_text, business_scenario FROM multiturn_chat.prompts WHERE id = %s", (prompt_id,))
            p_data = cur.fetchone()
            if not p_data:
                raise HTTPException(404, "Prompt not found")

            # 2. Divergence Check
            if not req.ignore_divergence:
                div_prompt = f"""
                You are an AI auditor. Check if the system prompt aligns with its intended business scenario.
                
                BUSINESS SCENARIO: "{p_data['business_scenario']}"
                SYSTEM PROMPT: "{p_data['prompt_text']}"
                
                Are these two significantly divergent, contradictory, or completely unrelated? 
                Reply EXACTLY with a single word: YES or NO.
                """
                div_res = call_llm([{"role": "user", "content": div_prompt}]).strip().upper()
                
                if "YES" in div_res:
                    return {
                        "status": "divergent_warning", 
                        "message": "⚠️ Warning: The current System Prompt and Business Scenario appear to be completely unrelated or contradictory.\n\nOptimizing based on conflicting information may yield poor results. Do you still want to proceed?"
                    }

            # 3. Fetch test results
            cur.execute("""
                SELECT tc.goal, tr.score, tr.reasoning 
                FROM multiturn_chat.test_cases tc
                JOIN multiturn_chat.test_results tr ON tc.id = tr.test_case_id
                WHERE tc.prompt_id = %s
            """, (prompt_id,))
            results = cur.fetchall()
            
            if not results:
                raise HTTPException(400, "Run an evaluation first to generate optimization data.")

            # 4. Build the prompt engineer instructions
            failures = [r for r in results if r['score'] < 80]
            successes = [r for r in results if r['score'] >= 80]
            
            if not failures:
                return {"status": "success", "optimized_prompt": p_data['prompt_text']} # Already perfect
            
            feedback_str = "SUCCESSFUL BEHAVIORS TO KEEP:\n"
            for s in successes: feedback_str += f"- Met Goal: {s['goal']}\n"
            
            feedback_str += "\nFAILURES TO FIX:\n"
            for f in failures: feedback_str += f"- Failed Goal: {f['goal']} | Reason: {f['reasoning']}\n"

            llm_prompt = f"""
            You are an Expert AI Prompt Engineer. Rewrite the system prompt to fix evaluation failures while maintaining strict compliance protocols.
            
            BUSINESS SCENARIO:
            {p_data['business_scenario']}
            
            CURRENT SYSTEM PROMPT:
            {p_data['prompt_text']}
            
            EVALUATION FEEDBACK:
            {feedback_str}
            
            INSTRUCTIONS:
            - Rewrite the "CURRENT SYSTEM PROMPT" to address the FAILURES.
            - Ensure you do NOT break the SUCCESSFUL BEHAVIORS.
            - Keep the structure clean and professional.
            - Output ONLY the newly rewritten prompt text. No introductory remarks.
            """
            
            # 5. Call LLM for Optimization
            optimized_text = call_llm([{"role": "user", "content": llm_prompt}])
            return {"status": "success", "optimized_prompt": optimized_text}

@app.post("/evaluator/prompts/{prompt_id}/save_version")
def save_new_version_endpoint(prompt_id: int, req: SaveVersionRequest):
    """Saves the edited text as a brand new prompt version, copying rubrics and test cases."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # 1. Get metadata from current prompt to carry over
            cur.execute("SELECT org_id, product_id, business_scenario FROM multiturn_chat.prompts WHERE id = %s", (prompt_id,))
            old_p = cur.fetchone()
            
            # 2. CRITICAL FIX: Find the absolute maximum version for this product
            cur.execute("SELECT MAX(version) as max_v FROM multiturn_chat.prompts WHERE product_id = %s", (old_p['product_id'],))
            max_v_row = cur.fetchone()
            new_version = (max_v_row['max_v'] or 0) + 1
            
            # 3. Insert new prompt version
            cur.execute("""
                INSERT INTO multiturn_chat.prompts (org_id, product_id, prompt_text, version, business_scenario)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (old_p['org_id'], old_p['product_id'], req.prompt_text, new_version, old_p['business_scenario']))
            
            new_id = cur.fetchone()['id']

            # 4. Copy Evaluation Rubric to the new version
            cur.execute("SELECT criteria_json FROM multiturn_chat.evaluation_rubrics WHERE prompt_id = %s", (prompt_id,))
            rubric_row = cur.fetchone()
            if rubric_row:
                cur.execute("""
                    INSERT INTO multiturn_chat.evaluation_rubrics (prompt_id, criteria_json)
                    VALUES (%s, %s)
                """, (new_id, rubric_row['criteria_json']))

            # 5. Copy existing Test Cases to the new version (Leaving behind old scores/transcripts)
            cur.execute("SELECT type, goal, initial_query FROM multiturn_chat.test_cases WHERE prompt_id = %s ORDER BY id ASC", (prompt_id,))
            old_tests = cur.fetchall()
            
            for t in old_tests:
                cur.execute("""
                    INSERT INTO multiturn_chat.test_cases (prompt_id, type, goal, initial_query)
                    VALUES (%s, %s, %s, %s)
                """, (new_id, t['type'], t['goal'], t['initial_query']))

            conn.commit()
            return {"status": "saved", "new_prompt_id": new_id, "new_version": new_version}
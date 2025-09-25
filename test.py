import sqlite3
import json
import requests
from fastapi import FastAPI, Form, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import datetime
from contextlib import asynccontextmanager

# --- DATABASE SETUP ---
DATABASE = 'triage_system.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Create Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
    ''')
    # Create Support Tickets Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            image_url TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    # Create AI Analysis Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            priority TEXT,
            category TEXT,
            FOREIGN KEY (ticket_id) REFERENCES support_tickets (id)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# --- LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    print("Server shutting down.")

# --- FASTAPI APP ---
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- MODELS ---
class User(BaseModel):
    name: str
    email: str

class TicketStatusUpdate(BaseModel):
    status: str

# --- CONFIGURATION ---
SMYTHOS_API_URL = "https://cmfxt5dlf45v723qu5e621ogt.agent.pa.smyth.ai/api/triage_ticket"

# --- ENDPOINTS ---
@app.get("/")
def read_root():
    return {"message": "Smart Triage Backend is running with SQLite!"}

@app.post("/register")
def register_user(user: User):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (user.name, user.email))
        conn.commit()
        new_user_id = cursor.lastrowid
        return {"id": new_user_id, "name": user.name, "email": user.email}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered.")
    finally:
        conn.close()
        return {"id": new_user_id, "name": user.name, "email": user.email}

@app.get("/tickets")
def get_tickets():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            st.id, st.description, st.status, st.created_at,
            u.name as user_name,
            ai.priority, ai.category
        FROM support_tickets st
        JOIN users u ON st.user_id = u.id
        LEFT JOIN ai_analysis ai ON st.id = ai.ticket_id
        ORDER BY st.created_at DESC
    ''')
    tickets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tickets

# --- NEW STATISTICS ENDPOINT ---
@app.get("/stats/last-hour")
def get_stats_last_hour():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    one_hour_ago = (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat()
    
    # Count tickets recorded in the last hour
    cursor.execute("SELECT COUNT(id) FROM support_tickets WHERE created_at >= ?", (one_hour_ago,))
    recorded_count = cursor.fetchone()[0]
    
    # Count tickets solved (status='Closed') in the last hour
    cursor.execute("SELECT COUNT(id) FROM support_tickets WHERE status = 'Closed' AND last_updated_at >= ?", (one_hour_ago,))
    solved_count = cursor.fetchone()[0]
    
    conn.close()
    return {"recorded_last_hour": recorded_count, "solved_last_hour": solved_count}


@app.post("/submit-ticket")
async def submit_ticket(
    user_id: int = Form(...),
    ticket_text: str = Form(...), 
    ticket_image: UploadFile = File(None)
):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="User ID not found.")
    
    data = {'ticket_text': ticket_text}
    files = {}
    if ticket_image:
        files['ticket_image'] = (ticket_image.filename, ticket_image.file, ticket_image.content_type)
    
    try:
        response = requests.post(SMYTHOS_API_URL, data=data, files=files if files else None)
        response.raise_for_status() 
        
        smythos_data = response.json()
        print(f"SUCCESS (Raw): Received from SmythOS: {smythos_data}")

        ## --- DATA CLEANING SECTION ---
        # The data is nested and stringified. Let's extract and clean it.
        json_string = smythos_data['result']['Output']['json_data']
        clean_data = json.loads(json_string)

        # The priority is double-escaped, so we parse it again
        if isinstance(clean_data.get('priority'), str):
             priority_obj = json.loads(clean_data['priority'])
             clean_data['priority'] = priority_obj['priority']
        
        print(f"SUCCESS (Cleaned): {clean_data}")

        # --- Get the specific values from the clean_data dictionary ---
        category = clean_data.get('category')
        priority = clean_data.get('priority')
        
        # --- Insert into the database ---
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO support_tickets (user_id, description, status, created_at) VALUES (?, ?, ?, ?)",
            (user_id, ticket_text, "New", timestamp)
        )
        new_ticket_id = cursor.lastrowid

        # Now, use the category and priority variables to insert into the ai_analysis table
        cursor.execute(
            "INSERT INTO ai_analysis (ticket_id, priority, category) VALUES (?, ?, ?)",
            (new_ticket_id, priority, category)
        )
        conn.commit()

        return {"id": new_ticket_id, "status": "Ticket created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process ticket: {e}")
    finally:
        conn.close()

@app.put("/tickets/{ticket_id}/status")
def update_ticket_status(ticket_id: int, status_update: TicketStatusUpdate):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE support_tickets SET status = ? WHERE id = ?", (status_update.status, ticket_id))
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Ticket not found.")
    conn.close()
    return {"id": ticket_id, "new_status": status_update.status}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
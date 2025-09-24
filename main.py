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
            confidence_score REAL,
            FOREIGN KEY (ticket_id) REFERENCES support_tickets (id)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# --- LIFESPAN MANAGER (Modern way to handle startup) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs on startup
    init_db()
    yield
    # This code runs on shutdown (optional)
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

@app.get("/tickets")
def get_tickets():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            st.id, st.description, st.status, st.created_at,
            u.name as user_name, u.email as user_email,
            ai.priority, ai.category
        FROM support_tickets st
        JOIN users u ON st.user_id = u.id
        LEFT JOIN ai_analysis ai ON st.id = ai.ticket_id
        ORDER BY st.created_at DESC
    ''')
    tickets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tickets

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
        # Assuming the AI call is successful and returns clean JSON
        # In a real scenario, you would have the live call here
        smythos_data = {"category": "Hardware", "priority": "High"} # Placeholder for AI response

        timestamp = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO support_tickets (user_id, description, status, created_at) VALUES (?, ?, ?, ?)",
            (user_id, ticket_text, "New", timestamp)
        )
        new_ticket_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO ai_analysis (ticket_id, priority, category) VALUES (?, ?, ?)",
            (new_ticket_id, smythos_data.get('priority'), smythos_data.get('category'))
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

# http://127.0.0.1:8000

# SMYTHOS_API_URL = "https://cmfxt5dlf45v723qu5e621ogt.agent.pa.smyth.ai/api/triage_ticket"
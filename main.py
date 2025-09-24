import requests
from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import datetime
import random
import json # Import the json library

# Initialize the FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
SMYTHOS_API_URL = "https://cmfxt5dlf45v723qu5e621ogt.agent.pa.smyth.ai/api/triage_ticket"

# --- IN-MEMORY DATABASE ---
tickets_db = []

@app.get("/")
def read_root():
    return {"message": "Smart Triage Backend is running!"}

@app.get("/tickets")
def get_tickets():
    return tickets_db

@app.post("/submit-ticket")
async def submit_ticket(
    ticket_text: str = Form(...), 
    user_name: str = Form(...),
    ticket_image: UploadFile = File(None)
):
    data = {'ticket_text': ticket_text}
    files = {}
    if ticket_image:
        files['ticket_image'] = (ticket_image.filename, ticket_image.file, ticket_image.content_type)
    
    try:
        response = requests.post(SMYTHOS_API_URL, data=data, files=files if files else None)
        response.raise_for_status() 
        
        smythos_data = response.json()
        print(f"SUCCESS (Raw): Received from SmythOS: {smythos_data}")

        # --- DATA CLEANING SECTION ---
        # The data is nested and stringified. Let's extract and clean it.
        json_string = smythos_data['result']['Output']['json_data']
        clean_data = json.loads(json_string)
        
        # The priority is double-escaped, so we parse it again
        if isinstance(clean_data.get('priority'), str):
             priority_obj = json.loads(clean_data['priority'])
             clean_data['priority'] = priority_obj['priority']
        
        print(f"SUCCESS (Cleaned): {clean_data}")

        # --- SAVE CLEAN DATA TO DATABASE ---
        new_ticket = {
            "id": random.randint(1000, 9999),
            "user_name": user_name,
            "description": ticket_text,
            "status": "New",
            "timestamp": datetime.datetime.now().isoformat(),
            "ai_analysis": clean_data # Save the clean data!
        }
        tickets_db.append(new_ticket)
        
        return new_ticket

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Failed to process the ticket.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# http://127.0.0.1:8000

# SMYTHOS_API_URL = "https://cmfxt5dlf45v723qu5e621ogt.agent.pa.smyth.ai/api/triage_ticket"
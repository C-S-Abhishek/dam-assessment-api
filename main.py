from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Any
import sqlite3

app = FastAPI()

# Allow CORS so your frontend can communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SyncPayload(BaseModel):
    assessments: List[List[Any]] # Receives the array of rows [cite: 61]

@app.post("/api/sync")
def sync_data(payload: SyncPayload):
    try:
        # Connect to a local SQLite database 
        conn = sqlite3.connect('dam_assessments.db')
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS assessments
                          (damName text, segment text, segWeight text, range text, 
                           height text, location text, component text, locWeight text, 
                           defect text, rank int, normRank real, defectWeight real, 
                           dsi real, weightedDsi real, image text)''')
        
        # Insert rows
        for row in payload.assessments:
            cursor.execute("INSERT INTO assessments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(row))
            
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Synced {len(payload.assessments)} rows."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/assessments")
def get_all_assessments():
    try:
        # Connect to the database
        conn = sqlite3.connect('dam_assessments.db')
        
        # This makes the data output with column names (like a dictionary)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        # Check if the table exists first to avoid errors
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assessments'")
        if not cursor.fetchone():
            return {"status": "empty", "message": "No data synced yet."}
            
        # Fetch all saved rows
        cursor.execute("SELECT * FROM assessments")
        rows = cursor.fetchall()
        conn.close()
        
        # Return the data
        return {"status": "success", "total_records": len(rows), "data": [dict(row) for row in rows]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

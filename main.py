import os
import jwt
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine

app = FastAPI()

# Allow your frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SECURITY & DATABASE CONFIGURATION ---
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_dam_encryption_key_2024")

# This is your active Supabase connection!
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:zncnLEXt98z5T5yL@db.zwfiedglfwjqptlhdquf.supabase.co:5432/postgres")

engine = create_engine(DATABASE_URL)
security = HTTPBearer()

# --- SECURITY PROTOCOL (JWT) ---
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token. Access denied.")

# --- API ENDPOINTS ---
@app.post("/api/login")
async def login(credentials: dict):
    """Verifies credentials securely on the server and issues a JWT token."""
    username = credentials.get("username")
    password = credentials.get("password")
    
    if username == "admin" and password == "admin":
        token = jwt.encode({"role": "admin"}, SECRET_KEY, algorithm="HS256")
        return {"status": "success", "token": token, "role": "admin"}
    elif username == "inspector" and password == "insp":
        token = jwt.encode({"role": "inspector"}, SECRET_KEY, algorithm="HS256")
        return {"status": "success", "token": token, "role": "inspector"}
    
    raise HTTPException(status_code=401, detail="Invalid Username or Password")

@app.post("/api/sync")
async def sync_data(request: Request, token: dict = Depends(verify_token)):
    """Receives offline data from the tablet and saves it permanently to PostgreSQL."""
    data = await request.json()
    if 'assessments' not in data or not data['assessments']:
        return {"status": "empty"}
    
    # Structure the data into a Pandas DataFrame
    df = pd.DataFrame(data['assessments'], columns=[
        "Dam Name", "Segment/System", "Seg Weight", "Range", "Height", "Location", 
        "Component", "Loc Weight", "Defect", "Severity Rank", "Norm Rank", 
        "Defect Weight", "DSI", "Weighted DSI", "Image (Base64)"
    ])
    
    try:
        # Push to Cloud PostgreSQL Database
        df.to_sql('assessments', engine, if_exists='append', index=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/assessments")
async def get_assessments(token: dict = Depends(verify_token)):
    """Fetches all historical data securely for the Admin Dashboard."""
    try:
        df = pd.read_sql_table('assessments', engine)
        
        # Rename columns so the frontend JavaScript understands them
        df = df.rename(columns={
            "Dam Name": "damName", "Segment/System": "segment", "Seg Weight": "segWeight",
            "Range": "range", "Height": "height", "Location": "location", 
            "Component": "component", "Loc Weight": "locWeight", "Defect": "defect",
            "Severity Rank": "rank", "Norm Rank": "normRank", "Defect Weight": "defectWeight",
            "DSI": "dsi", "Weighted DSI": "weightedDsi", "Image (Base64)": "image"
        })
        
        df = df.fillna("") # Prevent null errors
        records = df.to_dict(orient='records')
        return {"status": "success", "total_records": len(records), "data": records}
    except Exception as e:
        # If the table is empty/doesn't exist yet
        return {"status": "success", "data": []}

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict
import json
import uuid
from datetime import datetime
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

# Load environment variables
api_key = os.getenv("OPENAI_API_KEY")


app = FastAPI()

# Configure CORS
origins = os.getenv("CORS_ORIGINS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = OpenAI(api_key=api_key)
S3_BUCKET = os.getenv("S3_BUCKET", "")
s3_client = boto3.client("s3")


# 🔥 NEW: Biography Expert System Prompt
BIOGRAPHY_SYSTEM_PROMPT = """
You are an expert biographical researcher and historian.

Your role:
- Provide accurate, well-structured information about people's lives.
- Focus on:
  1. Early Life & Background
  2. Education
  3. Career Journey
  4. Major Achievements
  5. Contributions & Impact
  6. Awards & Recognition
  7. Interesting Facts (if relevant)

Guidelines:
- Be factual and avoid speculation.
- If unsure, clearly say "Information not widely documented".
- Prefer clarity over verbosity.
- Use structured paragraphs or bullet points when helpful.
- Answer follow-up questions with deeper insights.
- If the user asks something vague, interpret it intelligently.
- make sure the response would not be more than 10 lines.

Tone:
- Professional, informative, and engaging.
"""

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str

class Message(BaseModel):
    role: str
    content: str
    timestamp: str

# Memory management functions
def get_memory_path(session_id: str) -> str:
    return f"{session_id}.json"

def load_conversation(session_id: str) -> List[Dict]:
    
    """Load conversation history from storage"""
     
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=get_memory_path(session_id))
        return json.loads(response["Body"].read().decode("utf-8"))
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return []
            raise
def save_conversation(session_id: str, messages: List[Dict]):
    """Save conversation history to storage"""
    
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=get_memory_path(session_id),
        Body=json.dumps(messages, indent=2),
        ContentType="application/json",
        )
    


@app.get("/")
async def root():
    return {"message": "Biography Research AI API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Load conversation history
        conversation = load_conversation(session_id)
        # Build messages with history
        messages = [{"role": "system", "content": BIOGRAPHY_SYSTEM_PROMPT}]
        
        # Add conversation history (keep last 10 messages for context window)
        for msg in conversation[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        


        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3  # 🔥 lower = more factual
        )
        assistant_response = response.choices[0].message.content
        conversation.append(
            {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()}
        )
        conversation.append(
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": datetime.now().isoformat(),
            }
        )
        
        # Save updated conversation
        save_conversation(session_id, conversation)
        
        return ChatResponse(
            response=assistant_response,
            session_id=session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
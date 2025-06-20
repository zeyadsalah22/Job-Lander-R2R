from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, AsyncGenerator
import asyncio
import json
import uuid
import logging
from datetime import datetime, timedelta
from main import R2RChatbot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="R2R Chatbot Microservice", version="1.0.0")

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active chat sessions
# In production, use Redis or another persistent storage
active_sessions: Dict[str, Dict] = {}

# Session cleanup interval (in minutes)
SESSION_TIMEOUT = 30

class ChatSession:
    """Manages individual chat sessions"""
    def __init__(self, session_id: str, user_id: int, chatbot: R2RChatbot):
        self.session_id = session_id
        self.user_id = user_id
        self.chatbot = chatbot
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.is_active = True

    def update_activity(self):
        self.last_activity = datetime.now()

    def is_expired(self) -> bool:
        return datetime.now() - self.last_activity > timedelta(minutes=SESSION_TIMEOUT)

# Request/Response Models
class InitializeChatRequest(BaseModel):
    user_id: int
    applications_data: dict
    questions_data: dict

class InitializeChatResponse(BaseModel):
    session_id: str
    status: str
    message: str
    document_id: Optional[str] = None

class SendMessageRequest(BaseModel):
    session_id: str
    message: str

class SendMessageResponse(BaseModel):
    response: str
    conversation_id: str

class CloseChatRequest(BaseModel):
    session_id: str

# Session Management Functions
def create_session(user_id: int, chatbot: R2RChatbot) -> str:
    """Create a new chat session"""
    session_id = str(uuid.uuid4())
    session = ChatSession(session_id, user_id, chatbot)
    active_sessions[session_id] = session
    logger.info(f"Created session {session_id} for user {user_id}")
    return session_id

def get_session(session_id: str) -> Optional[ChatSession]:
    """Get an active chat session"""
    session = active_sessions.get(session_id)
    if session and not session.is_expired():
        session.update_activity()
        return session
    elif session and session.is_expired():
        # Clean up expired session
        cleanup_session(session_id)
    return None

def cleanup_session(session_id: str):
    """Clean up a chat session"""
    session = active_sessions.get(session_id)
    if session:
        # Delete the document from R2R
        try:
            asyncio.create_task(session.chatbot.delete_document())
            logger.info(f"Cleaned up session {session_id}")
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
        
        # Remove from active sessions
        del active_sessions[session_id]

async def cleanup_expired_sessions():
    """Background task to clean up expired sessions"""
    while True:
        expired_sessions = [
            session_id for session_id, session in active_sessions.items()
            if session.is_expired()
        ]
        
        for session_id in expired_sessions:
            cleanup_session(session_id)
            
        await asyncio.sleep(300)  # Check every 5 minutes

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    asyncio.create_task(cleanup_expired_sessions())

@app.post("/initialize-chat", response_model=InitializeChatResponse)
async def initialize_chat(request: InitializeChatRequest):
    """
    Initialize a new chat session for a user.
    Creates R2RChatbot instance, generates document, uploads to R2R.
    """
    try:
        logger.info(f"Initializing chat for user {request.user_id}")
        
        # Create chatbot instance
        chatbot = R2RChatbot(user_id=request.user_id)
        
        if chatbot.client is None:
            raise HTTPException(status_code=500, detail="R2R client initialization failed")
        
        # Generate document from applications and questions data
        chatbot.generate_application_document(
            request.applications_data, 
            request.questions_data
        )
        
        # Upload document to R2R
        document_id = await chatbot.upload_document_to_r2r()
        
        if not document_id:
            raise HTTPException(status_code=500, detail="Failed to upload document to R2R")
        
        # Create session
        session_id = create_session(request.user_id, chatbot)
        
        return InitializeChatResponse(
            session_id=session_id,
            status="success",
            message="Chat session initialized successfully",
            document_id=document_id
        )
        
    except Exception as e:
        logger.error(f"Error initializing chat: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize chat: {str(e)}")

@app.post("/send-message")
async def send_message(request: SendMessageRequest):
    """
    Send a message to the chatbot with streaming response.
    """
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            # Get response from chatbot
            response = await session.chatbot.send_message_to_r2r(request.message)
            
            if response:
                # Stream the response word by word for better UX
                words = response.split()
                for i, word in enumerate(words):
                    chunk = {
                        "type": "content",
                        "data": word + " ",
                        "is_final": i == len(words) - 1
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    await asyncio.sleep(0.05)  # Small delay for streaming effect
                
                # Send final metadata
                final_chunk = {
                    "type": "metadata",
                    "data": {
                        "conversation_id": session.chatbot.conversation_id,
                        "document_id": session.chatbot.document_id,
                        "session_id": session.session_id
                    },
                    "is_final": True
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
            else:
                error_chunk = {
                    "type": "error",
                    "data": "Sorry, I couldn't process your message. Please try again.",
                    "is_final": True
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_chunk = {
                "type": "error",
                "data": f"An error occurred: {str(e)}",
                "is_final": True
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.post("/close-chat")
async def close_chat(request: CloseChatRequest):
    """
    Close a chat session and clean up resources.
    """
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Clean up the session
        cleanup_session(request.session_id)
        
        return {"status": "success", "message": "Chat session closed successfully"}
        
    except Exception as e:
        logger.error(f"Error closing chat: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to close chat: {str(e)}")

@app.get("/session-status/{session_id}")
async def get_session_status(session_id: str):
    """
    Get the status of a chat session.
    """
    session = get_session(session_id)
    if not session:
        return {"status": "not_found", "message": "Session not found or expired"}
    
    return {
        "status": "active",
        "user_id": session.user_id,
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "document_id": session.chatbot.document_id,
        "conversation_id": session.chatbot.conversation_id
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn 
    uvicorn.run(app, host="0.0.0.0", port=8000) 
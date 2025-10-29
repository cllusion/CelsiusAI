"""
Celsius AI - FastAPI Web Interface
=================================

Description:
------------
This script provides a comprehensive, high-performance RESTful API and WebSocket
interface for the Celsius AI ecosystem using the FastAPI framework. It serves as
the primary backend for web-based user interfaces, handling requests for AI
interaction, system status, document management, and real-time communication.

Key Features:
-------------
- **Modern FastAPI Framework**: Built on a high-performance, asynchronous web framework.
- **Structured API with Tags**: Endpoints are organized with tags for clear documentation.
- **Enhanced Pydantic Models**: Rich data models with descriptions and examples for clarity.
- **Robust Dependency Injection**: Manages application state and resources cleanly.
- **Real-time WebSocket Communication**: A managed WebSocket endpoint for bidirectional updates.
- **Asynchronous File Handling**: Uses `aiofiles` for non-blocking file I/O.
- **Graceful Degradation**: The API can run in a degraded mode if core AI components fail to load.
- **CORS Enabled**: Allows cross-origin requests from frontend applications.
"""

# --- Standard Library Imports ---
import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Third-Party Imports ---
import aiofiles
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

# --- Project-Specific Imports ---
# Ensure the project root is in the Python path for module resolution
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

try:
    from core.assistant import CelsiusAI
    from src.core.config import CelsiusConfig
    from src.whitehat.authorization import WhiteHatAuthorizationManager

    CELSIUS_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import Celsius components: {e}. API will run in a degraded mode.")
    CELSIUS_COMPONENTS_AVAILABLE = False

    # Define dummy classes for degraded mode
    class CelsiusAI:
        async def initialize(self):
            pass

        async def shutdown(self):
            pass

        async def process_query(self, query: str) -> str:
            return "AI is in degraded mode."

    class CelsiusConfig:
        pass

    class WhiteHatAuthorizationManager:
        def request_authorization(self, **kwargs) -> str:
            return str(uuid.uuid4())

        def get_authorization_status(self, auth_id: str) -> dict:
            return {"status": "unknown"}


# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Application State Management ---
class AppState:
    """Manages the global state of the FastAPI application."""

    def __init__(self):
        self.ai_core: Optional[CelsiusAI] = None
        self.websocket_manager = WebSocketManager()

    async def startup(self):
        """Initializes application resources."""
        logger.info("Initializing application state...")
        if CELSIUS_COMPONENTS_AVAILABLE:
            try:
                config = CelsiusConfig()
                self.ai_core = CelsiusAI(config)
                await self.ai_core.initialize()
                logger.info("✅ Celsius AI core has been successfully initialized.")
            except Exception as e:
                logger.error(f"⚠️ ERROR: Celsius AI initialization failed: {e}", exc_info=True)
                self.ai_core = CelsiusAI()  # Fallback to dummy
        else:
            self.ai_core = CelsiusAI()  # Fallback to dummy
            logger.info("✅ API started in degraded mode. AI functionalities are disabled.")

    async def shutdown(self):
        """Cleans up application resources."""
        logger.info("Shutting down application state...")
        if self.ai_core and hasattr(self.ai_core, "shutdown"):
            await self.ai_core.shutdown()
            logger.info("✅ Celsius AI core has been shut down gracefully.")
        await self.websocket_manager.disconnect_all()


class WebSocketManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        disconnected_sockets = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except (WebSocketDisconnect, RuntimeError):
                disconnected_sockets.append(connection)
        for socket in disconnected_sockets:
            self.disconnect(socket)

    async def disconnect_all(self):
        for connection in self.active_connections[:]:
            await connection.close(code=status.WS_1012_SERVICE_RESTART)
            self.disconnect(connection)


# --- FastAPI Application Setup ---
app_state = AppState()
app = FastAPI(
    title="Celsius AI API",
    description="A comprehensive API for the Celsius AI cybersecurity assistant.",
    version="2.1.0",
    on_startup=[app_state.startup],
    on_shutdown=[app_state.shutdown],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Dependency Injection ---
def get_ai_core() -> CelsiusAI:
    if not app_state.ai_core:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI core is not available.")
    return app_state.ai_core


def get_websocket_manager() -> WebSocketManager:
    return app_state.websocket_manager


# --- Pydantic Models ---
class ChatMessage(BaseModel):
    message: str = Field(..., description="The user's chat message.", example="Analyze this log file for anomalies.")
    session_id: Optional[str] = Field(
        None, description="A unique identifier for the chat session.", example="session-12345"
    )


class ChatResponse(BaseModel):
    response: str = Field(..., description="The AI's response.", example="Analysis complete. No anomalies found.")
    timestamp: str = Field(
        ..., description="The ISO 8601 timestamp of the response.", example="2023-10-27T10:00:00.000Z"
    )


class SystemStatus(BaseModel):
    ai_status: str = Field(..., description="The operational status of the AI core.", example="online")
    last_update: str = Field(
        ..., description="The ISO 8601 timestamp of the status update.", example="2023-10-27T10:00:00.000Z"
    )


class AuthorizationRequest(BaseModel):
    """Request model for initiating a white hat authorization."""

    target_system: str = Field(..., example="api.example.com")
    techniques: List[str] = Field(..., example=["port_scanning", "sql_injection_detection"])
    purpose: str = Field(..., example="Quarterly security audit.")
    legal_basis: str = Field(..., example="Contract #12345")
    duration_hours: int = Field(..., gt=0, example=8)
    contact_info: str = Field(..., example="security-team@example.com")


class AuthorizationStatus(BaseModel):
    """Response model for white hat authorization status."""

    authorization_id: str
    status: str
    message: Optional[str] = None


class DocumentMetadata(BaseModel):
    """Response model for document metadata."""

    file_id: str
    original_filename: str
    upload_timestamp: str
    file_size_bytes: int
    content_type: Optional[str] = None


class FileUploadResponse(BaseModel):
    """Response model for a successful file upload."""

    file_id: str
    filename: str
    status: str


# ... other models can be enhanced similarly

# --- File and Directory Setup ---
DATA_DIR = PROJECT_ROOT / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
CHAT_HISTORY_DIR = DATA_DIR / "chat_history"
for dir_path in [DOCUMENTS_DIR, CHAT_HISTORY_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# --- API Endpoints ---


@app.get("/", response_class=HTMLResponse, tags=["General"])
async def root():
    """Serves a simple welcome page and a link to the API documentation."""
    return HTMLResponse(
        """
        <html>
            <head><title>Celsius AI</title></head>
            <body>
                <h1>🛡️ Celsius AI API is Running</h1>
                <p>API documentation is available at <a href="/docs">/docs</a>.</p>
            </body>
        </html>
    """
    )


@app.get("/api/status", response_model=SystemStatus, tags=["System"])
async def get_system_status(ai_core: CelsiusAI = Depends(get_ai_core)):
    """Provides the current operational status of the Celsius AI system."""
    return SystemStatus(ai_status="online" if ai_core else "offline", last_update=datetime.now().isoformat())


@app.post("/api/chat", response_model=ChatResponse, tags=["AI Interaction"])
async def chat_with_ai(
    message: ChatMessage,
    ai_core: CelsiusAI = Depends(get_ai_core),
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """
    Handles chat interactions with the Celsius AI.
    """
    try:
        response_text = await ai_core.process_query(message.message)
        timestamp = datetime.now().isoformat()
        chat_entry = {
            "timestamp": timestamp,
            "user_message": message.message,
            "ai_response": response_text,
            "session_id": message.session_id or "default",
        }
        await _save_chat_history(chat_entry)
        await ws_manager.broadcast({"type": "chat_message", "data": chat_entry})
        return ChatResponse(response=response_text, timestamp=timestamp)
    except Exception as e:
        logger.error(f"Chat processing error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing chat message.")


@app.get("/api/chat/history", response_model=List[Dict[str, Any]], tags=["Chat History"])
async def get_chat_history(days: int = 7):
    """
    Retrieves chat history from the last specified number of days.
    """
    history = []
    for i in range(days):
        date = datetime.now().date() - timedelta(days=i)
        chat_file = CHAT_HISTORY_DIR / f"chat_{date.strftime('%Y%m%d')}.json"
        if chat_file.exists():
            try:
                async with aiofiles.open(chat_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                    if content:
                        history.extend(json.loads(content))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not read or parse chat history for {date}: {e}")

    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return history[:200]  # Limit to the most recent 200 entries


@app.post("/api/documents/upload", tags=["Document Management"])
async def upload_document(file: UploadFile = File(...)):
    """
    Handles file uploads, validates them, and stores them with metadata.
    """
    allowed_types = {".pdf", ".docx", ".txt", ".json", ".png", ".jpg", ".jpeg"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type '{file_ext}' is not permitted.")

    file_id = str(uuid.uuid4())
    stored_filename = f"{file_id}{file_ext}"
    file_path = DOCUMENTS_DIR / stored_filename

    try:
        content = await file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        metadata = {
            "file_id": file_id,
            "original_filename": file.filename,
            "stored_filename": stored_filename,
            "upload_timestamp": datetime.now().isoformat(),
            "file_size_bytes": len(content),
            "content_type": file.content_type,
        }

        metadata_file = DOCUMENTS_DIR / f"{file_id}_meta.json"
        async with aiofiles.open(metadata_file, "w") as f:
            await f.write(json.dumps(metadata, indent=4))

        return {"file_id": file_id, "filename": file.filename, "status": "uploaded"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")


@app.get("/api/documents/{file_id}", tags=["Document Management"])
async def download_document(file_id: str):
    """
    Allows downloading of a previously uploaded file by its ID.
    """
    metadata_file = DOCUMENTS_DIR / f"{file_id}_meta.json"
    if not metadata_file.exists():
        raise HTTPException(status_code=404, detail="File metadata not found.")

    try:
        async with aiofiles.open(metadata_file, "r") as f:
            metadata = json.loads(await f.read())

        file_path = DOCUMENTS_DIR / metadata["stored_filename"]
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File data not found on server.")

        return FileResponse(
            file_path,
            filename=metadata["original_filename"],
            media_type=metadata.get("content_type", "application/octet-stream"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File download failed: {e}")


@app.get("/api/documents", response_model=List[Dict[str, Any]], tags=["Document Management"])
async def list_documents():
    """
    Lists all available documents by reading their metadata files.
    """
    documents = []
    for metadata_file in DOCUMENTS_DIR.glob("*_meta.json"):
        try:
            async with aiofiles.open(metadata_file, "r") as f:
                documents.append(json.loads(await f.read()))
        except (IOError, json.JSONDecodeError):
            continue  # Skip corrupted metadata files

    documents.sort(key=lambda x: x.get("upload_timestamp", ""), reverse=True)
    return documents


@app.post("/api/whitehat/authorize", tags=["White Hat Authorization"])
async def request_whitehat_authorization(request: AuthorizationRequest):
    """
    Submits a request for white hat penetration testing authorization.
    In a real system, this would trigger a formal review process.
    """
    if not CELSIUS_COMPONENTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="White Hat module is not available.")

    auth_manager = WhiteHatAuthorizationManager()
    # In a real system, you would pass more details from the request.
    auth_id = auth_manager.request_authorization(
        target_system=request.target_system,
        techniques=request.techniques,
        purpose=request.purpose,
        contact_info=request.contact_info,
        duration_hours=request.duration_hours,
    )

    return {
        "authorization_id": auth_id,
        "status": "submitted_for_review",
        "message": "Authorization request has been logged and is pending review.",
    }


@app.get("/api/whitehat/status/{authorization_id}", tags=["White Hat Authorization"])
async def get_whitehat_status(authorization_id: str):
    """
    Checks the status of a specific white hat authorization request.
    """
    if not CELSIUS_COMPONENTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="White Hat module is not available.")

    auth_manager = WhiteHatAuthorizationManager()
    status = auth_manager.get_authorization_status(authorization_id)

    if not status:
        raise HTTPException(status_code=404, detail="Authorization ID not found.")

    return status


# --- WebSocket Endpoint ---


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, ws_manager: WebSocketManager = Depends(get_websocket_manager)):
    """Handles real-time, bidirectional communication with clients."""
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "connection_status",
                "data": {"status": "connected", "message": "Welcome to Celsius AI real-time updates."},
            }
        )
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message from client via WebSocket: {data}")
            # Echo back for demonstration
            await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket.")
    finally:
        ws_manager.disconnect(websocket)


# --- Helper Functions ---
async def _save_chat_history(chat_entry: Dict[str, Any]):
    """Appends a chat interaction to the daily history file."""
    chat_file = CHAT_HISTORY_DIR / f"chat_{datetime.now().strftime('%Y%m%d')}.jsonl"
    try:
        async with aiofiles.open(chat_file, "a", encoding="utf-8") as f:
            await f.write(json.dumps(chat_entry) + "\n")
    except IOError as e:
        logger.error(f"Could not write to chat history file: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting Celsius AI FastAPI server for development...")
    uvicorn.run("src.api.web_interface:app", host="127.0.0.1", port=8000, reload=True, log_level="info")

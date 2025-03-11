from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.endpoints import auth, knowledge_bases, conversations, messages, users
from app.core.middleware import PermissionsMiddleware, DEFAULT_PATH_PERMISSIONS

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],  # Explicitly allow frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Permissions middleware
app.add_middleware(
    PermissionsMiddleware,
    path_permissions=DEFAULT_PATH_PERMISSIONS,
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["Knowledge Bases"])
app.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
app.include_router(messages.router, prefix="/conversations", tags=["Messages"])
app.include_router(users.router, prefix="/users", tags=["Users"])

@app.get("/")
async def root():
    return {"message": "Welcome to DocBrain API"} 
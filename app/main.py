from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.endpoints import auth, knowledge_bases, conversations, messages

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["Knowledge Bases"])
app.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
app.include_router(messages.router, prefix="/conversations", tags=["Messages"])

@app.get("/")
async def root():
    return {"message": "Welcome to DocBrain API"} 
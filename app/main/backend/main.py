from contextlib import asynccontextmanager

from botocore.exceptions import ClientError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from infra.storage.s3.config import get_s3_client
from routers.analytics import router as analytics_router
from routers.auth import router as auth_router
from routers.calls import router as calls_router
from routers.checks import router as checks_router
from routers.integrations import router as integrations_router
from routers.tasks import router as tasks_router
from routers.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=settings.S3_BUCKET_NAME)
    except ClientError:
        s3.create_bucket(Bucket=settings.S3_BUCKET_NAME)
    yield


app = FastAPI(title="AI Calls Analytics", root_path="/main", lifespan=lifespan)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(calls_router, prefix="/api/calls", tags=["calls"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(checks_router, prefix="/api/checks", tags=["checks"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(integrations_router, prefix="/api/integrations", tags=["integrations"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Fastapi running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}

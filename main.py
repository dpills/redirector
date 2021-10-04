import hashlib
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
STATIC_TOKEN = os.getenv("STATIC_TOKEN")
BASE_URL = os.getenv("BASE_URL", "")

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",  # noqa: E501
    datefmt="%d/%b/%Y %H:%M:%S",
)
logger = logging.getLogger("redirector")

app = FastAPI(
    title="Redirector", description="Redirector", version="1.0.0", docs_url="/"
)
security = HTTPBearer()
db = MongoClient(MONGO_URI)[MONGO_DB]


def validate_access_token(
    access_token: HTTPAuthorizationCredentials = Security(security),
):
    """
    Validate Access Token
    """
    if STATIC_TOKEN and access_token.credentials == STATIC_TOKEN:
        return True
    else:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/{alias}")
def redirector(alias: str):
    """
    Find and Redirect URLs
    """
    doc = db.urls.find_one({"alias": alias})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"{alias} not found",
        )

    return RedirectResponse(url=doc.get("original_url"))


class CreateURLResponse(BaseModel):
    alias: str
    short_url: str
    expire_dt: str


@app.post("/create_url", response_model=CreateURLResponse)
def create_url(
    original_url: str,
    custom_alias: Optional[str] = None,
    access_token: HTTPAuthorizationCredentials = Security(security),
    access_token_details: dict = Depends(validate_access_token),
):
    """
    Create URL
    """
    now = datetime.now()
    expire_dt = now + timedelta(days=365)

    if custom_alias:
        if db.urls.find_one({"alias": custom_alias}):
            raise HTTPException(
                status_code=400,
                detail=f"custom alias '{custom_alias}' is already used",
            )
        alias = custom_alias
    else:
        original_url_dt = f"{original_url}_{now}"
        alias = hashlib.md5(original_url_dt.encode()).hexdigest()[:10]

    r = db.urls.insert_one(
        {
            "created_dt": now,
            "expire_dt": expire_dt,
            "original_url": original_url,
            "alias": alias,
        }
    )
    logger.info(f"create_url: {r.inserted_id}")

    return {
        "alias": alias,
        "short_url": f"{BASE_URL}/{alias}",
        "expire_dt": expire_dt.isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)

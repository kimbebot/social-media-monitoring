"""
FastAPI server for managing monitored URLs and running scrapes.
"""
import asyncio
import io
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from loguru import logger

from app.config.settings import settings
from app.src.database.db_manager import db
from app.src.utils.encryption import encryption
from app.src.scrapers.linkedin_company_scraper import LinkedInCompanyScraper

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent
WEB_DIR = REPO_DIR / "web"

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


class MonitoredUrlCreate(BaseModel):
    platform: str
    url: str
    label: Optional[str] = None
    is_active: bool = True


class MonitoredUrlUpdate(BaseModel):
    url: Optional[str] = None
    label: Optional[str] = None
    is_active: Optional[bool] = None


class AccountCreate(BaseModel):
    platform: str
    username: str
    email: Optional[str] = None
    password: str
    is_active: bool = True


class RunScrapeRequest(BaseModel):
    platforms: Optional[List[str]] = Field(default=None)


class ProgressHub:
    def __init__(self):
        self.connections = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.connections.discard(websocket)

    async def broadcast(self, event: dict):
        if not self.connections:
            return
        message = json.dumps(event)
        for ws in list(self.connections):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws)


progress_hub = ProgressHub()
_current_job: Optional[asyncio.Task] = None


@app.on_event("startup")
async def _startup():
    await db.init_db()
    await db.ensure_default_platforms()


@app.get("/")
async def index():
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/api/platforms")
async def list_platforms():
    platforms = await db.get_active_platforms()
    return [{"id": p.id, "name": p.name} for p in platforms]


@app.post("/api/accounts")
async def create_account(payload: AccountCreate):
    platform = await db.get_or_create_platform(payload.platform, base_url="")
    encrypted = encryption.encrypt(payload.password)
    account = await db.create_account(
        platform_id=platform.id,
        username=payload.username,
        email=payload.email or payload.username,
        password_encrypted=encrypted,
    )
    if payload.is_active is False:
        await db.set_account_active(account.id, False)
    return {"id": account.id}


@app.get("/api/monitored-urls")
async def list_monitored_urls():
    urls = await db.list_monitored_urls()
    return [
        {
            "id": u.id,
            "platform_id": u.platform_id,
            "url": u.url,
            "label": u.label,
            "is_active": u.is_active,
            "last_checked_at": u.last_checked_at.isoformat() if u.last_checked_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_exported_at": u.last_exported_at.isoformat() if u.last_exported_at else None,
        }
        for u in urls
    ]


@app.post("/api/monitored-urls")
async def create_monitored_url(payload: MonitoredUrlCreate):
    platform = await db.get_or_create_platform(payload.platform, base_url="")
    monitored = await db.create_monitored_url(
        platform_id=platform.id,
        url=payload.url,
        label=payload.label,
        is_active=payload.is_active,
    )
    return {"id": monitored.id}


@app.patch("/api/monitored-urls/{monitored_id}")
async def update_monitored_url(monitored_id: int, payload: MonitoredUrlUpdate):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated = await db.update_monitored_url(monitored_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "ok"}


@app.delete("/api/monitored-urls/{monitored_id}")
async def delete_monitored_url(monitored_id: int):
    success = await db.delete_monitored_url(monitored_id)
    if not success:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "ok"}


@app.post("/api/run-scrape")
async def run_scrape(payload: RunScrapeRequest = Body(default=RunScrapeRequest())):
    global _current_job
    if _current_job and not _current_job.done():
        raise HTTPException(status_code=409, detail="Scrape already running")

    _current_job = asyncio.create_task(_run_scrape_job(payload.platforms))
    return {"status": "started"}


@app.get("/api/download-new")
async def download_new(platform: Optional[str] = None):
    urls = await db.get_active_monitored_urls()
    if platform:
        platform = platform.lower().strip()

    if not platform:
        raise HTTPException(status_code=400, detail="platform is required")

    wb = Workbook()
    ws = wb.active
    ws.title = f"{platform}-new-posts"
    ws.append(
        [
            "platform",
            "source_url",
            "label",
            "post_url",
            "author_name",
            "author_url",
            "content",
            "posted_at",
            "scraped_at",
            "likes_count",
            "comments_count",
            "shares_count",
        ]
    )
    wrote_rows = False

    for monitored in urls:
        plat = await db.get_platform_by_id(monitored.platform_id)
        if not plat:
            continue
        if platform and plat.name != platform:
            continue

        posts = await db.get_new_posts_for_url(
            monitored.platform_id, monitored.url, monitored.last_exported_at
        )
        if posts:
            for p in posts:
                ws.append(
                    [
                        plat.name,
                        monitored.url,
                        monitored.label,
                        p.post_url,
                        p.author_name,
                        p.author_url,
                        p.content,
                        p.posted_at.isoformat() if p.posted_at else None,
                        p.scraped_at.isoformat() if p.scraped_at else None,
                        p.likes_count,
                        p.comments_count,
                        p.shares_count,
                    ]
                )
                wrote_rows = True

        await db.update_monitored_url(
            monitored.id, {"last_exported_at": datetime.utcnow()}
        )

    if not wrote_rows:
        ws.append(["No new posts found for export"])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=new_posts_{platform}.xlsx"},
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await progress_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        progress_hub.disconnect(websocket)


async def _run_scrape_job(platform_filters: Optional[List[str]]):
    await progress_hub.broadcast({"type": "status", "message": "Starting scrape..."})
    urls = await db.get_active_monitored_urls()

    platforms = {}
    for u in urls:
        if platform_filters:
            platform = await db.get_platform_by_id(u.platform_id)
            if not platform or platform.name not in platform_filters:
                continue
        platforms.setdefault(u.platform_id, []).append(u)

    for platform_id, platform_urls in platforms.items():
        platform = await db.get_platform_by_id(platform_id)
        if not platform:
            continue

        platform_name = platform.name
        if platform_name != "linkedin":
            await progress_hub.broadcast(
                {
                    "type": "status",
                    "platform": platform_name,
                    "message": "No scraper configured yet.",
                }
            )
            continue

        await progress_hub.broadcast(
            {"type": "milestone", "platform": platform_name, "stage": "init"}
        )

        scraper = LinkedInCompanyScraper()
        try:
            await scraper.initialize()
            await scraper.start_browser(headless=settings.headless)

            account = await db.get_first_active_account(platform_id)
            if not account:
                await progress_hub.broadcast(
                    {
                        "type": "error",
                        "platform": platform_name,
                        "message": "No active account configured.",
                    }
                )
                continue

            await progress_hub.broadcast(
                {"type": "milestone", "platform": platform_name, "stage": "login"}
            )
            await scraper.login(account.username, "")

            total = len(platform_urls)
            processed = 0
            saved_total = 0

            for monitored in platform_urls:
                processed += 1
                await progress_hub.broadcast(
                    {
                        "type": "progress",
                        "platform": platform_name,
                        "stage": "scrape",
                        "current": processed,
                        "total": total,
                        "url": monitored.url,
                        "percent": int((processed / total) * 100),
                    }
                )

                posts = await scraper.scrape_company_posts(monitored.url, limit=0)
                saved = await scraper.save_company_posts(posts)
                saved_total += saved

                await db.update_monitored_url(
                    monitored.id, {"last_checked_at": datetime.utcnow()}
                )

                await progress_hub.broadcast(
                    {
                        "type": "milestone",
                        "platform": platform_name,
                        "stage": "save",
                        "current": processed,
                        "total": total,
                    }
                )

            await progress_hub.broadcast(
                {
                    "type": "done",
                    "platform": platform_name,
                    "saved": saved_total,
                    "total": total,
                }
            )

        except Exception as e:
            logger.error(f"Scrape error: {e}")
            await progress_hub.broadcast(
                {"type": "error", "platform": platform_name, "message": str(e)}
            )
        finally:
            await scraper.cleanup()

    await progress_hub.broadcast({"type": "status", "message": "Scrape finished."})

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
from app.src.scrapers.x_scraper import XScraper
from app.src.scrapers.instagram_scraper import InstagramScraper

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


class AccountUpdate(BaseModel):
    is_active: Optional[bool] = None


class AppSettings(BaseModel):
    headless: bool
    enabled_platforms: List[str]


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
_enabled_platforms: Optional[List[str]] = None


def _update_env_setting(key: str, value: str):
    env_path = BASE_DIR.parent / ".env"
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return
    lines = env_path.read_text().splitlines()
    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n")


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


@app.get("/api/settings")
async def get_settings():
    platforms = _enabled_platforms
    if platforms is None:
        platforms = [p.name for p in await db.get_active_platforms()]
    return {"headless": settings.headless, "enabled_platforms": platforms}


@app.patch("/api/settings")
async def update_settings(payload: AppSettings):
    settings.headless = payload.headless
    _update_env_setting("HEADLESS", "true" if payload.headless else "false")
    global _enabled_platforms
    _enabled_platforms = [p.lower() for p in payload.enabled_platforms]
    return {"status": "ok", "headless": settings.headless, "enabled_platforms": _enabled_platforms}


@app.get("/api/accounts")
async def list_accounts():
    accounts = await db.list_accounts()
    return [
        {
            "id": a.id,
            "platform_id": a.platform_id,
            "username": a.username,
            "email": a.email,
            "is_active": a.is_active,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in accounts
    ]


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
    else:
        await db.set_primary_account(platform.id, account.id)
    return {"id": account.id}


@app.patch("/api/accounts/{account_id}")
async def update_account(account_id: int, payload: AccountUpdate):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated = await db.update_account(account_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Not found")
    if "is_active" in data and data["is_active"] is True:
        await db.set_primary_account(updated.platform_id, updated.id)
    return {"status": "ok"}


@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: int):
    success = await db.delete_account(account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "ok"}


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
async def download_new():
    urls = await db.get_active_monitored_urls()

    wb = Workbook()
    ws = wb.active
    ws.title = "new-posts"
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
    filename = f"Social Media Monitoring - {datetime.utcnow().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
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
        platform = await db.get_platform_by_id(u.platform_id)
        if not platform:
            continue
        allowed = platform_filters
        if allowed is None:
            allowed = _enabled_platforms
        if allowed and platform.name not in allowed:
            continue
        platforms.setdefault(u.platform_id, []).append(u)

    for platform_id, platform_urls in platforms.items():
        platform = await db.get_platform_by_id(platform_id)
        if not platform:
            continue

        platform_name = platform.name
        if platform_name not in ("linkedin", "x", "instagram"):
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

        if platform_name == "linkedin":
            scraper = LinkedInCompanyScraper()
        elif platform_name == "instagram":
            scraper = InstagramScraper()
        else:
            scraper = XScraper(platform_name=platform_name)
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
            login_ok = await scraper.login(account.username, "")
            if not login_ok:
                await progress_hub.broadcast(
                    {
                        "type": "error",
                        "platform": platform_name,
                        "message": "Login failed; skipping platform run.",
                    }
                )
                await scraper.cleanup()
                continue

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

                if platform_name == "linkedin":
                    posts = await scraper.scrape_company_posts(monitored.url, limit=0)
                    saved = await scraper.save_company_posts(posts)
                elif platform_name == "instagram":
                    posts = await scraper.scrape_profile_posts(monitored.url, limit=5)
                    saved = await scraper.save_company_posts(posts)
                else:
                    posts = await scraper.scrape_profile_posts(monitored.url, limit=0)
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

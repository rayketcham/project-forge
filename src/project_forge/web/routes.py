"""API and page routes for the Project Forge dashboard."""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from project_forge.engine.scorer import score_summary
from project_forge.models import IdeaCategory, IdeaStatus
from project_forge.web.app import db, templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = await db.get_stats()
    recent_ideas = await db.list_ideas(limit=10)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "stats": stats, "recent_ideas": recent_ideas, "score_summary": score_summary},
    )


@router.get("/ideas", response_class=HTMLResponse)
async def ideas_list(
    request: Request,
    status: IdeaStatus | None = None,
    category: str | None = None,
    page: int = Query(default=1, ge=1),
):
    limit = 20
    offset = (page - 1) * limit
    cat = IdeaCategory(category) if category else None
    ideas = await db.list_ideas(status=status, category=cat, limit=limit, offset=offset)
    total = await db.count_ideas(status=status)
    return templates.TemplateResponse(
        "ideas.html",
        {
            "request": request,
            "ideas": ideas,
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit if total > 0 else 1,
            "status_filter": status,
            "category_filter": category,
            "categories": list(IdeaCategory),
            "score_summary": score_summary,
        },
    )


@router.get("/ideas/{idea_id}", response_class=HTMLResponse)
async def idea_detail(request: Request, idea_id: str):
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return templates.TemplateResponse(
        "idea_detail.html",
        {"request": request, "idea": idea, "score_summary": score_summary},
    )


@router.post("/ideas/{idea_id}/approve")
async def approve_idea(idea_id: str):
    idea = await db.update_idea_status(idea_id, "approved")
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return {"status": "approved", "id": idea_id}


@router.post("/ideas/{idea_id}/reject")
async def reject_idea(idea_id: str):
    idea = await db.update_idea_status(idea_id, "rejected")
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return {"status": "rejected", "id": idea_id}


@router.post("/ideas/{idea_id}/scaffold")
async def scaffold_idea(idea_id: str):
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.status not in ("new", "approved"):
        raise HTTPException(status_code=400, detail=f"Cannot scaffold idea with status: {idea.status}")
    # Scaffolding will be implemented in Phase 4
    await db.update_idea_status(idea_id, "approved")
    return {"status": "scaffold_queued", "id": idea_id}


@router.get("/projects", response_class=HTMLResponse)
async def projects_list(request: Request):
    ideas = await db.list_ideas(status="scaffolded")
    return templates.TemplateResponse(
        "projects.html",
        {"request": request, "projects": ideas},
    )


@router.get("/health")
async def health():
    return {"status": "ok", "service": "project-forge"}


@router.get("/api/stats")
async def api_stats():
    return await db.get_stats()

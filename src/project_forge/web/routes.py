"""API and page routes for the Project Forge dashboard."""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from project_forge.engine.scorer import score_summary
from project_forge.models import IdeaCategory, IdeaStatus
from project_forge.web.app import db, templates

router = APIRouter()


# === PAGE ROUTES ===


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = await db.get_stats()
    top_ideas = await db.list_ideas(limit=6)
    # Sort by score descending
    top_ideas.sort(key=lambda i: i.feasibility_score, reverse=True)
    categories = []
    for cat in IdeaCategory:
        count = len(await db.list_ideas(category=cat, limit=1000))
        ideas_in_cat = await db.list_ideas(category=cat, limit=100)
        avg = sum(i.feasibility_score for i in ideas_in_cat) / len(ideas_in_cat) if ideas_in_cat else 0
        categories.append({"name": cat.value, "count": count, "avg_score": round(avg, 2)})
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "top_ideas": top_ideas[:6],
            "categories": sorted(categories, key=lambda c: c["count"], reverse=True),
            "score_summary": score_summary,
        },
    )


@router.get("/explore", response_class=HTMLResponse)
async def explore(
    request: Request,
    category: str | None = None,
    status: IdeaStatus | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
):
    limit = 12
    offset = (page - 1) * limit
    cat = IdeaCategory(category) if category else None
    ideas = await db.list_ideas(status=status, category=cat, limit=limit, offset=offset)
    if q:
        q_lower = q.lower()
        all_ideas = await db.list_ideas(limit=1000)
        ideas = [
            i
            for i in all_ideas
            if q_lower in i.name.lower() or q_lower in i.tagline.lower() or q_lower in i.description.lower()
        ]
        ideas = ideas[offset : offset + limit]
    total = await db.count_ideas(status=status)
    return templates.TemplateResponse(
        "explore.html",
        {
            "request": request,
            "ideas": ideas,
            "total": total,
            "page": page,
            "pages": max(1, (total + limit - 1) // limit),
            "status_filter": status,
            "category_filter": category,
            "search_query": q or "",
            "categories": list(IdeaCategory),
            "score_summary": score_summary,
        },
    )


@router.get("/ideas", response_class=HTMLResponse)
async def ideas_list(
    request: Request,
    status: IdeaStatus | None = None,
    category: str | None = None,
    page: int = Query(default=1, ge=1),
):
    return await explore(request, category=category, status=status, page=page)


@router.get("/ideas/{idea_id}", response_class=HTMLResponse)
async def idea_detail(request: Request, idea_id: str):
    idea = await db.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    # Get related ideas (same category)
    related = await db.list_ideas(category=idea.category, limit=4)
    related = [r for r in related if r.id != idea.id][:3]
    return templates.TemplateResponse(
        "idea_detail.html",
        {"request": request, "idea": idea, "related": related, "score_summary": score_summary},
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
    await db.update_idea_status(idea_id, "approved")
    return {"status": "scaffold_queued", "id": idea_id}


@router.get("/projects", response_class=HTMLResponse)
async def projects_list(request: Request):
    ideas = await db.list_ideas(status="scaffolded")
    return templates.TemplateResponse(
        "projects.html",
        {"request": request, "projects": ideas},
    )


# === API ROUTES ===


@router.get("/health")
async def health():
    return {"status": "ok", "service": "project-forge"}


@router.get("/api/stats")
async def api_stats():
    return await db.get_stats()


@router.get("/api/top-ideas")
async def api_top_ideas(limit: int = Query(default=10, ge=1, le=50)):
    ideas = await db.list_ideas(limit=100)
    ideas.sort(key=lambda i: i.feasibility_score, reverse=True)
    return [i.model_dump() for i in ideas[:limit]]


@router.get("/api/categories")
async def api_categories():
    result = []
    for cat in IdeaCategory:
        ideas = await db.list_ideas(category=cat, limit=1000)
        count = len(ideas)
        avg = round(sum(i.feasibility_score for i in ideas) / count, 2) if count else 0
        result.append({"name": cat.value, "count": count, "avg_score": avg})
    return result


@router.get("/api/ideas")
async def api_ideas(
    category: str | None = None,
    status: IdeaStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    cat = IdeaCategory(category) if category else None
    ideas = await db.list_ideas(status=status, category=cat, limit=limit, offset=offset)
    total = await db.count_ideas(status=status)
    return {"ideas": [i.model_dump() for i in ideas], "total": total}


@router.get("/api/search")
async def api_search(q: str = Query(min_length=1), limit: int = Query(default=20, ge=1, le=100)):
    q_lower = q.lower()
    all_ideas = await db.list_ideas(limit=1000)
    matches = [
        i
        for i in all_ideas
        if q_lower in i.name.lower() or q_lower in i.tagline.lower() or q_lower in i.description.lower()
    ]
    return {"ideas": [i.model_dump() for i in matches[:limit]], "total": len(matches)}

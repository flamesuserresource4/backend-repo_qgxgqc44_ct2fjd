import os
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup

from database import db, create_document, get_documents
from schemas import SiteContent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# ----------------------
# Content Importer
# ----------------------

class ImportRequest(BaseModel):
    url: str
    language: Optional[str] = None


def extract_text_and_sections(html: str) -> Dict[str, Any]:
    """Parse HTML to collect text and rough sections without altering content."""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove script/style
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    # Collect navigation links if present
    nav_items = []
    for nav in soup.select('nav a[href]'):
        text = nav.get_text(strip=True)
        href = nav.get('href')
        if text:
            nav_items.append({"label": text, "href": href})

    # Heuristic sections by common landmarks
    sections: Dict[str, Any] = {}

    # Hero: first h1 and its following siblings up to next sectioning tag
    h1 = soup.find('h1')
    if h1:
        hero_text = [h1.get_text(" ", strip=True)]
        p = h1.find_next_siblings(limit=3)
        for node in p:
            t = node.get_text(" ", strip=True)
            if t:
                hero_text.append(t)
        sections["hero"] = hero_text

    # Services: lists near h2/h3 containing words like service/услуги
    services_blocks = []
    for hdr in soup.find_all(['h2', 'h3']):
        title = hdr.get_text(" ", strip=True)
        if any(k in title.lower() for k in ["service", "услуги", "сервисы"]):
            block_text = [title]
            for sib in hdr.find_next_siblings(limit=6):
                t = sib.get_text(" ", strip=True)
                if t:
                    block_text.append(t)
            services_blocks.append("\n".join(block_text))
    if services_blocks:
        sections["services"] = services_blocks

    # Testimonials: search for blocks with testimonial-related keywords
    testimonials = []
    for el in soup.find_all(text=True):
        txt = el.strip()
        low = txt.lower()
        if low and any(k in low for k in ["отзывы", "testimonial", "feedback", "клиенты о нас"]):
            parent_block = el.parent.get_text(" ", strip=True)
            if parent_block and parent_block not in testimonials:
                testimonials.append(parent_block)
    if testimonials:
        sections["testimonials"] = testimonials[:10]

    # Contact: forms or contact blocks
    contact_texts = []
    for form in soup.find_all('form'):
        t = form.get_text(" ", strip=True)
        if t:
            contact_texts.append(t)
    contact_headings = []
    for hdr in soup.find_all(['h2', 'h3', 'h4']):
        title = hdr.get_text(" ", strip=True)
        if any(k in title.lower() for k in ["контакт", "contact", "связаться", "заявка"]):
            block = [title]
            for sib in hdr.find_next_siblings(limit=6):
                st = sib.get_text(" ", strip=True)
                if st:
                    block.append(st)
            contact_headings.append("\n".join(block))
    contacts = contact_texts + contact_headings
    if contacts:
        sections["contact"] = contacts

    # Plain text dump
    body = soup.find('body') or soup
    raw_text = body.get_text("\n", strip=True)

    return {
        "raw_text": raw_text,
        "sections": sections,
        "navigation": nav_items,
    }


@app.post("/api/import", response_model=SiteContent)
def import_content(req: ImportRequest):
    """Fetch a URL and store its text content verbatim into the database."""
    try:
        resp = requests.get(req.url, timeout=20)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"Upstream returned {resp.status_code}")

    extracted = extract_text_and_sections(resp.text)

    doc = SiteContent(
        source_url=req.url,
        language=req.language,
        raw_html=resp.text,
        raw_text=extracted.get("raw_text"),
        sections=extracted.get("sections"),
        navigation=extracted.get("navigation"),
    )

    try:
        inserted_id = create_document("sitecontent", doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return doc


@app.get("/api/content", response_model=list[SiteContent])
def get_latest_content(limit: int = 1):
    try:
        docs = get_documents("sitecontent", {}, limit=limit)
        # Convert to Pydantic models while preserving raw text
        out = []
        for d in docs:
            out.append(SiteContent(
                source_url=d.get("source_url", ""),
                language=d.get("language"),
                raw_html=d.get("raw_html"),
                raw_text=d.get("raw_text"),
                sections=d.get("sections", {}),
                navigation=d.get("navigation", []),
            ))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from duckduckgo_search import DDGS
import uvicorn
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import httpx
import asyncio

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def perform_search(query, max_results=10):
    results = []
    
    # Helper to check if results are poor
    def is_poor_quality(results):
        if not results:
            return True
        first_title = results[0].get('title', '').lower()
        # Check for spelling/definition results
        if "spelling" in first_title or "correct" in first_title or "definition" in first_title or "vs" in first_title:
            return True
        # Check for Chinese characters (common issue with "2025" queries)
        for char in first_title:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    # Helper to clean query (remove year)
    def clean_query_year(q):
        import re
        return re.sub(r'\s+202[0-9]', '', q)

    # 1. Try original query
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region='in-en', max_results=max_results))
    except Exception as e:
        print(f"Error with default backend: {e}")

    # Helper to run search and check quality
    def try_search(q):
        try:
            with DDGS() as ddgs:
                res = list(ddgs.text(q, region='in-en', max_results=max_results))
                if res and not is_poor_quality(res):
                    return res
        except Exception:
            pass
        return None

    # Helper to get suggestion
    def get_suggestion(q):
        try:
            suggestions = get_autocomplete_suggestions(q)
            if suggestions and len(suggestions) > 1 and isinstance(suggestions[1], list) and len(suggestions[1]) > 0:
                top = suggestions[1][0]
                if top.lower().strip() != q.lower().strip():
                    return top
        except Exception:
            pass
        return None

    if is_poor_quality(results):
        # 2. Try Cleaned Query (No Year)
        cleaned_query = clean_query_year(query)
        if cleaned_query != query:
            print(f"Poor results. Trying without year: {cleaned_query}")
            new_results = try_search(cleaned_query)
            if new_results:
                results = new_results
                query = cleaned_query
            else:
                # 3. Try Suggestions (Cleaned)
                suggestion_cleaned = get_suggestion(cleaned_query)
                if suggestion_cleaned:
                    print(f"Poor results. Trying suggestion for cleaned query: {suggestion_cleaned}")
                    new_results = try_search(suggestion_cleaned)
                    if new_results:
                        results = new_results
                        query = suggestion_cleaned

    if is_poor_quality(results):
        # 4. Try Suggestions (Original) - Fallback
        suggestion_original = get_suggestion(query)
        if suggestion_original:
            print(f"Poor results. Trying suggestion for original query: {suggestion_original}")
            new_results = try_search(suggestion_original)
            if new_results:
                results = new_results
                query = suggestion_original

    # 5. Fallback to 'html' backend if still no results or very poor
    if not results:
        try:
            print("Falling back to 'html' backend")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region='in-en', backend='html', max_results=max_results))
        except Exception as e:
            print(f"Error with html backend: {e}")
            
    return results

def fetch_instant_answer(query):
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        response = requests.get(url, params=params)
        data = response.json()
        return data.get("AbstractText") or data.get("Abstract") or "No instant answer available."
    except Exception as e:
        print(f"Error fetching instant answer: {e}")
        return "Error fetching instant answer."

def image_search(query, max_results=10):
    try:
        with DDGS() as ddgs:
            return list(ddgs.images(query, region='in-en', max_results=max_results))
    except Exception as e:
        print(f"Error fetching images: {e}")
        return []

def get_autocomplete_suggestions(query):
    try:
        url = f"https://duckduckgo.com/ac/?q={query}&type=list"
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error fetching suggestions: {e}")
        return []

def get_related_topics(query):
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json"}
        response = requests.get(url, params=params)
        data = response.json()
        return data.get("RelatedTopics", [])
    except Exception as e:
        print(f"Error fetching related topics: {e}")
        return []

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    results = perform_search(query, max_results=10)
    
    return templates.TemplateResponse(request=request, name="results.html", context={"results": results, "query": query})

@app.get("/api/search")
async def api_search(query: str):
    results = perform_search(query, max_results=10)
    return {"results": results}

@app.get("/api/instant-answer")
async def api_instant_answer(query: str):
    answer = fetch_instant_answer(query)
    return {"answer": answer}

@app.get("/api/images")
async def api_images(query: str):
    images = image_search(query)
    return {"images": images}

@app.get("/api/autocomplete")
async def api_autocomplete(query: str):
    suggestions = get_autocomplete_suggestions(query)
    return {"suggestions": suggestions}

@app.get("/api/related-topics")
async def api_related_topics(query: str):
    topics = get_related_topics(query)
    return {"topics": topics}

@app.get("/api/read")
async def api_read(url: str):
    try:
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text()
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return {"url": url, "content": text}
    except Exception as e:
        return {"url": url, "error": str(e)}

async def fetch_and_parse(client, url):
    try:
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        response = await client.get(url, headers=headers, timeout=10, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    except Exception:
        return "Error fetching content."

@app.get("/api/deep-search")
async def api_deep_search(query: str, max_results: int = 5):
    results = perform_search(query, max_results=max_results)
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for result in results:
            tasks.append(fetch_and_parse(client, result['href']))
        
        contents = await asyncio.gather(*tasks)
        
        for i, content in enumerate(contents):
            results[i]['full_content'] = content
            
    return {"query": query, "results": results}

@app.get("/llm-view", response_class=HTMLResponse)
async def llm_view(request: Request, query: str, max_results: int = 5):
    # Reuse the logic or call the function directly if possible, but for now let's just fetch via internal call or duplicate logic? 
    # Better to call the function logic.
    data = await api_deep_search(query, max_results)
    return templates.TemplateResponse(request=request, name="llm_view.html", context={"data": data})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

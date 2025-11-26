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
    try:
        # Try default backend (api)
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region='wt-wt', max_results=max_results))
    except Exception as e:
        print(f"Error with default backend: {e}")
    
    # If no results or error, try 'html' backend
    if not results:
        try:
            print("Falling back to 'html' backend")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region='wt-wt', backend='html', max_results=max_results))
        except Exception as e:
            print(f"Error with html backend: {e}")
            
    return results

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

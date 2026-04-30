from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import bleach

app = FastAPI()

ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong']
ALLOWED_ATTRIBUTES = {}

def sanitize_comment(text: str) -> str:
    return bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )

comments_db = []

@app.middleware("http")
async def add_csp_header(request: Request, call_next):
    response = await call_next(request)
    csp = "default-src 'self'; script-src 'self'; style-src 'self';"
    response.headers["Content-Security-Policy"] = csp
    return response

@app.get("/comments", response_class=HTMLResponse)
def get_comments():
    comments_html = "".join(f"<li>{comment}</li>" for comment in comments_db)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Comments</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Оставить объявление</h1>
        <form method="post" action="/comments">
            <textarea name="text" rows="4" cols="50" placeholder="Ваше сообщение..."></textarea><br>
            <button type="submit">Send</button>
        </form>
        <h2>Ранее оставленные:</h2>
        <ul>
            {comments_html}
        </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.post("/comments")
def post_comments(text: str = Form(...)):
    clean_text = sanitize_comment(text)
    comments_db.append(clean_text)
    return RedirectResponse(url="/comments", status_code=303)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

comments_db = []

# CSP middleware
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
    <head><title>Comments (CSP only)</title></head>
    <body>
        <h1>Оставить объявление</h1>
        <form method="post" action="/comments">
            <textarea name="text" rows="4" cols="50"></textarea><br>
            <button type="submit">Send</button>
        </form>
        <h2>Ранее оставленные:</h2>
        <ul>{comments_html}</ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.post("/comments")
def post_comments(text: str = Form(...)):
    comments_db.append(text)   # без очистки
    return RedirectResponse(url="/comments", status_code=303)

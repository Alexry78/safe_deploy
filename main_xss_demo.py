from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

comments_db = []

@app.get("/comments", response_class=HTMLResponse)
def get_comments():
    comments_html = "".join(f"<li>{comment}</li>" for comment in comments_db)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Comments (УЯЗВИМАЯ ВЕРСИЯ)</title>
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
    # ⚠️ ВНИМАНИЕ: ПОЛНАЯ УЯЗВИМОСТЬ — НЕТ НИКАКОЙ ЗАЩИТЫ
    comments_db.append(text)  # напрямую добавляем опасный ввод
    return RedirectResponse(url="/comments", status_code=303)

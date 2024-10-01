# ------------------------------ PACKAGES ------------------------------
# Third-party libraries
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import (
    get_swagger_ui_oauth2_redirect_html,
    get_swagger_ui_html,
)

# Local imports
from src.app import app
from fastapi.staticfiles import StaticFiles

# ------------------------------ MAIN ------------------------------
router = APIRouter(prefix="/docs", tags=["docs"])

app.mount("/docs/styles", StaticFiles(directory="documentation/static/styles"))


@router.get("/", include_in_schema=False)
async def custom_swagger_ui_html():
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
    )
    html_content = html.body.decode("utf-8")
    modified_html_content = html_content.replace(
        "</head>",
        '<link rel="stylesheet" type="text/css" href="/docs/styles/theme-flattop.css"></head>',
    )
    return HTMLResponse(content=modified_html_content)


@router.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@router.get("/scans", response_class=HTMLResponse)
async def scan_documentation():
    try:
        with open("documentation/static/scan.html", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="HTML page not found")


@router.get("/users", response_class=HTMLResponse)
async def user_documentation():
    try:
        with open("documentation/static/user.html", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="HTML page not found")

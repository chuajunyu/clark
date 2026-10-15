from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from storage import (
    add_print_revision,
    get_voucher,
    get_vouchers,
    list_vouchers,
    save_voucher,
)
from voucher_pdf import OUTPUT_DIR, make_a4_pdf, make_direct_revision, normalize_data, format_voucher_date


BASE_DIR = Path(__file__).parent
app = FastAPI(title="Clark")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["voucher_date"] = format_voucher_date
templates.env.globals["asset_version"] = lambda name: sha256(
    (BASE_DIR / "static" / name).read_bytes()
).hexdigest()[:12]
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/healthz", include_in_schema=False)
def healthcheck():
    """Report whether the web process is ready to serve requests."""
    return {"status": "ok"}


def blank_voucher() -> dict:
    return normalize_data({
        "id": "", "voucher_number": "", "voucher_date": "", "payee": "",
        "line_items": [], "payment_method": "", "account_code": "",
        "approved_by": "", "received_by": "", "record_version": 0,
        "print_history": [],
    })


def parse_voucher_date(value: str) -> str:
    value = value.strip()
    try:
        return datetime.strptime(value, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        return value


def voucher_values(form) -> dict:
    line_items = [
        {"description": str(form.get(f"description_{index}", "")), "amount": str(form.get(f"amount_{index}", ""))}
        for index in range(1, 8)
    ]
    return normalize_data({
        "voucher_number": str(form.get("voucher_number", "")),
        "voucher_date": parse_voucher_date(str(form.get("voucher_date", ""))),
        "payee": str(form.get("payee", "")),
        "line_items": line_items,
        "payment_method": str(form.get("payment_method", "")),
        "account_code": str(form.get("account_code", "")),
        "approved_by": str(form.get("approved_by", "")),
        "received_by": str(form.get("received_by", "")),
    })


def render_editor(request: Request, voucher: dict, message: str = "", tray_add_id: str = ""):
    return templates.TemplateResponse("editor.html", {
        "request": request, "voucher": voucher, "message": message,
        "tray_add_id": tray_add_id, "is_new": not voucher.get("id"),
    })


def pdf_file(filename: str) -> Path | None:
    if filename != Path(filename).name:
        return None
    path = OUTPUT_DIR / filename
    return path if path.is_file() else None


@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse("/vouchers/new", status_code=302)


@app.get("/vouchers/new", response_class=HTMLResponse)
def new_voucher(request: Request):
    return render_editor(request, blank_voucher())


@app.get("/vouchers", response_class=HTMLResponse)
def saved_vouchers(request: Request, q: str = ""):
    return templates.TemplateResponse("saved_vouchers.html", {
        "request": request, "vouchers": list_vouchers(q), "query": q,
    })


@app.get("/vouchers/{voucher_id}/view", response_class=HTMLResponse)
def view_voucher(request: Request, voucher_id: str, saved: int = 0, tray_added: int = 0):
    voucher = get_voucher(voucher_id)
    if not voucher:
        return templates.TemplateResponse("message.html", {
            "request": request, "title": "Voucher not found",
            "message": "That saved voucher could not be found.",
        }, status_code=404)
    message = "Voucher saved." if saved else ""
    if tray_added:
        message = "Voucher saved and added to the A4 print tray."
    return render_editor(request, voucher, message, voucher_id if tray_added else "")


@app.post("/vouchers/action")
async def voucher_action(request: Request):
    form = await request.form()
    action = str(form.get("action", "save"))
    voucher_id = str(form.get("voucher_id", ""))
    try:
        voucher = save_voucher(voucher_values(form), voucher_id)
    except RuntimeError as exc:
        return templates.TemplateResponse("message.html", {
            "request": request, "title": "Voucher could not be saved", "message": str(exc),
        }, status_code=500)

    if action == "direct":
        revision_number = len(voucher.get("print_history", [])) + 1
        direct, archive = make_direct_revision(voucher, revision_number)
        add_print_revision(voucher["id"], {
            "revision": revision_number,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "direct_pdf": direct.name,
            "archive_pdf": archive.name,
        })
        return RedirectResponse(f"/vouchers/{voucher['id']}/prints/{revision_number}", status_code=303)
    if action == "tray":
        return RedirectResponse(f"/vouchers/{voucher['id']}/view?tray_added=1", status_code=303)
    return RedirectResponse(f"/vouchers/{voucher['id']}/view?saved=1", status_code=303)


@app.get("/vouchers/{voucher_id}/edit")
def legacy_edit_voucher(voucher_id: str):
    return RedirectResponse(f"/vouchers/{voucher_id}/view", status_code=302)


@app.get("/vouchers/{voucher_id}/prints/{revision_number}", response_class=HTMLResponse)
def print_revision(request: Request, voucher_id: str, revision_number: int):
    voucher = get_voucher(voucher_id)
    if not voucher:
        return HTMLResponse("Voucher not found", status_code=404)
    revision = next((item for item in voucher.get("print_history", []) if int(item.get("revision", 0)) == revision_number), None)
    if not revision:
        return HTMLResponse("Print revision not found", status_code=404)
    return templates.TemplateResponse("print_preview.html", {
        "request": request,
        "title": f"Voucher print preview - revision {revision_number}",
        "subtitle": voucher.get("voucher_number") or "Untitled voucher",
        "pdf_name": revision["direct_pdf"], "archive_name": revision["archive_pdf"],
        "edit_url": f"/vouchers/{voucher_id}/view", "is_direct": True,
    })


@app.get("/tray", response_class=HTMLResponse)
def a4_tray(request: Request):
    return templates.TemplateResponse("a4_tray.html", {"request": request})


@app.post("/print/a4", response_class=HTMLResponse)
async def print_a4(request: Request):
    form = await request.form()
    try:
        raw_ids = json.loads(str(form.get("voucher_ids_json", "[]")))
    except json.JSONDecodeError:
        raw_ids = []
    voucher_ids = []
    for value in raw_ids if isinstance(raw_ids, list) else []:
        voucher_id = str(value)
        if voucher_id and voucher_id not in voucher_ids:
            voucher_ids.append(voucher_id)
    vouchers = get_vouchers(voucher_ids)
    if not vouchers:
        return RedirectResponse("/tray?error=empty", status_code=303)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = make_a4_pdf(vouchers, f"a4_{stamp}_{uuid4().hex[:6]}.pdf")
    return templates.TemplateResponse("print_preview.html", {
        "request": request, "title": "A4 voucher sheet preview",
        "subtitle": f"{len(vouchers)} voucher{'s' if len(vouchers) != 1 else ''} - two per A4 page",
        "pdf_name": path.name, "archive_name": "", "edit_url": "/tray", "is_direct": False,
    })


@app.get("/api/vouchers/summaries")
def voucher_summaries(ids: str = ""):
    vouchers = get_vouchers([value for value in ids.split(",") if value])
    return JSONResponse({"vouchers": [{
        "id": voucher["id"], "voucher_number": voucher.get("voucher_number", ""),
        "voucher_date": format_voucher_date(voucher.get("voucher_date", "")), "payee": voucher.get("payee", ""),
        "amount": voucher.get("amount", "0.00"),
    } for voucher in vouchers]})


@app.get("/pdf/{filename}")
def inline_pdf(filename: str):
    path = pdf_file(filename)
    if not path:
        return HTMLResponse("PDF not found", status_code=404)
    return FileResponse(path, media_type="application/pdf", filename=path.name, content_disposition_type="inline")


@app.get("/download/{filename}")
def download_pdf(filename: str):
    path = pdf_file(filename)
    if not path:
        return HTMLResponse("PDF not found", status_code=404)
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@app.get("/files/{filename}")
def legacy_download(filename: str):
    return download_pdf(filename)

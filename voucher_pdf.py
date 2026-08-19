"""ReportLab PDF generation for Clark payment vouchers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import os
from pathlib import Path
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from config import CONFIG, pt


BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output" / "pdf"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ONES = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def clean_filename(value: str) -> str:
    safe = "".join(character if character.isalnum() or character in "-_" else "_" for character in value)
    return safe.strip("_") or "voucher"


def normalize_data(data: dict) -> dict:
    normalized = dict(data)
    raw_items = normalized.get("line_items")
    if not isinstance(raw_items, list):
        raw_items = [{"description": normalized.get("description", ""), "amount": normalized.get("amount", "")}]
    items = []
    for item in raw_items[:7]:
        if isinstance(item, dict):
            items.append({
                "description": str(item.get("description", "")).strip(),
                "amount": str(item.get("amount", "")).strip(),
            })
    while len(items) < 7:
        items.append({"description": "", "amount": ""})
    total = Decimal("0")
    invalid_amounts = []
    has_amount = False
    for index, item in enumerate(items, start=1):
        has_amount = has_amount or bool(item["amount"])
        try:
            total += Decimal(item["amount"].replace(",", "")) if item["amount"] else Decimal("0")
        except InvalidOperation:
            invalid_amounts.append(index)
    normalized["line_items"] = items
    normalized["amount"] = f"{total:.2f}"
    normalized["description"] = "; ".join(item["description"] for item in items if item["description"])
    normalized["invalid_amount_rows"] = invalid_amounts
    normalized["has_amount"] = has_amount
    for key in ("voucher_number", "voucher_date", "payee", "payment_method", "account_code", "approved_by", "received_by"):
        normalized[key] = str(normalized.get(key, "")).strip()
    return normalized


def integer_words(number: int) -> str:
    if number < 0:
        return "Minus " + integer_words(abs(number))
    if number < 20:
        return ONES[number]
    if number < 100:
        return TENS[number // 10] + ("-" + ONES[number % 10] if number % 10 else "")
    if number < 1000:
        return ONES[number // 100] + " Hundred" + (" " + integer_words(number % 100) if number % 100 else "")
    for value, name in ((1_000_000, "Million"), (1_000, "Thousand")):
        if number >= value:
            return integer_words(number // value) + f" {name}" + (" " + integer_words(number % value) if number % value else "")
    return str(number)


def amount_words(value: str) -> str:
    try:
        amount = Decimal(value.replace(",", "")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return value
    dollars = int(amount)
    cents = int((amount - dollars) * 100)
    result = f"{integer_words(dollars)} Dollars"
    if cents:
        result += f" and {integer_words(cents)} Cents"
    return result + " Only"


class VoucherGeometry:
    def __init__(self, width: float, height: float):
        layout = CONFIG["layout"]
        self.width = width
        self.height = height
        self.sx = width / pt(layout["base_width_mm"])
        self.sy = height / pt(layout["base_height_mm"])

    def x(self, key: str) -> float:
        return pt(CONFIG["layout"][key]) * self.sx

    def y(self, key: str) -> float:
        return self.height - pt(CONFIG["layout"][key]) * self.sy

    def ys(self, top_mm: float) -> float:
        return self.height - pt(top_mm) * self.sy


def fit_text(value: str, font: str, size: float, max_width: float) -> str:
    if stringWidth(value, font, size) <= max_width:
        return value
    suffix = "..."
    while value and stringWidth(value + suffix, font, size) > max_width:
        value = value[:-1]
    return value.rstrip() + suffix


def wrap_text(value: str, font: str, size: float, max_width: float, max_lines: int) -> list[str]:
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(lines)) < len(value):
        lines[-1] = fit_text(lines[-1], font, size, max_width)
    return lines


def draw_dotted_line(pdf: canvas.Canvas, x1: float, y: float, x2: float) -> None:
    pdf.saveState()
    pdf.setDash(1, 2)
    pdf.setLineWidth(0.5)
    pdf.line(x1, y, x2, y)
    pdf.restoreState()


def draw_structure(pdf: canvas.Canvas, geometry: VoucherGeometry) -> None:
    layout = CONFIG["layout"]
    style = CONFIG["style"]
    left, right = geometry.x("content_left_mm"), geometry.x("content_right_mm")
    divider = geometry.x("description_amount_divider_x_mm")
    inner = geometry.x("amount_inner_divider_x_mm")
    pdf.setStrokeColor(colors.HexColor("#3d4347"))
    pdf.setFillColor(colors.HexColor("#343a40"))
    pdf.setLineWidth(style["line_width_pt"])
    pdf.setFont(style["font_bold"], style["title_size"])
    pdf.drawString(geometry.x("title_x_mm"), geometry.y("title_y_mm"), "PAYMENT VOUCHER")
    pdf.setFont(style["font"], style["label_size"])
    pdf.drawString(geometry.x("voucher_label_x_mm"), geometry.y("voucher_y_mm"), "Voucher No :")
    pdf.drawString(geometry.x("date_label_x_mm"), geometry.y("date_y_mm"), "Date :")
    draw_dotted_line(pdf, geometry.x("voucher_value_x_mm"), geometry.y("voucher_y_mm") - 1, right)
    draw_dotted_line(pdf, geometry.x("date_value_x_mm"), geometry.y("date_y_mm") - 1, right)
    pdf.setFont(style["font"], style["label_size"] + 1)
    pdf.drawString(geometry.x("pay_label_x_mm"), geometry.y("pay_y_mm"), "PAY TO")
    pdf.line(left, geometry.y("pay_line_y_mm"), right, geometry.y("pay_line_y_mm"))
    pdf.setFont(style["font_bold"], style["label_size"] + 1)
    pdf.drawCentredString(geometry.x("description_center_x_mm"), geometry.y("table_header_y_mm"), "D E S C R I P T I O N")
    pdf.drawCentredString(geometry.x("amount_center_x_mm"), geometry.y("table_header_y_mm"), "A M O U N T")
    pdf.line(left, geometry.y("table_header_bottom_y_mm"), right, geometry.y("table_header_bottom_y_mm"))
    for top_mm in layout["table_row_lines_y_mm"]:
        pdf.line(left, geometry.ys(top_mm), right, geometry.ys(top_mm))
    pdf.line(divider, geometry.y("pay_line_y_mm"), divider, geometry.y("account_row_bottom_y_mm"))
    pdf.line(inner, geometry.y("table_header_bottom_y_mm"), inner, geometry.y("account_row_bottom_y_mm"))
    pdf.setFont(style["font"], style["label_size"])
    pdf.drawString(geometry.x("account_label_x_mm"), geometry.y("account_value_y_mm"), "A/c")
    pdf.drawString(geometry.x("payment_label_x_mm"), geometry.y("payment_value_y_mm"), "Cash/Cheque/Online")
    pdf.drawString(geometry.x("total_currency_x_mm"), geometry.y("total_value_y_mm"), "$")
    pdf.line(left, geometry.y("account_row_bottom_y_mm"), right, geometry.y("account_row_bottom_y_mm"))
    account_divider = geometry.x("account_payment_divider_x_mm")
    pdf.line(account_divider, geometry.ys(layout["table_row_lines_y_mm"][-1]), account_divider, geometry.y("account_row_bottom_y_mm"))
    pdf.drawString(geometry.x("sum_label_x_mm"), geometry.y("sum_label_y_mm"), "The Sum of Dollars :")
    draw_dotted_line(pdf, geometry.x("sum_value_x_mm"), geometry.y("sum_first_y_mm") - 1, right)
    draw_dotted_line(pdf, left, geometry.y("sum_second_y_mm") - 1, right)
    pdf.drawString(geometry.x("approved_label_x_mm"), geometry.y("signature_y_mm"), "Payment Approved by :")
    pdf.drawString(geometry.x("received_label_x_mm"), geometry.y("signature_y_mm"), "Received by :")
    draw_dotted_line(pdf, geometry.x("approved_value_x_mm"), geometry.y("signature_y_mm") - 1, geometry.x("received_label_x_mm") - 4)
    draw_dotted_line(pdf, geometry.x("received_value_x_mm"), geometry.y("signature_y_mm") - 1, right)


def draw_values(pdf: canvas.Canvas, geometry: VoucherGeometry, data: dict) -> None:
    layout = CONFIG["layout"]
    style = CONFIG["style"]
    font = style["font"]
    size = style["value_size"]
    right = geometry.x("content_right_mm")
    divider = geometry.x("description_amount_divider_x_mm")
    pdf.setFillColor(colors.black)
    pdf.setFont(font, size)
    pdf.drawString(geometry.x("voucher_value_x_mm"), geometry.y("voucher_y_mm"), fit_text(data["voucher_number"], font, size, right - geometry.x("voucher_value_x_mm")))
    pdf.drawString(geometry.x("date_value_x_mm"), geometry.y("date_y_mm"), fit_text(data["voucher_date"], font, size, right - geometry.x("date_value_x_mm")))
    pdf.drawString(geometry.x("pay_value_x_mm"), geometry.y("pay_y_mm"), fit_text(data["payee"], font, size, right - geometry.x("pay_value_x_mm")))
    description_width = divider - geometry.x("description_x_mm") - 4
    for index, item in enumerate(data["line_items"][:layout["description_rows"]]):
        top = layout["description_first_y_mm"] + index * layout["description_line_gap_mm"]
        if item["description"]:
            pdf.drawString(geometry.x("description_x_mm"), geometry.ys(top), fit_text(item["description"], font, size, description_width))
        if item["amount"]:
            pdf.drawRightString(geometry.x("amount_value_right_x_mm"), geometry.ys(top), item["amount"])
    small_size = style["small_value_size"]
    pdf.setFont(font, small_size)
    pdf.drawString(geometry.x("account_value_x_mm"), geometry.y("account_value_y_mm"), fit_text(data["account_code"], font, small_size, geometry.x("account_payment_divider_x_mm") - geometry.x("account_value_x_mm") - 3))
    pdf.drawString(geometry.x("payment_value_x_mm"), geometry.y("payment_value_y_mm"), fit_text(data["payment_method"], font, small_size, divider - geometry.x("payment_value_x_mm") - 3))
    pdf.setFont(font, size)
    if data.get("has_amount"):
        pdf.drawRightString(geometry.x("total_value_right_x_mm"), geometry.y("total_value_y_mm"), data["amount"])
    words = wrap_text(amount_words(data["amount"]), font, small_size, right - geometry.x("sum_value_x_mm"), 2) if data.get("has_amount") else []
    pdf.setFont(font, small_size)
    if words:
        pdf.drawString(geometry.x("sum_value_x_mm"), geometry.y("sum_first_y_mm"), words[0])
        if len(words) > 1:
            pdf.drawString(geometry.x("content_left_mm"), geometry.y("sum_second_y_mm"), words[1])
    pdf.drawString(geometry.x("approved_value_x_mm"), geometry.y("signature_y_mm"), data["approved_by"])
    pdf.drawString(geometry.x("received_value_x_mm"), geometry.y("signature_y_mm"), data["received_by"])


def draw_voucher(pdf: canvas.Canvas, x: float, y: float, width: float, height: float, data: dict, include_structure: bool, apply_offsets: bool = False) -> None:
    pdf.saveState()
    offset_x = pt(CONFIG["direct"]["offset_x_mm"]) if apply_offsets else 0
    offset_y = -pt(CONFIG["direct"]["offset_y_mm"]) if apply_offsets else 0
    pdf.translate(x + offset_x, y + offset_y)
    geometry = VoucherGeometry(width, height)
    if include_structure:
        draw_structure(pdf, geometry)
    draw_values(pdf, geometry, data)
    pdf.restoreState()


def _atomic_pdf(final_path: Path, builder) -> Path:
    temporary = final_path.with_name(f".{final_path.name}.{uuid4().hex}.tmp")
    try:
        builder(temporary)
        os.replace(temporary, final_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return final_path


def make_single_pdf(
    data: dict,
    final_path: Path,
    include_structure: bool,
    apply_offsets: bool,
    use_a5_wrapper: bool = False,
) -> Path:
    data = normalize_data(data)
    direct_config = CONFIG["direct"]
    voucher_width = pt(direct_config["width_mm"])
    voucher_height = pt(direct_config["height_mm"])
    if use_a5_wrapper:
        page_width = pt(direct_config["pdf_page_width_mm"])
        page_height = pt(direct_config["pdf_page_height_mm"])
        content_x = pt(direct_config["page_content_x_mm"])
        content_y = page_height - voucher_height - pt(direct_config["page_content_y_mm"])
    else:
        page_width = voucher_width
        page_height = voucher_height
        content_x = 0
        content_y = 0

    def build(path: Path) -> None:
        pdf = canvas.Canvas(str(path), pagesize=(page_width, page_height))
        draw_voucher(
            pdf,
            content_x,
            content_y,
            voucher_width,
            voucher_height,
            data,
            include_structure=include_structure,
            apply_offsets=apply_offsets,
        )
        pdf.showPage()
        pdf.save()

    return _atomic_pdf(final_path, build)


def make_direct_revision(data: dict, revision: int) -> tuple[Path, Path]:
    normalized = normalize_data(data)
    short_id = str(normalized.get("id", "voucher"))[:6]
    number = clean_filename(normalized["voucher_number"])
    voucher_date = clean_filename(normalized["voucher_date"] or "undated")
    stem = f"{number}_{voucher_date}_{short_id}_r{revision:03d}"
    direct = OUTPUT_DIR / f"{stem}_direct_print.pdf"
    archive = OUTPUT_DIR / f"{stem}_archive.pdf"
    make_single_pdf(normalized, archive, include_structure=True, apply_offsets=False)
    make_single_pdf(
        normalized,
        direct,
        include_structure=False,
        apply_offsets=True,
        use_a5_wrapper=True,
    )
    return direct, archive


def make_a4_pdf(vouchers: list[dict], filename: str) -> Path:
    normalized = [normalize_data(voucher) for voucher in vouchers]
    final_path = OUTPUT_DIR / filename

    def build(path: Path) -> None:
        pdf = canvas.Canvas(str(path), pagesize=A4)
        slot_width = A4[0]
        slot_height = A4[1] / 2
        mark = pt(CONFIG["a4"]["crop_mark_mm"])
        for page_start in range(0, len(normalized), 2):
            pair = normalized[page_start:page_start + 2]
            for position, data in enumerate(pair):
                y = slot_height if position == 0 else 0
                draw_voucher(pdf, 0, y, slot_width, slot_height, data, include_structure=True)
            middle = A4[1] / 2
            pdf.setStrokeColor(colors.black)
            pdf.setLineWidth(0.4)
            pdf.line(0, middle, mark, middle)
            pdf.line(A4[0] - mark, middle, A4[0], middle)
            pdf.line(A4[0] / 2, middle - mark / 2, A4[0] / 2, middle + mark / 2)
            pdf.showPage()
        pdf.save()

    return _atomic_pdf(final_path, build)

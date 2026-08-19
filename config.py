"""Physical print configuration for Clark.

All coordinates are millimetres from the top-left of the nominal voucher.
Change this file - not application code - when calibrating paper or field positions.
"""

from reportlab.lib.units import mm

CONFIG = {
    "direct": {
        # Voucher coordinates remain 210 x 140 mm. The values-only PDF is
        # wrapped in an A5 landscape page so browser print dialogs can select
        # a standard paper size without scaling the voucher layout.
        "width_mm": 210.0,
        "height_mm": 140.0,
        "pdf_page_width_mm": 210.0,
        "pdf_page_height_mm": 148.0,
        # Position of the 210 x 140 voucher area inside the A5 page,
        # measured from the page's top-left corner.
        "page_content_x_mm": 0.0,
        "page_content_y_mm": 4.0,
        "offset_x_mm": 0.0,
        "offset_y_mm": -1.5,
    },
    "a4": {
        "width_mm": 210.0,
        "height_mm": 297.0,
        "vouchers_per_page": 2,
        "crop_mark_mm": 5.0,
    },
    "style": {
        "font": "Helvetica",
        "font_bold": "Helvetica-Bold",
        "value_size": 8.5,
        "small_value_size": 7.5,
        "label_size": 7.5,
        "title_size": 13.0,
        "line_width_pt": 0.65,
    },
    "layout": {
        # Reference geometry follows the supplied scan, normalized to 210 x 140 mm.
        "base_width_mm": 210.0,
        "base_height_mm": 140.0,
        "content_left_mm": 27.0,
        "content_right_mm": 194.0,
        "title_x_mm": 27.0,
        "title_y_mm": 14.0,
        "voucher_label_x_mm": 140.0,
        "voucher_value_x_mm": 162.0,
        "voucher_y_mm": 12.0,
        "date_label_x_mm": 140.0,
        "date_value_x_mm": 157.0,
        "date_y_mm": 20.5,
        "pay_label_x_mm": 49.0,
        "pay_value_x_mm": 70.0,
        "pay_y_mm": 32.0,
        "pay_line_y_mm": 34.0,
        "table_header_y_mm": 39.0,
        "table_header_bottom_y_mm": 42.0,
        "description_center_x_mm": 95.0,
        "amount_center_x_mm": 176.0,
        "description_x_mm": 34.0,
        "description_first_y_mm": 48.0,
        "description_line_gap_mm": 7.0,
        "description_rows": 7,
        "description_amount_divider_x_mm": 157.0,
        "amount_inner_divider_x_mm": 184.0,
        "amount_value_right_x_mm": 181.5,
        "table_row_lines_y_mm": [49.0, 56.0, 63.0, 70.0, 77.0, 84.0, 91.0],
        "account_row_bottom_y_mm": 100.0,
        "account_label_x_mm": 28.0,
        "account_value_x_mm": 40.0,
        "account_value_y_mm": 98.0,
        "account_payment_divider_x_mm": 88.0,
        "payment_label_x_mm": 91.0,
        "payment_value_x_mm": 130.0,
        "payment_value_y_mm": 98.0,
        "total_currency_x_mm": 160.0,
        "total_value_right_x_mm": 181.5,
        "total_value_y_mm": 98.0,
        "sum_label_x_mm": 28.0,
        "sum_label_y_mm": 109.0,
        "sum_value_x_mm": 63.0,
        "sum_first_y_mm": 108.5,
        "sum_second_y_mm": 116.0,
        "approved_label_x_mm": 28.0,
        "approved_value_x_mm": 67.0,
        "received_label_x_mm": 127.0,
        "received_value_x_mm": 151.0,
        "signature_y_mm": 130.0,
    },
}


def pt(mm_value: float) -> float:
    return mm_value * mm

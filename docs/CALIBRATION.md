# Clark voucher calibration

This document records how the direct-print voucher was calibrated and how to repeat the process after another test print or printer change.

## Coordinate system

All field positions in `config.py` are millimetres from the top-left of the voucher. Direct-print offsets behave as follows:

- Positive `offset_x_mm` moves every value right.
- Negative `offset_x_mm` moves every value left.
- Positive `offset_y_mm` moves every value down.
- Negative `offset_y_mm` moves every value up.

The reconstructed archive and A4 layouts use the field coordinates but do not apply direct-printer offsets.

## Calibration method used on 2026-08-19

Source scans:

- Blank voucher: `Scanned_20260819-1548.pdf`
- Dummy direct print: `Scanned_20260819-1612.pdf`

The scanner auto-cropped the two pages differently, so page edges were not used as measurement anchors. The process was:

1. Render both scans at 200 DPI.
2. Register measurements against persistent voucher features: the description table lines, amount dividers, payee rule, account row, and signature dots.
3. Measure each value relative to the nearest printed label or line.
4. Derive the local scale from the main table width. In the test scan, approximately 2,210 rendered pixels represented the configured 167 mm content width, or about 13.2 pixels per millimetre.
5. Convert displacement with `millimetres = pixels / 13.2`.
6. Round corrections to the nearest 0.5 or 1 mm because scanner perspective and ink thickness limit finer accuracy.
7. Use a global offset only when every field shows the same displacement. Use field-specific positions when some fields are already correct.

## Changes from the first dummy print

| Setting | Before | After | Change | Reason |
|---|---:|---:|---:|---|
| `direct.offset_y_mm` | 0.0 mm | -1.5 mm | 1.5 mm up | Value baselines were sitting on or crossing printed rules. |
| `voucher_value_x_mm` | 157.0 mm | 162.0 mm | 5.0 mm right | Voucher number overlapped `Voucher No`. |
| `pay_value_x_mm` | 65.0 mm | 70.0 mm | 5.0 mm right | Payee overlapped `PAY TO`. |
| `description_x_mm` | 29.0 mm | 34.0 mm | 5.0 mm right | Description began too close to the left table edge. |
| `account_value_x_mm` | 36.0 mm | 40.0 mm | 4.0 mm right | Account code overlapped `A/c`. |
| `payment_value_x_mm` | 121.0 mm | 130.0 mm | 9.0 mm right | Payment method overlapped `Cash/Cheque/Online`; shifted a further 4 mm right in the latest pass. |
| `sum_value_x_mm` | 59.0 mm | 63.0 mm | 4.0 mm right | Amount-in-words overlapped `The Sum of Dollars`. |
| `approved_value_x_mm` | 63.0 mm | 67.0 mm | 4.0 mm right | Approver name overlapped `Payment Approved by`. |

Follow-up adjustment after reviewing `CAL-0002`: the direct-print values in the bottom payment row were moved down by 2 mm:

| Setting | Before | After | Change |
|---|---:|---:|---:|
| `account_value_y_mm` | 96.0 mm | 98.0 mm | 2.0 mm down |
| `payment_value_y_mm` | 96.0 mm | 98.0 mm | 2.0 mm down |
| `total_value_y_mm` | 96.0 mm | 98.0 mm | 2.0 mm down |

The following were deliberately unchanged because the scan showed acceptable horizontal placement:

- `date_value_x_mm`: 157.0 mm
- `amount_value_right_x_mm`: 181.5 mm
- `total_value_right_x_mm`: 181.5 mm
- `received_value_x_mm`: 151.0 mm
- `direct.offset_x_mm`: 0.0 mm

## How PDF generation works

1. FastAPI receives the local HTML form submission.
2. ReportLab creates the PDF with a physical page size expressed in millimetres.
3. `VoucherGeometry` converts top-left millimetre coordinates into ReportLab's bottom-left point coordinates.
4. Direct mode calls `draw_values()` only and applies the configured printer offsets.
5. The complete archive calls `draw_structure()` followed by `draw_values()` without direct-printer offsets.
6. A4 mode creates a portrait A4 page, divides it into two 210 x 148.5 mm landscape slots, and renders one complete voucher in each slot.
7. The resulting PDFs are stored under `output/pdf/` using voucher number, date, and output type.

ReportLab draws native PDF text and vector lines. Clark does not generate screenshots and does not depend on browser print layout.

## Repeating the calibration

1. Restart or refresh Clark after changing `config.py`.
2. Generate a direct-print PDF using obvious dummy values.
3. Print at Actual size / 100%. Disable Fit, Shrink, Scale to page, and borderless enlargement.
4. Scan the entire printed voucher as straight as possible at 200 DPI or higher.
5. Measure the misalignment in millimetres or provide the scan for comparison.
6. If all values move together, change `offset_x_mm` or `offset_y_mm`.
7. If only one field is wrong, change that field's X or Y coordinate under `CONFIG["layout"]`.
8. Repeat until the largest visible error is within the printer's normal feed tolerance.

This calibration is based on one physical print. A second dummy print is recommended before using real voucher stock for production.

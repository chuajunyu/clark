# Clark

Clark is a local-first payment-voucher tool. It includes an interface for administrative staff to easily fill up payment vouchers in the same format as the physical printed payment vouchers you can get at local Singapore bookstores. Printing is made easy, you can either print on the printed payment voucher template, a blank A5 paper, or print 2 at a time on an A4 paper.
## Setup

```cmd
py -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run

```powershell
uvicorn app:app --reload
```

Open http://127.0.0.1:8000.

Use one Uvicorn process for this POC. No authentication, database, cloud service, or network connection is required.

## Docker deployment

Clark includes a production `Dockerfile` and `compose.yaml`. The Compose service:

- starts automatically after Docker or the server restarts;
- runs one Uvicorn process as an unprivileged user;
- checks `/healthz` to confirm the application is responding;
- stores voucher records and generated PDFs outside the container.

### First deployment on the server

Clone the repository, then create the persistent host directories. Clark runs inside the container as UID and GID `10001`, so the directories must be writable by that account:

```sh
cd clark
mkdir -p data output/pdf
sudo chown -R 10001:10001 data output/pdf
docker compose up -d --build
```

Check the deployment:

```sh
docker compose ps
curl --fail http://127.0.0.1:8000/healthz
docker compose logs --tail=100 clark
```

Open `http://SERVER-LAN-IP:8000` from a computer on the same network. Clark has no authentication, so do not forward this port through the router or otherwise expose it directly to the internet.

The persistent paths are:

| Server path | Container path | Contents |
| --- | --- | --- |
| `./data` | `/app/data` | Saved voucher records |
| `./output/pdf` | `/app/output/pdf` | Generated PDF revisions |

Existing records and PDFs are intentionally ignored by Git. Copy these two directories to the server separately if migrating an existing Clark installation.

### Updates

After pulling a new version:

```sh
git pull
docker compose up -d --build
docker compose ps
```

Recreating the container does not remove either persistent host directory.

### Backup and restore

Back up both `data/` and `output/pdf/`. For a simple consistent offline backup, briefly stop Clark, copy the directories to another device, and start it again:

```sh
docker compose stop
# Copy data/ and output/pdf/ to the backup destination.
docker compose start
```

To restore, stop Clark, replace both directories from the same backup set, restore ownership with `sudo chown -R 10001:10001 data output/pdf`, and start the service.

### Local verification

Install the development-only test dependencies and run the smoke tests:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

Validate the Compose file without starting it:

```sh
docker compose config --quiet
```

## Staff workflow

### Create or edit a voucher

1. Open **New voucher**.
2. Fill any fields that are needed. Every field is optional.
3. Choose one action:
   - **Save draft** keeps the voucher for later.
   - **Preview & print on voucher paper** saves it and opens the values-only PDF preview.
   - **Save & add to A4 tray** saves it and adds its ID to the temporary A4 selection in this browser tab.

The editor shows **Not saved**, **Saved**, or **Unsaved changes**. If a user tries to leave a changed form, the browser warns them.

### Find and reprint

Open **Saved vouchers** to search by voucher number or payee. A saved voucher can be viewed, updated, added to the A4 tray, or reopened at its latest print revision.

Drafts are stored in `data/vouchers.json`. Each record contains the voucher fields, seven line items, timestamps, and print-history filenames. Writes are atomic so an interrupted save does not leave a half-written JSON file.

### Direct voucher printing

The print page immediately embeds the values-only PDF intended for pre-printed stock. Choose **Open print controls** and confirm:

- the HP printer is selected;
- the custom voucher paper size is selected;
- scaling is **Actual size / 100%**;
- **Fit to page** is off.

Browsers and Windows require the normal print confirmation dialog. Clark cannot safely select the printer or print silently.

Each print creates immutable files, for example:

```text
PV-001_2026-08-19_a1b2c3_r001_direct_print.pdf
PV-001_2026-08-19_a1b2c3_r001_archive.pdf
```

Printing after another edit creates `r002` rather than overwriting `r001`. This avoids the Windows “PDF is open or locked” problem and preserves exact reprints.

### A4 printing

The A4 tray stores only saved voucher IDs in browser `sessionStorage`. It is a temporary selection for the current browser tab, not business data. Closing the tab clears the selection; saved vouchers remain in the backend JSON file.

1. Add saved vouchers to the tray.
2. Open **A4 print tray**.
3. Review or remove the selected vouchers.
4. Choose **Preview A4 sheet**.
5. Print on A4 portrait paper at Actual size / 100%.

Clark places two complete landscape vouchers on each A4 page. If the selection is odd, the lower half of the last page remains blank.

## How PDFs are generated

FastAPI loads the saved voucher JSON. ReportLab draws text and vector lines directly at coordinates measured in millimetres. Clark does not use screenshots, browser print layout, OCR, or a cloud service.

- **Direct print:** values only on a standard A5 landscape PDF page. The calibrated 210 x 140 mm voucher area is top-aligned inside the 210 x 148 mm page, leaving 8 mm blank at the bottom for browser and printer compatibility.
- **Archive:** custom-size complete voucher with structure and values.
- **A4 sheet:** two complete landscape vouchers per portrait A4 page, with centre crop marks.

Generated files are saved under `output/pdf/`.

## Paper size and alignment

All physical measurements remain in `config.py`, expressed in millimetres from the top-left of the voucher.

```python
CONFIG["direct"]["width_mm"]
CONFIG["direct"]["height_mm"]
CONFIG["direct"]["pdf_page_width_mm"]
CONFIG["direct"]["pdf_page_height_mm"]
CONFIG["direct"]["page_content_x_mm"]  # move the voucher area within A5
CONFIG["direct"]["page_content_y_mm"]  # positive moves the voucher area down
CONFIG["direct"]["offset_x_mm"]  # positive moves right
CONFIG["direct"]["offset_y_mm"]  # positive moves down
```

Individual field positions remain under `CONFIG["layout"]`. Restart Clark after changing the configuration.

## HP LaserJet MFP M141

Create or select a custom paper size matching the configured width and height. Load the voucher in the orientation shown by the HP driver. Select the same custom size in both printer properties and the PDF print dialog.

For A4 mode, select A4 portrait and Actual size. Cut at the centre crop marks.

## POC limits

Clark has no authentication, database, cloud hosting, OCR, carbon-copy reproduction, printer-status monitoring, silent printing, or accounting integration.

# Keenu IDP — Intelligent Document Processing

AI-powered document classification and data extraction for Keenu (Pakistan digital payments). Upload scanned images of CNICs, driving licences, invoices, receipts, resumes, and forms — get back structured JSON, CSV, and PDF outputs in seconds.

**Live demo:** [frontend-two-chi-91.vercel.app](https://frontend-two-chi-91.vercel.app)

---

## Features

- Classifies documents into 7 categories (CNIC, Driving Licence, Invoices, Receipts, Resumes, Forms, Other)
- Extracts structured fields using Google Gemini multimodal AI
- Outputs per-category JSON, CSV (Excel-compatible), and PDF
- Sample image sidebar — demo without your own documents
- Drag-and-drop upload, up to 10 images per batch
- Results persist in browser storage across page refreshes

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (Vercel)                         │
│                                                                  │
│  ┌──────────────┐   ┌────────────────────────────────────────┐  │
│  │   Sidebar    │   │            Main Content                │  │
│  │              │   │                                        │  │
│  │ Sample imgs  │   │  1. FileUploader (drag-drop / click)   │  │
│  │ per category │──▶│  2. Processing spinner (POST in-flight)│  │
│  │ Click/drag   │   │  3. OutputPanel (JSON · CSV · PDF)     │  │
│  │ to add       │   │     ↳ View modal (inline table)        │  │
│  └──────────────┘   │     ↳ Download link                    │  │
│                      └────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │  POST /api/jobs (multipart)
                               │  ← JobState (JSON, sync)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Heroku)                    │
│                                                                  │
│  routes.py                                                       │
│  └── POST /api/jobs ──▶ processor.py                            │
│                             │                                    │
│                    for each image (serial):                      │
│                    ┌─────────────────────┐                       │
│                    │  1. classify_doc()  │──▶ Gemini API         │
│                    │  2. extract_fields()│──▶ Gemini API         │
│                    │  3. validate_fields │                       │
│                    └─────────────────────┘                       │
│                             │                                    │
│                    output_generator.py                           │
│                    ├── {category}.json  (embedded in response)  │
│                    ├── {category}.csv   (embedded in response)  │
│                    └── {category}.pdf  (disk, download only)    │
│                                                                  │
│  GET /api/jobs/{id}/download/{file} ──▶ FileResponse            │
└─────────────────────────────────────────────────────────────────┘
```

### Data flow

```
Image bytes
    │
    ▼
┌──────────────┐     Gemini multimodal prompt      ┌─────────────────┐
│  Resize if   │ ──────────────────────────────▶   │  Classification │
│  > 4 MB      │ ◀──────────────────────────────   │  → category str │
└──────────────┘     {"category": "cnic"}           └─────────────────┘
    │
    ▼
┌──────────────┐     Gemini multimodal prompt      ┌─────────────────┐
│  Same image  │ ──────────────────────────────▶   │  Field extract  │
│  + category  │ ◀──────────────────────────────   │  → JSON fields  │
└──────────────┘     {"name": "...", "cnic_number": "..."}           
    │
    ▼
┌──────────────┐
│ validate +   │  Normalise keys (snake_case), type-check values
│ normalise    │
└──────────────┘
    │
    ▼
┌──────────────┐
│ schema_merger│  Union of all keys across records, null-fill missing
│ per category │
└──────────────┘
    │
    ├── JSON (indent=2, embedded in response for View)
    ├── CSV  (utf-8-sig for Excel, embedded in response)
    └── PDF  (Pillow multi-page, disk only, download link)
```

---

## Document categories & extracted fields

| Category | Emoji | Key fields extracted |
|---|---|---|
| `cnic` | 🪪 | name, cnic_number, date_of_birth, gender, issue_date, expiry_date |
| `driving_licence` | 🚗 | name, licence_number, dob, issue_date, expiry_date, blood_group, address |
| `invoices` | 🧾 | vendor_name, invoice_number, date, items[], subtotal, tax, total_amount |
| `receipt` | 🛒 | vendor_name, date, items[], subtotal, tax, total_amount, payment_method |
| `resumes` | 📄 | name, email, phone, skills[], education[], experience[], summary |
| `forms` | 📋 | all visible key-value pairs |
| `other` | 📁 | any visible structured information |

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, CSS Modules |
| Backend | FastAPI (Python 3.11), Uvicorn |
| AI | Google Gemini `gemini-3.1-flash-lite-preview` (multimodal) |
| PDF generation | Pillow |
| Frontend hosting | Vercel |
| Backend hosting | Heroku |

---

## Local development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google API key with Gemini access

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env in project root
echo "GOOGLE_API_KEY=your-key-here" > ../.env

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Create .env.local
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Deployment

### Backend → Heroku

```bash
heroku create your-app-name
heroku config:set GOOGLE_API_KEY=your-key
heroku config:set ALLOWED_ORIGINS=https://your-frontend.vercel.app

# Push only backend/ subdir as Heroku root
git subtree push --prefix backend heroku main
```

### Frontend → Vercel

```bash
cd frontend
echo "https://your-app-name.herokuapp.com" | vercel env add VITE_API_URL production
vercel --prod
```

---

## Project structure

```
keenu_work/
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # POST /api/jobs (sync), GET download
│   │   ├── models/schemas.py      # Pydantic models
│   │   ├── services/
│   │   │   ├── gemini_service.py  # Gemini classify + extract
│   │   │   ├── processor.py       # Serial image pipeline
│   │   │   ├── output_generator.py# JSON / CSV / PDF writer
│   │   │   └── schema_merger.py   # Key normalisation + union
│   │   ├── utils/
│   │   │   ├── logger.py
│   │   │   └── validators.py
│   │   ├── config.py
│   │   └── main.py                # FastAPI app, CORS
│   ├── tests/
│   ├── Procfile
│   ├── runtime.txt
│   └── requirements.txt
├── frontend/
│   ├── public/samples/            # 30 sample images (5 per category)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── Footer.jsx
│   │   │   ├── Sidebar.jsx        # Sample image browser
│   │   │   ├── FileUploader.jsx   # Drag-drop upload zone
│   │   │   └── OutputPanel.jsx    # Results grid (View / Download)
│   │   ├── data/samples.js        # Static sample image manifest
│   │   ├── services/api.js        # Axios client
│   │   ├── App.jsx                # App shell, localStorage persistence
│   │   └── main.jsx
│   ├── vercel.json
│   └── vite.config.js
├── dataset/                       # (gitignored) local test images
└── .env                           # (gitignored) GOOGLE_API_KEY
```

---

## Notes

- **Heroku ephemeral filesystem**: output files on disk are cleared on dyno restart. JSON and CSV content is embedded in the API response and saved to browser `localStorage` so results survive a page refresh. PDF download links require the dyno to be alive.
- **Serial Gemini calls**: each image makes 2 sequential API calls (classify then extract) to avoid exhausting free-tier quota. Processing time is roughly 5–15 seconds per image.
- **10-image limit**: enforced on both frontend and backend.

---

*Made by [Danish](https://github.com/danisaysskol/keenu-idp)*

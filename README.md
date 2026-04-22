# 📄 Paperless Document Management System

A college-level web application for digitizing, storing, and searching documents.  
**Stack:** Django · MySQL · Bootstrap 5 · jQuery · Tesseract OCR

---

## 📁 Project Structure

```
paperless_dms/
│
├── manage.py
├── requirements.txt
│
├── paperless_dms/               ← Django project package
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── documents/                   ← Single Django app
│   ├── __init__.py
│   ├── admin.py
│   ├── forms.py
│   ├── models.py
│   ├── ocr.py
│   ├── urls.py
│   ├── views.py
│   └── templates/
│       └── documents/
│           ├── base.html
│           ├── login.html
│           ├── register.html
│           ├── dashboard.html
│           ├── upload.html
│           ├── search.html
│           ├── document_detail.html
│           └── document_confirm_delete.html
│
└── media/                       ← Uploaded files (auto-created)
    └── documents/
```

---

## ⚙️ Setup Instructions

### 1. Install Tesseract OCR

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install tesseract-ocr -y
```

**Windows:**
- Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
- During install, note the path (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe`)
- Add it to `ocr.py` if needed:
  ```python
  import pytesseract
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

**macOS:**
```bash
brew install tesseract
```

---

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Create the MySQL Database

Log into MySQL and run:
```sql
CREATE DATABASE paperless_dms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

### 4. Configure Database Credentials

Open `paperless_dms/settings.py` and update:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'paperless_dms',
        'USER': 'root',           # ← your MySQL username
        'PASSWORD': 'your_pass',  # ← your MySQL password
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

---

### 5. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 6. Create a Superuser (optional, for Django Admin)

```bash
python manage.py createsuperuser
```

---

### 7. Start the Development Server

```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000**

---

## ✅ Features

| Feature | Description |
|---|---|
| User Auth | Register, login, logout with session management |
| Document Upload | PDF, JPG, PNG — up to 10 MB |
| OCR | Auto text extraction via Tesseract on upload |
| Full-Text Search | Searches titles, OCR text, notes, and tags |
| Category Filter | Organise docs into named categories |
| Tag Filter | Multi-tag documents with comma-separated tags |
| Document Detail | View full extracted text with word count |
| Delete | Removes DB record and physical file |
| Django Admin | Manage all data at `/admin/` |

---

## 🗄️ Database Schema

```
auth_user          — Django built-in users
documents_category — id, name, description
documents_tag      — id, name
documents_document — id, title, file, file_type, extracted_text,
                     notes, upload_date, uploaded_by_id, category_id
documents_document_tags — M2M through table
```

---

## 📦 Dependencies Explained

| Package | Purpose |
|---|---|
| `Django` | Web framework (views, ORM, auth, admin) |
| `mysqlclient` | MySQL database driver for Django |
| `Pillow` | Image processing required by pytesseract |
| `pytesseract` | Python wrapper for Tesseract OCR |
| `pdfplumber` | Direct text extraction from text-based PDFs |
| `PyMuPDF` | Render scanned PDF pages to images for OCR |

---

## 🔧 Troubleshooting

**`TesseractNotFoundError`** — Tesseract binary not found. Install it (see Step 1) or set the path manually in `ocr.py`.

**`mysqlclient` install fails on Ubuntu** — Run:
```bash
sudo apt install python3-dev default-libmysqlclient-dev build-essential pkg-config -y
```

**`mysqlclient` install fails on Windows** — Use the prebuilt wheel:
```bash
pip install mysqlclient --only-binary :all:
```

**PDF shows no extracted text** — The PDF is likely scanned. The system will automatically fall back to Tesseract OCR via PyMuPDF page rendering.

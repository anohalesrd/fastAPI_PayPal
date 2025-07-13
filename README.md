# 💳 PayPal Subscription Demo (FastAPI + HTML)

This is a demo project that integrates the PayPal JS SDK with a Python backend using FastAPI.

The frontend has two buttons:

1. **Create a payment (order)** with PayPal and capture it (then you can refund or continue).
2. **Create a subscription**: the backend does the following:
   - Creates a product
   - Creates a plan
   - Checks if the plan is active
   - Creates a real subscription in PayPal

---

## 🚀 Requirements

- OS: Windows 10+ (or WSL with Ubuntu)
- Python 3.11+
- PayPal account (Sandbox mode)
- Virtual environment (recommended)
- VSCode

---

## ⚙️ Create a virtual environment and install dependencies (Ubuntu example)

$ source env/bin/activate
$ pip install -r requirements.txt

# .env file with your PayPal Sandbox credentials

- CLIENT_ID=***CLIENT_ID***
- CLIENT_SECRET=***CLIENT_SECRET***

# Run FastAPI local server with uvicorn
- uvicorn main:app --reload --port 8000
- Open url in browser: http://127.0.0.1:8000
  *Note: Enable popup windows in the browser

# Project Scheme

PayPal/
└── env/
    ├── .env (dependencies)
    ├── main.py (Backend FastAPI)
    ├── index.html (JS + HTML)
    ├── processing_subs.html (Use for response during de subscription process)
    ├── requirements.txt (mandatory librearies to run main.py with uvicorn)
    ├── .env (sandbox PayPal credentials)
    ├── .gitignore (ignore files to push)
  

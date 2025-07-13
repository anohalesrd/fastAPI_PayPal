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
## Workflow

    User->>Frontend: Clicks on PayPal button
    Frontend->>Backend: POST /create-order
    Backend->>PayPal: POST /v2/checkout/orders
    PayPal-->>Backend: Returns orderID
    Backend-->>Frontend: Sends orderID to client

    User->>Frontend: Approves payment in PayPal popup
    Frontend->>Backend: POST /capture-order/{orderID}
    Backend->>PayPal: POST /v2/checkout/orders/{orderID}/capture
    PayPal-->>Backend: Returns transaction details (ID, status)
    Backend-->>Frontend: Sends JSON response (status + transaction_id)
    Frontend->>Frontend: Displays confirmation modal

    Note over Frontend: "Refund" button becomes visible after successful payment

    User->>Frontend: Clicks on "Refund" button
    Frontend->>Backend: POST /refund-transaction/{transaction_id}
    Backend->>PayPal: POST /v2/payments/captures/{transaction_id}/refund
    PayPal-->>Backend: Returns refund details (refund_id, status)
    Backend-->>Frontend: Sends refund result to client
    Frontend->>Frontend: Displays refund confirmation modal
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
  

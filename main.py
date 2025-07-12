from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging
import json
import requests
import os
from dotenv import load_dotenv
import base64
from fastapi.responses import HTMLResponse

'''
load credential from file .env
'''
load_dotenv()

'''
create class app from FastAPI
'''

app = FastAPI()

PAYPAL_CLIENT_ID = os.getenv("CLIENT_ID")
PAYPAL_SECRET = os.getenv("CLIENT_SECRET")

'''
get access token from PayPal and endpoint for manage payments orders

docs: https://developer.paypal.com/api/rest/authentication/
'''

PAYPAL_OAUTH_URL = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
PAYPAL_ORDER_URL = "https://api-m.sandbox.paypal.com/v2/checkout/orders"

'''
send index.html to browser
'''
@app.get("/")
def template():
    return FileResponse('index.html')


def get_token():

    auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_SECRET}".encode()).decode()

    headers = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
    "grant_type": "client_credentials"
    }

    response = requests.post(PAYPAL_OAUTH_URL, headers=headers, data=data)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error obteniendo token de PayPal")
    
    token = response.json().get("access_token")

    return token


def create_order(token: str):
    '''
    docs: https://developer.paypal.com/docs/api/orders/v2/#orders_create
    Creates an order. Merchants and partners can add Level 2 and 3 data to payments to reduce risk and payment processing costs

    Function args:
        'token': access token getted in get_token function
    
    Required parameters: 
        - purchase_units: An array of purchase units. Each purchase unit establishes a contract between a payer and the payee
        - intent: capture payment immediately or authorize a payment for an order after order creation (CAPTURE, AUTHORIZE)

    Responses:
        - 200 SUCCESSFUL > A successful response to an idempotent request returns the HTTP 200 OK status code with a JSON response body that shows order details.

        - 201 SUCCESSFUL > A successful request returns the HTTP 201 Created status code 
          and a JSON response body that includes by default a minimal response with the ID, status, and HATEOAS links

        - 400 FAILED > Request is not well-formed, syntactically incorrect, or violates schema.

        - 422 FAILED > The requested action could not be performed, semantically incorrect, or failed business validation.

    '''

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": "1.00"
                }
            }
        ]
    }

    response = requests.post(PAYPAL_ORDER_URL, json=data, headers=headers)

    if response.status_code in (200,201):
        print('Payment Order Created: ', response.json())
    else:
        raise Exception (f"Error: {response.status_code}")
    
    order = response.json()
    return order["id"]

'''
request to create-order endpoint and returns an Order ID
'''
@app.post('/create-order')
def create_paypal_order():
    token = get_token()
    order_id = create_order(token)
    return {'id': order_id}

'''
request to capture-order endpoint, the backend capture the payment
'''
@app.post("/capture-order/{order_id}")
def capture_order(order_id: str):

    token = get_token()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    url = f'{PAYPAL_ORDER_URL}/{order_id}/capture'

    response = requests.post(url, headers=headers)

    if response.status_code in (200, 201):
        print('Payment Captured', response.json())
        capture_data = response.json()
    else:
        raise HTTPException(f'Error: {response.status_code}')
    
    transaction_id = capture_data["purchase_units"][0]["payments"]["captures"][0]["id"]
    status = capture_data["purchase_units"][0]["payments"]["captures"][0]["status"]
    
    return {"transaction_id": transaction_id,
            "status": status}

@app.post('/refund-transaction/{capture_id}')
def refund(capture_id: str):
    token = get_token()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    url = f'https://api.sandbox.paypal.com/v2/payments/captures/{capture_id}/refund'

    response = requests.post(url, headers=headers)

    if response.status_code in (200, 201):
        refund_data = response.json()
        refund_id = refund_data['id']
        refund_status = refund_data['status']
        return {"message": "Refund completed","refund_id": refund_id, "refund_status": refund_status}
    else:
        raise HTTPException(status_code=response.status_code, detail="Refund failed")


@app.post('/create-product')
def create_product():
    token = get_token()

    headers = {
        "Authorization": f'Bearer {token}',
        "Content-Type": "application/json"
    }

    data = {
        "name": "Test product",
        "description": "Test monthly suscription",
        "type": "SERVICE",
        "category": "SOFTWARE"
    }

    url = "https://api-m.sandbox.paypal.com/v1/catalogs/products"

    response = requests.post(url, headers=headers, json=data)

    if response.status_code in (200,201):
        print('Product created successfully')
        return response.json()
    else:
        raise Exception('Error: ', response.status_code)

@app.post('/create-plan')
def create_plan(product_id: str):
    token = get_token()

    headers= {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {
        "product_id": product_id,
        "name": "Monthly Plan",
        "billing_cycles": [{
            "frequency": {
                "interval_unit": "MONTH",
                "interval_count": 1
            },
            "tenure_type": "REGULAR",
            "sequence": 1,
            "total_cycles": 0,
            "pricing_scheme": {
                "fixed_price": {
                    "value": "10",
                    "currency_code": "USD"
                }
            }
        }],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee": {
                "value": "0",
                "currency_code": "USD"
            },
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3
        }
    }

    url = "https://api-m.sandbox.paypal.com/v1/billing/plans"

    response = requests.post(url, headers=headers, json=data)
    '''
    print('*************************************')
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    print('*************************************')
    '''

    if response.status_code in (200, 201):
        print('Plan Created Successfully')
        returned_data = response.json()

        plan_id = returned_data['id']
        url_get_plan = f"https://api-m.sandbox.paypal.com/v1/billing/plans/{plan_id}"
        response_plan = requests.get(url_get_plan, headers=headers)

        if response_plan.status_code == 200:
            plan = response_plan.json()

            interval_unit = plan['billing_cycles'][0]['frequency']['interval_unit']
            value = plan['billing_cycles'][0]['pricing_scheme']['fixed_price']['value']
            currency_code = plan['billing_cycles'][0]['pricing_scheme']['fixed_price']['currency_code']

            return {
                "id": plan['id'],
                "name": plan['name'],
                "interval_unit": interval_unit,
                "value": value,
                "currency_code": currency_code
            }
        else:
            raise Exception('Error fetching plan details', {
                "Error": response_plan.status_code,
                "Data": response_plan.text
            })
    else:
        raise Exception('Error creating plan', {
            "Error": response.status_code,
            "Data": response.text
        })

@app.post('/activate-plan')
def activate_plan(plan_id: str):
    token = get_token()

    headers = {"Authorization": f'Bearer {token}',
               "Content-Type": "application/json",
               "Accept": "application/json"}

    url = f"https://api-m.sandbox.paypal.com/v1/billing/plans/{plan_id}/activate"

    get_url = f"https://api-m.sandbox.paypal.com/v1/billing/plans/{plan_id}"
    get_response = requests.get(get_url, headers=headers)

    if get_response.status_code != 200:
        raise Exception('Error getting plan', get_response.status_code)
    
    plan_status = get_response.json().get('status')

    if plan_status =='ACTIVE':
        return {'message': "Plan is already active."}

    if plan_status not in ("CREATED","INACTIVE"):
        raise Exception("Error Status Invalid", plan_status)

    response = requests.post(url, headers=headers, data="{}")

    if response.status_code == 204:
        print(f'Plan {plan_id} activate successfully')
    else:
        raise Exception('Error: ', response.status_code, response.text)
    
@app.post('/create-subscription')
def create_suscription(plan_id: str):
    token = get_token()

    headers = {"Authorization": f"Bearer {token}",
               "Content-Type": "application/json"
               }
    
    data = {"plan_id": plan_id,
            "subscriber": {
                "name": {
                    "given_name": "John",
                    "surname": "Doe"
                },
                "email_address": "customer@example.com"
            },
            "application_context": {
                "brand_name": "Company Happy Friends",
                "locale": "es-ES",
                "return_url": "http://localhost:8000/success",
                "cancel_url": "http://localhost:8000/cancel"
                }
            }
    
    url = "https://api-m.sandbox.paypal.com/v1/billing/subscriptions"

    response = requests.post(url, headers=headers, json=data)

    
    print('*************************************')
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())    
    print('*************************************')

    if response.status_code in (200,201):
        print('Suscription Created Successfully')
        returned_data = response.json()

        links = returned_data.get("links", [])
        approve_link = None
        cancel_link = None

        for link in links:
            if link.get("rel") == "approve":
                approve_link = link.get("href")
            elif link.get('rel') == "cancel":
                cancel_link = link.get("href")

        if approve_link:
            return {
                "id": returned_data['id'],
                "status": returned_data['status'],
                "approve_link": approve_link,
                "cancel_link": cancel_link
            }
    else:
        raise Exception('Error: ', response.status_code, response.text)

@app.get('/success', response_class = HTMLResponse)
def return_url(request: Request):
    subscription_id = request.query_params.get('subscription_id')
    ba_token = request.query_params.get("ba_token")
    token = request.query_params.get("token")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Subscription Successful</title>
        <style>
            body {{
                background-color: #f9f9f9;
                font-family: Arial, sans-serif;
                text-align: center;
                padding-top: 50px;
            }}
            .check {{
                font-size: 80px;
                color: #4CAF50;
            }}
            .message {{
                font-size: 24px;
                margin-top: 20px;
                color: #333;
            }}
            .sub-id {{
                margin-top: 10px;
                font-size: 18px;
                color: #777;
            }}
            .close-note {{
                margin-top: 30px;
                font-size: 14px;
                color: #aaa;
            }}
        </style>
        <script>
            setTimeout(() => {{
                window.close();
            }}, 50000);
        </script>
    </head>
    <body>
        <div class="check">✔️</div>
        <div class="message">¡You are subscribed!</div>
        <div class="sub-id">Subscription ID: <strong>{subscription_id}</strong></div>
        <div class="close-note">This window will close automatically.</div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

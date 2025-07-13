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


# load credential from file .env
load_dotenv()

# create class app from FastAPI
app = FastAPI()


# enviroment varibales
PAYPAL_CLIENT_ID = os.getenv("CLIENT_ID")
PAYPAL_SECRET = os.getenv("CLIENT_SECRET")

'''
get access token from PayPal and endpoint for manage payments orders
docs: https://developer.paypal.com/api/rest/authentication/
'''
PAYPAL_OAUTH_URL = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
PAYPAL_ORDER_URL = "https://api-m.sandbox.paypal.com/v2/checkout/orders"


# send index.html to browser to show event buttons
@app.get("/")
def template():
    return FileResponse('index.html')

def get_token():
    '''
    Obtain an OAuth 2.0 access token to interact with PayPal API
    docs: https://developer.paypal.com/api/rest/authentication/#client-credentials-grant

    **Encode CLIENT_ID:CLIENT_SECRET in Base64 before sending it in the API call
    '''
    auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_SECRET}".encode()).decode()

    headers = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
    "grant_type": "client_credentials"
    }

    response = requests.post(PAYPAL_OAUTH_URL, headers=headers, data=data)

    print('*************************************')
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    print('*************************************')

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error getting PayPal access token")
    
    token = response.json().get("access_token")
    return token


def create_order(token: str):
    '''
    Create a PayPal order with intent to capture payment immediately
    Intent is set to "CAPTURE" which means the payment will be captured immediately

    docs: https://developer.paypal.com/docs/api/orders/v2/#orders_create
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

    response = requests.post(PAYPAL_ORDER_URL,headers=headers, json=data)

    print('*************************************')
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    print('*************************************')

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
    '''
    Create a PayPal payment order.
    This endpoint get access token from PayPal, then create payment order with intent to 
    capture payment inmediately

    Returns:
              {
                  "id": "<order_id>"
              }
    docs: https://developer.paypal.com/docs/api/orders/v2/#orders_create
    '''
    token = get_token()
    order_id = create_order(token)
    return {'id': order_id}

@app.post("/capture-order/{order_id}")
def capture_order(order_id: str):
    '''
        Capture a PayPal payment for a given order Id

            Args:
            order_id (str): The PayPal order ID to capture payment for.

        Returns:
                {
                    "transaction_id": "<capture_transaction_id>",
                    "status": "<capture_status>"
                }
        
        docs: https://developer.paypal.com/docs/api/orders/v2/#orders_capture
    '''
    token = get_token()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    url = f'{PAYPAL_ORDER_URL}/{order_id}/capture'

    response = requests.post(url, headers=headers)

    print('*************************************')
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    print('*************************************')

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
    '''
    Process a refund for a completed PayPal capture transaction

    Args:
        capture_id (str): The PayPal capture transaction ID to refund.

    Returns:
              {
                  "message": "Refund completed",
                  "refund_id": "refund_transaction_id",
                  "refund_status": "refund_status"
              }
    
    docs: https://developer.paypal.com/docs/api/payments/captures/#captures_refund
    '''
    token = get_token()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    url = f'https://api.sandbox.paypal.com/v2/payments/captures/{capture_id}/refund'

    response = requests.post(url, headers=headers)

    print('*************************************')
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    print('*************************************')

    if response.status_code in (200, 201):
        refund_data = response.json()
        refund_id = refund_data['id']
        refund_status = refund_data['status']
        return {"message": "Refund completed","refund_id": refund_id, "refund_status": refund_status}
    else:
        raise HTTPException(status_code=response.status_code, detail="Refund failed")

@app.post('/create-product')
def create_product():
    '''
    
    Create a new product in the PayPal catalog with predefined details such as name, description,
    type, and category in the PayPal environment.

    Returns:
        dict: The JSON response from PayPal with the created product details.
    
    docs: https://developer.paypal.com/docs/api/catalog-products/v1/#products_create
    '''
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
    '''
    Create a billing plan for a given product in PayPal

    Args:
        product_id (str): The PayPal product ID to associate with the plan.

    Returns:
        dict: Plan details including plan ID, name, billing interval, price value, and currency.
    
    docs: https://developer.paypal.com/docs/api/subscriptions/v1/#plans_create
    '''
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


    print('*************************************')
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    print('*************************************')


    if response.status_code in (200, 201):
        print('Plan Created Successfully')
        returned_data = response.json()

        plan_id = returned_data['id']
        url_get_plan = f"https://api-m.sandbox.paypal.com/v1/billing/plans/{plan_id}"
        response_plan = requests.get(url_get_plan, headers=headers)

        print('*************************************')
        print("Status code:", response.status_code)
        print("Response JSON:", response_plan.json())
        print('*************************************')

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
    '''
    Activate a PayPal billing plan given the plan id

    Args:
        plan_id (str): The PayPal billing plan ID to activate.

    Returns:
        dict: A message indicating the activation result.
    
    docs: https://developer.paypal.com/docs/api/subscriptions/v1/#plans_activate

    By default, the plan is activated at the moment of creating it but we create
    this endpoint for more flexibility to the API consumer
    '''
    token = get_token()

    headers = {"Authorization": f'Bearer {token}',
               "Content-Type": "application/json",
               "Accept": "application/json"}

    url = f"https://api-m.sandbox.paypal.com/v1/billing/plans/{plan_id}/activate"

    get_url = f"https://api-m.sandbox.paypal.com/v1/billing/plans/{plan_id}"
    get_response = requests.get(get_url, headers=headers)

    print('*************************************')
    print("Status code:", get_response.status_code)
    print("Response JSON:", get_response.json())
    print('*************************************')

    if get_response.status_code != 200:
        raise Exception('Error getting plan', get_response.status_code)
    
    plan_status = get_response.json().get('status')

    if plan_status =='ACTIVE':
        return {'message': "Plan is already active."}

    if plan_status not in ("CREATED","INACTIVE"):
        raise Exception("Error Status Invalid", plan_status)

    response = requests.post(url, headers=headers, data="{}")

    print('*************************************')
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    print('*************************************')

    if response.status_code == 204:
        print(f'Plan {plan_id} activate successfully')
    else:
        raise Exception('Error: ', response.status_code, response.text)
    
@app.post('/create-subscription')
def create_suscription(plan_id: str):
    '''
    Create a new PayPal subscription for a given billing plan

    Args:
        plan_id (str): The PayPal billing plan ID to associate with the subscription.

    Returns:
        dict: Contains subscription ID, status, approval link, and cancel link send to the frontend

    docs: https://developer.paypal.com/docs/api/subscriptions/v1/#subscriptions_create
    '''
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
    '''
    Handle PayPal subscription approval redirect in frontend

   Args:
        request (Request): FastAPI Request object containing query parameters from PayPal:
            - subscription_id (str): Id of the approved subscription.

    Returns:
        HTMLResponse: A confirmation web page with subscription success message.

    Notes:
        - This page includes a visual confirmation and auto-closes after a few seconds.
        - This endpoint does not verify the subscription; it only displays a message based on the redirect.
    
    docs: https://developer.paypal.com/docs/subscriptions/integrate/#4-get-the-transaction-details
    '''
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
                background-color: #f2f4f7;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .checkmark-circle {{
                width: 100px;
                height: 100px;
                border-radius: 50%;
                background: #28a745;
                display: flex;
                align-items: center;
                justify-content: center;
                animation: pop 0.5s ease-out;
            }}
            .checkmark {{
                color: white;
                font-size: 60px;
            }}
            .message {{
                font-size: 26px;
                color: #333;
                margin-top: 20px;
                font-weight: 600;
            }}
            .sub-id {{
                margin-top: 10px;
                font-size: 18px;
                color: #555;
            }}
            .close-note {{
                margin-top: 30px;
                font-size: 14px;
                color: #999;
            }}
            @keyframes pop {{
                0% {{
                    transform: scale(0);
                    opacity: 0;
                }}
                100% {{
                    transform: scale(1);
                    opacity: 1;
                }}
            }}
        </style>
        <script>
            setTimeout(() => {{
                window.close();
            }}, 50000);
        </script>
    </head>
    <body>
        <div class="checkmark-circle">
            <div class="checkmark">&#10004;</div>
        </div>
        <div class="message">¡You are subscribed!</div>
        <div class="sub-id">Subscription ID: <strong>{subscription_id}</strong></div>
        <div class="close-note">This window will close automatically.</div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/processing_subs.html", response_class=HTMLResponse)
def processing():
    '''
    Show the subscription processing HTML page

    Returns:
        HTMLResponse: The raw HTML content of `processing_subs.html`.

    Notes:
        - Ensure that `processing_subs.html` exists in the root directory or provide the correct path.
        - This page is static and does not interact with any backend logic or API.
    '''
    with open('processing_subs.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
        return HTMLResponse(content=html_content)
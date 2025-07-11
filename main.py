from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
import base64

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

if __name__ == "__main__":
    token = get_token()
    print("Access token:", token)

    order_id = create_order(token)
    print("Order id:", order_id)

    transaction_id = capture_order(order_id)
    print('Transaction Id: ', transaction_id)


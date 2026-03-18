# apps/payments/paystack.py

import requests
import json
import hmac
import hashlib
from django.conf import settings


class Paystack:
    """
    Paystack API wrapper for payment processing
    """
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.base_url = settings.PAYSTACK_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def initialize_transaction(self, email, amount, reference=None, callback_url=None, metadata=None):
        """
        Initialize a transaction
        """
        url = f"{self.base_url}/transaction/initialize"
        
        data = {
            "email": email,
            "amount": int(amount * 100),  # Convert to pesewas/kobo (smallest currency unit)
            "currency": settings.PAYSTACK_CURRENCY,
            "channels": settings.PAYSTACK_CHANNELS,
        }
        
        if reference:
            data["reference"] = reference
        
        if callback_url:
            data["callback_url"] = callback_url
        
        if metadata:
            data["metadata"] = metadata
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def verify_transaction(self, reference):
        """
        Verify a transaction
        """
        url = f"{self.base_url}/transaction/verify/{reference}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def list_transactions(self, per_page=50, page=1):
        """
        List all transactions
        """
        url = f"{self.base_url}/transaction?perPage={per_page}&page={page}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def fetch_transaction(self, transaction_id):
        """
        Fetch a single transaction
        """
        url = f"{self.base_url}/transaction/{transaction_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def charge_authorization(self, email, amount, authorization_code, reference=None):
        """
        Charge a customer using a previous authorization
        """
        url = f"{self.base_url}/transaction/charge_authorization"
        
        data = {
            "email": email,
            "amount": int(amount * 100),
            "authorization_code": authorization_code,
            "currency": settings.PAYSTACK_CURRENCY
        }
        
        if reference:
            data["reference"] = reference
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def create_customer(self, email, first_name=None, last_name=None, phone=None):
        """
        Create a customer
        """
        url = f"{self.base_url}/customer"
        
        data = {
            "email": email,
        }
        
        if first_name:
            data["first_name"] = first_name
        
        if last_name:
            data["last_name"] = last_name
        
        if phone:
            data["phone"] = phone
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def list_customers(self, per_page=50, page=1):
        """
        List all customers
        """
        url = f"{self.base_url}/customer?perPage={per_page}&page={page}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def fetch_customer(self, customer_id):
        """
        Fetch a single customer
        """
        url = f"{self.base_url}/customer/{customer_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def list_banks(self, country='ghana'):
        """
        List all banks
        """
        url = f"{self.base_url}/bank?country={country}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def resolve_account_number(self, account_number, bank_code):
        """
        Resolve account number
        """
        url = f"{self.base_url}/bank/resolve?account_number={account_number}&bank_code={bank_code}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def create_transfer_recipient(self, name, account_number, bank_code, type='nuban', currency='GHS'):
        """
        Create a transfer recipient
        """
        url = f"{self.base_url}/transferrecipient"
        
        data = {
            "type": type,
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def initiate_transfer(self, amount, recipient_code, reason=None):
        """
        Initiate a transfer
        """
        url = f"{self.base_url}/transfer"
        
        data = {
            "source": "balance",
            "amount": int(amount * 100),
            "recipient": recipient_code,
            "currency": settings.PAYSTACK_CURRENCY
        }
        
        if reason:
            data["reason"] = reason
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def finalize_transfer(self, transfer_code, otp):
        """
        Finalize a transfer
        """
        url = f"{self.base_url}/transfer/finalize_transfer"
        
        data = {
            "transfer_code": transfer_code,
            "otp": otp
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            return response.json()
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def verify_webhook(self, request):
        """
        Verify webhook signature
        """
        signature = request.headers.get('x-paystack-signature')
        
        if not signature or not settings.PAYSTACK_WEBHOOK_SECRET:
            return False
        
        # Compute expected signature
        payload = request.body
        expected_signature = hmac.new(
            settings.PAYSTACK_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


# Singleton instance
paystack = Paystack()
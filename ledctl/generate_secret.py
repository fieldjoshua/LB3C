#!/usr/bin/env python3
"""
Generate a secure secret key for Flask
"""

import secrets
import string

def generate_secret_key(length=32):
    """Generate a secure random secret key"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == '__main__':
    secret_key = generate_secret_key()
    print(f"Generated secret key: {secret_key}")
    print("\nAdd this to your .env file:")
    print(f"FLASK_SECRET_KEY={secret_key}")
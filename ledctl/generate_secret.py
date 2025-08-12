#!/usr/bin/env python3
"""
Generate a secure secret key for Flask configuration.
"""
import secrets

def generate_secret_key():
    """Generate a cryptographically secure secret key."""
    return secrets.token_hex(32)

if __name__ == "__main__":
    key = generate_secret_key()
    print("\nGenerated Secret Key:")
    print("=" * 50)
    print(key)
    print("=" * 50)
    print("\nAdd this to your .env file:")
    print(f"FLASK_SECRET_KEY={key}")
    print("\nNever commit this key to version control!")
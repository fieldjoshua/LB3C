#!/usr/bin/env python3
"""
Generate API keys for the LED Control System.
"""
import secrets
import hashlib
import sys

def generate_api_key():
    """Generate a cryptographically secure API key."""
    return secrets.token_urlsafe(32)

def hash_api_key(key):
    """Generate SHA256 hash of API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()

if __name__ == "__main__":
    # Generate one or more keys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    print("\nGenerated API Keys:")
    print("=" * 60)
    
    keys = []
    for i in range(count):
        key = generate_api_key()
        key_hash = hash_api_key(key)
        keys.append(key)
        
        print(f"\nKey {i+1}:")
        print(f"  API Key: {key}")
        print(f"  Hash: {key_hash[:16]}...")
    
    print("\n" + "=" * 60)
    print("\nAdd to your .env file:")
    print(f"API_KEYS={','.join(keys)}")
    print("\nEnable API authentication:")
    print("API_AUTH_ENABLED=True")
    print("\nNever share these keys or commit them to version control!")
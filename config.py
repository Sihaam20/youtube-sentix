import secrets

# Generate a secure random key with 24 bytes (recommended)
SECRET_KEY = secrets.token_hex(24)
print(SECRET_KEY)
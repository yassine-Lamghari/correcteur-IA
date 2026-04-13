import requests

# Create a test user
print("Creating test user...")
try:
    url = "http://127.0.0.1:8000/api/v1/auth/register"
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    }

    response = requests.post(url, json=payload, timeout=30)
    print(f"Registration status: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 200:
        print("User created successfully!")

        # Now login
        print("\nLogging in...")
        login_url = "http://127.0.0.1:8000/api/v1/auth/login"
        login_data = {"username": "testuser", "password": "testpass123"}

        login_response = requests.post(login_url, data=login_data, timeout=30)
        print(f"Login status: {login_response.status_code}")

        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            print(f"Login successful! Token: {token[:50]}...")
        else:
            print(f"Login failed: {login_response.text}")
    else:
        print("User might already exist. Trying to login...")

        # Try to login with existing user
        login_url = "http://127.0.0.1:8000/api/v1/auth/login"
        login_data = {"username": "testuser", "password": "testpass123"}

        response = requests.post(login_url, data=login_data, timeout=30)
        print(f"Login status: {response.status_code}")

        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"Login successful! Token: {token[:50]}...")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
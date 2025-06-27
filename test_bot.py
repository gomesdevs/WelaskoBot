import requests

token = "8092707019:AAHAKF6wXgulDy8uLnbN-6ZhXAdOjpZNAvA"

# Testar se o bot está acessível
response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
print("Status:", response.status_code)
print("Response:", response.json())
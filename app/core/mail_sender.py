import requests

EMAIL_SERVICE_URL = "http://email-service:5000/send-email"


def send_verification_email(to_email: str, verification_link: str):
    try:
        response = requests.post(
            EMAIL_SERVICE_URL,
            json={
                "to": to_email,
                "subject": "Verify Your Account",
                "text": f"Click the link below to verify your account:\n\n{verification_link}"
            },
            timeout=10
        )

        response.raise_for_status()
        print("Verification email sent to:", to_email)
        return True

    except requests.RequestException as e:
        print("Email service error:", e)
        return False

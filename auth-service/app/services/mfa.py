"""
auth-service/app/services/mfa.py

TOTP-based MFA using pyotp (Google Authenticator compatible).

TOTP (Time-based One-Time Password, RFC 6238) generates 6-digit codes that
change every 30 seconds using a shared secret + current time. This is the
same algorithm used by Google Authenticator, Authy, and most authenticator apps.

The shared secret is stored encrypted in the DB (see crypto.py) so a DB breach
alone cannot be used to generate valid codes without the master encryption key.
"""

import io
import base64
import pyotp
import qrcode
from typing import Optional
from ..config import settings


def generate_totp_secret() -> str:
    """
    Generate a new random TOTP secret.
    pyotp.random_base32() returns a 16+ character base32 string
    that encodes 80+ bits of entropy — sufficient for TOTP security.
    """
    return pyotp.random_base32()


def get_totp_uri(secret: str, user_email: str) -> str:
    """
    Build the otpauth:// URI that QR code apps parse.
    The issuer label (org name) appears in the authenticator app alongside
    the user's email so they can identify which account the code is for.
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=user_email,
        issuer_name=settings.ORG_NAME
    )


def generate_qr_code_base64(secret: str, user_email: str) -> str:
    """
    Generate a QR code PNG image and return it as a base64 string.
    The frontend renders this as <img src="data:image/png;base64,...">
    without needing to store or serve the image as a separate file.
    """
    uri = get_totp_uri(secret, user_email)
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Write to in-memory buffer — avoids temp files and filesystem permission issues
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify a 6-digit TOTP code against the user's secret.
    
    valid_window=1 allows ±30 seconds of clock drift between the user's
    device and the server — necessary because mobile device clocks can lag
    and TOTP codes are only valid for 30-second windows.
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)

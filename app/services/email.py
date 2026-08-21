import secrets
import logging
from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

# Setup FastAPI Mail Configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    SUPPRESS_SEND=settings.SUPPRESS_SEND
)

fastmail = FastMail(conf)


def generate_otp() -> str:
    """Generates a secure 6-digit numeric OTP string."""
    return str(secrets.randbelow(900000) + 100000)


async def send_email_async(subject: str, email_to: str, html_content: str) -> None:
    """Sends email asynchronously."""
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=html_content,
        subtype=MessageType.html
    )

    if settings.SUPPRESS_SEND:
        logger.info(f"========== DEV EMAIL QUEUED ==========")
        logger.info(f"TO: {email_to}")
        logger.info(f"SUBJECT: {subject}")
        logger.info(f"BODY:\n{html_content}")
        logger.info(f"=======================================")
    else:
        try:
            await fastmail.send_message(message)
            logger.info(f"Email sent successfully to {email_to}")
        except Exception as e:
            logger.error(f"Failed to send email to {email_to}: {str(e)}")


class EmailQueueService:

    @classmethod
    def send_verification_otp(
        cls,
        background_tasks: BackgroundTasks,
        email: str,
        otp: str,
        full_name: str
    ) -> None:
        """Enqueues verification OTP email task to FastAPI BackgroundTasks."""
        subject = f"Your Verification Code: {otp}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #2c3e50;">Welcome to {settings.PROJECT_NAME}, {full_name}!</h2>
                    <p>Thank you for signing up. Please use the following 6-digit verification code to complete your registration:</p>
                    <div style="background-color: #f4f6f7; padding: 15px; text-align: center; border-radius: 6px; margin: 20px 0;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #2980b9;">{otp}</span>
                    </div>
                    <p><strong>Note:</strong> This OTP is valid for <strong>5 minutes</strong>. If you did not request this code, please ignore this email.</p>
                </div>
            </body>
        </html>
        """
        background_tasks.add_task(send_email_async, subject, email, html_content)

    @classmethod
    def send_password_reset_otp(
        cls,
        background_tasks: BackgroundTasks,
        email: str,
        otp: str,
        full_name: str
    ) -> None:
        """Enqueues password reset OTP email task to FastAPI BackgroundTasks."""
        subject = f"Password Reset Code: {otp}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #2c3e50;">Password Reset Request</h2>
                    <p>Hi {full_name},</p>
                    <p>We received a request to reset your password. Use the code below to proceed:</p>
                    <div style="background-color: #f4f6f7; padding: 15px; text-align: center; border-radius: 6px; margin: 20px 0;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #e74c3c;">{otp}</span>
                    </div>
                    <p><strong>Note:</strong> This code will expire in <strong>5 minutes</strong>.</p>
                </div>
            </body>
        </html>
        """
        background_tasks.add_task(send_email_async, subject, email, html_content)

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

SENDGRID_API_KEY    = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL          = os.getenv("SENDGRID_FROM_EMAIL")
FRONTEND_URL        = os.getenv("FRONTEND_URL", "http://localhost:3000")



async def send_otp_email(to_email: str, otp: str, name: str) -> bool:
    print(SENDGRID_API_KEY)
    print(FROM_EMAIL)
    try:
        # message = Mail(
        #     from_email  = FROM_EMAIL,
        #     to_emails   = to_email,
        #     subject     = "Your Verification Code",
        #     html_content= f"""
        #     <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        #         <h2 style="color: #1F4E79;">Verify Your Account</h2>
        #         <p>Hi {name},</p>
        #         <p>Your one-time verification code is:</p>
        #         <div style="background: #f0f4f8; padding: 20px; text-align: center; 
        #                     border-radius: 8px; margin: 20px 0;">
        #             <h1 style="color: #1F4E79; letter-spacing: 8px; margin: 0;">
        #                 {otp}
        #             </h1>
        #         </div>
        #         <p>This code expires in <strong>1 minute</strong>.</p>
        #         <p>If you did not create an account, ignore this email.</p>
        #         <br/>
        #         <p>— Chat App Team</p>
        #     </div>
        #     """
        # )
        message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject="K-Chat - Verification Code",
        plain_text_content=f"Your verification code is: {otp}",
        html_content=f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
            <h2 style="color: #1F4E79;">Verify Your Account</h2>

            <p>Hi {name},</p>

            <p>Your one-time verification code is:</p>

            <div style="
                background: #f0f4f8;
                padding: 20px;
                text-align: center;
                border-radius: 8px;
                margin: 20px 0;
            ">
                <h1 style="
                    color: #1F4E79;
                    letter-spacing: 8px;
                    margin: 0;
                ">
                    {otp}
                </h1>
            </div>

            <p>This code expires in <strong>1 minute</strong>.</p>

            <p>If you did not request this, you can safely ignore this email.</p>

            <hr>

            <p style="font-size:12px;color:#666;">
                K-Chat Support<br>
                support@yourdomain.com
            </p>
        </div>
        """
        )

        sg          = SendGridAPIClient(SENDGRID_API_KEY)
        response    = sg.send(message)
        print(f"Email sent to {to_email} — Status: {response.status_code}")
        return True

    except Exception as e:
        print(f"SendGrid error: {e}")
        return False


async def send_password_reset_email(to_email: str, name: str, token: str) -> bool:
    reset_link = f"{FRONTEND_URL}/reset_password?token={token}"
    try:
        message = Mail(
            from_email   = FROM_EMAIL,
            to_emails    = to_email,
            subject      = "K-Chat - Reset Your Password",
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
                <h2 style="color: #1F4E79;">Reset Your Password</h2>
                <p>Hi {name},</p>
                <p>We received a request to reset your password.
                   Click the button below to set a new one:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}"
                       style="background: #1F4E79; color: white; padding: 14px 28px;
                              text-decoration: none; border-radius: 6px;
                              font-size: 16px; font-weight: bold;">
                        Reset Password
                    </a>
                </div>
                <p>This link expires in <strong>10 minutes</strong>.</p>
                <p>If you did not request a password reset, ignore this email.
                   Your password will not change.</p>
                <br/>
                <p>— K-Chat Team</p>
            </div>
            """
        )
        sg       = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Reset email sent to {to_email} — Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"SendGrid reset error: {e}")
        return False
"""Email Service for sending notifications.

This service handles all email-related operations including:
- Sending alert emails
- Managing SMTP configuration
- Logging email attempts
"""

import logging
import smtplib
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""
    
    # Default SMTP settings (can be overridden via settings)
    DEFAULT_SMTP_HOST = 'smtp.gmail.com'
    DEFAULT_SMTP_PORT = 587
    
    # These should be configured via environment variables in production
    DEFAULT_SENDER_EMAIL = 'wildeye2026@gmail.com'
    DEFAULT_SENDER_PASSWORD = 'rgww pfxi huno frig'
    
    @classmethod
    def _get_smtp_config(cls) -> dict:
        """Get SMTP configuration from settings or defaults.
        
        Returns:
            Dictionary with SMTP configuration
        """
        from django.conf import settings
        
        return {
            'host': getattr(settings, 'EMAIL_SMTP_HOST', cls.DEFAULT_SMTP_HOST),
            'port': getattr(settings, 'EMAIL_SMTP_PORT', cls.DEFAULT_SMTP_PORT),
            'sender_email': getattr(settings, 'EMAIL_SENDER', cls.DEFAULT_SENDER_EMAIL),
            'sender_password': getattr(settings, 'EMAIL_PASSWORD', cls.DEFAULT_SENDER_PASSWORD),
        }
    
    @classmethod
    def send_mail(
        cls,
        subject: str,
        message: str,
        to: str,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None
    ) -> bool:
        """Send an email message.
        
        Args:
            subject: Email subject line
            message: Email body content
            to: Recipient email address
            sender_email: Optional override for sender email
            sender_password: Optional override for sender password
            
        Returns:
            True if email sent successfully, False otherwise
        """
        config = cls._get_smtp_config()
        
        # Use provided credentials or fall back to config
        email = sender_email or config['sender_email']
        password = sender_password or config['sender_password']
        
        try:
            logger.info(f"Sending email to {to}: {subject}")
            
            # Create SMTP session
            server = smtplib.SMTP(config['host'], config['port'])
            server.starttls()  # Enable TLS
            
            # Login and send
            server.login(email, password)
            
            # Format message
            formatted_message = f'Subject: {subject}\n\n{message}'
            
            server.sendmail(email, to, formatted_message)
            server.quit()
            
            logger.info(f"Email sent successfully to {to}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    @classmethod
    def send_alert(
        cls,
        message: str,
        recipient_list: list,
        subject: str = "Wild Animal Alert"
    ) -> dict:
        """Send alert emails to multiple recipients.
        
        Args:
            message: Alert message content
            recipient_list: List of recipient email addresses
            subject: Email subject (default: "Wild Animal Alert")
            
        Returns:
            Dictionary with 'success_count' and 'failed_count'
        """
        success_count = 0
        failed_count = 0
        
        for recipient in recipient_list:
            if cls.send_mail(subject, message, recipient):
                success_count += 1
            else:
                failed_count += 1
        
        logger.info(
            f"Alert emails sent: {success_count} success, {failed_count} failed"
        )
        
        return {
            'success_count': success_count,
            'failed_count': failed_count
        }
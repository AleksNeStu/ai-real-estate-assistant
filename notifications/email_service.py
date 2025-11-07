"""
Email service for sending notifications.

Supports multiple email providers (Gmail, Outlook, SendGrid)
with HTML templates, retry logic, and rate limiting.
"""

import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum
import re


class EmailProvider(str, Enum):
    """Supported email providers."""
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    SENDGRID = "sendgrid"
    CUSTOM = "custom"


@dataclass
class EmailConfig:
    """Email service configuration."""
    provider: EmailProvider
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    from_email: str
    from_name: str = "Real Estate Assistant"
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = 30


class EmailValidationError(Exception):
    """Raised when email validation fails."""
    pass


class EmailSendError(Exception):
    """Raised when email sending fails."""
    pass


class EmailService:
    """
    Email service for sending notifications.

    Supports HTML and plain text emails with retry logic.
    """

    def __init__(self, config: EmailConfig, max_retries: int = 3):
        """
        Initialize email service.

        Args:
            config: Email configuration
            max_retries: Maximum number of retry attempts
        """
        self.config = config
        self.max_retries = max_retries
        self._sent_count = 0
        self._failed_count = 0

    def validate_email(self, email: str) -> bool:
        """
        Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            html: Whether body is HTML
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            True if sent successfully, False otherwise

        Raises:
            EmailValidationError: If email address is invalid
            EmailSendError: If sending fails after retries
        """
        # Validate recipient
        if not self.validate_email(to_email):
            raise EmailValidationError(f"Invalid email address: {to_email}")

        # Validate CC/BCC if provided
        if cc:
            for email in cc:
                if not self.validate_email(email):
                    raise EmailValidationError(f"Invalid CC email: {email}")

        if bcc:
            for email in bcc:
                if not self.validate_email(email):
                    raise EmailValidationError(f"Invalid BCC email: {email}")

        # Create message
        msg = self._create_message(to_email, subject, body, html, cc, bcc)

        # Send with retry logic
        for attempt in range(self.max_retries):
            try:
                self._send_message(msg)
                self._sent_count += 1
                return True
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self._failed_count += 1
                    raise EmailSendError(f"Failed to send email after {self.max_retries} attempts: {str(e)}")

                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt
                time.sleep(wait_time)

        return False

    def send_bulk_emails(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        html: bool = False,
        batch_size: int = 50,
        delay_between_batches: float = 1.0
    ) -> dict:
        """
        Send email to multiple recipients in batches.

        Args:
            recipients: List of recipient email addresses
            subject: Email subject
            body: Email body
            html: Whether body is HTML
            batch_size: Number of emails per batch
            delay_between_batches: Delay between batches (seconds)

        Returns:
            Dictionary with success/failure counts
        """
        results = {
            'sent': 0,
            'failed': 0,
            'failed_emails': []
        }

        for i in range(0, len(recipients), batch_size):
            batch = recipients[i:i + batch_size]

            for email in batch:
                try:
                    self.send_email(email, subject, body, html)
                    results['sent'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['failed_emails'].append({'email': email, 'error': str(e)})

            # Delay between batches to avoid rate limits
            if i + batch_size < len(recipients):
                time.sleep(delay_between_batches)

        return results

    def send_test_email(self, to_email: str) -> bool:
        """
        Send a test email to verify configuration.

        Args:
            to_email: Test recipient

        Returns:
            True if successful
        """
        subject = "Test Email - Real Estate Assistant"
        body = """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Test Email</h2>
            <p>This is a test email to verify your email configuration.</p>
            <p>If you're receiving this, your email service is working correctly!</p>
            <p style="color: #666; font-size: 0.9em; margin-top: 20px;">
                Sent from Real Estate Assistant Notification System
            </p>
        </body>
        </html>
        """

        return self.send_email(to_email, subject, body, html=True)

    def get_statistics(self) -> dict:
        """
        Get email sending statistics.

        Returns:
            Dictionary with sent/failed counts
        """
        total = self._sent_count + self._failed_count
        success_rate = (self._sent_count / total * 100) if total > 0 else 0

        return {
            'sent': self._sent_count,
            'failed': self._failed_count,
            'total': total,
            'success_rate': success_rate
        }

    def _create_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool,
        cc: Optional[List[str]],
        bcc: Optional[List[str]]
    ) -> MIMEMultipart:
        """Create email message."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr((self.config.from_name, self.config.from_email))
        msg['To'] = to_email

        if cc:
            msg['Cc'] = ', '.join(cc)

        if bcc:
            msg['Bcc'] = ', '.join(bcc)

        # Add body
        if html:
            part = MIMEText(body, 'html')
        else:
            part = MIMEText(body, 'plain')

        msg.attach(part)

        return msg

    def _send_message(self, msg: MIMEMultipart):
        """Send email message via SMTP."""
        if self.config.use_ssl:
            # Use SSL
            with smtplib.SMTP_SSL(
                self.config.smtp_server,
                self.config.smtp_port,
                timeout=self.config.timeout
            ) as server:
                server.login(self.config.username, self.config.password)
                server.send_message(msg)
        else:
            # Use TLS
            with smtplib.SMTP(
                self.config.smtp_server,
                self.config.smtp_port,
                timeout=self.config.timeout
            ) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.username, self.config.password)
                server.send_message(msg)


class EmailServiceFactory:
    """Factory for creating pre-configured email services."""

    @staticmethod
    def create_gmail_service(
        username: str,
        password: str,
        from_name: str = "Real Estate Assistant"
    ) -> EmailService:
        """
        Create Gmail email service.

        Args:
            username: Gmail address
            password: App-specific password
            from_name: Display name for sender

        Returns:
            Configured EmailService
        """
        config = EmailConfig(
            provider=EmailProvider.GMAIL,
            smtp_server='smtp.gmail.com',
            smtp_port=587,
            username=username,
            password=password,
            from_email=username,
            from_name=from_name,
            use_tls=True,
            use_ssl=False
        )

        return EmailService(config)

    @staticmethod
    def create_outlook_service(
        username: str,
        password: str,
        from_name: str = "Real Estate Assistant"
    ) -> EmailService:
        """
        Create Outlook/Hotmail email service.

        Args:
            username: Outlook email address
            password: Account password
            from_name: Display name for sender

        Returns:
            Configured EmailService
        """
        config = EmailConfig(
            provider=EmailProvider.OUTLOOK,
            smtp_server='smtp-mail.outlook.com',
            smtp_port=587,
            username=username,
            password=password,
            from_email=username,
            from_name=from_name,
            use_tls=True,
            use_ssl=False
        )

        return EmailService(config)

    @staticmethod
    def create_custom_service(
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        from_name: str = "Real Estate Assistant",
        use_tls: bool = True,
        use_ssl: bool = False
    ) -> EmailService:
        """
        Create custom SMTP email service.

        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP port
            username: SMTP username
            password: SMTP password
            from_email: Sender email address
            from_name: Display name for sender
            use_tls: Whether to use TLS
            use_ssl: Whether to use SSL

        Returns:
            Configured EmailService
        """
        config = EmailConfig(
            provider=EmailProvider.CUSTOM,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            username=username,
            password=password,
            from_email=from_email,
            from_name=from_name,
            use_tls=use_tls,
            use_ssl=use_ssl
        )

        return EmailService(config)

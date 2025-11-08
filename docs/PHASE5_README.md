# Phase 5: Notification System

## Overview

Phase 5 implements a comprehensive notification system that alerts users about property updates, price changes, and new listings matching their saved searches.

**Status**: 🚧 In Progress
**Version**: 1.0.0
**Date**: 2025-11-07

---

## 🎯 Goals

1. **Email Notifications**: Send automated email alerts to users
2. **Price Drop Alerts**: Notify when property prices decrease
3. **New Property Alerts**: Notify about new listings matching saved searches
4. **Scheduled Digests**: Daily/weekly summary of market activity
5. **Notification Preferences**: User control over notification types and frequency
6. **Notification History**: Track all sent notifications

---

## 📦 Features

### 1. Email Service (`notifications/email_service.py`)

**SMTP-based email delivery with support for:**
- Multiple email providers (Gmail, Outlook, SendGrid)
- HTML and plain text emails
- Attachment support
- Template rendering
- Retry logic with exponential backoff
- Rate limiting
- Email validation

### 2. Alert Manager (`notifications/alert_manager.py`)

**Intelligent alert triggering:**
- Price drop detection
- New property matching
- Saved search monitoring
- Alert deduplication
- Customizable thresholds
- Batch alert processing

### 3. Notification Preferences (`notifications/notification_preferences.py`)

**User preference management:**
- Email frequency (instant, daily, weekly)
- Alert types (price drops, new properties, market updates)
- Quiet hours
- Alert thresholds (e.g., only > 10% price drops)
- Per-search notification settings

### 4. Email Templates (`notifications/email_templates.py`)

**Professional HTML email templates:**
- Price drop alert template
- New property alert template
- Daily digest template
- Weekly summary template
- Saved search match template
- Responsive design for mobile

### 5. Notification History (`notifications/notification_history.py`)

**Track and manage notifications:**
- Sent notification log
- Delivery status tracking
- User notification statistics
- Failure tracking and retry queue
- Notification analytics

---

## 🔧 Configuration

### Email Provider Setup

**Gmail:**
```python
email_config = {
    'provider': 'gmail',
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'username': 'your-email@gmail.com',
    'password': 'app-specific-password',  # Use app password, not account password
    'use_tls': True
}
```

**SendGrid:**
```python
email_config = {
    'provider': 'sendgrid',
    'api_key': 'your-sendgrid-api-key',
    'from_email': 'notifications@yourdomain.com',
    'from_name': 'Real Estate Assistant'
}
```

**Environment Variables:**
```bash
# .env file
EMAIL_PROVIDER=gmail
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM_NAME=Real Estate Assistant
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

---

## 📚 Usage Examples

### Setting Up Email Service

```python
from notifications import EmailService, EmailConfig

# Configure email service
config = EmailConfig(
    provider='gmail',
    smtp_server='smtp.gmail.com',
    smtp_port=587,
    username='your-email@gmail.com',
    password='your-app-password',
    use_tls=True,
    from_email='your-email@gmail.com',
    from_name='Real Estate Assistant'
)

# Initialize service
email_service = EmailService(config)

# Send simple email
email_service.send_email(
    to_email='user@example.com',
    subject='Price Drop Alert',
    body='A property you saved has dropped in price!',
    html=True
)
```

### Price Drop Alerts

```python
from notifications import AlertManager
from utils import SavedSearchManager

# Initialize managers
alert_manager = AlertManager(email_service)
search_manager = SavedSearchManager()

# Check for price drops
price_drops = alert_manager.check_price_drops(
    current_properties=current_listings,
    previous_properties=previous_listings,
    threshold_percent=5.0  # Alert for 5%+ drops
)

# Send alerts
for drop in price_drops:
    alert_manager.send_price_drop_alert(
        user_email='user@example.com',
        property_info=drop['property'],
        old_price=drop['old_price'],
        new_price=drop['new_price'],
        percent_drop=drop['percent_drop']
    )
```

### New Property Alerts

```python
# Check for new properties matching saved searches
new_matches = alert_manager.check_new_property_matches(
    new_properties=today_listings,
    saved_searches=search_manager.get_all_searches(),
    user_email='user@example.com'
)

# Send new property alerts
alert_manager.send_new_property_alerts(
    user_email='user@example.com',
    matches=new_matches
)
```

### Scheduled Digest

```python
from notifications import DigestGenerator

# Generate daily digest
digest = DigestGenerator(properties)
digest_html = digest.generate_daily_digest(
    user_searches=user_searches,
    new_properties_count=15,
    price_changes_count=5,
    market_summary=market_insights.get_overall_statistics()
)

# Send digest
email_service.send_email(
    to_email='user@example.com',
    subject='Daily Real Estate Digest - November 7, 2025',
    body=digest_html,
    html=True
)
```

### User Preferences

```python
from notifications import NotificationPreferences, AlertFrequency, AlertType

# Create preferences
prefs = NotificationPreferences(
    user_email='user@example.com',
    alert_frequency=AlertFrequency.DAILY,
    enabled_alerts=[
        AlertType.PRICE_DROP,
        AlertType.NEW_PROPERTY,
        AlertType.MARKET_UPDATE
    ],
    price_drop_threshold=5.0,  # Only alert for 5%+ drops
    quiet_hours_start='22:00',
    quiet_hours_end='08:00',
    digest_day='monday'  # Weekly digest on Mondays
)

# Save preferences
prefs_manager = NotificationPreferencesManager()
prefs_manager.save_preferences(prefs)
```

---

## 📧 Email Templates

### Price Drop Alert

```html
Subject: 🔔 Price Drop Alert - Property in {city}

<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
        <h2 style="color: #2ca02c;">💰 Price Drop Alert!</h2>

        <p>Great news! A property you're watching has dropped in price:</p>

        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <h3 style="margin-top: 0;">{property_type} in {city}</h3>
            <p><strong>Previous Price:</strong> <span style="text-decoration: line-through;">${old_price}</span></p>
            <p><strong>New Price:</strong> <span style="color: #2ca02c; font-size: 1.2em;">${new_price}</span></p>
            <p><strong>Savings:</strong> <span style="color: #2ca02c;">-{percent_drop}% (${savings})</span></p>

            <div style="margin-top: 15px;">
                <p><strong>Details:</strong></p>
                <ul>
                    <li>{rooms} bedrooms, {bathrooms} bathrooms</li>
                    <li>{area_sqm} sqm</li>
                    <li>Amenities: {amenities}</li>
                </ul>
            </div>

            <a href="{property_url}" style="display: inline-block; background-color: #1f77b4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 10px;">
                View Property
            </a>
        </div>

        <p style="color: #666; font-size: 0.9em;">
            You're receiving this because you saved this property or have an active search matching it.
        </p>
    </div>
</body>
</html>
```

### New Property Match

```html
Subject: 🏠 New Properties Match Your Search - {search_name}

<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
        <h2 style="color: #1f77b4;">🏠 New Property Matches!</h2>

        <p>We found {count} new properties matching your search: <strong>{search_name}</strong></p>

        {for property in properties}
        <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #1f77b4;">
            <h3 style="margin-top: 0;">{property.city} - ${property.price}/month</h3>
            <p>{property.rooms} bed | {property.bathrooms} bath | {property.area_sqm} sqm</p>
            <p>{property.description}</p>
            <a href="{property.url}">View Details →</a>
        </div>
        {endfor}

        <a href="{manage_searches_url}" style="display: inline-block; background-color: #1f77b4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 10px;">
            Manage Searches
        </a>
    </div>
</body>
</html>
```

### Daily Digest

```html
Subject: 📊 Your Daily Real Estate Digest - {date}

<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
        <h2>📊 Daily Real Estate Digest</h2>
        <p style="color: #666;">{date}</p>

        <div style="display: flex; justify-content: space-around; margin: 20px 0;">
            <div style="text-align: center;">
                <h3 style="color: #1f77b4; margin: 5px 0;">{new_properties}</h3>
                <p style="color: #666; margin: 0;">New Properties</p>
            </div>
            <div style="text-align: center;">
                <h3 style="color: #2ca02c; margin: 5px 0;">{price_drops}</h3>
                <p style="color: #666; margin: 0;">Price Drops</p>
            </div>
            <div style="text-align: center;">
                <h3 style="color: #ff7f0e; margin: 5px 0;">${avg_price}</h3>
                <p style="color: #666; margin: 0;">Avg Price</p>
            </div>
        </div>

        <h3>📈 Market Summary</h3>
        <ul>
            <li>Total Active Listings: {total_properties}</li>
            <li>Average Price: ${average_price}</li>
            <li>Price Trend: {trend_direction} ({trend_percent}%)</li>
        </ul>

        <h3>🔔 Your Saved Searches</h3>
        {for search in active_searches}
        <div style="background-color: white; padding: 10px; border-radius: 5px; margin: 10px 0;">
            <strong>{search.name}</strong>: {search.new_matches} new matches
        </div>
        {endfor}

        <a href="{dashboard_url}" style="display: inline-block; background-color: #1f77b4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 15px;">
            View Dashboard
        </a>
    </div>
</body>
</html>
```

---

## 🔒 Security & Privacy

### Best Practices

1. **Email Security:**
   - Use app-specific passwords (not account passwords)
   - Enable 2FA on email accounts
   - Use TLS/SSL for SMTP connections
   - Validate email addresses before sending

2. **Data Privacy:**
   - Store minimal user data
   - Encrypt sensitive information
   - Comply with email marketing regulations (CAN-SPAM, GDPR)
   - Provide easy unsubscribe options

3. **Rate Limiting:**
   - Limit emails per user per day
   - Implement exponential backoff for retries
   - Respect email provider limits

4. **Unsubscribe:**
   - Include unsubscribe link in all emails
   - Honor unsubscribe requests immediately
   - Provide preference management UI

---

## 🧪 Testing

### Unit Tests

```bash
# Run all Phase 5 tests
./run_tests.sh phase5

# Run specific components
./run_tests.sh email        # Email service tests
./run_tests.sh alerts       # Alert manager tests
./run_tests.sh notifications # Full notification tests
```

### Manual Testing

```python
# Test email sending
from notifications import EmailService

service = EmailService(config)
service.send_test_email('your-email@example.com')
```

---

## 📊 Notification Analytics

Track notification effectiveness:

```python
from notifications import NotificationHistory

history = NotificationHistory()

# Get statistics
stats = history.get_statistics(user_email='user@example.com')
print(f"Total sent: {stats.total_sent}")
print(f"Open rate: {stats.open_rate}%")
print(f"Click rate: {stats.click_rate}%")

# Get recent notifications
recent = history.get_recent_notifications(limit=10)
```

---

## 🚀 Deployment

### Scheduled Jobs

Use cron or task scheduler for periodic checks:

```bash
# Check for new properties every hour
0 * * * * python -m notifications.jobs.check_new_properties

# Send daily digests at 8 AM
0 8 * * * python -m notifications.jobs.send_daily_digest

# Send weekly digests on Monday at 9 AM
0 9 * * 1 python -m notifications.jobs.send_weekly_digest

# Check price drops every 6 hours
0 */6 * * * python -m notifications.jobs.check_price_drops
```

### Production Considerations

1. **Email Service:**
   - Use dedicated email service (SendGrid, AWS SES)
   - Set up SPF, DKIM, DMARC records
   - Monitor deliverability rates

2. **Queue System:**
   - Use message queue (Redis, RabbitMQ) for high volume
   - Implement retry logic
   - Handle failures gracefully

3. **Monitoring:**
   - Track delivery rates
   - Monitor bounce rates
   - Alert on delivery failures

---

## 📝 Change Log

### Version 1.0.0 (2025-11-07)

**New Features:**
- ✅ Email service with SMTP support
- ✅ Price drop alert system
- ✅ New property matching alerts
- ✅ User notification preferences
- ✅ HTML email templates
- ✅ Notification history tracking
- ✅ Scheduled digest generation
- ✅ Alert deduplication
- ✅ Rate limiting
- ✅ Retry logic

---

## 🤝 Contributing

When extending Phase 5:

1. **Add new alert types**: Extend AlertType enum
2. **New templates**: Add to email_templates.py
3. **Test thoroughly**: Add unit tests for new features
4. **Rate limits**: Respect email provider limits
5. **User privacy**: Always provide unsubscribe option

---

**Phase 5 Status**: 🚧 In Progress
**Next Step**: Implement email service and alert manager

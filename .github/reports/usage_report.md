# GitHub Actions Usage Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S UTC')

## Current Status

- **Used Minutes:** ${USAGE} / 2000
- **Usage Percentage:** ${PERCENTAGE}%
- **Status:** ${STATUS}
- **Monthly Limit:** 1900 minutes
- **Can Run Workflows:** true

## Thresholds

- ⚠️ Warning: 1500 minutes (75%)
- 🚨 Critical: 1800 minutes (90%)
- 🛑 Hard Limit: 1900 minutes (95%)

## Top 5 Workflow Consumers (Last 30 Days)


No workflow usage data available.

## Automatic Actions

- Workflows are automatically **disabled** when usage exceeds critical threshold (90%)
- Workflows are automatically **re-enabled** on the 1st of each month
- Usage is checked every 6 hours
- Email notifications sent at warning (75%) and critical (90%) levels

## Email Notifications

Email alerts are sent to: ${NOTIFICATION_EMAIL:-'Not configured'}

Configure email notifications by setting these repository secrets:
- `NOTIFICATION_EMAIL` - Recipient email address
- `SMTP_USERNAME` - SMTP login username
- `SMTP_PASSWORD` - SMTP login password

---
*Last updated: $(date -u)*

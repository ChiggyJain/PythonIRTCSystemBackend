
#!/usr/bin/env bash

# Base target
export BASE_URL="http://127.0.0.1:8000"

# Load profile (for most APIs)
export VUS=2
export DURATION=30s

# Verified user (must have is_email_verified=Y)
export TEST_USER_EMAIL_VERIFIED="verified.user@example.com"
export TEST_USER_PASSWORD_VERIFIED="Password@123"

# Unverified user (must have is_email_verified=N)
export TEST_USER_EMAIL_UNVERIFIED="unverified.user@example.com"
export TEST_USER_PASSWORD_UNVERIFIED="Password@123"

# For single-shot confirm scripts (manual OTP flow)
# Set these right before running confirm scripts.
# export ACCESS_TOKEN="..."
# export CHALLENGE_ID="..."
# export OTP_CODE="123456"
# export NEW_PASSWORD="NewStrong@123"
# export CONFIRM_PASSWORD="NewStrong@123"

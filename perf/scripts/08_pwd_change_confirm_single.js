import http from 'k6/http';
import { check, fail } from 'k6';
import { BASE_URL, buildSingleOptions } from '../lib/config.js';
import { authHeaders, envOrFail } from '../lib/helpers.js';

export const options = buildSingleOptions('pwd_change_confirm', 1200, 1);

export default function () {
  // Single-shot only. OTP/challenge are one-time.
  const accessToken = envOrFail('ACCESS_TOKEN');
  const challengeId = envOrFail('CHALLENGE_ID');
  const otpCode = envOrFail('OTP_CODE');
  const newPassword = envOrFail('NEW_PASSWORD');
  const confirmPassword = envOrFail('CONFIRM_PASSWORD');

  if (newPassword !== confirmPassword) {
    fail('NEW_PASSWORD and CONFIRM_PASSWORD must match');
  }

  const res = http.post(
    `${BASE_URL}/api/v1/users/password/change/confirm`,
    JSON.stringify({
      challenge_id: challengeId,
      otp: otpCode,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }),
    {
      headers: authHeaders(accessToken),
      tags: { endpoint: 'pwd_change_confirm' },
    }
  );

  check(res, {
    'pwd confirm http 200': (r) => r.status === 200,
  });
}

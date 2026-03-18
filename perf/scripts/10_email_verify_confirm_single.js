import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, buildSingleOptions } from '../lib/config.js';
import { authHeaders, envOrFail } from '../lib/helpers.js';

export const options = buildSingleOptions('email_verify_confirm', 1200, 1);

export default function () {
  // Single-shot only. OTP/challenge are one-time.
  const accessToken = envOrFail('ACCESS_TOKEN');
  const challengeId = envOrFail('CHALLENGE_ID');
  const otpCode = envOrFail('OTP_CODE');

  const res = http.post(
    `${BASE_URL}/api/v1/users/email/verification/confirm`,
    JSON.stringify({
      challenge_id: challengeId,
      otp: otpCode,
    }),
    {
      headers: authHeaders(accessToken),
      tags: { endpoint: 'email_verify_confirm' },
    }
  );

  check(res, {
    'email verify confirm http 200': (r) => r.status === 200,
  });
}

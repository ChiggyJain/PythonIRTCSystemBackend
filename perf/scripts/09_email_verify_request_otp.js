import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, buildLoadOptions } from '../lib/config.js';
import { authHeaders, loginUnverifiedUser, safeJson } from '../lib/helpers.js';

export const options = buildLoadOptions('email_verify_request_otp', 700, Number(__ENV.VUS || 1), __ENV.DURATION || '20s');

export default function () {
  const tokens = loginUnverifiedUser('login_setup_email_verify_req');

  const res = http.post(
    `${BASE_URL}/api/v1/users/email/verification/request-otp`,
    JSON.stringify({ channel: 'EMAIL' }),
    {
      headers: authHeaders(tokens.accessToken),
      tags: { endpoint: 'email_verify_request_otp' },
    }
  );

  const body = safeJson(res);

  check(res, {
    'email verify request http 202': (r) => r.status === 202,
    'email verify request has challenge_id': () => !!body?.data?.challenge_id,
  });
}

import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, buildLoadOptions } from '../lib/config.js';
import { authHeaders, loginVerifiedUser, safeJson, uniqueEmail } from '../lib/helpers.js';

export const options = buildLoadOptions('email_change_request_otp', 700, Number(__ENV.VUS || 1), __ENV.DURATION || '20s');

export default function () {
  const tokens = loginVerifiedUser('login_setup_email_change_req');

  const res = http.post(
    `${BASE_URL}/api/v1/users/email/change/request-otp`,
    JSON.stringify({
      channel: 'EMAIL',
      new_email: uniqueEmail('emailchange'),
    }),
    {
      headers: authHeaders(tokens.accessToken),
      tags: { endpoint: 'email_change_request_otp' },
    }
  );

  const body = safeJson(res);

  check(res, {
    'email change request http 202': (r) => r.status === 202,
    'email change request has challenge_id': () => !!body?.data?.challenge_id,
  });
}

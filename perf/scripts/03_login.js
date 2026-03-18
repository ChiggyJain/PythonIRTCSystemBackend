
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, JSON_HEADERS, buildLoadOptions } from '../lib/config.js';
import { envOrFail, safeJson } from '../lib/helpers.js';

export const options = buildLoadOptions('login', 1000, Number(__ENV.VUS || 1), __ENV.DURATION || '20s');

export default function () {
  const payload = {
    email: envOrFail('TEST_USER_EMAIL_VERIFIED'),
    password: envOrFail('TEST_USER_PASSWORD_VERIFIED'),
  };

  const res = http.post(`${BASE_URL}/api/v1/users/login`, JSON.stringify(payload), {
    headers: JSON_HEADERS,
    tags: { endpoint: 'login' },
  });

  const body = safeJson(res);

  check(res, {
    'login http 200': (r) => r.status === 200,
    'login access token exists': () => !!body?.data?.tokens?.access_token,
    'login refresh token exists': () => !!body?.data?.tokens?.refresh_token,
  });
}

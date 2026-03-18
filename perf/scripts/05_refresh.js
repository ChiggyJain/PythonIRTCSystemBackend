import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, JSON_HEADERS, buildLoadOptions } from '../lib/config.js';
import { loginVerifiedUser, safeJson } from '../lib/helpers.js';

export const options = buildLoadOptions('refresh', 500, Number(__ENV.VUS || 1), __ENV.DURATION || '20s');

export default function () {
  // Fresh token each iteration to avoid using revoked refresh token.
  const tokens = loginVerifiedUser('login_setup_refresh');
  const res = http.post(
    `${BASE_URL}/api/v1/auth/refresh`,
    JSON.stringify({ refresh_token: tokens.refreshToken }),
    {
      headers: JSON_HEADERS,
      tags: { endpoint: 'refresh' },
    }
  );

  const body = safeJson(res);

  check(res, {
    'refresh http 200': (r) => r.status === 200,
    'refresh new access token exists': () => !!body?.data?.access_token,
    'refresh new refresh token exists': () => !!body?.data?.refresh_token,
  });
}

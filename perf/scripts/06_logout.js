import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, JSON_HEADERS, buildLoadOptions } from '../lib/config.js';
import { authHeaders, loginVerifiedUser } from '../lib/helpers.js';

export const options = buildLoadOptions('logout', 500, Number(__ENV.VUS || 1), __ENV.DURATION || '20s');

export default function () {
  const tokens = loginVerifiedUser('login_setup_logout');

  const res = http.post(
    `${BASE_URL}/api/v1/auth/logout`,
    JSON.stringify({ refresh_token: tokens.refreshToken }),
    {
      headers: authHeaders(tokens.accessToken),
      tags: { endpoint: 'logout' },
    }
  );

  check(res, {
    'logout http 200': (r) => r.status === 200,
  });
}

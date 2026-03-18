
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, buildLoadOptions } from '../lib/config.js';
import { authHeaders, loginVerifiedUser, safeJson } from '../lib/helpers.js';

export const options = buildLoadOptions('profile_details', 300);

export function setup() {
  // One login during setup, then endpoint-only measurement in default.
  return loginVerifiedUser('login_setup_profile');
}

export default function (data) {
  const res = http.get(`${BASE_URL}/api/v1/users/profile_details`, {
    headers: authHeaders(data.accessToken),
    tags: { endpoint: 'profile_details' },
  });

  const body = safeJson(res);

  check(res, {
    'profile http 200': (r) => r.status === 200,
    'profile has email': () => !!body?.data?.email,
  });
}

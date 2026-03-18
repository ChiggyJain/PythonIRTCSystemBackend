import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, buildLoadOptions } from '../lib/config.js';
import { authHeaders, loginVerifiedUser, safeJson } from '../lib/helpers.js';

export const options = buildLoadOptions('pwd_change_request_otp', 700, Number(__ENV.VUS || 1), __ENV.DURATION || '20s');

export default function () {
  const tokens = loginVerifiedUser('login_setup_pwd_req');

  const res = http.post(
    `${BASE_URL}/api/v1/users/password/change/request-otp`,
    JSON.stringify({ channel: 'EMAIL' }),
    {
      headers: authHeaders(tokens.accessToken),
      tags: { endpoint: 'pwd_change_request_otp' },
    }
  );

  const body = safeJson(res);

  check(res, {
    'pwd request otp http 202': (r) => r.status === 202,
    'pwd request otp has challenge_id': () => !!body?.data?.challenge_id,
  });
}

import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';
import { BASE_URL, buildLoadOptions } from '../lib/config.js';
import { authHeaders, loginVerifiedUser, safeJson } from '../lib/helpers.js';

const acceptedCounter = new Counter('pwd_req_otp_accepted_total');
const throttledCounter = new Counter('pwd_req_otp_throttled_total');

const baseOptions = buildLoadOptions(
  'pwd_change_request_otp',
  700,
  Number(__ENV.VUS || 1),
  __ENV.DURATION || '20s',
  { includeHttpReqFailed: false } // policy mode: 429 is expected
);

export const options = {
  ...baseOptions,
  thresholds: {
    ...baseOptions.thresholds,
    pwd_req_otp_accepted_total: ['count>=1'],
    pwd_req_otp_throttled_total: ['count>=1'],
  },
};

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

  if (res.status === 202) acceptedCounter.add(1);
  if (res.status === 429) throttledCounter.add(1);

  check(res, {
    'pwd request otp http 202 or 429': (r) => r.status === 202 || r.status === 429,
    'pwd request otp has challenge_id when 202': () =>
      res.status !== 202 || !!body?.data?.challenge_id,
  });
}

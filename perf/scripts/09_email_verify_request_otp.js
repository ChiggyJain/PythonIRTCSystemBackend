import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';
import { BASE_URL, buildLoadOptions } from '../lib/config.js';
import { authHeaders, loginUnverifiedUser, safeJson } from '../lib/helpers.js';

const emailVerifyReqAcceptedTotal = new Counter('email_verify_req_accepted_total');
const emailVerifyReqThrottledTotal = new Counter('email_verify_req_throttled_total');

const baseOptions = buildLoadOptions(
  'email_verify_request_otp',
  700,
  Number(__ENV.VUS || 1),
  __ENV.DURATION || '20s'
);

export const options = {
  ...baseOptions,
  thresholds: {
    // Keep latency threshold
    'http_req_duration{endpoint:email_verify_request_otp}': ['p(95)<700'],

    // Policy-mode checks: both should happen in this test
    email_verify_req_accepted_total: ['count>=1'],
    email_verify_req_throttled_total: ['count>=1'],
  },
};

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

  if (res.status === 202) emailVerifyReqAcceptedTotal.add(1);
  if (res.status === 429) emailVerifyReqThrottledTotal.add(1);

  check(res, {
    'email verify request http 202 or 429': (r) => r.status === 202 || r.status === 429,
    'email verify request has challenge_id when 202': () =>
      res.status !== 202 || !!body?.data?.challenge_id,
  });
}

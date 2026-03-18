import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';
import { BASE_URL, buildLoadOptions } from '../lib/config.js';
import { authHeaders, loginVerifiedUser, safeJson, uniqueEmail } from '../lib/helpers.js';

const emailChangeReqAcceptedTotal = new Counter('email_change_req_accepted_total');
const emailChangeReqThrottledTotal = new Counter('email_change_req_throttled_total');

const baseOptions = buildLoadOptions(
  'email_change_request_otp',
  700,
  Number(__ENV.VUS || 1),
  __ENV.DURATION || '20s'
);

export const options = {
  ...baseOptions,
  thresholds: {
    // Keep latency threshold
    'http_req_duration{endpoint:email_change_request_otp}': ['p(95)<700'],

    // Policy-mode expectations (both should happen)
    email_change_req_accepted_total: ['count>=1'],
    email_change_req_throttled_total: ['count>=1'],
  },
};

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

  if (res.status === 202) emailChangeReqAcceptedTotal.add(1);
  if (res.status === 429) emailChangeReqThrottledTotal.add(1);

  check(res, {
    'email change request http 202 or 429': (r) => r.status === 202 || r.status === 429,
    'email change request has challenge_id when 202': () =>
      res.status !== 202 || !!body?.data?.challenge_id,
  });
}

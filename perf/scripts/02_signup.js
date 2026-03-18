
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, JSON_HEADERS, buildLoadOptions } from '../lib/config.js';
import { uniqueEmail, uniqueMobile, safeJson } from '../lib/helpers.js';

export const options = buildLoadOptions('signup', 600, Number(__ENV.VUS || 1), __ENV.DURATION || '20s');

export default function () {
  const password = 'PerfUser@123';
  const payload = {
    first_name: 'Perf',
    last_name: `User`,
    mobile: uniqueMobile(),
    email: uniqueEmail('signup'),
    gender: 'Male',
    password,
    confirm_password: password,
  };

  const res = http.post(`${BASE_URL}/api/v1/users/signup`, JSON.stringify(payload), {
    headers: JSON_HEADERS,
    tags: { endpoint: 'signup' },
  });

  const body = safeJson(res);

  check(res, {
    'signup http 200/201': (r) => r.status === 200 || r.status === 201,
    'signup has userId': () => !!body?.data?.userId,
  });
}

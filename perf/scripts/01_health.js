
import http from 'k6/http';
import { check } from 'k6';
import { BASE_URL, buildLoadOptions } from '../lib/config.js';

export const options = buildLoadOptions('health', 100);

export default function () {
  const res = http.get(`${BASE_URL}/health`, {
    tags: { endpoint: 'health' },
  });

  check(res, {
    'health http 200': (r) => r.status === 200,
  });
}


import http from 'k6/http';
import { check, fail } from 'k6';
import { BASE_URL, JSON_HEADERS } from './config.js';

export function safeJson(res) {
  try {
    return res.json();
  } catch (_) {
    return {};
  }
}

export function envOrFail(name) {
  const value = __ENV[name];
  if (!value) {
    fail(`Missing environment variable: ${name}`);
  }
  return value;
}

export function uniqueEmail(prefix = 'perf') {
  return `${prefix}.${Date.now()}.${__VU}.${__ITER}@example.com`;
}

export function uniqueMobile() {
  // 10-digit, starts with 9
  const nineDigits = Math.floor(Math.random() * 1_000_000_000).toString().padStart(9, '0');
  return `9${nineDigits}`;
}

export function authHeaders(accessToken) {
  return {
    ...JSON_HEADERS,
    Authorization: `Bearer ${accessToken}`,
  };
}

export function loginWithCredentials({ email, password, tag = 'login_setup' }) {
  const res = http.post(
    `${BASE_URL}/api/v1/users/login`,
    JSON.stringify({ email, password }),
    {
      headers: JSON_HEADERS,
      tags: { endpoint: tag },
      timeout: '30s',
    }
  );

  const ok = check(res, {
    'login http 200': (r) => r.status === 200,
  });

  if (!ok) {
    fail(`Login failed. status=${res.status} body=${res.body}`);
  }

  const body = safeJson(res);
  const accessToken = body?.data?.tokens?.access_token;
  const refreshToken = body?.data?.tokens?.refresh_token;

  if (!accessToken || !refreshToken) {
    fail(`Login response missing tokens. body=${res.body}`);
  }

  return { accessToken, refreshToken };
}

export function loginVerifiedUser(tag = 'login_verified_setup') {
  return loginWithCredentials({
    email: envOrFail('TEST_USER_EMAIL_VERIFIED'),
    password: envOrFail('TEST_USER_PASSWORD_VERIFIED'),
    tag,
  });
}

export function loginUnverifiedUser(tag = 'login_unverified_setup') {
  return loginWithCredentials({
    email: envOrFail('TEST_USER_EMAIL_UNVERIFIED'),
    password: envOrFail('TEST_USER_PASSWORD_UNVERIFIED'),
    tag,
  });
}

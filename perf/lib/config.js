export const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';

export const JSON_HEADERS = {
  'Content-Type': 'application/json',
};

const DEFAULT_VUS = Number(__ENV.VUS || 2);
const DEFAULT_DURATION = __ENV.DURATION || '30s';

function buildThresholds(endpoint, p95Ms, thresholdOpts = {}) {
  const {
    includeHttpReqFailed = true,
    maxFailRate = 0.01,
  } = thresholdOpts;

  const thresholds = {
    [`http_req_duration{endpoint:${endpoint}}`]: [`p(95)<${p95Ms}`],
  };

  if (includeHttpReqFailed) {
    thresholds[`http_req_failed{endpoint:${endpoint}}`] = [`rate<${maxFailRate}`];
  }

  return thresholds;
}

export function buildLoadOptions(
  endpoint,
  p95Ms,
  vus = DEFAULT_VUS,
  duration = DEFAULT_DURATION,
  thresholdOpts = {}
) {
  return {
    scenarios: {
      main: {
        executor: 'constant-vus',
        vus,
        duration,
      },
    },
    thresholds: buildThresholds(endpoint, p95Ms, thresholdOpts),
    summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  };
}

export function buildSingleOptions(
  endpoint,
  p95Ms,
  iterations = Number(__ENV.ITERATIONS || 1),
  thresholdOpts = {}
) {
  return {
    vus: 1,
    iterations,
    thresholds: buildThresholds(endpoint, p95Ms, thresholdOpts),
    summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  };
}

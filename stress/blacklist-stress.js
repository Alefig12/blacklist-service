// Prueba de estrés del microservicio con k6 (Entrega 4).
// Se ejecuta con stress/run-stress.ps1, que genera el token y pasa las variables:
//   BASE_URL  URL del ALB de Fargate
//   TOKEN     Bearer token del API
//   PROFILE   smoke (validación corta) | stress (rampa completa, ~11 min)
import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomItem, uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

const BASE_URL = __ENV.BASE_URL;
const PROFILE = __ENV.PROFILE || 'smoke';
const AUTH = { 'Content-Type': 'application/json', Authorization: `Bearer ${__ENV.TOKEN}` };

const PROFILES = {
  smoke: [
    { duration: '30s', target: 2 },
  ],
  // Rampa por escalones: cada escalón dura lo suficiente para verse en New Relic (ventanas de 1 min).
  stress: [
    { duration: '1m', target: 10 },
    { duration: '2m', target: 30 },
    { duration: '2m', target: 60 },
    { duration: '2m', target: 100 },
    { duration: '3m', target: 100 },
    { duration: '1m', target: 0 },
  ],
};

// Los 4xx son respuestas esperadas del API: solo los 5xx y los errores de red cuentan como fallas.
http.setResponseCallback(http.expectedStatuses({ min: 200, max: 499 }));

export const options = {
  scenarios: {
    trafico: { executor: 'ramping-vus', startVUs: 0, stages: PROFILES[PROFILE], gracefulRampDown: '30s' },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    'http_req_duration{tipo:consulta}': ['p(95)<1000'],
    'http_req_duration{tipo:registro}': ['p(95)<1000'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

function body(email, extra = {}) {
  return JSON.stringify({ email, app_uuid: uuidv4(), blocked_reason: 'Prueba de estrés k6', ...extra });
}

// Emails registrados por cada VU, para que las consultas encuentren datos reales.
const registrados = [];

export default function () {
  const r = Math.random();

  if (r < 0.55 && registrados.length > 0) {
    // Consulta de un email que está en la lista negra.
    const res = http.get(`${BASE_URL}/blacklists/${randomItem(registrados)}`, { headers: AUTH, tags: { tipo: 'consulta' } });
    check(res, { 'consulta 200': (x) => x.status === 200 });
  } else if (r < 0.85) {
    // Registro de un email nuevo.
    const email = `k6.${uuidv4()}@stress.test`;
    const res = http.post(`${BASE_URL}/blacklists`, body(email), { headers: AUTH, tags: { tipo: 'registro' } });
    if (check(res, { 'registro 201': (x) => x.status === 201 })) registrados.push(email);
  } else if (r < 0.90) {
    // Consulta de un email que no está en la lista.
    const res = http.get(`${BASE_URL}/blacklists/no.${uuidv4()}@stress.test`, { headers: AUTH, tags: { tipo: 'consulta' } });
    check(res, { 'no registrado 200': (x) => x.status === 200 });
  } else if (r < 0.94 && registrados.length > 0) {
    // Email duplicado: el API responde 409.
    const res = http.post(`${BASE_URL}/blacklists`, body(randomItem(registrados)), { headers: AUTH, tags: { tipo: 'invalida' } });
    check(res, { 'duplicado 409': (x) => x.status === 409 });
  } else if (r < 0.97) {
    // Email con formato inválido: 400.
    const res = http.post(`${BASE_URL}/blacklists`, body('no-es-un-email'), { headers: AUTH, tags: { tipo: 'invalida' } });
    check(res, { 'invalido 400': (x) => x.status === 400 });
  } else {
    // Sin token: 401 (error esperado en New Relic).
    const res = http.get(`${BASE_URL}/blacklists/cliente@correo.com`, { tags: { tipo: 'invalida' } });
    check(res, { 'sin token 401': (x) => x.status === 401 });
  }

  sleep(0.2 + Math.random() * 0.3);
}

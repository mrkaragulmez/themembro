// backend/tests/load/k6_script.js
// Faz 5 — k6 yük testi senaryosu
//
// Kullanım (k6 kurulu ise):
//   BASE_URL=http://localhost:8000 k6 run tests/load/k6_script.js
//
// Docker ile:
//   docker run --rm -i \
//     -e BASE_URL=http://host.docker.internal:8000 \
//     grafana/k6 run - < tests/load/k6_script.js
//
// SLA Hedefleri:
//   - http_req_duration P95 < 500ms
//   - http_req_failed   < %1

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// ─── Özel Metrikler ────────────────────────────────────────────────

const chatErrors   = new Counter('chat_errors');
const chatDuration = new Trend('chat_duration', true);
const slaViolation = new Rate('sla_violations');

// ─── Test Konfigürasyonu ───────────────────────────────────────────

export const options = {
  stages: [
    { duration: '30s', target: 10  },  // Yavaş yükseliş
    { duration: '90s', target: 50  },  // Hedef yük      (50 VU)
    { duration: '60s', target: 100 },  // Stres testi
    { duration: '30s', target: 0   },  // Soğuma
  ],
  thresholds: {
    // SLA: P95 < 500ms
    http_req_duration: ['p(95)<500'],
    // Hata oranı: < %1
    http_req_failed:   ['rate<0.01'],
    // Özel: SLA ihlal oranı < %5
    sla_violations:    ['rate<0.05'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// ─── Yardımcı: Basit JWT Üretici ──────────────────────────────────
// NOT: Gerçek HMAC imzası k6'da crypto ile yapılabilir ama test için
// sunucudan /api/v1/auth/login ile gerçek token alınır.

function makeHeaders(token, tenantSlug) {
  return {
    'Authorization': `Bearer ${token}`,
    'X-Tenant-Slug': tenantSlug,
    'Content-Type':  'application/json',
  };
}

// ─── Ana Test Senaryosu ────────────────────────────────────────────

export default function () {
  const tenantSlug = `tenant-0${Math.floor(Math.random() * 5) + 1}`;

  // ── Adım 1: Health Check ────────────────────────────────────────
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health: status 200': (r) => r.status === 200,
    'health: ok mesajı':  (r) => r.json('status') === 'ok',
  });

  sleep(0.5);

  // ── Adım 2: Login ile Gerçek Token Al ──────────────────────────
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({
      email:    `loadtest@${tenantSlug}.example.com`,
      password: 'LoadTest1234!',
    }),
    { headers: { 'Content-Type': 'application/json', 'X-Tenant-Slug': tenantSlug } }
  );

  // Login başarısız olabilir (test kullanıcısı yoksa) — devam et
  if (loginRes.status !== 200) {
    slaViolation.add(0);  // login hatası SLA ihlali sayılmaz
    sleep(1);
    return;
  }

  const token = loginRes.json('access_token');
  if (!token) {
    sleep(1);
    return;
  }

  const headers = makeHeaders(token, tenantSlug);

  sleep(0.2);

  // ── Adım 3: Membro Listesi ─────────────────────────────────────
  const membrosRes = http.get(`${BASE_URL}/api/v1/membros/`, { headers });
  check(membrosRes, {
    'membros: status 200': (r) => r.status === 200,
  });

  const membros = membrosRes.json() || [];
  if (!membros.length) {
    sleep(1);
    return;
  }
  const membroId = membros[0].id;

  sleep(0.3);

  // ── Adım 4: Chat Mesajı ────────────────────────────────────────
  const messages = [
    'Merhaba, bana yardım edebilir misin?',
    'Şirket politikamız nedir?',
    'Son toplantımızı hatırlatır mısın?',
    'Bilgi bankasında ne arıyorsam bul.',
  ];

  const startTime = Date.now();
  const chatRes = http.post(
    `${BASE_URL}/api/v1/agents/${membroId}/chat`,
    JSON.stringify({
      message: messages[Math.floor(Math.random() * messages.length)],
    }),
    { headers, timeout: '10s' }
  );
  const elapsed = Date.now() - startTime;

  chatDuration.add(elapsed);

  const chatOk = check(chatRes, {
    'chat: status 200':         (r) => r.status === 200,
    'chat: reply alanı mevcut': (r) => r.json('reply') !== undefined,
    'chat: P95 < 500ms':        () => elapsed < 500,
  });

  if (!chatOk) {
    chatErrors.add(1);
    slaViolation.add(1);
  } else {
    slaViolation.add(0);
  }

  if (chatRes.status !== 200) {
    console.warn(`Chat hatası: ${chatRes.status} — ${chatRes.body.substring(0, 200)}`);
  }

  sleep(1);
}

// ─── Test Özeti ────────────────────────────────────────────────────

export function handleSummary(data) {
  const p95 = data.metrics.http_req_duration?.values?.['p(95)'] ?? 'N/A';
  const errRate = (data.metrics.http_req_failed?.values?.rate ?? 0) * 100;
  const chatP95 = data.metrics.chat_duration?.values?.['p(95)'] ?? 'N/A';

  console.log('\n' + '='.repeat(60));
  console.log('k6 Yük Testi — SLA Raporu');
  console.log(`  Genel P95 Gecikme  : ${typeof p95 === 'number' ? p95.toFixed(0) : p95}ms  (Hedef: <500ms)`);
  console.log(`  Chat P95 Gecikme   : ${typeof chatP95 === 'number' ? chatP95.toFixed(0) : chatP95}ms`);
  console.log(`  HTTP Hata Oranı    : ${errRate.toFixed(2)}%  (Hedef: <%1)`);
  console.log('='.repeat(60) + '\n');

  return {
    'reports/k6_summary.json': JSON.stringify(data, null, 2),
  };
}

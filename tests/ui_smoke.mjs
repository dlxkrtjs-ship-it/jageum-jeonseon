// 화면 시험: 실행기를 띄우고 브라우저로 열어 오류 없이 동작하는지 확인한다.
//   npm i playwright@1.48.2 && npx playwright install chromium && node tests/ui_smoke.mjs
import { spawn } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium } from 'playwright';

const home = mkdtempSync(join(tmpdir(), 'jj-'));
const srv = spawn(process.env.PYTHON || 'python3', ['server/warroom.py', '--no-browser', '--no-update-check', '--port', '8799'],
  { env: { ...process.env, HOME: home, USERPROFILE: home } });
const url = await new Promise((res, rej) => {
  let buf = '';
  const t = setTimeout(() => rej(new Error('실행기가 주소를 출력하지 않음: ' + buf)), 15000);
  srv.stdout.on('data', d => {
    buf += d;
    const m = buf.match(/http:\/\/127\.0\.0\.1:\d+\/\?t=\S+/);
    if (m) { clearTimeout(t); res(m[0]); }
  });
});
const fail = [];
const check = (ok, msg) => { console.log((ok ? 'ok   ' : 'FAIL ') + msg); if (!ok) fail.push(msg); };
const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto(url);
  await page.waitForTimeout(2500);
  check(await page.isVisible('#rLink'), '계좌 연결 패널이 보임');
  await page.click('#lkSync');
  await page.waitForTimeout(1500);
  check((await page.$$('tr[data-row]')).length === 6, '데모 동기화로 6개 종목 반영');
  for (const v of ['ink', 'flat', '3d']) {
    if (await page.isVisible(`[data-v="${v}"]`)) {
      await page.click(`[data-v="${v}"]`);
      await page.waitForTimeout(v === '3d' ? 4000 : 1200);
    }
  }
  check(!!(await page.evaluate(() => window.WR3D)), '3D 엔진 로드');
  await page.click('#rAssign');
  await page.waitForTimeout(500);
  check((await page.$$('#rGens .gen')).length === 6, '장수 열전 카드 6장');
  await page.goto(url.replace(/\?t=.*/, '#training'));
  await page.waitForTimeout(1500);
  for (let i = 0; i < 3; i++) await page.click('#advance');
  check((await page.textContent('#advance')).includes('4개월차'), '연병(모의전) 3개월 진행');
  check(errors.length === 0, '페이지 오류 없음' + (errors.length ? ': ' + errors.join(' | ') : ''));
} finally {
  await browser.close();
  srv.kill();
}
if (fail.length) { console.error(`실패 ${fail.length}건`); process.exit(1); }
console.log('화면 시험 통과');

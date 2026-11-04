#!/usr/bin/env python3
"""
자금전선 작전상황실 — 로컬 실행기

내 PC에서만 도는 작은 웹 서버입니다.
- 증권사 API 키는 이 PC의 설정 파일에만 저장되고, 증권사 서버 말고는 어디에도 보내지 않습니다.
- 서버는 127.0.0.1(내 컴퓨터)에서만 접속을 받고, 실행할 때마다 새로 만든 접속 토큰이 있어야 API를 호출할 수 있습니다.
- 표준 라이브러리만 사용합니다.

지원: 키움증권(REST API), 토스증권(Open API), 한국투자증권(KIS Open API), 데모(키 없이 체험)
"""
import argparse, json, os, random, re, secrets, socket, sys, threading, time, urllib.error, urllib.parse, urllib.request, webbrowser
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

VERSION = "0.3.0"
REPO = "dlxkrtjs-ship-it/jageum-jeonseon"
APP_NAME = "자금전선 작전상황실"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".jageum-jeonseon")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
TOKEN_FILE = os.path.join(CONFIG_DIR, "tokens.json")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")
LOCK = threading.Lock()


def app_dir():
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "app")


# ---------------------------------------------------------------- 설정 저장
def _write_private(path, data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, 0o700)
    except OSError:
        pass
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def load_config():
    return _read(CONFIG_FILE)


def save_config(cfg):
    _write_private(CONFIG_FILE, cfg)


SECRET_FIELDS = {"secretkey", "client_secret", "app_secret"}


def public_config(cfg):
    """브라우저에 돌려줄 설정. 비밀값은 '설정됨' 여부만 알려준다."""
    out = {"broker": cfg.get("broker", "demo"), "brokers": {}}
    for b in ("kiwoom", "toss", "kis"):
        c = cfg.get(b, {})
        out["brokers"][b] = {k: ("" if k in SECRET_FIELDS else v) for k, v in c.items()}
        out["brokers"][b]["_secretSet"] = any(c.get(k) for k in SECRET_FIELDS)
        out["brokers"][b]["_ready"] = broker_ready(b, c)
    return out


def broker_ready(b, c):
    need = {"kiwoom": ["appkey", "secretkey"], "toss": ["client_id", "client_secret"], "kis": ["app_key", "app_secret", "account"]}[b]
    return all(c.get(k) for k in need)


# ---------------------------------------------------------------- HTTP 도우미
class BrokerError(Exception):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status


class TokenExpired(BrokerError):
    pass


def http_json(method, url, headers=None, body=None, form=False, want_headers=False, _try=0):
    data = None
    h = dict(headers or {})
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
            h.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            data = json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json;charset=UTF-8")
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            payload = json.loads(r.read().decode("utf-8") or "{}")
            return (payload, {k.lower(): v for k, v in r.headers.items()}) if want_headers else payload
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8") or "{}")
        except ValueError:
            payload = {}
        if (e.code == 429 or e.code >= 500) and _try < 2:
            try:
                wait = min(5.0, float(e.headers.get("Retry-After") or 0)) or (1.0 + _try)
            except ValueError:
                wait = 1.0 + _try
            time.sleep(wait)
            return http_json(method, url, headers, body, form, want_headers, _try + 1)
        msg = (payload.get("error") or {}).get("message") if isinstance(payload.get("error"), dict) else None
        msg = msg or payload.get("return_msg") or payload.get("msg1") or payload.get("error_description") or f"HTTP {e.code}"
        if e.code == 401:
            raise TokenExpired(msg, 401)
        if e.code == 403:
            msg += " — 증권사에 등록한 허용 IP와 지금 PC의 IP가 같은지 확인하세요."
        if e.code == 429:
            msg = "증권사 호출 한도를 넘었습니다. 자동 동기화 간격을 늘려 주세요."
        raise BrokerError(msg, e.code)
    except urllib.error.URLError as e:
        raise BrokerError(f"증권사 서버에 연결하지 못했습니다: {e.reason}")


def num(v):
    if v is None:
        return 0.0
    s = str(v).strip().replace(",", "")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def token_cache(key):
    return _read(TOKEN_FILE).get(key)


def token_store(key, token, exp_ts):
    data = _read(TOKEN_FILE)
    data[key] = {"token": token, "exp": exp_ts}
    _write_private(TOKEN_FILE, data)


def drop_tokens(prefix):
    data = _read(TOKEN_FILE)
    kept = {k: v for k, v in data.items() if not k.startswith(prefix)}
    if kept != data:
        _write_private(TOKEN_FILE, kept)


def cached_token(key):
    c = token_cache(key)
    if c and c.get("exp", 0) > time.time() + 120:
        return c["token"]
    return None


# ---------------------------------------------------------------- 키움증권 REST API
def kiwoom_balance(c):
    base = os.environ.get("WARROOM_KIWOOM_BASE") or ("https://mockapi.kiwoom.com" if c.get("env") == "mock" else "https://api.kiwoom.com")
    tkey = f"kiwoom:{c.get('env','real')}:{c['appkey'][:6]}"
    token = cached_token(tkey)
    if not token:
        r = http_json("POST", base + "/oauth2/token", body={"grant_type": "client_credentials", "appkey": c["appkey"], "secretkey": c["secretkey"]})
        if r.get("return_code") not in (0, "0") or not r.get("token"):
            raise BrokerError(r.get("return_msg") or "키움 접근토큰 발급 실패")
        token = r["token"]
        try:
            exp = datetime.strptime(str(r.get("expires_dt")), "%Y%m%d%H%M%S").timestamp()
        except ValueError:
            exp = time.time() + 6 * 3600
        token_store(tkey, token, exp)

    def call(api_id, body, cont="N", nxt=""):
        hdr = {"authorization": f"Bearer {token}", "api-id": api_id, "cont-yn": cont, "next-key": nxt}
        r, h = http_json("POST", base + "/api/dostk/acnt", headers=hdr, body=body, want_headers=True)
        if r.get("return_code") not in (0, "0", 20, "20", None):
            raise BrokerError(f"{api_id}: {r.get('return_msg')}")
        return r, h

    holdings, cont, nxt = [], "N", ""
    for _ in range(20):
        r, h = call("kt00018", {"qry_tp": "1", "dmst_stex_tp": "KRX"}, cont, nxt)
        for row in r.get("acnt_evlt_remn_indv_tot") or []:
            qty = abs(num(row.get("rmnd_qty")))
            if qty <= 0:
                continue
            code = str(row.get("stk_cd", "")).strip()
            if code[:1] in ("A", "J", "Q") and len(code) == 7:
                code = code[1:]
            holdings.append({"name": str(row.get("stk_nm", "")).strip(), "code": code, "qty": qty,
                             "avg": abs(num(row.get("pur_pric"))), "price": abs(num(row.get("cur_prc")))})
        if h.get("cont-yn") == "Y" and h.get("next-key"):
            cont, nxt = "Y", h["next-key"]
            time.sleep(0.25)
        else:
            break
    d, _ = call("kt00001", {"qry_tp": "3"})
    cash = num(d.get("entr"))
    return {"source": "키움증권" + (" 모의" if c.get("env") == "mock" else ""), "cash": cash, "holdings": holdings}


# ---------------------------------------------------------------- 토스증권 Open API
TOSS = os.environ.get("WARROOM_TOSS_BASE") or "https://openapi.tossinvest.com"  # 환경변수는 개발·시험용


def toss_balance(c):
    tkey = f"toss:{c['client_id'][:8]}"
    token = cached_token(tkey)
    if not token:
        r = http_json("POST", TOSS + "/oauth2/token", body={"grant_type": "client_credentials", "client_id": c["client_id"], "client_secret": c["client_secret"]}, form=True)
        token = r.get("access_token")
        if not token:
            raise BrokerError("토스증권 토큰 발급 실패")
        token_store(tkey, token, time.time() + int(r.get("expires_in") or 3600))
    auth = {"Authorization": f"Bearer {token}"}
    seq = str(c.get("account_seq") or "").strip()
    if not seq:
        accts = http_json("GET", TOSS + "/api/v1/accounts", headers=auth).get("result") or []
        if not accts:
            raise BrokerError("토스증권 계좌를 찾지 못했습니다.")
        seq = str(accts[0].get("accountSeq"))
    hdr = dict(auth, **{"X-Tossinvest-Account": seq})
    res = http_json("GET", TOSS + "/api/v1/holdings", headers=hdr).get("result") or {}
    usd = None
    holdings = []
    for it in res.get("items") or []:
        qty = num(it.get("quantity"))
        if qty <= 0:
            continue
        rate = 1.0
        if it.get("currency") == "USD":
            if usd is None:
                q = "?" + urllib.parse.urlencode({"baseCurrency": "USD", "quoteCurrency": "KRW"})
                usd = num((http_json("GET", TOSS + "/api/v1/exchange-rate" + q, headers=auth).get("result") or {}).get("midRate")) or 1.0
            rate = usd
        holdings.append({"name": it.get("name") or it.get("symbol"), "code": it.get("symbol", ""), "qty": qty,
                         "avg": round(num(it.get("averagePurchasePrice")) * rate, 2), "price": round(num(it.get("lastPrice")) * rate, 2)})
    bp = http_json("GET", TOSS + "/api/v1/buying-power?currency=KRW", headers=hdr).get("result") or {}
    return {"source": "토스증권", "cash": num(bp.get("cashBuyingPower")), "holdings": holdings}


# ---------------------------------------------------------------- 한국투자증권 KIS Open API
def kis_balance(c):
    mock = bool(c.get("mock"))
    base = "https://openapivts.koreainvestment.com:29443" if mock else "https://openapi.koreainvestment.com:9443"
    cano, prdt = (c["account"].split("-") + ["01"])[:2]
    tkey = f"kis:{'mock' if mock else 'real'}:{c['app_key'][:6]}"
    token = cached_token(tkey)
    if not token:
        r = http_json("POST", base + "/oauth2/tokenP", body={"grant_type": "client_credentials", "appkey": c["app_key"], "appsecret": c["app_secret"]})
        token = r.get("access_token")
        if not token:
            raise BrokerError("한국투자증권 토큰 발급 실패")
        token_store(tkey, token, time.time() + int(r.get("expires_in") or 86400))
    holdings, cash, fk, nk, cont = [], None, "", "", ""
    for _ in range(20):
        q = "?" + urllib.parse.urlencode({"CANO": cano, "ACNT_PRDT_CD": prdt, "AFHR_FLPR_YN": "N", "OFL_YN": "", "INQR_DVSN": "02", "UNPR_DVSN": "01",
                                          "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "00", "CTX_AREA_FK100": fk, "CTX_AREA_NK100": nk})
        hdr = {"authorization": f"Bearer {token}", "appkey": c["app_key"], "appsecret": c["app_secret"],
               "tr_id": "VTTC8434R" if mock else "TTTC8434R", "custtype": "P", "tr_cont": cont}
        r, h = http_json("GET", base + "/uapi/domestic-stock/v1/trading/inquire-balance" + q, headers=hdr, want_headers=True)
        if r.get("rt_cd") != "0":
            raise BrokerError(f"잔고 조회 실패: {r.get('msg1')}")
        for o in r.get("output1") or []:
            qty = num(o.get("hldg_qty"))
            if qty > 0:
                holdings.append({"name": o["prdt_name"].strip(), "code": o["pdno"], "qty": qty, "avg": num(o["pchs_avg_pric"]), "price": num(o["prpr"])})
        if cash is None and r.get("output2"):
            cash = num(r["output2"][0].get("dnca_tot_amt"))
        if h.get("tr_cont") in ("F", "M"):
            fk, nk, cont = r.get("ctx_area_fk100", ""), r.get("ctx_area_nk100", ""), "N"
            time.sleep(0.2)
        else:
            break
    return {"source": "한국투자증권" + (" 모의" if mock else ""), "cash": cash or 0, "holdings": holdings}


# ---------------------------------------------------------------- 데모
_DEMO = [("삼성전자", "005930", 80, 72000, 78500), ("SK하이닉스", "000660", 10, 180000, 212000), ("NAVER", "035420", 12, 215000, 188000),
         ("현대차", "005380", 8, 245000, 238000), ("에코프로비엠", "247540", 15, 260000, 175000), ("KODEX 국고채10년", "", 40, 98000, 101200)]


def demo_balance(_c):
    t = time.time() / 600.0
    hs = []
    for i, (n, code, q, a, p) in enumerate(_DEMO):
        drift = 1 + 0.06 * __import__("math").sin(t + i * 1.7) + random.uniform(-0.01, 0.01)
        hs.append({"name": n, "code": code, "qty": q, "avg": a, "price": round(p * drift)})
    return {"source": "데모 (가상 데이터)", "cash": 5200000, "holdings": hs}


BROKERS = {"kiwoom": kiwoom_balance, "toss": toss_balance, "kis": kis_balance, "demo": demo_balance}
BROKER_NAMES = {"kiwoom": "키움증권", "toss": "토스증권", "kis": "한국투자증권", "demo": "데모"}


def merge_balances(parts):
    """여러 증권사 잔고를 하나로. 같은 종목(코드, 없으면 이름)은 수량을 더하고 평균단가는 수량 가중 평균."""
    merged, cash = {}, 0.0
    for p in parts:
        cash += p.get("cash") or 0
        for h in p["holdings"]:
            k = h.get("code") or h["name"]
            m = merged.get(k)
            if not m:
                merged[k] = dict(h)
                continue
            q = m["qty"] + h["qty"]
            m["avg"] = round((m["avg"] * m["qty"] + h["avg"] * h["qty"]) / q, 2) if q else m["avg"]
            m["qty"], m["price"] = q, h["price"] or m["price"]
    return {"cash": cash, "holdings": list(merged.values())}


def fetch_all(cfg):
    ready = [b for b in ("kiwoom", "toss", "kis") if broker_ready(b, cfg.get(b, {}))]
    if not ready:
        raise BrokerError("합칠 증권사가 없습니다. 증권사별로 키를 먼저 저장하세요.")
    parts, errors = [], []
    for b in ready:
        try:
            parts.append(fetch_balance(b))
        except BrokerError as e:
            errors.append(f"{BROKER_NAMES[b]}: {e}")
    if not parts:
        raise BrokerError(" / ".join(errors))
    out = merge_balances(parts)
    out.update(source=" + ".join(p["source"] for p in parts), broker="all", errors=errors,
               asOf=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    return out


def my_public_ip():
    req = urllib.request.Request("https://api.ipify.org?format=json", headers={"User-Agent": "jageum-jeonseon"})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode()).get("ip", "")


def fetch_balance(broker=None):
    cfg = load_config()
    b = broker or cfg.get("broker") or "demo"
    if b == "all":
        return fetch_all(cfg)
    if b not in BROKERS:
        raise BrokerError(f"알 수 없는 증권사: {b}")
    c = cfg.get(b, {})
    if b != "demo" and not broker_ready(b, c):
        raise BrokerError("API 키가 설정되지 않았습니다. 계좌 연결 설정에서 키를 넣어 주세요.")
    with LOCK:
        try:
            out = BROKERS[b](c)
        except TokenExpired:
            drop_tokens(b + ":")  # 만료·폐기된 토큰을 버리고 한 번만 다시 발급
            try:
                out = BROKERS[b](c)
            except TokenExpired as e:
                raise BrokerError(f"인증이 거부되었습니다({e}). 키가 맞는지, 다른 곳에서 같은 키로 토큰을 새로 받지 않았는지 확인하세요.", 401)
    out["broker"] = b
    out["asOf"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return out


# ---------------------------------------------------------------- 웹 서버
class Handler(BaseHTTPRequestHandler):
    server_version = "jageum-jeonseon/" + VERSION
    token = ""
    port = 0

    def log_message(self, fmt, *args):
        if self.server.verbose:
            super().log_message(fmt, *args)

    def _host_ok(self):
        host = (self.headers.get("Host") or "").lower()
        return host in (f"127.0.0.1:{self.port}", f"localhost:{self.port}")

    CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
           "font-src https://fonts.gstatic.com data:; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:; "
           "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")

    def _send(self, code, obj=None, ctype="application/json; charset=utf-8", raw=None):
        body = raw if raw is not None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if ctype.startswith("text/html"):
            self.send_header("Content-Security-Policy", self.CSP)
        self.end_headers()
        self.wfile.write(body)

    def _api_ok(self):
        if not self._host_ok():
            self._send(403, {"error": "허용되지 않은 호스트"})
            return False
        if not secrets.compare_digest(self.headers.get("X-Warroom-Token", ""), self.token):
            self._send(401, {"error": "접속 토큰이 맞지 않습니다. 실행기가 띄운 주소로 다시 접속하세요."})
            return False
        return True

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/api/"):
            if not self._api_ok():
                return
            if path == "/api/status":
                return self._send(200, {"app": APP_NAME, "version": VERSION, "config": public_config(load_config())})
            if path == "/api/state":
                return self._send(200, {"state": _read(STATE_FILE) or None})
            if path == "/api/myip":
                try:
                    return self._send(200, {"ip": my_public_ip()})
                except Exception:
                    return self._send(502, {"error": "공인 IP를 확인하지 못했습니다. 인터넷 연결을 확인하세요."})
            if path == "/api/update":
                return self._send(200, check_update(self.server.update_check))
            if path == "/api/balance":
                try:
                    return self._send(200, fetch_balance())
                except BrokerError as e:
                    return self._send(502, {"error": str(e)})
            return self._send(404, {"error": "없는 경로"})
        if not self._host_ok():
            return self._send(403, {"error": "허용되지 않은 호스트"})
        if path in ("/", "/index.html"):
            with open(os.path.join(app_dir(), "index.html"), "rb") as f:
                return self._send(200, raw=f.read(), ctype="text/html; charset=utf-8")
        m = re.fullmatch(r"/vendor/([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.js)", path)
        if m:
            fp = os.path.join(app_dir(), "vendor", m.group(1))
            if os.path.isfile(fp):
                with open(fp, "rb") as f:
                    return self._send(200, raw=f.read(), ctype="application/javascript; charset=utf-8")
        self._send(404, {"error": "없는 경로"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if not self._api_ok():
            return
        try:
            n = min(int(self.headers.get("Content-Length") or 0), 4 * 1024 * 1024)
            body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except ValueError:
            return self._send(400, {"error": "잘못된 요청"})
        if path == "/api/config":
            cfg = load_config()
            b = body.get("broker")
            if b in BROKERS or b == "all":
                cfg["broker"] = b
            for name, fields in (("kiwoom", ("appkey", "secretkey", "env")), ("toss", ("client_id", "client_secret", "account_seq")),
                                 ("kis", ("app_key", "app_secret", "account", "mock"))):
                src = (body.get("brokers") or {}).get(name)
                if not isinstance(src, dict):
                    continue
                dst = cfg.setdefault(name, {})
                for k in fields:
                    if k not in src:
                        continue
                    v = src[k]
                    if k in SECRET_FIELDS and (v is None or v == ""):
                        continue  # 비워 두면 기존 비밀값 유지
                    dst[k] = v.strip() if isinstance(v, str) else v
            if body.get("forget"):
                cfg.pop(body["forget"], None)
                _write_private(TOKEN_FILE, {k: v for k, v in _read(TOKEN_FILE).items() if not k.startswith(body["forget"] + ":")})
            save_config(cfg)
            return self._send(200, {"ok": True, "config": public_config(cfg)})
        if path == "/api/state":
            if not isinstance(body.get("state"), dict):
                return self._send(400, {"error": "잘못된 상태"})
            _write_private(STATE_FILE, body["state"])
            return self._send(200, {"ok": True})
        if path == "/api/test":
            try:
                r = fetch_balance(body.get("broker"))
                return self._send(200, {"ok": True, "count": len(r["holdings"]), "cash": r["cash"], "source": r["source"], "errors": r.get("errors", [])})
            except BrokerError as e:
                return self._send(502, {"error": str(e)})
        self._send(404, {"error": "없는 경로"})


_UPDATE = {}


def _ver(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:3]) or (0,)


def check_update(enabled):
    """GitHub 최신 릴리스와 비교. 실행 중 한 번만 묻는다. --no-update-check 로 끌 수 있다."""
    if not enabled:
        return {"current": VERSION, "newer": False}
    if not _UPDATE:
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest", headers={"Accept": "application/vnd.github+json", "User-Agent": "jageum-jeonseon"})
            with urllib.request.urlopen(req, timeout=4) as r:
                d = json.loads(r.read().decode("utf-8"))
            _UPDATE.update(latest=d.get("tag_name", ""), url=d.get("html_url", f"https://github.com/{REPO}/releases/latest"))
        except Exception:
            _UPDATE.update(latest="", url="")
    return {"current": "v" + VERSION, "latest": _UPDATE.get("latest"), "url": _UPDATE.get("url"),
            "newer": bool(_UPDATE.get("latest")) and _ver(_UPDATE["latest"]) > _ver(VERSION)}


def free_port(preferred):
    for p in [preferred] + list(range(preferred + 1, preferred + 30)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise SystemExit("빈 포트를 찾지 못했습니다.")


def main():
    ap = argparse.ArgumentParser(description=APP_NAME + " 로컬 실행기")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--no-browser", action="store_true", help="브라우저를 자동으로 열지 않음")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--no-update-check", action="store_true", help="새 버전 확인(GitHub 접속)을 하지 않음")
    ap.add_argument("--print-balance", metavar="BROKER", nargs="?", const="", help="서버 없이 잔고를 JSON으로 출력하고 종료")
    a = ap.parse_args()
    if a.print_balance is not None:
        try:
            print(json.dumps(fetch_balance(a.print_balance or None), ensure_ascii=False, indent=1))
        except BrokerError as e:
            raise SystemExit(f"오류: {e}")
        return
    port = free_port(a.port)
    Handler.token = secrets.token_urlsafe(24)
    Handler.port = port
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.verbose = a.verbose
    srv.update_check = not a.no_update_check
    url = f"http://127.0.0.1:{port}/?t={Handler.token}"
    print(f"{APP_NAME} v{VERSION}", flush=True)
    print(f"브라우저에서 열기: {url}", flush=True)
    print("이 창을 닫으면 종료됩니다. (Ctrl+C)", flush=True)
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

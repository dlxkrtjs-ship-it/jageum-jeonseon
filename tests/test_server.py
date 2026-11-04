"""로컬 서버 보안·저장 동작 시험.  python3 tests/test_server.py"""
import json, os, sys, tempfile, threading, urllib.error, urllib.request
os.environ["HOME"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
import warroom
from http.server import ThreadingHTTPServer

port = warroom.free_port(18877)
warroom.Handler.token, warroom.Handler.port = "TESTTOKEN", port
srv = ThreadingHTTPServer(("127.0.0.1", port), warroom.Handler); srv.verbose = False; srv.update_check = False
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{port}"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def call(path, method="GET", body=None, token="TESTTOKEN", host=None):
    h = {"Content-Type": "application/json"}
    if token: h["X-Warroom-Token"] = token
    if host: h["Host"] = host
    req = urllib.request.Request(base + path, method=method, headers=h, data=json.dumps(body).encode() if body is not None else None)
    try:
        with opener.open(req, timeout=10) as r: return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e: return e.code, e.read(), dict(e.headers)

assert call("/api/status", token=None)[0] == 401, "토큰 없으면 거부"
assert call("/api/status", token="WRONG")[0] == 401, "틀린 토큰 거부"
assert call("/api/status", host=f"evil.example:{port}")[0] == 403, "다른 호스트 거부 (DNS 리바인딩 방지)"
assert call("/", host=f"evil.example:{port}", token=None)[0] == 403
code, body, hdr = call("/", token=None)
assert code == 200 and "connect-src 'self'" in hdr.get("Content-Security-Policy", ""), "화면에 CSP 적용"
assert call("/vendor/three.min.js", token=None)[0] == 200, "3D 엔진을 로컬에서 제공"
for bad in ("/vendor/../server/warroom.py", "/vendor/%2e%2e/server/warroom.py", "/vendor/x.py", "/server/warroom.py"):
    assert call(bad, token=None)[0] == 404, bad
code, body, _ = call("/api/config", "POST", {"broker": "kiwoom", "brokers": {"kiwoom": {"appkey": "AK", "secretkey": "SECRET!", "env": "mock"}}})
pub = json.loads(body)["config"]
assert code == 200 and "SECRET!" not in body.decode() and pub["brokers"]["kiwoom"]["_secretSet"], "비밀키는 화면으로 돌려주지 않음"
cfg_path = os.path.join(os.environ["HOME"], ".jageum-jeonseon", "config.json")
assert json.load(open(cfg_path))["kiwoom"]["secretkey"] == "SECRET!"
if os.name == "posix": assert oct(os.stat(cfg_path).st_mode & 0o777) == "0o600", "설정 파일은 본인만 읽기"
call("/api/config", "POST", {"brokers": {"kiwoom": {"appkey": "AK2", "secretkey": ""}}})
assert json.load(open(cfg_path))["kiwoom"]["secretkey"] == "SECRET!", "비밀키 칸을 비우면 기존 값 유지"
call("/api/config", "POST", {"forget": "kiwoom"})
assert "kiwoom" not in json.load(open(cfg_path)), "키 삭제"
assert call("/api/state", "POST", {"state": {"cash": 1, "holdings": [{"name": "A"}]}})[0] == 200
assert json.loads(call("/api/state")[1])["state"]["cash"] == 1, "출정 기록 저장/불러오기"
call("/api/config", "POST", {"broker": "demo"})
code, body, _ = call("/api/balance")
assert code == 200 and len(json.loads(body)["holdings"]) == 6, "데모 잔고"
assert json.loads(call("/api/update")[1])["newer"] is False
assert warroom._ver("v0.10.0") > warroom._ver("0.9.9")
print("ok: 서버 시험 통과")
srv.shutdown()

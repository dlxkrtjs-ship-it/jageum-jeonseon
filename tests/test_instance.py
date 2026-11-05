"""실행기 중복 실행 방지와 끄기 시험.  python3 tests/test_instance.py"""
import json, os, subprocess, sys, tempfile, time, urllib.request
here = os.path.dirname(os.path.abspath(__file__))
srv = os.path.join(here, "..", "server", "warroom.py")
env = dict(os.environ, HOME=tempfile.mkdtemp(), PYTHONIOENCODING="utf-8")
env["USERPROFILE"] = env["HOME"]
args = [sys.executable, srv, "--no-browser", "--no-update-check", "--port", "18866"]
a = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, text=True, encoding="utf-8")
url = ""
for _ in range(50):
    line = a.stdout.readline()
    if "http://" in line:
        url = line.split("열기: ")[1].strip(); break
assert url, "첫 실행기 주소"
sess = os.path.join(env["HOME"], ".jageum-jeonseon", "session.json")
for _ in range(20):
    if os.path.exists(sess): break
    time.sleep(.1)
assert os.path.exists(sess), "세션 파일"
b = subprocess.run(args, env=env, capture_output=True, text=True, encoding="utf-8", timeout=20)
assert "이미 실행 중" in b.stdout and url in b.stdout and b.returncode == 0, b.stdout + b.stderr
tok = url.split("t=")[1]
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
req = urllib.request.Request(url.split("/?")[0] + "/api/shutdown", data=b"{}", method="POST", headers={"X-Warroom-Token": tok, "Content-Type": "application/json"})
assert json.loads(op.open(req, timeout=5).read())["ok"]
a.wait(timeout=10)
assert a.returncode == 0 and not os.path.exists(sess), "끄면 세션 파일 정리"
print("ok: 중복 실행 방지·끄기")

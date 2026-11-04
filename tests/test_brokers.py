"""가짜 증권사 서버로 키움·토스 잔고 변환을 시험한다.  python3 tests/test_brokers.py"""
import os, sys, tempfile, threading, time
port = 18999
os.environ["HOME"] = tempfile.mkdtemp()
os.environ["WARROOM_KIWOOM_BASE"] = os.environ["WARROOM_TOSS_BASE"] = f"http://127.0.0.1:{port}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server")); sys.path.insert(0, os.path.dirname(__file__))
import importlib, mock_brokers, warroom
from http.server import ThreadingHTTPServer
srv = ThreadingHTTPServer(("127.0.0.1", port), mock_brokers.H); threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(.2)
importlib.reload(warroom)
k = warroom.kiwoom_balance({"appkey": "APPKEY1234", "secretkey": "S", "env": "real"})
assert k["cash"] == 5200000, k
assert [h["code"] for h in k["holdings"]] == ["005930", "000660", "035420"], k
assert k["holdings"][1]["price"] == 212000 and k["holdings"][0]["qty"] == 80
t = warroom.toss_balance({"client_id": "CID12345", "client_secret": "S"})
assert t["cash"] == 3000000, t
aapl = [h for h in t["holdings"] if h["code"] == "AAPL"][0]
assert aapl["qty"] == 2.5 and aapl["price"] == round(210.5 * 1375, 2), aapl
assert warroom.cached_token("toss:CID12345") == "TSTOKEN"
# 폐기된 토큰이 캐시에 있으면 버리고 새로 받아 다시 시도, 429는 잠시 뒤 재시도
warroom.save_config({"broker": "toss", "toss": {"client_id": "CID99999", "client_secret": "S"}})
warroom.token_store("toss:CID99999", "OLDTOKEN", time.time() + 3600)
mock_brokers.H.hits["accounts"] = 0
r = warroom.fetch_balance()
assert r["cash"] == 3000000 and warroom.cached_token("toss:CID99999") == "TSTOKEN", r
assert mock_brokers.H.hits["accounts"] == 2, "429 뒤 재시도"
# 여러 증권사 합치기: 같은 종목은 수량 합산·평균단가 가중 평균, 예수금 합산
warroom.save_config({"broker": "all", "kiwoom": {"appkey": "APPKEY1234", "secretkey": "S", "env": "real"},
                     "toss": {"client_id": "CID99999", "client_secret": "S"}})
m = warroom.fetch_balance()
ss = [h for h in m["holdings"] if h["code"] == "005930"][0]
assert ss["qty"] == 85 and ss["avg"] == round((72000 * 80 + 70000 * 5) / 85, 2), ss
assert m["cash"] == 5200000 + 3000000 and m["broker"] == "all" and not m["errors"], m
assert len(m["holdings"]) == 4, [h["code"] for h in m["holdings"]]
print("ok: 키움", len(k["holdings"]), "종목 / 토스", len(t["holdings"]), "종목 / 토큰 폐기·호출 한도 재시도 / 여러 증권사 합치기")

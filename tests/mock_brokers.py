"""시험용 가짜 증권사 서버. 키움 REST·토스 Open API 문서의 응답 모양을 흉내 낸다."""
import json, sys, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def j(self, code, obj, hdr=None):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json")
        for k, v in (hdr or {}).items(): self.send_header(k, v)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        n = int(self.headers.get("Content-Length") or 0); return self.rfile.read(n).decode()
    def do_POST(self):
        b = self.body()
        if self.path == "/oauth2/token" and "appkey" in b:   # 키움
            d = json.loads(b); assert d["grant_type"] == "client_credentials" and d["secretkey"]
            return self.j(200, {"return_code": 0, "return_msg": "정상", "token": "KWTOKEN", "expires_dt": "20991231235959", "token_type": "bearer"})
        if self.path == "/oauth2/token":                       # 토스 (form)
            f = urllib.parse.parse_qs(b); assert f["grant_type"] == ["client_credentials"] and f["client_secret"]
            assert self.headers["Content-Type"].startswith("application/x-www-form-urlencoded")
            return self.j(200, {"access_token": "TSTOKEN", "token_type": "Bearer", "expires_in": 86400})
        if self.path == "/api/dostk/acnt":
            assert self.headers["authorization"] == "Bearer KWTOKEN"
            api = self.headers["api-id"]
            if api == "kt00018":
                if self.headers.get("cont-yn") != "Y":
                    return self.j(200, {"return_code": 0, "tot_evlt_amt": "000000012345678", "acnt_evlt_remn_indv_tot": [
                        {"stk_cd": "A005930", "stk_nm": "삼성전자", "rmnd_qty": "000000000000080", "pur_pric": "000000000072000", "cur_prc": "+000000000078500"},
                        {"stk_cd": "A000660", "stk_nm": "SK하이닉스", "rmnd_qty": "000000000000010", "pur_pric": "000000000180000", "cur_prc": "-000000000212000"}]},
                        {"cont-yn": "Y", "next-key": "PAGE2"})
                assert self.headers.get("next-key") == "PAGE2"
                return self.j(200, {"return_code": 0, "acnt_evlt_remn_indv_tot": [
                    {"stk_cd": "A035420", "stk_nm": "NAVER", "rmnd_qty": "000000000000012", "pur_pric": "000000000215000", "cur_prc": "000000000188000"}]}, {"cont-yn": "N"})
            if api == "kt00001":
                return self.j(200, {"return_code": 0, "entr": "000000005200000", "d2_entra": "000000005100000"})
        self.j(404, {"error": {"message": "no route"}})
    hits = {"accounts": 0}
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if self.headers["Authorization"] == "Bearer OLDTOKEN":   # 폐기된 토큰
            return self.j(401, {"error": {"code": "token-revoked", "message": "token revoked"}})
        assert self.headers["Authorization"] == "Bearer TSTOKEN"
        if u.path == "/api/v1/accounts":
            H.hits["accounts"] += 1
            if H.hits["accounts"] == 1:                           # 첫 호출은 호출 한도 초과
                return self.j(429, {"error": {"message": "rate limited"}}, {"Retry-After": "0"})
        if u.path == "/api/v1/accounts":
            return self.j(200, {"result": [{"accountNo": "123-45", "accountSeq": 7, "accountType": "GENERAL"}]})
        if u.path == "/api/v1/holdings":
            assert self.headers["X-Tossinvest-Account"] == "7"
            return self.j(200, {"result": {"totalPurchaseAmount": [], "items": [
                {"symbol": "005930", "name": "삼성전자", "marketCountry": "KR", "currency": "KRW", "quantity": "5", "lastPrice": "78500", "averagePurchasePrice": "70000"},
                {"symbol": "AAPL", "name": "애플", "marketCountry": "US", "currency": "USD", "quantity": "2.5", "lastPrice": "210.5", "averagePurchasePrice": "190.25"}]}})
        if u.path == "/api/v1/exchange-rate":
            assert q["baseCurrency"] == ["USD"]
            return self.j(200, {"result": {"baseCurrency": "USD", "quoteCurrency": "KRW", "rate": "1380.5", "midRate": "1375"}})
        if u.path == "/api/v1/buying-power":
            assert q["currency"] == ["KRW"] and self.headers["X-Tossinvest-Account"] == "7"
            return self.j(200, {"result": {"currency": "KRW", "cashBuyingPower": "3000000"}})
        self.j(404, {"error": {"message": "no route"}})

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()

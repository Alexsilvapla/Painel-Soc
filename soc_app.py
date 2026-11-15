"""Painel SOC para Windows (somente leitura, somente neste computador).

Lê as falhas de login do Windows (evento 4625) e entrega para o painel.
Não altera nada no sistema e só aceita conexões do próprio computador.
"""
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
import ipaddress
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
LOCK = threading.Lock()
STATE = {"readable": False, "events": [], "last": 0, "net_events": [], "net_last": 1, "net_open": 0}


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def parse_events(xml_text):
    """Transforma o XML do wevtutil em uma lista simples de eventos."""
    try:
        root = ET.fromstring("<Events>" + xml_text + "</Events>")
    except ET.ParseError:
        return []
    result = []
    for ev in root.findall("e:Event", NS):
        rid = ev.find("e:System/e:EventRecordID", NS)
        when = ev.find("e:System/e:TimeCreated", NS)
        data = {d.get("Name"): (d.text or "") for d in ev.findall("e:EventData/e:Data", NS)}
        if rid is None:
            continue
        result.append({
            "id": int(rid.text),
            "time": when.get("SystemTime") if when is not None else "",
            "user": data.get("TargetUserName", ""),
            "ip": data.get("IpAddress", "-"),
        })
    return result


def read_failed_logons(count=50):
    """Retorna a lista de eventos, ou None se não conseguiu ler o log."""
    cmd = ["wevtutil", "qe", "Security", "/q:*[System[(EventID=4625)]]",
           "/c:%d" % count, "/rd:true", "/f:xml"]
    flags = 0x08000000 if os.name == "nt" else 0  # não abre janela preta
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15, creationflags=flags)
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return parse_events(out.stdout)


def worker():
    first = True
    while True:
        events = read_failed_logons()
        with LOCK:
            if events is None:
                STATE["readable"] = False
            else:
                STATE["readable"] = True
                if first:  # o que já existia fica de fora: só eventos novos
                    STATE["last"] = max([e["id"] for e in events], default=0)
                    first = False
                else:
                    new = sorted((e for e in events if e["id"] > STATE["last"]), key=lambda e: e["id"])
                    if new:
                        STATE["events"] = (STATE["events"] + new)[-500:]
                        STATE["last"] = new[-1]["id"]
        time.sleep(2)


RISKY_IN = {22, 23, 135, 139, 445, 3389, 5900}   # portas de acesso remoto/compartilhamento
RISKY_OUT = {23, 4444, 6667, 31337}               # portas muito usadas em invasões
PS_NET = ("$p=@{};Get-Process|ForEach-Object{$p[[int]$_.Id]=$_.ProcessName};"
          "Get-NetTCPConnection|Select-Object LocalPort,RemoteAddress,RemotePort,"
          "@{n='State';e={[string]$_.State}},OwningProcess,"
          "@{n='Proc';e={$p[[int]$_.OwningProcess]}}|ConvertTo-Json -Compress")


def is_public(ip):
    try:
        a = ipaddress.ip_address(ip.split("%")[0])
        return not (a.is_private or a.is_loopback or a.is_link_local or a.is_multicast or a.is_unspecified)
    except ValueError:
        return False


def read_connections():
    """Lista as conexões TCP do computador (somente leitura). None se falhar."""
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_NET]
    flags = 0x08000000 if os.name == "nt" else 0
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=20, creationflags=flags)
        if out.returncode != 0 or not out.stdout.strip():
            return None
        data = json.loads(out.stdout)
    except Exception:
        return None
    return [data] if isinstance(data, dict) else data


def scan_connections(rows):
    """Separa as conexões ativas com a internet/rede e marca as incomuns."""
    listening = {int(r["LocalPort"]) for r in rows if r.get("State") == "Listen"}
    conns = {}
    for r in rows:
        if r.get("State") != "Established":
            continue
        ip = str(r.get("RemoteAddress") or "")
        if not ip or ip.startswith("127.") or ip in ("::1", "0.0.0.0", "::"):
            continue
        lport, rport = int(r["LocalPort"]), int(r["RemotePort"])
        direction = "in" if lport in listening else "out"
        sus = ((direction == "in" and is_public(ip) and lport in RISKY_IN)
               or (direction == "out" and rport in RISKY_OUT))
        conns[(lport, ip, rport, r.get("OwningProcess"))] = {
            "remote": ip, "port": rport, "dir": direction, "sus": sus,
            "proc": r.get("Proc") or "", "pid": r.get("OwningProcess")}
    return conns


def net_worker():
    prev = None
    while True:
        rows = read_connections()
        if rows is not None:
            conns = scan_connections(rows)
            with LOCK:
                STATE["net_open"] = len(conns)
                if prev is not None:  # a primeira leitura é só a base: só conexões novas contam
                    for key in [k for k in conns if k not in prev][:60]:
                        STATE["net_last"] += 1
                        STATE["net_events"].append(dict(conns[key], id=STATE["net_last"]))
                    STATE["net_events"] = STATE["net_events"][-300:]
            prev = set(conns)
        time.sleep(3)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/events":
            since = int(parse_qs(url.query).get("since", ["-1"])[0] or -1)
            with LOCK:
                events = [e for e in STATE["events"] if e["id"] > since] if since >= 0 else []
                payload = {"readable": STATE["readable"], "events": events, "last": STATE["last"]}
            self._send(200, json.dumps(payload).encode(), "application/json")
        elif url.path == "/api/net":
            since = int(parse_qs(url.query).get("since", ["-1"])[0] or -1)
            with LOCK:
                events = [e for e in STATE["net_events"] if e["id"] > since] if since >= 0 else []
                payload = {"open": STATE["net_open"], "events": events, "last": STATE["net_last"]}
            self._send(200, json.dumps(payload).encode(), "application/json")
        elif url.path in ("/", "/index.html"):
            with open(os.path.join(BASE, "painel-soc.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        else:
            self._send(404, b"nao encontrado", "text/plain")


class Api:
    """Funções que a página pode chamar (tela cheia com F11)."""
    window = None

    def fullscreen(self):
        if self.window is not None:
            self.window.toggle_fullscreen()


def start_server():
    server = ThreadingHTTPServer((HOST, 0), Handler)  # porta livre escolhida pelo sistema
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server.server_address[1]


def main():
    # Rodando pelo código-fonte (não pelo .exe): pede administrador se faltar.
    if os.name == "nt" and not getattr(sys, "frozen", False) and not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
                                            '"%s"' % os.path.abspath(__file__), None, 1)
        return
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=net_worker, daemon=True).start()
    url = "http://%s:%d" % (HOST, start_server())
    try:
        import webview
        api = Api()
        api.window = webview.create_window("Painel SOC", url, width=1280, height=800,
                                           background_color="#050a12", js_api=api)
        webview.start()
    except Exception:
        webbrowser.open(url)  # plano B: abre no navegador
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()

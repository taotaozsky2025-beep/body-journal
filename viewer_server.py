"""Loopback dashboard with a fixed, authenticated local sync action."""
import csv,json,math,threading,time,secrets,subprocess,os
from datetime import datetime,timezone,timedelta
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent
PORT=19842
CST=timezone(timedelta(hours=8))
last_access=time.monotonic()
sync_token=secrets.token_urlsafe(32)
sync_lock=threading.Lock()
sync_state={'State':'idle','Phase':'idle'}

def current_progress(progress,started):
    return datetime.fromisoformat(progress['Updated'])>=datetime.fromisoformat(started)

def sync_status():
    result=dict(sync_state)
    if result['State']=='running':
        try:
            progress=json.loads((ROOT/'.local'/'workflow.json').read_text(encoding='utf-8-sig'))
            if current_progress(progress,result['Started']):
                result.update({key:progress[key] for key in ('State','Phase','Cloud','GitHub','Updated') if key in progress})
                # The worker remains authoritative until the process exits.
                result['State']='running'
        except (OSError,ValueError,KeyError):pass
    return {**result,'token':sync_token}

def run_sync():
    global sync_state
    try:
        powershell=Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        # Let Windows PowerShell construct its own module path instead of
        # inheriting a PowerShell 7 host's incompatible module directories.
        environment={key:value for key,value in os.environ.items() if key.upper()!='PSMODULEPATH'}
        process=subprocess.run([str(powershell),'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','RemoteSigned',
            '-File',str(ROOT/'Sync-And-Upload.ps1'),'-NonInteractive'],cwd=ROOT,stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=environment,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=660)
        progress=json.loads((ROOT/'.local'/'workflow.json').read_text(encoding='utf-8-sig'))
        if not current_progress(progress,sync_state['Started']):raise ValueError('No current result')
        if process.returncode and progress.get('State') not in {'partial','error'}:raise ValueError('Sync is already running or failed')
        sync_state={key:progress[key] for key in ('State','Phase','Cloud','GitHub','Updated') if key in progress}
    except Exception:
        sync_state={'State':'error','Phase':'finished','Message':'同步未完成，可能已有同步任务正在执行。请稍后重试，本地记录已保留。'}
    finally:sync_lock.release()

def dataset():
    path=ROOT/'weights_full.csv'
    rows=[]
    if path.exists():
        with path.open(encoding='utf-8-sig',newline='') as stream:
            for record in csv.DictReader(stream):
                row={'Date':record['Date'],'Timestamp':int(datetime.strptime(record['Date'],'%Y-%m-%d %H:%M:%S').replace(tzinfo=CST).timestamp())}
                for key,value in record.items():
                    if key in {'Date','Timestamp','User','Source'}:continue
                    try:
                        number=float(value)
                        row[key]=number if math.isfinite(number) else None
                    except (TypeError,ValueError):row[key]=None
                rows.append(row)
    updated=None
    status=ROOT/'last-success.json'
    if status.exists():
        try:updated=json.loads(status.read_text(encoding='utf-8-sig')).get('Updated')
        except (ValueError,OSError):pass
    return {'rows':sorted(rows,key=lambda r:r['Timestamp']),'updated':updated,'timezone':'Asia/Shanghai'}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,body,mime='application/json; charset=utf-8',status=200,download=False):
        if isinstance(body,str):body=body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        if download:self.send_header('Content-Disposition','attachment; filename="body-records.csv"')
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        global last_access
        if self.headers.get('Host') not in {f'127.0.0.1:{PORT}',f'localhost:{PORT}'}:
            self.send('{}',status=403);return
        origin=self.headers.get('Origin')
        if origin and origin not in {f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'}:
            self.send('{}',status=403);return
        last_access=time.monotonic()
        path=urlsplit(self.path).path
        assets={'/':('dashboard.html','text/html; charset=utf-8'),'/app.js':('dashboard.js','text/javascript; charset=utf-8'),'/stats.js':('dashboard-stats.js','text/javascript; charset=utf-8'),'/style.css':('dashboard.css','text/css; charset=utf-8')}
        try:
            if path=='/api/health':self.send(json.dumps({'application':'local-scale-dashboard','version':2,'root':str(ROOT)}))
            elif path=='/api/sync':self.send(json.dumps(sync_status(),ensure_ascii=False))
            elif path=='/api/data':self.send(json.dumps(dataset(),ensure_ascii=False))
            elif path=='/download/full.csv':self.send((ROOT/'weights_full.csv').read_bytes(),'text/csv; charset=utf-8',download=True)
            elif path in assets:
                name,mime=assets[path];self.send((ROOT/name).read_bytes(),mime)
            else:self.send('{}',status=404)
        except (OSError,ValueError):self.send('{"error":"无法读取本地记录，请稍后刷新。"}',status=503)

    def do_POST(self):
        global sync_state,last_access
        allowed={f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'}
        if self.headers.get('Host') not in {f'127.0.0.1:{PORT}',f'localhost:{PORT}'} or self.headers.get('Origin') not in allowed:
            self.send('{}',status=403);return
        if not secrets.compare_digest(self.headers.get('X-Sync-Token',''),sync_token):
            self.send('{}',status=403);return
        if self.path!='/api/sync':self.send('{}',status=404);return
        if self.headers.get('Content-Length','0')!='0' or self.headers.get('Transfer-Encoding'):
            self.send('{}',status=400);self.close_connection=True;return
        last_access=time.monotonic()
        if not sync_lock.acquire(blocking=False):self.send(json.dumps(sync_status()),status=409);return
        sync_state={'State':'running','Phase':'xiaomi','Started':datetime.now(timezone.utc).isoformat()}
        threading.Thread(target=run_sync,daemon=True).start()
        self.send(json.dumps(sync_status()),status=202)

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    def idle_shutdown():
        while True:
            time.sleep(60)
            if time.monotonic()-last_access>7200 and not sync_lock.locked():
                server.shutdown();return
    threading.Thread(target=idle_shutdown,daemon=True).start()
    server.serve_forever()

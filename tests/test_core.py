"""Synthetic fixtures only. No cloud account, device or real measurements."""
import csv,importlib.util,io,json,os,shutil,subprocess,sys,tempfile,threading,time,unittest,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
import csv_merge,git_sync,hd01s_sync,viewer_server

def git(root,*args):
    p=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True)
    if p.returncode:raise AssertionError(p.stderr)
    return p.stdout.strip()

def write(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['Date','User','Weight_kg'])
        writer.writeheader();writer.writerows(rows)

def read(path):
    with path.open(encoding='utf-8-sig') as stream:return list(csv.DictReader(stream))

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent,prefix='synthetic-')
        self.root=Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(Path(__file__).resolve().parent))
    def tearDown(self):self.temp.cleanup()

    def test_retention_and_csv_privacy(self):
        fixture={'uid':'1','did':'synthetic-device','type':'history','key':'keyid_fixture','time':2524608000,
                 'value':json.dumps({'weight':73.0,'bfp':19.0,'user':{'birthday':'synthetic-only'},'unknown_secret':'fixture-only'})}
        archive=self.root/'history.json'
        hd01s_sync.merge_history(archive,[fixture])
        self.assertEqual(hd01s_sync.merge_history(archive,[]),[fixture])
        changed=dict(fixture,value=json.dumps({'weight':99.0}))
        self.assertEqual(hd01s_sync.merge_history(archive,[changed]),[fixture])
        with patch.object(hd01s_sync,'ROOT',self.root):
            path=hd01s_sync.export_full_csv([fixture],'keyid_fixture')
            before=path.read_bytes();hd01s_sync.export_full_csv([changed],'keyid_fixture')
            self.assertEqual(path.read_bytes(),before)
            self.assertNotIn('birthday',before.decode('utf-8-sig'))
            self.assertNotIn('unknown_secret',before.decode('utf-8-sig'))

    def test_timestamp_and_member_merge(self):
        base={'Date':'2050-01-01 08:00:00','User':'fixture-a','Weight_kg':'73'}
        write(self.root/'base',[base]);write(self.root/'ours',[dict(base,Weight_kg='99')])
        write(self.root/'theirs',[dict(base,Weight_kg='88'),dict(base,User='fixture-b')])
        csv_merge.merge(self.root/'base',self.root/'ours',self.root/'theirs')
        result=read(self.root/'ours')
        self.assertEqual(len(result),2);self.assertEqual(result[0],base)

    def test_unknown_model_fails_before_authentication(self):
        (self.root/'settings.json').write_text(json.dumps({'Region':'cn','Model':'synthetic.unsupported'}))
        with patch.object(hd01s_sync,'ROOT',self.root),patch.object(hd01s_sync,'Cloud') as cloud:
            with self.assertRaises(ValueError):hd01s_sync.main()
            cloud.assert_not_called()

    def test_public_repository_rejected(self):
        response=io.BytesIO(json.dumps({'private':False,'default_branch':'main'}).encode())
        credential=type('Result',(),{'returncode':0,'stdout':'password=synthetic-placeholder\n'})()
        with patch.object(git_sync.subprocess,'run',return_value=credential),patch.object(git_sync.urllib.request,'urlopen',return_value=response):
            with self.assertRaisesRegex(RuntimeError,'public repository'):
                git_sync.verify_private('https://github.com/example/public-code.git')
        with self.assertRaises(RuntimeError):git_sync.verify_private('https://user:secret@github.com/example/repo')

    def test_two_computers_union_and_no_empty_commit(self):
        origin=self.root/'origin.git';git(self.root,'init','--bare','--initial-branch=main',str(origin))
        seed=self.root/'seed';seed.mkdir();git(seed,'init','-b','main')
        git(seed,'config','user.name','Synthetic');git(seed,'config','user.email','synthetic@example.invalid')
        (seed/'.gitattributes').write_text('*.csv -text merge=bodycsv\n')
        base={'Date':'2050-01-01 08:00:00','User':'keyid_fixture','Weight_kg':'73'}
        for name in ['weights_full.csv','weights_full_keyid_fixture.csv']:write(seed/name,[base])
        git(seed,'add','.');git(seed,'commit','-m','Synthetic base');git(seed,'remote','add','origin',str(origin));git(seed,'push','-u','origin','main')
        apps=[]
        for label,day in [('a','02'),('b','03')]:
            app=self.root/label;app.mkdir();(app/'.local').mkdir();data=app/'.local/data-repository'
            git(self.root,'clone',str(origin),str(data))
            shutil.copy2(APP/'csv_merge.py',app/'csv_merge.py')
            (app/'settings.json').write_text(json.dumps({'PrimaryProfile':'keyid_fixture'}))
            (app/'.local/data-sync.json').write_text(json.dumps({'Repository':str(origin)}))
            for name in ['weights_full.csv','weights_full_keyid_fixture.csv']:
                write(app/name,[base,dict(base,Date=f'2050-01-{day} 08:00:00')])
            apps.append((app,data))
        def sync(index,mode):
            app,data=apps[index]
            with patch.multiple(git_sync,APP=app,ROOT=data,CONFIG=app/'.local/data-sync.json'),patch.object(git_sync,'verify_private',return_value='synthetic-private'),patch.object(git_sync,'system_proxy'),patch.object(sys,'argv',['git_sync.py',mode]),patch('sys.stdout',new_callable=io.StringIO):
                git_sync.main()
        sync(0,'upload');sync(1,'upload');sync(0,'pull')
        for app,_ in apps:self.assertEqual(len(read(app/'weights_full.csv')),3)
        sync(0,'upload');head=git(apps[0][1],'rev-parse','HEAD');sync(0,'upload')
        self.assertEqual(git(apps[0][1],'rev-parse','HEAD'),head)

    def test_setup_initializes_empty_private_archive(self):
        origin=self.root/'empty.git';git(self.root,'init','--bare','--initial-branch=main',str(origin))
        app=self.root/'app';app.mkdir();(app/'.local').mkdir()
        shutil.copy2(APP/'csv_merge.py',app/'csv_merge.py')
        data=app/'.local/data-repository';config=app/'.local/data-sync.json'
        with patch.multiple(git_sync,APP=app,ROOT=data,CONFIG=config),patch.object(git_sync,'verify_private',return_value='synthetic-private'):
            git_sync.setup(str(origin))
        self.assertTrue(config.exists());self.assertEqual(git(data,'branch','--show-current'),'main')
        self.assertIn('merge=bodycsv',(data/'.gitattributes').read_text())
        self.assertEqual(git(data,'status','--porcelain'),'')

    def test_sync_endpoint_origin_and_duplicate_clicks(self):
        spec=importlib.util.spec_from_file_location('isolated_viewer',APP/'viewer_server.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.ROOT=self.root;(self.root/'.local').mkdir()
        gate=threading.Event()
        def fake_run(*args,**kwargs):
            self.assertFalse(any(key.upper()=='PSMODULEPATH' for key in kwargs['env']))
            gate.wait(5)
            (self.root/'.local/workflow.json').write_text(json.dumps({'State':'complete','Phase':'finished','Cloud':'success','GitHub':'success','Updated':datetime.now(timezone.utc).isoformat()}))
            return type('Result',(),{'returncode':0})()
        server=module.ThreadingHTTPServer(('127.0.0.1',0),module.Handler);module.PORT=server.server_port
        threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{module.PORT}'
        def request(method='GET',headers=None,path='/api/sync'):
            try:
                with urllib.request.urlopen(urllib.request.Request(origin+path,method=method,headers=headers or {})) as response:return response.status,json.load(response)
            except urllib.error.HTTPError as error:return error.code,json.load(error)
        try:
            with patch.object(module.subprocess,'run',side_effect=fake_run):
                _,status=request();headers={'Origin':origin,'X-Sync-Token':status['token']}
                self.assertEqual(request('POST')[0],403)
                self.assertEqual(request('POST',dict(headers,Origin='https://untrusted.example'))[0],403)
                self.assertEqual(request('POST',headers)[0],202);self.assertEqual(request('POST',headers)[0],409)
                self.assertEqual(request(path='/token.dpapi')[0],404)
                gate.set()
                for _ in range(100):
                    if request()[1]['State']=='complete':break
                    time.sleep(.02)
                self.assertEqual(request()[1]['State'],'complete')
        finally:gate.set();server.shutdown();server.server_close()

    def test_public_ignore_rules(self):
        git(self.root,'init');shutil.copy2(APP/'.gitignore',self.root/'.gitignore')
        for name in ['weights.csv','weights_full_keyid_fixture.csv','settings.json','token.dpapi','account.json','auth-helper/go2rtc.yaml','.local/data-sync.json','private-history/member.json']:
            self.assertEqual(git(self.root,'check-ignore',name),name)
        self.assertEqual(subprocess.run(['git','-C',str(self.root),'check-ignore','settings.example.json'],capture_output=True).returncode,1)

if __name__=='__main__':unittest.main()

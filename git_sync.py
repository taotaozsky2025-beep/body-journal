"""Synchronize measurement CSVs to a separate, verified private GitHub repo."""
import json,os,re,shlex,subprocess,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path

APP=Path(__file__).resolve().parent
ROOT=APP/'.local'/'data-repository'
CONFIG=APP/'.local'/'data-sync.json'
DATA=re.compile(r'^weights(?:_full)?(?:_keyid_[A-Za-z0-9_-]+)?\.csv$')
sys.path.insert(0,str(APP))
from csv_merge import merge

def git(*args,check=True):
    result=subprocess.run(['git','-C',str(ROOT),*args],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if check and result.returncode:raise RuntimeError('Git operation failed: '+args[0])
    return result

def system_proxy():
    if sys.platform!='win32' or os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'):return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            enabled=winreg.QueryValueEx(key,'ProxyEnable')[0];server=winreg.QueryValueEx(key,'ProxyServer')[0]
        if enabled and server:
            if '=' in server:server=dict(item.split('=',1) for item in server.split(';') if '=' in item).get('https','')
            if server:os.environ['HTTPS_PROXY']=server if '://' in server else 'http://'+server
    except OSError:pass

def verify_private(remote):
    match=re.fullmatch(r'https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?',remote)
    if not match:raise RuntimeError('Expected an HTTPS GitHub URL without embedded credentials')
    owner,repo=match.groups()
    process=subprocess.run(['git','credential','fill'],input=f'protocol=https\nhost=github.com\nusername={owner}\n\n',capture_output=True,text=True)
    if process.returncode:raise RuntimeError('Sign into GitHub through Git Credential Manager first')
    credentials=dict(line.split('=',1) for line in process.stdout.splitlines() if '=' in line)
    request=urllib.request.Request(f'https://api.github.com/repos/{owner}/{repo}',headers={
        'Authorization':'Bearer '+credentials['password'],'Accept':'application/vnd.github+json','User-Agent':'body-journal','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(request,timeout=30) as response:metadata=json.load(response)
    if not metadata.get('private'):raise RuntimeError('Refusing to synchronize measurements to a public repository')
    if metadata.get('default_branch') not in {None,'main'}:raise RuntimeError('The private data repository must use the main branch')
    return metadata['html_url']

def configure():
    driver=shlex.quote(Path(sys.executable).as_posix())+' '+shlex.quote((APP/'csv_merge.py').as_posix())+' "%O" "%A" "%B"'
    git('config','--local','merge.bodycsv.driver',driver)
    git('config','--local','core.hooksPath',str(APP/'.local'/'disabled-hooks'))
    for key,value in [('user.name','Body Journal Sync'),('user.email','body-journal-sync@users.noreply.github.com')]:
        if not git('config',key,check=False).stdout.strip():git('config','--local',key,value)

def checkpoint():
    changes=[entry for entry in git('status','--porcelain','-z').stdout.split('\0') if entry]
    if any(not DATA.fullmatch(entry[3:]) for entry in changes):raise RuntimeError('Unexpected changes in the private data checkout; inspect it before retrying')
    paths=[p.name for p in ROOT.glob('weights*.csv') if DATA.fullmatch(p.name)]
    if paths:git('add','--',*paths)
    if git('diff','--cached','--quiet',check=False).returncode:git('commit','-m','Archive new measurements')

def copy_union(source,destination):
    for path in source.glob('weights*.csv'):
        if DATA.fullmatch(path.name):
            target=destination/path.name
            merge(target,target,path)

def refresh_aliases():
    settings=json.loads((APP/'settings.json').read_text(encoding='utf-8-sig'))
    profile=settings.get('PrimaryProfile')
    candidates=list(APP.glob('weights_full_keyid_*.csv'))
    if not profile and len(candidates)==1:profile=candidates[0].stem.removeprefix('weights_full_')
    if not profile:return
    if not re.fullmatch(r'keyid_[A-Za-z0-9_-]+',profile):raise ValueError('Unexpected profile')
    for prefix in ('weights','weights_full'):
        source=APP/f'{prefix}_{profile}.csv'
        if source.exists():(APP/f'{prefix}.csv').write_bytes(source.read_bytes())

def setup(remote):
    verify_private(remote)
    if ROOT.exists():raise RuntimeError('A data checkout already exists; inspect it before changing repositories')
    ROOT.parent.mkdir(exist_ok=True)
    result=subprocess.run(['git','clone','--',remote,str(ROOT)],capture_output=True,text=True)
    if result.returncode:raise RuntimeError('Could not clone the private data repository')
    verify_private(git('remote','get-url','origin').stdout.strip());configure()
    if git('rev-parse','--verify','HEAD',check=False).returncode:
        git('checkout','-B','main')
        (ROOT/'.gitattributes').write_text('*.csv -text merge=bodycsv\n',encoding='utf-8')
        (ROOT/'.gitignore').write_text('/*\n!/.gitignore\n!/.gitattributes\n!/weights*.csv\n*.previous.csv\n',encoding='utf-8')
        git('add','--','.gitattributes','.gitignore');git('commit','-m','Initialize private measurement archive')
        verify_private(remote);git('push','-u','origin','main')
    # Existing data repositories must opt in to the CSV merge driver too.
    attributes=ROOT/'.gitattributes'
    if not attributes.exists() or 'merge=bodycsv' not in attributes.read_text(encoding='utf-8'):
        raise RuntimeError('Add *.csv -text merge=bodycsv to the private repository .gitattributes first')
    CONFIG.write_text(json.dumps({'Repository':remote}),encoding='utf-8')

def main():
    mode=sys.argv[1] if len(sys.argv)>1 else 'pull'
    system_proxy()
    if mode=='setup':setup(sys.argv[2]);print('Private data repository configured.');return
    if mode not in {'pull','upload','configure'}:raise ValueError('Unexpected mode')
    if not CONFIG.exists():raise RuntimeError('Run Setup-DataSync.ps1 to configure a PRIVATE data repository first')
    remote=json.loads(CONFIG.read_text(encoding='utf-8'))['Repository']
    if git('remote','get-url','origin').stdout.strip()!=remote:raise RuntimeError('Private data origin changed; inspect it before retrying')
    repository=verify_private(remote);configure()
    if mode=='configure':return
    copy_union(APP,ROOT);checkpoint()
    result=git('-c','core.editor=true','pull','--rebase','origin','main',check=False)
    if result.returncode:
        git('rebase','--abort',check=False)
        raise RuntimeError('Could not merge remote history; local records retained')
    copy_union(ROOT,APP);refresh_aliases()
    if mode=='upload':
        copy_union(APP,ROOT);checkpoint();verify_private(remote);git('push','origin','HEAD:main')
    status={'Success':True,'Mode':mode,'Updated':datetime.now(timezone.utc).isoformat(),'Commit':git('rev-parse','HEAD').stdout.strip()}
    (APP/'.local'/'github-sync.json').write_text(json.dumps(status),encoding='utf-8');print(json.dumps(status))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'Success':False,'Message':str(error) if isinstance(error,RuntimeError) else type(error).__name__}));sys.exit(1)

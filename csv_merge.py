"""Git three-way CSV merge: keep committed records, append unseen timestamps."""
import csv,io,sys
from pathlib import Path

def read(path):
    text=Path(path).read_text(encoding='utf-8-sig') if Path(path).exists() else ''
    if not text.strip():return [],[]
    reader=csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or 'Date' not in reader.fieldnames:raise ValueError('Expected a measurement CSV')
    return reader.fieldnames,list(reader)

def merge(base,ours,theirs):
    columns=[];records={}
    for source in (base,ours,theirs):
        names,rows=read(source)
        for name in names:
            if name not in columns:columns.append(name)
        for row in rows:
            key=(row['Date'],row.get('User',''))
            records.setdefault(key,row)
    with Path(ours).open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns)
        writer.writeheader();writer.writerows(sorted(records.values(),key=lambda row:(row['Date'],row.get('User',''))))

if __name__=='__main__':
    try:merge(*sys.argv[1:4])
    except Exception:print('Measurement CSV merge requires manual inspection.',file=sys.stderr);sys.exit(1)

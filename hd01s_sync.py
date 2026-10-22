"""Read-only HD01S history adapter; authorization arrives exclusively on stdin."""
import base64
import csv
import hashlib
import http.cookiejar
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
MODEL = 'bairen.scales.hd01s'

def b64(value):
    return base64.b64encode(value).decode('ascii')

def rc4(key, data):
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + key[i % len(key)]) % 256
        state[i], state[j] = state[j], state[i]
    i = j = 0
    output = bytearray()
    for n, value in enumerate(bytes(1024) + data):
        i = (i + 1) % 256
        j = (j + state[i]) % 256
        state[i], state[j] = state[j], state[i]
        if n >= 1024:
            output.append(value ^ state[(state[i] + state[j]) % 256])
    return bytes(output)

class Cloud:
    def __init__(self, token_map):
        if len(token_map) != 1:
            raise ValueError('Expected one authorized account')
        self.uid, token = next(iter(token_map.values())).split(':', 1)
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        request = urllib.request.Request(
            'https://account.xiaomi.com/pass/serviceLogin?_json=true&sid=xiaomiio',
            headers={'Cookie': f'userId={self.uid}; passToken={token}'})
        raw = self.opener.open(request, timeout=60).read().decode('utf-8')
        if not raw.startswith('&&&START&&&'):
            raise ValueError('Unexpected authorization response')
        auth = json.loads(raw[len('&&&START&&&'):])
        location = auth.get('location', '')
        if not location:
            raise ValueError('Authorization expired; local browser sign-in required')
        target = urllib.parse.urlparse(location)
        if target.scheme != 'https' or not (target.hostname.endswith('.mi.com') or target.hostname.endswith('.xiaomi.com')):
            raise ValueError('Unexpected authorization redirect')
        self.secret = base64.b64decode(auth['ssecurity'])
        response = self.opener.open(location, timeout=60)
        response.read()
        self.cookies = '; '.join(v.split(';', 1)[0] for v in response.headers.get_all('Set-Cookie', []))
        self.uid = str(auth.get('userId', self.uid))

    def read(self, path, params):
        allowed = {'/v2/home/device_list_page', '/v2/device/getsettingv2', '/user/get_user_device_data'}
        if path not in allowed:
            raise ValueError('API is outside the read-only allowlist')
        data = json.dumps(params, separators=(',', ':'))
        nonce = os.urandom(8) + struct.pack('>I', int(time.time() / 60))
        signed = hashlib.sha256(self.secret + nonce).digest()
        sign = lambda value: b64(hashlib.sha1(value.encode('utf-8')).digest())
        plain_hash = sign('POST&' + path + '&data=' + data + '&' + b64(signed))
        form = {'data': b64(rc4(signed, data.encode('utf-8'))),
                'rc4_hash__': b64(rc4(signed, plain_hash.encode('ascii')))}
        form['signature'] = sign('POST&' + path + '&data=' + form['data'] + '&rc4_hash__=' + form['rc4_hash__'] + '&' + b64(signed))
        form['_nonce'] = b64(nonce)
        request = urllib.request.Request('https://api.io.mi.com/app' + path,
            urllib.parse.urlencode(form).encode('ascii'),
            {'Content-Type': 'application/x-www-form-urlencoded', 'Cookie': self.cookies})
        result = json.loads(rc4(signed, base64.b64decode(self.opener.open(request, timeout=60).read())))
        if result.get('code') != 0:
            raise ValueError('Cloud read returned a nonzero status')
        return result['result']

def atomic_json(path, value):
    pending = path.with_suffix(path.suffix + '.pending')
    with pending.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False)
    os.replace(pending, path)

def read_profiles(cloud, did):
    profiles = {}
    last_id = 0
    for _ in range(100):
        response = cloud.read('/v2/device/getsettingv2',
            {'last_id': last_id, 'did': did, 'settings': [], 'prefix_filter': 'keyid_'})
        profiles.update(response.get('settings', {}))
        if response.get('is_last_page', True):
            return profiles
        next_id = response.get('last_id')
        if next_id == last_id:
            raise ValueError('Profile pagination did not advance')
        last_id = next_id
    raise ValueError('Too many profile pages')

def read_history(cloud, did, profile):
    records = {}
    end = int(time.time())
    for _ in range(1000):
        page = cloud.read('/user/get_user_device_data',
            {'did': did, 'uid': int(cloud.uid), 'type': 'history', 'key': profile,
             'time_start': 0, 'time_end': end, 'limit': 1000, 'group': 'raw'})
        if not isinstance(page, list):
            raise ValueError('Unexpected history format')
        for row in page:
            if row.get('key') != profile or row.get('type') != 'history' or str(row.get('did')) != str(did):
                raise ValueError('History belongs to another device/profile')
            stamp = float(row['time'])
            value = json.loads(row['value'])
            if stamp in records and json.loads(records[stamp]['value']) != value:
                raise ValueError('Conflicting records share a timestamp')
            records[stamp] = row
        if len(page) < 1000:
            return list(records.values())
        oldest = min(float(r['time']) for r in page)
        next_end = int(oldest)
        if next_end >= end:
            raise ValueError('History pagination did not advance')
        end = next_end
    raise ValueError('Too many history pages')

FIELDS = {'weight': 'Weight', 'bmi': 'BMI', 'bfp': 'BodyFat', 'water': 'BodyWater',
          'boneSC': 'BoneMass', 'pAge': 'MetabolicAge', 'muscle': 'MuscleMass',
          'protein': 'ProteinMass', 'vf': 'VisceralFat', 'bmr': 'BasalMetabolism',
          'Smuscle': 'SkeletalMuscleMass'}

def convert(history, profile):
    result = []
    for row in history:
        value = json.loads(row['value'])
        weight = float(value.get('weight', 0))
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError('Invalid weight; existing export retained')
        stamp = float(row['time'])
        if stamp != int(stamp):
            raise ValueError('Subsecond record requires lossless CSV support')
        record = {'Date': datetime.fromtimestamp(stamp, CST).isoformat(), 'User': profile, 'Source': MODEL}
        for original, standard in FIELDS.items():
            number = value.get(original)
            if number is not None:
                number = float(number)
                if not math.isfinite(number):
                    raise ValueError('Non-finite measurement')
                if standard == 'VisceralFat':
                    record['VisceralFatExact'] = number
                    if number != int(number):
                        continue
                if standard in {'MetabolicAge', 'VisceralFat', 'BasalMetabolism'}:
                    if number != int(number):
                        raise ValueError('Fractional value cannot be represented by upstream format')
                    number = int(number)
                record[standard] = number
        result.append(record)
    return sorted(result, key=lambda row: row['Date'])

def merge_history(archive, incoming):
    previous = json.loads(archive.read_text(encoding='utf-8')) if archive.exists() else []
    identity = lambda row: (str(row['uid']), str(row['did']), row['type'], row['key'], float(row['time']))
    merged = {identity(row): row for row in previous}
    for row in incoming:
        merged.setdefault(identity(row), row)
    history = sorted(merged.values(), key=lambda row: float(row['time']), reverse=True)
    if previous != history:
        backups = archive.parent / 'snapshots'
        backups.mkdir(exist_ok=True)
        stamp = datetime.now(CST).strftime('%Y%m%d-%H%M%S-%f')
        if archive.exists():
            shutil.copy2(archive, backups / (archive.stem + '-' + stamp + '-before.json'))
        atomic_json(archive, history)
        shutil.copy2(archive, backups / (archive.stem + '-' + stamp + '-after.json'))
    return history

FULL_COLUMNS = {
    'weight': 'Weight_kg', 'bmi': 'BMI', 'bfp': 'BodyFat_percent',
    'muscle': 'MuscleMass_kg', 'muscleRate': 'MuscleRate_percent',
    'Smuscle': 'SkeletalMuscleMass_kg', 'SmuscleRate': 'SkeletalMuscleRate_percent',
    'water': 'BodyWater_percent', 'waterContent': 'BodyWaterMass_kg',
    'boneSC': 'BoneMass_kg', 'protein': 'ProteinMass_kg', 'proteinRate': 'ProteinRate_percent',
    'vf': 'VisceralFat', 'bmr': 'BasalMetabolism_kcal_per_day', 'pAge': 'MetabolicAge_years',
    'fat': 'FatMass_kg', 'freeFat': 'FatFreeMass_kg', 'standardWeight': 'StandardWeight_kg',
    'weightControls': 'WeightControl_kg', 'muscleControls': 'MuscleControl_kg',
    'fatControls': 'FatControl_kg', 'obesity': 'ObesityIndex_raw', 'score': 'BodyScore',
    'weight2': 'OriginalDisplayWeight', 'unit': 'OriginalUnitCode', 'point': 'OriginalDecimalCode'}

def export_full_csv(history, profile):
    destination = ROOT / ('weights_full_' + profile + '.csv')
    rows = []
    for record in sorted(history, key=lambda row: float(row['time'])):
        value = json.loads(record['value'])
        row = {'Date': datetime.fromtimestamp(float(record['time']), CST).strftime('%Y-%m-%d %H:%M:%S'),
               'Timestamp': record['time'], 'User': profile, 'Source': MODEL}
        row.update({column: value.get(key, '') for key, column in FULL_COLUMNS.items()})
        rows.append(row)
    columns = ['Date', 'Timestamp', 'User', 'Source'] + list(FULL_COLUMNS.values())
    append_csv_rows(destination, rows, columns, bom=True)
    return destination

def append_csv_rows(destination, rows, columns, bom=False):
    exists = destination.exists() and destination.stat().st_size > 0
    previous = []
    if exists:
        with destination.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            columns = reader.fieldnames
            previous = list(reader)
    dates = {row['Date'] for row in previous}
    additions = []
    for row in rows:
        if row['Date'] not in dates:
            additions.append(row)
            dates.add(row['Date'])
    if additions:
        if exists:
            shutil.copy2(destination, destination.with_suffix('.previous.csv'))
        encoding = 'utf-8-sig' if bom and not exists else 'utf-8'
        with destination.open('a', encoding=encoding, newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
            if not exists:
                writer.writeheader()
            writer.writerows(additions)
    return len(previous) + len(additions)

def export_csv(stage, profile, weights):
    if not re.fullmatch(r'keyid_[A-Za-z0-9_-]+', profile):
        raise ValueError('Unexpected profile identifier')
    destination = ROOT / ('weights_' + profile + '.csv')
    data_file = stage / 'source.json'
    atomic_json(data_file, weights)
    pending = stage / 'weights.csv'
    if pending.exists():
        pending.unlink()
    config = stage / 'export.json'
    atomic_json(config, {'export_hd01s': {'from': 'json source.json', 'to': 'csv weights.csv'}})
    process = subprocess.run([str(ROOT / 'scaleconnect.exe'), '-c', 'export.json'],
        cwd=stage, capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    if process.returncode != 0 or b'export_hd01s: OK' not in process.stderr:
        raise ValueError('SmartScaleConnect export failed')
    with pending.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    dates = [row['Date'] for row in rows]
    if len(dates) != len(set(dates)):
        raise ValueError('Duplicate timestamps in CSV')
    if len(rows) < len(weights):
        raise ValueError('Export dropped records')
    # HD01S stores fractional visceral-fat indices; upstream represents this
    # field as an integer. Restore the original index without rounding it.
    exact = {datetime.fromisoformat(w['Date']).strftime('%Y-%m-%d %H:%M:%S'): w.get('VisceralFatExact') for w in weights}
    for row in rows:
        value = exact.get(row['Date'])
        if value is not None:
            row['VisceralFat'] = format(value, '.12g')
    with pending.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    count = append_csv_rows(destination, rows, list(rows[0]))
    return destination, count

def main():
    settings=json.loads((ROOT / 'settings.json').read_text(encoding='utf-8-sig'))
    if settings.get('Region')!='cn' or settings.get('Model')!=MODEL:
        raise ValueError('This adapter is validated only for HD01S in the China region')
    cloud = Cloud(json.loads(sys.stdin.read()))
    devices = cloud.read('/v2/home/device_list_page', {})
    if devices.get('has_more'):
        raise ValueError('Device-list pagination requires adaptation')
    scales = [d for d in devices.get('list', []) if d.get('model') == MODEL and str(d.get('uid')) == cloud.uid]
    if settings.get('DeviceId'):
        scales=[d for d in scales if str(d.get('did'))==str(settings['DeviceId'])]
    if len(scales) != 1:
        raise ValueError('Expected exactly one owned HD01S')
    did = scales[0]['did']
    profiles = read_profiles(cloud, did)
    stage = ROOT / 'runtime-hd01s'
    stage.mkdir(exist_ok=True)
    archives = ROOT / 'private-history'
    archives.mkdir(exist_ok=True)
    output = []
    for profile in sorted(profiles):
        if not re.fullmatch(r'keyid_[A-Za-z0-9_-]+', profile):
            raise ValueError('Unexpected profile identifier')
        incoming = read_history(cloud, did, profile)
        history = merge_history(archives / (profile + '.json'), incoming)
        if not history:
            continue
        weights = convert(history, profile)
        destination, count = export_csv(stage, profile, weights)
        full_csv = export_full_csv(history, profile)
        output.append({'File': destination.name, 'FullFile': full_csv.name, 'CloudRows': len(incoming), 'Rows': count,
                       'LatestDate': weights[-1]['Date'], 'SHA256': hashlib.sha256(destination.read_bytes()).hexdigest()})
    if not output:
        raise ValueError('No usable history; existing CSV retained')
    settings=json.loads((ROOT / 'settings.json').read_text(encoding='utf-8-sig'))
    primary=settings.get('PrimaryProfile')
    selected=next((entry for entry in output if entry['File']=='weights_'+primary+'.csv'),None) if primary else (output[0] if len(output)==1 else None)
    if selected:
        alias = ROOT / 'weights.csv'
        pending = ROOT / 'weights.csv.pending'
        if not alias.exists() or alias.read_bytes() != (ROOT / selected['File']).read_bytes():
            shutil.copy2(ROOT / selected['File'], pending)
            os.replace(pending, alias)
        full_alias = ROOT / 'weights_full.csv'
        full_pending = ROOT / 'weights_full.csv.pending'
        if not full_alias.exists() or full_alias.read_bytes() != (ROOT / selected['FullFile']).read_bytes():
            shutil.copy2(ROOT / selected['FullFile'], full_pending)
            os.replace(full_pending, full_alias)
    else:
        raise ValueError('Primary profile unavailable; select the intended member')
    status = {'Success': True, 'Updated': datetime.now(CST).isoformat(), 'Model': MODEL,
              'ProfilesFound': len(profiles), 'Exports': output, 'Timezone': 'Asia/Shanghai', 'WeightUnit': 'kg'}
    atomic_json(ROOT / 'last-success.json', status)
    atomic_json(ROOT / 'diagnostic.json', {'Success': True, 'Code': 'OK', 'Adapter': 'HD01S-history'})
    print(json.dumps(status))

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Never emit upstream response bodies or authentication URLs.
        frames=traceback.extract_tb(error.__traceback__)
        status = {'Success': False, 'Code': 'HD01S_SYNC_FAILED', 'ErrorType': type(error).__name__,
                  'OwnSourceLines':[f.lineno for f in frames if Path(f.filename).name == Path(__file__).name],
                  'HttpStatus':getattr(error,'code',None)}
        atomic_json(ROOT / 'diagnostic.json', status)
        print(json.dumps(status))
        sys.exit(1)

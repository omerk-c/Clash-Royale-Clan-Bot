import json
import sys

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_keys(d, prefix=''):
    keys = set()
    for k, v in d.items():
        keys.add(prefix + k)
        if isinstance(v, dict):
            keys.update(get_keys(v, prefix + k + '.'))
    return keys

try:
    en = load_json('locales/en.json')
    tr = load_json('locales/tr.json')
    print('JSON files are valid.')
    
    en_keys = get_keys(en)
    tr_keys = get_keys(tr)
    
    missing_in_tr = en_keys - tr_keys
    missing_in_en = tr_keys - en_keys
    
    if not missing_in_tr and not missing_in_en:
        print('Key parity is PERFECT.')
    else:
        if missing_in_tr:
            print('Missing in tr.json:', missing_in_tr)
        if missing_in_en:
            print('Missing in en.json:', missing_in_en)
except Exception as e:
    print('Error:', e)
    sys.exit(1)

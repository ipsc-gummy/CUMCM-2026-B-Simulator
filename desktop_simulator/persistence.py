"""Local portable settings and durable session/event records."""
import json
import os
from pathlib import Path

DEFAULTS = {'robot_id': 'LOCAL-0001', 'port': 2026, 'display_rows': 1000}


def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)


class Store:
    def __init__(self, root):
        self.root = Path(root)
        for name in ('logs', 'state', 'config', 'data'):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.config_path = self.root / 'config/settings.json'
        if not self.config_path.exists():
            atomic_json(self.config_path, DEFAULTS)
        self.settings = json.loads(self.config_path.read_text(encoding='utf-8'))
        self.recover()

    def recover(self):
        # Abrupt process termination leaves an active checkpoint; never resume it.
        for path in (self.root / 'state').glob('*.json'):
            row = json.loads(path.read_text(encoding='utf-8'))
            if row['state'] in ('PREPARING', 'COUNTDOWN', 'WAITING_FOR_ENTER', 'RUNNING'):
                row.update(state='ABORTED', reason='process_interrupted')
                atomic_json(path, row)

    def save_settings(self, settings):
        atomic_json(self.config_path, settings)
        self.settings = dict(settings)

    def checkpoint(self, row):
        atomic_json(self.root / 'state' / (row['case_id'] + '.json'), row)

    def append(self, case_id, event):
        with (self.root / 'logs' / (case_id + '.jsonl')).open('a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=True, allow_nan=False) + '\n')
            f.flush()
            os.fsync(f.fileno())

    def history(self):
        rows = [json.loads(p.read_text(encoding='utf-8')) for p in (self.root / 'state').glob('*.json')]
        return sorted(rows, key=lambda r: r['created_ms'], reverse=True)

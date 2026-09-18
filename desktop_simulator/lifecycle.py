"""Local session lifecycle. Core owns every physical action and virtual second."""
import copy
import math
import threading
import time
import traceback
import uuid
from collections import deque
from .core_adapter import prepare
from .protocol import validate, HTTPError

ACTIVE = {'PREPARING', 'COUNTDOWN', 'WAITING_FOR_ENTER', 'RUNNING'}
OPEN = {'WAITING_FOR_ENTER', 'RUNNING'}
TERMINAL = {'FINISHED', 'ABORTED', 'TIMEOUT'}


def wire_seconds(value):
    rounded = round(value, 6)
    return int(rounded) if rounded.is_integer() else rounded


class Session:
    def __init__(self, store, clock=time.monotonic, wall=time.time):
        self.store, self.clock, self.wall = store, clock, wall
        self.lock = threading.RLock()
        self.gate = threading.Lock()
        self.inflight = threading.Lock()
        self.pending = None
        self.state = 'IDLE'
        self.row = None
        self.env = None
        self.scene = None
        self.events = deque(maxlen=store.settings['display_rows'])
        self.cache = {}
        self.cache_limit = 100000
        self.countdown_end = self.window_end = self.program_end = None
        self.error = ''

    def rejected(self):
        return {'accepted': False, 'real_timestamp_ms': int(self.wall()*1000), 'virtual_time_s': 0}

    def start(self, task, mode, seed=None):
        with self.lock:
            if self.state in ACTIVE:
                raise ValueError('本局尚未结束')
            if task not in ('q3', 'q4') or mode not in ('practice', 'formal'):
                raise ValueError('Unknown task/mode')
            self.state = 'PREPARING'
            case_id = str(uuid.uuid4()).upper()
            self.row = dict(case_id=case_id, task=task, mode=mode, state=self.state,
                            created_ms=int(self.wall()*1000), virtual_time_s=0, reason='', actions=0)
            self.events.clear()
            self.cache.clear()
            self.env = self.scene = None
            self.error = ''
            self.countdown_end = self.window_end = self.program_end = None
            self._checkpoint()
            worker = threading.Thread(target=self._prepare, args=(case_id, task, seed), daemon=True)
            worker.start()
            return worker

    def _prepare(self, case_id, task, seed):
        try:
            # Session identity selects a scene; the frozen generator alone owns distributions.
            env, scene = prepare(task, 0 if seed is None else seed, case_id)
            with self.lock:
                if self.row['case_id'] != case_id or self.state != 'PREPARING':
                    return
                self.env, self.scene = env, scene
                self.countdown_end = self.clock() + 5
                self.state = 'COUNTDOWN'
                self._checkpoint()
        except Exception:
            with self.lock:
                self.error = traceback.format_exc()
                self.store.append(case_id, {'type': 'technical_error', 'traceback': self.error})
                self._finish('ABORTED', 'technical_error')

    def _checkpoint(self):
        self.row['state'] = self.state
        self.row['virtual_time_s'] = round(self.env.total_time_s, 6) if self.env else 0
        self.store.checkpoint(self.row)

    def _tick(self):
        now = self.clock()
        if self.state == 'COUNTDOWN' and now >= self.countdown_end:
            self.state = 'WAITING_FOR_ENTER'
            self.window_end = self.countdown_end + 1500
            self._checkpoint()
        if self.state in OPEN:
            if now >= self.window_end:
                self._finish('TIMEOUT', 'test_window_timeout')
            elif self.program_end is not None and now >= self.program_end:
                self._finish('TIMEOUT', 'program_timeout')
            elif self.env.total_time_s >= 360000:
                self._finish('TIMEOUT', 'virtual_timeout')

    def tick(self):
        with self.lock:
            self._tick()

    def is_open(self):
        with self.lock:
            self._tick()
            return self.state in OPEN

    def _finish(self, state, reason):
        self.state = state
        self.row.update(reason=reason, ended_ms=int(self.wall()*1000))
        self.row['window_remaining'] = max(0, math.ceil(self.window_end-self.clock())) if self.window_end else 0
        self.row['program_remaining'] = max(0, math.ceil(min(self.window_end, self.program_end)-self.clock())) if self.program_end else None
        if self.row['mode'] == 'practice' and self.scene is not None:
            n = self.scene['N']
            d = sum(s.get('direction_deg') is not None for s in self.scene['sources'])
            self.row['summary'] = {'source_total': n, 'omni': n-d, 'directional': d}
        self._checkpoint()
        self.store.append(self.row['case_id'], {'type': 'session_end', **self.row})

    def abort(self, reason='manual_abort'):
        with self.lock:
            if self.state in ACTIVE:
                self._finish('ABORTED', reason)

    def snapshot(self):
        with self.lock:
            self._tick()
            result = dict(state=self.state, row=copy.deepcopy(self.row), events=list(self.events), error=self.error)
            now = self.clock()
            result['countdown'] = max(0, math.ceil(self.countdown_end-now)) if self.state == 'COUNTDOWN' else None
            result['window_remaining'] = max(0, math.ceil(self.window_end-now)) if self.window_end else None
            result['program_remaining'] = max(0, math.ceil(min(self.program_end,self.window_end)-now)) if self.program_end else None
            if self.state in TERMINAL:
                result['window_remaining'] = self.row['window_remaining']
                result['program_remaining'] = self.row['program_remaining']
            return result

    def record(self, path, payload, status, response, received_ms, replay=False):
        with self.lock:
            if not self.row:
                return
            event = dict(type='http', received_ms=received_ms, path=path,
                         position=payload.get('position'), channel=payload.get('channel'),
                         request_id=payload.get('request_id'), status=status,
                         response=copy.deepcopy(response), replay=replay)
            self.events.append(event)
            self.store.append(self.row['case_id'], event)

    def handle(self, path, payload):
        received = int(self.wall()*1000)
        try:
            known = validate(path, payload)
        except HTTPError as exc:
            response = self.rejected()
            self.record(path, payload, exc.status, response, received)
            return exc.status, response
        if not known or payload['arena_id'] != 'default' or payload['robot_id'] != self.store.settings['robot_id']:
            response = self.rejected()
            self.record(path, payload, 200, response, received)
            return 200, response
        identity = (path, payload)
        with self.inflight:
            acquired = self.gate.acquire(blocking=False)
            same = self.pending == identity
            if acquired:
                self.pending = copy.deepcopy(identity)
        if not acquired:
            if not same:
                return 409, self.rejected()
            self.gate.acquire()
        try:
            with self.lock:
                request_id = payload['request_id']
                if request_id in self.cache:
                    original, response = self.cache[request_id]
                    status = 200 if original == identity else 409
                    response = copy.deepcopy(response) if status == 200 else self.rejected()
                    self.record(path, payload, status, response, received, replay=status == 200)
                    return status, response
                self._tick()
                if self.state not in OPEN or (path != '/enter' and self.state != 'RUNNING') or (path == '/enter' and self.state != 'WAITING_FOR_ENTER'):
                    response = self.rejected()
                    self.record(path, payload, 200, response, received)
                    return 200, response
                if len(self.cache) >= self.cache_limit:
                    return 429, self.rejected()
                # A registered action finishes even if its computation crosses a real deadline.
                if path == '/enter':
                    entered_at = self.clock()
                    self.program_end = entered_at + 1200
                    self.state = 'RUNNING'
                    result = {'max_virtual_duration_s': 360000, 'max_real_duration_s': 1200,
                              'remaining_real_duration_s': max(0, math.floor(min(self.window_end, self.program_end)-entered_at))}
                elif path == '/exit':
                    result = {'exit_reason': 'user_exit'}
                else:
                    position = (payload['position']['x'], payload['position']['y'])
                    result = getattr(self.env, path[1:])(position, int(payload['channel']))
                response = {**result, 'accepted': True, 'real_timestamp_ms': int(self.wall()*1000),
                            'virtual_time_s': wire_seconds(self.env.total_time_s)}
                self.cache[request_id] = (copy.deepcopy(identity), copy.deepcopy(response))
                self.row['actions'] += 1
                self.record(path, payload, 200, response, received)
                if path == '/exit':
                    self._finish('FINISHED', 'user_exit')
                else:
                    self._checkpoint()
                    self._tick()
                return 200, response
        except Exception:
            with self.lock:
                self.error = traceback.format_exc()
                self.store.append(self.row['case_id'], {'type': 'technical_error', 'traceback': self.error})
                self._finish('ABORTED', 'technical_error')
            return 500, self.rejected()
        finally:
            with self.inflight:
                self.pending = None
                self.gate.release()

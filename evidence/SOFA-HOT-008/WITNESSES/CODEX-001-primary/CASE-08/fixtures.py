import json
import urllib.error
from collections import defaultdict, deque


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def sleep(self, seconds):
        seconds = float(seconds)
        if seconds < 0:
            raise ValueError("negative fake sleep")
        self.sleeps.append(seconds)
        self.now += seconds

    def monotonic(self):
        return self.now


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload, sort_keys=True).encode()


def http_error(code, retry_after=None):
    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return urllib.error.HTTPError("http://127.0.0.1/synthetic", code,
                                  "synthetic", headers, None)


class FakeAPI:
    def __init__(self, submit_sequences=None, status_sequences=None):
        self.submit_sequences = {
            key: deque(value) for key, value in (submit_sequences or {}).items()
        }
        self.status_sequences = {
            key: deque(value) for key, value in (status_sequences or {}).items()
        }
        self.submit_calls = []
        self.poll_calls = []
        self._job_counter = 0

    @staticmethod
    def _resolve(event):
        if isinstance(event, BaseException):
            raise event
        return event

    def submit(self, url, params):
        self.submit_calls.append({"url": url, "params": dict(params)})
        sequence = self.submit_sequences.get(url)
        if sequence:
            return FakeResponse(self._resolve(sequence.popleft()))
        self._job_counter += 1
        return FakeResponse({"job_id": f"job-{self._job_counter}"})

    def status(self, job_id):
        self.poll_calls.append(job_id)
        sequence = self.status_sequences.get(job_id)
        if sequence:
            return FakeResponse(self._resolve(sequence.popleft()))
        return FakeResponse({"status": "success"})


class CostList(list):
    def __init__(self, values=()):
        super().__init__(values)
        self.shift_cost = 0

    def pop(self, index=-1):
        if index == 0:
            self.shift_cost += max(0, len(self) - 1)
        return super().pop(index)

    def insert(self, index, value):
        if index == 0:
            self.shift_cost += len(self)
        return super().insert(index, value)

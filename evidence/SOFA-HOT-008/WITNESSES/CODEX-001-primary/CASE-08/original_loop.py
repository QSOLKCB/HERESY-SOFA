import json
import urllib.error


class SimulationLimit(RuntimeError):
    def __init__(self, operations, queue, inflight):
        super().__init__("bounded simulation operation ceiling reached")
        self.operations = operations
        self.queue = list(queue)
        self.inflight = dict(inflight)
        self.queue_shift_cost = getattr(queue, "shift_cost", 0)


def run_original(urls, api, clock, concurrency=3, poll_interval=15,
                 block_backoff=900, max_operations=100,
                 initial_inflight=None, queue_factory=list):
    queue = queue_factory(urls)
    inflight = dict(initial_inflight or {})
    results = []
    operations = 0
    while queue or inflight:
        while queue and len(inflight) < concurrency:
            if operations >= max_operations:
                raise SimulationLimit(operations, queue, inflight)
            operations += 1
            url = queue.pop(0)
            try:
                response = json.loads(api.submit(
                    url, {"url": url, "if_not_archived_within": "30d"}
                ).read())
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 503):
                    queue.insert(0, url)
                    clock.sleep(block_backoff)
                    continue
                raise
            if response.get("job_id"):
                inflight[response["job_id"]] = url
        clock.sleep(poll_interval)
        for job_id, url in list(inflight.items()):
            if operations >= max_operations:
                raise SimulationLimit(operations, queue, inflight)
            operations += 1
            status = json.loads(api.status(job_id).read())
            if status.get("status") != "pending":
                results.append({"url": url, "status": status})
                del inflight[job_id]
    return {
        "results": results,
        "operations": operations,
        "queue_shift_cost": getattr(queue, "shift_cost", 0),
        "clock": clock.monotonic(),
    }

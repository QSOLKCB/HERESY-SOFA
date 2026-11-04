HOST = "web.archive.org"
SPN_CONCURRENCY = 3        # outstanding SPN2 jobs per process
SPN_POLL = 15              # seconds between polls of /save/status/<job_id>
BLOCK_BACKOFF = 900        # fixed wait after a 429/503; our own choice, not a server value

def spn_request(url, auth, method="GET", params=None):
    # thin wrapper: urllib request with the account's auth headers, POST for /save
    ...

queue, inflight = list(urls_to_submit), {}
while queue or inflight:
    while queue and len(inflight) < SPN_CONCURRENCY:
        u = queue.pop(0)
        try:
            r = json.loads(spn_request(
                "https://" + HOST + "/save", auth, "POST",
                {"url": u, "if_not_archived_within": "30d"},
            ).read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                queue.insert(0, u)          # put it back, do not lose it
                time.sleep(BLOCK_BACKOFF)
                continue
            raise
        if r.get("job_id"):
            inflight[r["job_id"]] = u
    time.sleep(SPN_POLL)
    for job, u in list(inflight.items()):
        status = json.loads(spn_request(
            "https://" + HOST + "/save/status/" + job, auth).read())
        if status.get("status") != "pending":
            record_result(u, status)        # then verify with the CDX check from the linked TIL
            del inflight[job]

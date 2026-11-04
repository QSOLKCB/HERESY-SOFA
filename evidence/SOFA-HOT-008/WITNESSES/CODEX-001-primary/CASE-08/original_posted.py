"""The post's loop, preserved as unexecuted source text."""

POSTED_LOOP = r'''
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
                queue.insert(0, u)
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
            record_result(u, status)
            del inflight[job]
'''

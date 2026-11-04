# LOCAL-VERIFY-001 — open issues

No item below was executed in this campaign.

## Pyright 1.1.414

- **Prerequisite:** a verified, locally available Pyright 1.1.414 executable; no npm invocation or network installation during the evidence run.
- **Expected evidence:** exact argv, version output, diagnostics and exit codes for every GenericAlias/TypeVarTuple fixture.
- **Negative controls:** one-TypeVar excess arguments, literal ellipsis in a pack, custom `__class_getitem__`, and a runtime-only alias.
- **Platform:** the same CPython-compatible source fixtures; checker platform itself may differ if disclosed.
- **Live service needed:** no.

## Mypy 2.3.1

- **Prerequisite:** a verified local mypy 2.3.1 installation or immutable cache artifact.
- **Expected evidence:** strict diagnostics for ignored, unignored and sound dataclass fixtures plus bare/annotated instantiations.
- **Negative controls:** show that a clean checker result cannot alter `type(myclass[C2]().var)`.
- **Platform:** Python version and typeshed identity must be recorded.
- **Live service needed:** no.

## CPython version scope

- **Prerequisite:** already installed, authorized CPython 3.11/3.12/3.13 interpreters; do not download them merely for this test.
- **Expected evidence:** verbatim GenericAlias exception and TypeVarTuple runtime metadata per version.
- **Negative controls:** invalid ordinary-generic arity and unchecked GenericAlias values.
- **Platform:** native local interpreters.
- **Live service needed:** no.

## Internet Archive SPN2 quota and shared-account concurrency

- **Prerequisite:** explicit authorization, disposable test account/credentials, documented traffic budget and service-safe schedule.
- **Expected evidence:** server-confirmed response codes/headers, job IDs, account-scoped concurrency observations and a controlled one-worker baseline.
- **Negative controls:** identical URL mix at concurrency 1; two processes with coordinated versus independent admission; permanent refusal without success claims.
- **Platform:** any recorded client platform; clocks must be synchronized.
- **Live service needed:** yes. Prohibited in LOCAL-VERIFY-001.

## Retry-After and ambiguous acceptance

- **Prerequisite:** authoritative SPN2 protocol documentation or explicitly authorized fault-injection environment.
- **Expected evidence:** whether 429/503 responses contain valid `Retry-After`, whether a submission can commit before a 503/lost response, and whether an idempotency or reconciliation mechanism exists.
- **Negative controls:** malformed/missing header, HTTP-date versus delta-seconds, committed request with lost response, and definitive pre-commit rejection.
- **Platform:** service test harness with request correlation IDs and redacted credentials.
- **Live service needed:** yes unless authoritative documentation resolves the semantics.

## Missing job identifiers

- **Prerequisite:** documented response schema or authorized sandbox capable of emitting success-like bodies without `job_id`.
- **Expected evidence:** server-side acceptance state correlated with the client-visible body.
- **Negative controls:** explicit rejection, empty identifier, wrong identifier type and response loss after commit.
- **Platform:** protocol-level harness.
- **Live service needed:** likely yes.

## Success, index visibility and durable capture

- **Prerequisite:** authorized capture submissions and an independent archive-index lookup strategy.
- **Expected evidence:** timestamps for submit success, first index visibility and durable readback; disclose eventual-consistency windows.
- **Negative controls:** status success with no index entry, delayed entry, mismatched URL/timestamp and later disappearance.
- **Platform:** networked test host with UTC timestamps.
- **Live service needed:** yes. Prohibited in LOCAL-VERIFY-001.

## `if_not_archived_within`

- **Prerequisite:** authoritative documentation or authorized paired live submissions.
- **Expected evidence:** request payload, returned capture identity and independently observed crawl/quota effect.
- **Negative controls:** recently captured versus uncaptured URL, parameter omitted, boundary age and invalid value.
- **Platform:** authorized SPN2 environment.
- **Live service needed:** yes for behavioral proof.

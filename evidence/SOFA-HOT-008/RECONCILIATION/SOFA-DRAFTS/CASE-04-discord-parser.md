There is a separate executable defect in the posted shell parser. `curl -w "\n%{http_code}\n"` creates a delimiter, but the immediate `tr '\n' ' '` removes every newline before `tail -n1` runs. For synthetic 403, 404, and 429 responses, `STATUS` contained the body plus status and Bash emitted `integer expected`; the 403 branch was never reached.

The request also uses an unquoted webhook expansion, `cut -d= -f2` truncates a value containing another `=`, and `-d @payload.json` sends form content unless JSON `Content-Type` is set. Preserve response body, headers, and `%{http_code}` separately; quote the URL; send JSON explicitly; and use bounded `Retry-After` handling for 429/503 only. A 403 alone is not evidence to regenerate a webhook.

These are loopback parser controls, not a diagnosis of any live Discord incident. Evidence identifier: CODEX-001 report SHA-256 `3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229`.

More edge case Gremlins for the Goblin God!

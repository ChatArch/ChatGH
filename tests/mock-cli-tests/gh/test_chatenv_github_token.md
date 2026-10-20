# GitHub configuration test through ChatEnv

## Initial environment

Install ChatGH with its registered ChatEnv provider. Use Click's runner and a
task-local ChatEnv home. All HTTP responses in this suite are mocked; no real
credentials or external services are used.

## Expected process and results

1. Invoke `chatenv test -t gh -I` after loading a synthetic token. The GitHub
   provider calls the reusable checker with that exact value, then displays
   validity, UTC expiration, and remaining days without printing the token.
2. A valid token more than seven days from expiration passes. A token at or below
   seven days prints a visible renewal warning while remaining successful.
3. Invalid, expired, missing, or uncheckable credentials produce explicit failure
   text and a nonzero exit. A network/permission error is not called expiration.
4. Unknown expiration remains unknown; it is never rendered as never expiring.
5. The provider uses the value ChatEnv already selected. It does not reload an
   active profile or resolve repository credentials, so named profiles can be
   tested without crossing identities.
6. An unrelated netrc credential cannot replace the selected bearer token;
   environment proxy settings remain effective.

```sh
python -m pytest tests/mock-cli-tests/gh/test_chatenv_github_token.py -q
```

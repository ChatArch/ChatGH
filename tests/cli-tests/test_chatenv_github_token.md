# Real GitHub PAT smoke test

## Initial environment

Install the changed ChatGH package and ChatEnv profile patch in an isolated
environment or the explicitly authorized existing ChatArch environment. Keep
credentials in their existing typed GitHub profile, never in argv or logs.

## Expected process and results

1. Run `chatenv test -t gh -I` with the user's current active configuration. It
   performs one authenticated GET to GitHub `/user` and prints validity,
   expiration, and remaining days, or a classified failure.
2. If GitHub supplies an expiration header, compare the displayed UTC timestamp
   and remaining duration. If no header exists, report unknown expiration.
3. Run `chatenv test -t gh <profile> -I` only for a selected existing profile (or
   use a task-local synthetic profile for missing credentials); ensure no global
   profile activation or secret changes occur.
4. Record only status, timestamps, remaining days and exit code. Never record raw
   tokens, HTTP Authorization headers, or response bodies with private user data.

```sh
chatenv test -t gh -I
chatenv test -t gh '<existing-profile>' -I
```

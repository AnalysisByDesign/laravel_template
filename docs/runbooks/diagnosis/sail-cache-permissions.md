# Runbook: Sail cache permission failures (`Utime failed: Permission denied`)

**Symptom**: a large number of tests fail at once with HTTP 500, and the exception is always the same:

```
ErrorException: touch(): Utime failed: Permission denied
  in vendor/laravel/framework/src/Illuminate/View/Compilers/BladeCompiler.php
```

## How to recognise it in ten seconds

Three things together, and all three must hold before you believe this diagnosis:

1. **Every failure is a 500, not an assertion.** The test never reaches its own expectations.
2. **The stack trace is in `BladeCompiler`, not in application code.**
3. **Tests that render no Blade still pass.** Pure file-scanning tests such as the prose style guard are the fastest control group.

If a code change caused the failures, the third check fails too. If only the Blade-rendering tests fail, the code is fine and the container is not.

## What is actually wrong

`sail test` runs as the host user's uid and gid (mapped through `WWWUSER` and `WWWGROUP`). Some other process wrote the cache directories as **root**, and a non-root process cannot change the mtime of a root-owned file.

**The confusing part**: `is_writable()` returns `true`. `utime()` requires ownership rather than write permission, so Blade can create a compiled view it cannot subsequently stamp.

## Confirm it

```bash
cd laravel

# Which user do tests run as?
./vendor/bin/sail php -r 'echo posix_getuid(),":",posix_getgid(),"\n";'

# Reproduce the exact failure
./vendor/bin/sail php -r '$f=glob("storage/framework/views/*.php")[0];
  var_dump(is_writable($f), @touch($f)); echo error_get_last()["message"] ?? "ok","\n";'

# Who owns the caches, as the container sees them?
./vendor/bin/sail exec -T laravel.test sh -c '
  for d in storage/framework/views storage/framework/cache storage/framework/sessions \
           storage/framework/testing storage/logs bootstrap/cache; do
    echo "$d:"; find "$d" -maxdepth 1 -mindepth 1 -printf "    %u:%g\n" | sort | uniq -c
  done'
```

`is_writable` true with `touch` false is the signature. Any `root:root` in the last command is the cause. The host view can be misleading: some Docker runtimes map container-root files back to the host user, so only the in-container view tells the truth.

## Fix it

Substitute the uid and gid from the first command:

```bash
cd laravel
./vendor/bin/sail exec -T --user root laravel.test sh -c '
  rm -rf storage/framework/views/*.php
  chown -R <uid>:<gid> storage bootstrap/cache'
```

Compiled views are derived output, so deleting them is free. Then re-run the failing tests; there is no rebuild step.

## Where the root-owned files come from

`sail php`, `sail artisan` and `sail test` run as the mapped user. **`sail exec` and `sail root-shell` run as root.** Any root-context command that **writes** into `storage/` or `bootstrap/cache` causes this. A cache clear alone is harmless; a cache warm (`php artisan optimize`, `view:cache`) compiles every template as root.

## Avoiding it

**Run artisan through `sail artisan` (or `make artisan`), never through `sail exec` or a root shell.** If you do need a root context, assume it has poisoned the caches if it touched them, and run the fix above before trusting a test run.

This is not a dev stack bounce and does not need one.

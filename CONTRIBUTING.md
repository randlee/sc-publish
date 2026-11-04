# Contributing to sc-publish

sc-publish is a shared release kit. Every repository that consumes it
inherits every change made here. The kit exists to make publishing simple
for those repositories, and that purpose outranks any single repository's
needs.

**Pull requests that do not comply with every rule below will be rejected.**
There are no exceptions for urgency, for a release in progress, or for a
change that is "only small".

## Kinds of pull request

- **Bug fix.** The kit does not behave as documented or as a reasonable
  user would expect: it crashes, returns a wrong result or exit code, or
  fails for a valid configuration. A bug fix links the issue that describes the
  defect and how to reproduce it, includes a test that fails before the fix
  and passes after it, and changes nothing beyond what the fix needs. Bug
  fixes are always welcome.
- **Improvement.** Anything that adds or changes behaviour. An improvement
  must meet rule 1 below.

Rules 2 to 6 apply to both kinds. A bug fix that adds a gate, a
repository-specific branch or a consumer requirement is rejected like any
other change.

## Rules

1. **Every improvement must make sc-publish simpler, easier to adopt, or
   more extensible for consuming repositories.** An improvement that does
   none of these does not belong in the kit. A change that makes the kit
   harder to understand, configure or adopt is rejected, whatever it adds.

2. **Every change must be repository-agnostic.** Kit files must not name,
   detect or special-case any repository, path, command, toolchain or
   policy. Repository-specific behaviour lives only in that repository's own
   manifest or configuration.

3. **New behaviour must be an extension point.** If a repository needs
   something the kit does not do, add a generic, opt-in hook that any
   repository can use. A repository that does not opt in must behave exactly
   as it did before the change, and the pull request must include a test
   that proves it.

4. **The kit has no mandatory gates.** A publish may fail only because of a
   manifest, credential or registry error. A check runs only when the
   consuming repository has declared it. The kit must not ship a built-in
   check that every consumer has to satisfy.

5. **No new requirements on consumers.** A change must not add a required
   input, secret, file, tool, version floor or manual step for repositories
   that do not use the new behaviour.

6. **Consumers never patch the kit locally.** Vendored kit files are not
   edited in consuming repositories. A gap is reported as an issue on
   randlee/sc-publish that describes the generic extension point needed.

## Opening a pull request

Every pull request body is rendered with sc-compose in strict mode from the
template for its kind:

- bug fix: `.github/sc-publish-pr-bug-fix.md.j2`
- improvement: `.github/sc-publish-pr-improvement.md.j2`

```sh
sc-compose render --strict --var-file pr-vars.json \
  --file .github/sc-publish-pr-improvement.md.j2 --output pr-body.md
```

Pull requests are written mostly by agents, and the strict render refuses a
body with a field missing. Every field must also carry real content; an
empty or placeholder value is treated as missing.

Every checklist item must be ticked. An item that cannot honestly be ticked
means the pull request is not ready. A change whose only value is to the
submitting repository is not a kit change; it belongs in that repository's
own configuration.

Review is the enforcement. A reviewer rejects a pull request whose body was
not rendered from the right template, has an empty field or an unticked
item, or names no benefit to other consumers.

## Review

Reviewers check every pull request against the rules above and reject it
if it:

- is more complicated than the problem it solves;
- adds repository-specific logic to kit files;
- adds a mandatory gate or built-in check; or
- pushes any new requirement onto consumers that did not opt in.

A rejected pull request is not reworked by adding options or exceptions to
the rules. Simplify the change, or turn it into an extension point.

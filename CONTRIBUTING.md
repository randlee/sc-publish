# Contributing to sc-publish

sc-publish is a shared release kit. Every repository that consumes it
inherits every change made here. The kit exists to make publishing simple
for those repositories, and that purpose outranks any single repository's
needs.

**Pull requests that do not comply with every rule below will be rejected.**
There are no exceptions for urgency, for a release in progress, or for a
change that is "only small".

## Rules

1. **Every change must make sc-publish simpler, easier to adopt, or more
   extensible for consuming repositories.** A change that does none of these
   does not belong in the kit. A change that makes the kit harder to
   understand, configure or adopt is rejected, whatever it adds.

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

Every pull request body is rendered from
`.github/sc-publish-pr-template.md.j2` with sc-compose in strict mode, so
no field can be left out:

```sh
sc-compose render --strict --var-file pr-vars.json \
  --file .github/sc-publish-pr-template.md.j2 --output pr-body.md
```

The body must name the submitting repository and agent, and justify the
change's value to the other repositories that consume the kit. A change
whose only value is to the submitting repository is not a kit change; it
belongs in that repository's own configuration. Every item on the
template's compliance checklist must be ticked, and the body requests
review against this document. Pull requests opened without a rendered body,
with an unticked checklist item, or with a justification that names no
benefit to other consumers are rejected.

## Review

Reviewers check every pull request against the rules above and reject it
if it:

- is more complicated than the problem it solves;
- adds repository-specific logic to kit files;
- adds a mandatory gate or built-in check; or
- pushes any new requirement onto consumers that did not opt in.

A rejected pull request is not reworked by adding options or exceptions to
the rules. Simplify the change, or turn it into an extension point.

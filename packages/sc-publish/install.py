#!/usr/bin/env bash
# Copy the canonical publish-kit overlay into a consuming repository.
# Usage: sync-overlay.sh [--dry-run] /absolute/or/relative/path/to/consumer
set -euo pipefail

usage() {
  printf 'Usage: %s [--dry-run] <consumer-repository>\n' "${0##*/}" >&2
}

dry_run=false
case "${1:-}" in
  --dry-run)
    dry_run=true
    shift
    ;;
  --help|-h)
    usage
    exit 0
    ;;
esac

if [[ "$#" -ne 1 ]]; then
  usage
  exit 2
fi

consumer_root=$1
if [[ ! -d "$consumer_root" ]]; then
  printf 'Consumer repository does not exist: %s\n' "$consumer_root" >&2
  exit 2
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
overlay_root="$script_dir/overlay"
if [[ ! -d "$overlay_root" ]]; then
  printf 'Publish-kit overlay is missing: %s\n' "$overlay_root" >&2
  exit 2
fi

changed=false
while IFS= read -r -d '' source_file; do
  relative_path=${source_file#"$overlay_root/"}
  destination_file="$consumer_root/$relative_path"

  if [[ "$dry_run" == true ]]; then
    if [[ -e "$destination_file" ]]; then
      if ! diff -u -L "consumer/$relative_path" -L "publish-kit/$relative_path" \
          "$destination_file" "$source_file"; then
        changed=true
      fi
    else
      diff -u -L "consumer/$relative_path" -L "publish-kit/$relative_path" \
        /dev/null "$source_file" || true
      changed=true
    fi
    continue
  fi

  mkdir -p "$(dirname -- "$destination_file")"
  if [[ ! -e "$destination_file" ]] || ! cmp -s "$source_file" "$destination_file"; then
    cp -p "$source_file" "$destination_file"
    printf 'copied %s\n' "$relative_path"
    changed=true
  fi
done < <(find "$overlay_root" -type f -print0)

if [[ "$dry_run" == true ]]; then
  if [[ "$changed" == true ]]; then
    exit 1
  fi
  printf 'Publish-kit overlay is in sync.\n'
fi

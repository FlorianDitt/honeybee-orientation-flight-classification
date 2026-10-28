#!/usr/bin/env bash
# Build the static labeler and publish it as the only commit of the gh-pages branch.
# The clips never enter the history of main, and old deploys do not pile up.
set -euo pipefail
cd "$(dirname "$0")/.."

[[ -f public-web/data/site.json ]] || { echo "public-web/data/site.json missing: run 'uv run beeflight-clips' first" >&2; exit 1; }
remote=$(git remote get-url origin)
npx astro build --config astro.config.web.mjs
touch dist-web/.nojekyll  # keep _astro/ (Jekyll would drop folders starting with _)

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp -r dist-web/. "$tmp"
git -C "$tmp" init -q -b gh-pages
git -C "$tmp" add -A
git -C "$tmp" commit -q -m "Deploy labeler ($(git rev-parse --short HEAD))"
git -C "$tmp" push -q -f "$remote" gh-pages
echo "pushed gh-pages ($(du -sh dist-web | cut -f1)); live in about a minute"

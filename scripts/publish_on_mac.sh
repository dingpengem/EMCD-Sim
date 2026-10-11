#!/usr/bin/env bash
# Run on your own Mac after unpacking the EMCD-Sim archive into ~/EM_code/EMCD-Sim.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if ! command -v gh >/dev/null; then
  echo 'Install the GitHub CLI first: brew install gh' >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo 'Authenticate first with: gh auth login' >&2
  exit 1
fi
if gh repo view dingpengem/EMCD-Sim >/dev/null 2>&1; then
  echo 'Repository dingpengem/EMCD-Sim already exists. Aborting to avoid overwriting history.' >&2
  exit 1
fi
if [[ -d .git ]]; then
  echo 'This directory already contains a .git repository; verify remote/history manually.' >&2
  exit 1
fi
git init -b main
git add .
git commit -m "Initialize independent EMCD simulator with FCC Ni baseline"
gh repo create dingpengem/EMCD-Sim --public --source=. --remote=origin --push
printf '\nPublished to https://github.com/dingpengem/EMCD-Sim\n'

#!/usr/bin/env sh
set -eu
target="$1"
cp candidate/app.py "$target/app.py"
printf 'v3\n' > "$target/VERSION"

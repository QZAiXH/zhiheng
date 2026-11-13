#!/usr/bin/env bash
# One bounded, human-assisted reproduction attempt.
# Copy into the assigned task run location and adapt the default instructions.
# Usage: bash human-reproduction.sh [action-instruction] [observation-question]
# Use an interactive terminal. Never enter credentials or unredacted secrets here.
# Source: Matt Pocock, mattpocock-skills 1.3.2,
# skills/engineering/diagnosing-bugs/scripts/hitl-loop.template.sh.
# Adaptation: configurable prompts, explicit uncertain outcome, bounded execution.

set -euo pipefail

action_instruction=${1:-'Follow the agreed reproduction steps in the application. Sign in only through its own interface.'}
observation_question=${2:-'Describe the observed symptom, expected result, and relevant timestamp. Redact sensitive values.'}

printf '\nAction: %s\n' "$action_instruction"
printf 'Press Enter after completing this attempt: '
IFS= read -r completed_attempt

printf '\nDid the exact reported symptom occur? Enter yes, no, or uncertain: '
IFS= read -r symptom_outcome
case "$symptom_outcome" in
  yes|no|uncertain) ;;
  *) printf 'Invalid observation: use yes, no, or uncertain.\n' >&2; exit 2 ;;
esac

printf '\n%s\n> ' "$observation_question"
IFS= read -r symptom_observation
printf '\nSYMPTOM_OCCURRED=%s\nOBSERVATION=%s\n' "$symptom_outcome" "$symptom_observation"

# MIT License
#
# Copyright (c) 2026 Matt Pocock
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

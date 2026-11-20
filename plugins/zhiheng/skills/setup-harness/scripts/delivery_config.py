"""Read or prepare the delivery line and apply an approved guide update."""

import argparse
import fcntl
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


MODES = ('local', 'github-pr')
TRACKERS = ('github', 'gitlab', 'local')
DELIVERY_LINE = re.compile(rb'^<!-- harness-delivery(?=[: \t\r\n]|$)[^\r\n]*', re.MULTILINE)
VALID_LINE = re.compile(rb'<!-- harness-delivery: (local|github-pr) -->')


def delivery_line(guide):
    lines = list(DELIVERY_LINE.finditer(guide))
    if not lines:
        return None
    if len(lines) != 1 or not VALID_LINE.fullmatch(lines[0].group()):
        raise ValueError('Expected exactly one valid harness-delivery line.')
    return lines[0]


def prepare(guide, line, mode):
    desired = f'<!-- harness-delivery: {mode} -->'.encode('ascii')
    if line:
        return guide[:line.start()] + desired + guide[line.end():]

    first_lf = guide.find(b'\n')
    newline = b'\r\n' if first_lf > 0 and guide[first_lf - 1:first_lf] == b'\r' else b'\n'
    if guide and not guide.endswith(newline):
        guide += newline
    if guide and not guide.endswith(newline * 2):
        guide += newline
    return guide + desired + newline


def apply(guide, candidate, baseline):
    desired = candidate.read_bytes()
    if delivery_line(desired) is None:
        raise ValueError('The approved candidate needs a harness-delivery line.')

    guide = guide.resolve()
    expected = baseline.read_bytes() if baseline is not None else None
    guide.parent.mkdir(parents=True, exist_ok=True)
    directory = os.open(guide.parent, os.O_RDONLY)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX)
        write_if_current(guide, desired, expected, candidate)
    finally:
        os.close(directory)


def write_if_current(guide, desired, expected, candidate):
    try:
        current = guide.read_bytes()
    except FileNotFoundError:
        current = None

    if current == desired:
        return
    stale = 'The guide changed after the preview. Prepare a new preview.'
    if current != expected:
        raise ValueError(stale)

    with tempfile.NamedTemporaryFile(dir=guide.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        temporary.write_bytes(desired)
        shutil.copymode(guide if current is not None else candidate, temporary)
        if current is None:
            os.link(temporary, guide)
        else:
            if guide.read_bytes() != current:
                raise ValueError(stale)
            os.replace(temporary, guide)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    read = commands.add_parser('read')
    read.add_argument('guide', type=Path)
    draft = commands.add_parser('prepare')
    draft.add_argument('guide', type=Path)
    draft.add_argument('tracker', choices=TRACKERS)
    draft.add_argument('mode', choices=MODES)
    approved = commands.add_parser('apply')
    approved.add_argument('guide', type=Path)
    approved.add_argument('candidate', type=Path)
    approved.add_argument('--baseline', type=Path)
    args = parser.parse_args()

    try:
        if args.command == 'apply':
            apply(args.guide, args.candidate, args.baseline)
            return
        guide = args.guide.read_bytes()
        line = delivery_line(guide)
        if args.command == 'read':
            print(VALID_LINE.fullmatch(line.group())[1].decode('ascii') if line else 'missing')
        else:
            if args.mode == 'github-pr' and args.tracker != 'github':
                raise ValueError('github-pr requires the GitHub Issues tracker.')
            sys.stdout.buffer.write(prepare(guide, line, args.mode))
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()

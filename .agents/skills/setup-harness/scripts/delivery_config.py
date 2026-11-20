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
STRUCTURAL_LINE = re.compile(
    rb'^(?: {0,3}(?P<fence>`{3,}|~{3,})(?P<info>[^\r\n]*)'
    rb'|<!-- harness-delivery(?=[: \t\r\n]|$)[^\r\n]*)',
    re.MULTILINE,
)
VALID_LINE = re.compile(rb'<!-- harness-delivery: (local|github-pr) -->')
LIST_ITEM = re.compile(rb' {0,3}(?:[-+*]|[0-9]{1,9}[.)])(?P<space> +|$)')
THEMATIC_BREAK = re.compile(rb' {0,3}(?:(?:- *){3,}|(?:\* *){3,})')


def inspect_guide(guide):
    """Locate the active marker and a place to add one outside fenced examples."""
    marker = None
    fence = None
    list_indent = 0
    insertion = len(guide)
    for row in re.finditer(rb'(?m)^[^\n]+', guide):
        if fence is None:
            content = row.group().rstrip(b'\r').expandtabs(4)
            if not content.strip():
                continue
            if list_indent and content.startswith(b' ' * list_indent):
                continue
            list_indent = 0
            item = LIST_ITEM.match(content)
            if item and not THEMATIC_BREAK.fullmatch(content):
                # Indented continuations belong to the list, including its code fences.
                spaces = len(item['space'])
                list_indent = item.start('space') + (spaces if 1 <= spaces <= 4 else 1)
                continue
        line = STRUCTURAL_LINE.match(guide, row.start())
        if not line:
            continue
        delimiter = line['fence']
        if fence is not None:
            if delimiter and delimiter.startswith(fence) and not line['info'].strip(b' \t'):
                fence = None
                insertion = len(guide)
        elif delimiter:
            if delimiter.startswith(b'~') or b'`' not in line['info']:
                fence = delimiter
                insertion = line.start()
        elif marker is None and VALID_LINE.fullmatch(line.group()):
            marker = line
        else:
            raise ValueError('Expected exactly one valid harness-delivery line.')
    return marker, insertion


def prepare(guide, line, insertion, mode):
    desired = f'<!-- harness-delivery: {mode} -->'.encode('ascii')
    if line:
        return guide[:line.start()] + desired + guide[line.end():]

    first_lf = guide.find(b'\n')
    newline = b'\r\n' if first_lf > 0 and guide[first_lf - 1:first_lf] == b'\r' else b'\n'
    prefix, suffix = guide[:insertion], guide[insertion:]
    if prefix and not prefix.endswith(newline):
        prefix += newline
    if prefix and not prefix.endswith(newline * 2):
        prefix += newline
    return prefix + desired + newline + (newline + suffix if suffix else b'')


def apply(guide, candidate, baseline):
    desired = candidate.read_bytes()
    marker, _ = inspect_guide(desired)
    if marker is None:
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
        line, insertion = inspect_guide(guide)
        if args.command == 'read':
            print(VALID_LINE.fullmatch(line.group())[1].decode('ascii') if line else 'missing')
        else:
            if args.mode == 'github-pr' and args.tracker != 'github':
                raise ValueError('github-pr requires the GitHub Issues tracker.')
            sys.stdout.buffer.write(prepare(guide, line, insertion, args.mode))
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()

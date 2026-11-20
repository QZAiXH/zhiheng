#!/usr/bin/env python3
"""Verify, load, or provision an OpenViking project key."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class KeepCredentialsOnHost(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


client = build_opener(ProxyHandler({}), KeepCredentialsOnHost())


def authorization_header(key):
    if not key:
        raise ValueError("Missing credential.")
    if not key.isascii() or not key.isprintable() or any(char.isspace() for char in key):
        raise ValueError("The credential must be a single API key.")
    return f"Bearer {key}"


def request(url, key, payload=None):
    headers = {"Authorization": authorization_header(key), "Content-Type": "application/json"}
    data = json.dumps(payload).encode() if payload is not None else None
    with client.open(Request(url, data=data, headers=headers), timeout=30) as response:
        return json.load(response)


def verify(url, account, user, key):
    health = request(f"{url.rstrip('/')}/health", key)
    identity = (health.get("account_id"), health.get("user_id"), health.get("role"))
    if health.get("auth_mode") != "api_key" or identity != (account, user, "user"):
        raise ValueError("The service did not attest the selected account and ordinary user.")


def read_key(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)) as stream:
        mode = os.fstat(stream.fileno()).st_mode
        if not stat.S_ISREG(mode) or mode & 0o077:
            raise ValueError("Use a private regular key file (0600 or 0400).")
        key = stream.read().strip()
    if not key:
        raise ValueError("The key file is empty.")
    return key


def save_key(path, key):
    if not isinstance(key, str) or not key.strip():
        raise ValueError("The server did not return a project key. Inspect membership before retrying.")
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(key + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def membership(url, root_key):
    try:
        return request(url, root_key)["result"]
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def provision(args):
    server = json.loads(args.config.read_text())["server"]
    if server.get("auth_mode") not in (None, "", "api_key") or not server.get("root_api_key"):
        raise ValueError("Provisioning requires an OpenViking api_key deployment.")
    host = server.get("host", "127.0.0.1")
    host = {"0.0.0.0": "127.0.0.1", "": "127.0.0.1", "::": "::1"}.get(host, host)
    if ":" in host:
        host = f"[{host}]"
    url = f"http://{host}:{server.get('port', 1933)}"
    path = args.key_file
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        info = os.fstat(directory)
        if info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise ValueError("Use a credential directory controlled by the provisioning operator.")
        fcntl.flock(directory, fcntl.LOCK_EX)
        try:
            key = read_key(path)
        except FileNotFoundError:
            key = None
        if key is not None:
            try:
                verify(url, args.account, args.user, key)
                return "Reused"
            except HTTPError as exc:
                if exc.code != 401 or not args.rotate_lost_key:
                    raise

        accounts = url + "/api/v1/admin/accounts"
        account = accounts + "/" + quote(args.account, safe="")
        users = account + "/users"
        user = users + "/" + quote(args.user, safe="")
        root_key = server["root_api_key"]
        if membership(account, root_key) is None:
            if args.user == "maintainer":
                raise ValueError("Choose an ordinary user distinct from the new account's bootstrap administrator.")
            request(accounts, root_key, {"account_id": args.account, "admin_user_id": "maintainer"})
        member = membership(user, root_key)
        if member is None:
            issued = request(users, root_key, {"user_id": args.user, "role": "user"})
        elif member["role"] != "user":
            raise ValueError("The selected user has a different role. Select an ordinary project user.")
        elif args.rotate_lost_key:
            issued = request(user + "/key", root_key, {})
        else:
            raise ValueError("User already exists. Retrieve its saved key or authorize lost-key rotation.")
        key = issued["result"]["user_key"]
        save_key(path, key)
        os.fsync(directory)
        verify(url, args.account, args.user, key)
        return "Verified new key for"
    finally:
        os.close(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    check = modes.add_parser("verify", help="Check the selected ordinary identity without admin access.")
    check.add_argument("--url", required=True, help="Trusted project service base URL.")
    keys = check.add_mutually_exclusive_group(required=True)
    keys.add_argument("--key-env", help="Name of the project key environment variable.")
    keys.add_argument("--key-file", type=Path, help="Private project key file outside the repository.")
    issue = modes.add_parser("provision", help="Run on the authorized service host to create or resume a binding.")
    issue.add_argument("--config", type=Path, required=True, help="Service-side OpenViking JSON configuration.")
    issue.add_argument("--key-file", type=Path, required=True, help="Private credential destination outside Git.")
    issue.add_argument("--rotate-lost-key", action="store_true", help="Invalidate an existing lost key after explicit authorization.")
    headers = modes.add_parser("mcp-headers", help="Supply the Authorization header to Codex.")
    headers.add_argument("--key-file", type=Path, required=True, help="Private project key file outside the repository.")
    for command in (check, issue):
        command.add_argument("--account", required=True, help="Selected OpenViking account ID.")
        command.add_argument("--user", default="codex", help="Ordinary project user (default: codex).")
    args = parser.parse_args()
    if args.mode == "mcp-headers":
        print(json.dumps({"Authorization": authorization_header(read_key(args.key_file))}))
        return
    if any(value in ("", ".", "..") or "/" in value for value in (args.account, args.user)):
        parser.error("Supply a single account and user identifier.")
    if args.mode == "provision":
        status = provision(args)
    else:
        key = os.environ.get(args.key_env) if args.key_env else read_key(args.key_file)
        verify(args.url, args.account, args.user, key)
        status = "Verified"
    print(f"{status} {args.account}/{args.user} (ordinary user).")


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        sys.exit(f"OpenViking returned HTTP {error.code}. Check the binding and the saved credential.")
    except (OSError, ValueError, KeyError) as error:
        sys.exit(str(error))

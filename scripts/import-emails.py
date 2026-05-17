#!/usr/bin/env python3
"""
Import .eml files into the MailSubsystem sandbox IMAP server.

Usage:
    # Import a single file
    python3 import-emails.py email.eml

    # Import a directory of .eml files
    python3 import-emails.py ~/exported-emails/

    # Import from an mbox file
    python3 import-emails.py mailbox.mbox

    # Import into a specific folder
    python3 import-emails.py --folder "Work" ~/exported-emails/

    # Dry run (count files without importing)
    python3 import-emails.py --dry-run ~/exported-emails/

Exporting emails to .eml:
    - Thunderbird: Select emails > Save As > .eml files
    - Apple Mail: Select emails > drag to Finder (creates .eml files)
    - Gmail (Google Takeout): takeout.google.com > select Mail > .mbox format
    - Outlook: Select email > Save As > .eml or .msg
    - mutt/neomutt: pipe to file with | cat > email.eml
"""

import argparse
import imaplib
import mailbox
import os
import sys
from pathlib import Path


def connect_imap(host, port, user, password):
    """Connect to the sandbox IMAP server."""
    try:
        imap = imaplib.IMAP4(host, int(port))
        imap.login(user, password)
        return imap
    except imaplib.IMAP4.error as e:
        print(f"IMAP login failed: {e}")
        print("Is the sandbox running? Try: make start")
        sys.exit(1)
    except ConnectionRefusedError:
        print(f"Cannot connect to {host}:{port}")
        print("Is the sandbox running? Try: make start")
        sys.exit(1)


def ensure_folder(imap, folder):
    """Create IMAP folder if it doesn't exist."""
    status, _ = imap.select(f'"{folder}"')
    if status != "OK":
        imap.create(f'"{folder}"')
        imap.subscribe(f'"{folder}"')
        print(f"  Created folder: {folder}")
    imap.select("INBOX")


def import_raw_email(imap, raw_bytes, folder="INBOX"):
    """Append a single raw email to the IMAP server."""
    status, response = imap.append(
        f'"{folder}"', None, None, raw_bytes
    )
    return status == "OK"


def read_eml_file(path):
    """Read a .eml file and return raw bytes."""
    with open(path, "rb") as f:
        return f.read()


def import_eml_files(imap, paths, folder, dry_run=False):
    """Import a list of .eml file paths."""
    success = 0
    failed = 0
    for path in paths:
        name = os.path.basename(path)
        if dry_run:
            print(f"  [dry-run] Would import: {name}")
            success += 1
            continue
        try:
            raw = read_eml_file(path)
            if import_raw_email(imap, raw, folder):
                success += 1
            else:
                print(f"  Failed: {name}")
                failed += 1
        except Exception as e:
            print(f"  Error reading {name}: {e}")
            failed += 1
    return success, failed


def import_mbox(imap, mbox_path, folder, dry_run=False):
    """Import emails from an mbox file."""
    mbox = mailbox.mbox(mbox_path)
    success = 0
    failed = 0
    for i, message in enumerate(mbox):
        if dry_run:
            subject = message.get("Subject", "(no subject)")
            print(f"  [dry-run] Would import #{i+1}: {subject[:60]}")
            success += 1
            continue
        try:
            raw = message.as_bytes()
            if import_raw_email(imap, raw, folder):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  Error importing message #{i+1}: {e}")
            failed += 1
    return success, failed


def collect_eml_files(path):
    """Recursively collect .eml files from a path."""
    path = Path(path)
    if path.is_file() and path.suffix.lower() == ".eml":
        return [path]
    elif path.is_dir():
        files = sorted(path.rglob("*.eml"))
        if not files:
            print(f"No .eml files found in {path}")
            sys.exit(1)
        return files
    else:
        print(f"Not a .eml file or directory: {path}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Import emails into the MailSubsystem sandbox IMAP server."
    )
    parser.add_argument(
        "source",
        help="Path to .eml file, directory of .eml files, or .mbox file",
    )
    parser.add_argument(
        "--folder",
        default="INBOX",
        help="IMAP folder to import into (default: INBOX)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("SANDBOX_IMAP_HOST", "localhost"),
        help="IMAP host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        default=os.environ.get("SANDBOX_IMAP_PORT", "1143"),
        help="IMAP port (default: 1143, plaintext)",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("SANDBOX_IMAP_USER", "testuser"),
        help="IMAP username (default: testuser)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("SANDBOX_IMAP_PASS", "testpass123"),
        help="IMAP password (default: testpass123)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count emails without importing",
    )
    args = parser.parse_args()

    source = Path(args.source)
    is_mbox = source.is_file() and source.suffix.lower() in (".mbox", ".mbx")

    # Connect
    if not args.dry_run:
        print(f"Connecting to {args.host}:{args.port} as {args.user}...")
        imap = connect_imap(args.host, args.port, args.user, args.password)
        if args.folder != "INBOX":
            ensure_folder(imap, args.folder)
    else:
        imap = None

    # Import
    if is_mbox:
        print(f"Importing from mbox: {source}")
        success, failed = import_mbox(imap, source, args.folder, args.dry_run)
    else:
        files = collect_eml_files(source)
        print(f"Found {len(files)} .eml file(s)")
        success, failed = import_eml_files(imap, files, args.folder, args.dry_run)

    # Summary
    action = "Would import" if args.dry_run else "Imported"
    print(f"\n{action} {success} email(s) into {args.folder}", end="")
    if failed:
        print(f" ({failed} failed)")
    else:
        print()

    if not args.dry_run and imap:
        imap.logout()

    if not args.dry_run and success > 0:
        print(f"\nNext steps:")
        print(f"  make check              # verify connectivity")
        print(f"  make sync               # sync sandbox emails")
        print(f"  make analyze            # run AI analysis")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

# Configuration
LS_CMD = "/Applications/Little Snitch.app/Contents/Components/littlesnitch"
USER = os.environ.get("USER")


def run_command(cmd, shell=False):
    try:
        result = subprocess.run(cmd, shell=shell, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Stderr: {e.stderr}")
        sys.exit(1)


def get_binary_hash(path):
    # Resolve symlink to get actual file for hashing
    # Little Snitch likely hashes the *resolved* binary on disk.
    resolved_path = os.path.realpath(path)
    if not os.path.exists(resolved_path):
        print(f"Error: File not found: {resolved_path}")
        sys.exit(1)

    print(f"Hashing binary at: {resolved_path}")
    sha256_hash = hashlib.sha256()
    with open(resolved_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def export_config(output_path):
    print("Exporting Little Snitch configuration...")
    run_command(["sudo", LS_CMD, "-u", USER, "export-model", output_path])


def restore_config(input_path):
    print("Restoring Little Snitch configuration...")
    run_command(["sudo", LS_CMD, "-u", USER, "restore-model", input_path])


def find_code_requirement_key(config, binary_path):
    # Try to find an existing key in codeRequirements that matches the binary path
    # This is tricky because keys can be paths or patterns.
    # For now, we'll look for exact matches or matches that resolve to the same file.

    # Common pattern in LS: path.usr/local/Cellar/package/version/bin/binary
    # We might need to handle Homebrew paths specially.

    real_path = os.path.realpath(binary_path)

    # Check if real path is in Cellar
    if "Cellar" in real_path:
        # Construct pattern like "path.usr/local/Cellar/mosh/*/bin/mosh-server"
        parts = real_path.split("/")
        try:
            cellar_index = parts.index("Cellar")
            # e.g. /usr/local/Cellar/mosh/1.4.0_34/bin/mosh-server
            # pattern: path.usr/local/Cellar/mosh/*/bin/mosh-server
            # parts[cellar_index+2] is the version, replace with *
            package_name = parts[cellar_index + 1]
            relative_path = "/".join(parts[cellar_index + 3 :])

            # Construct key
            # Note: LS keys often start with "path." and use dots instead of slashes for the prefix?
            # No, looking at JSON: "path.usr/local/Cellar/mosh/*/bin/mosh-server"
            # It seems to be literal string "path." + path with glob.

            # Heuristic: try to find a key that "looks like" our path
            for key in config.get("codeRequirements", {}):
                if package_name in key and relative_path in key:
                    return key
        except ValueError:
            pass

    return None


def update_rule(args):
    binary_path = args.path
    if not os.path.exists(binary_path):
        binary_path = shutil.which(binary_path)
        if not binary_path:
            print(f"Error: Could not find binary: {args.path}")
            sys.exit(1)

    print(f"Processing binary: {binary_path}")
    resolved_path = os.path.realpath(binary_path)
    print(f"Resolved path: {resolved_path}")

    new_hash = get_binary_hash(resolved_path)
    print(f"Calculated Hash: {new_hash}")

    # Create persistent backup directory
    backup_dir = os.path.expanduser("~/.ls_backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_file = os.path.join(backup_dir, f"ls_backup_{timestamp}.json")
    # Keep the modified file in tmp as it's transient
    modified_file = f"/tmp/ls_modified_{timestamp}.json"

    export_config(backup_file)
    print(f"✅ Backup saved to: {backup_file}")

    with open(backup_file) as f:
        config = json.load(f)

    # 1. Update Code Requirements (Trusted Anchors)
    cr_key = find_code_requirement_key(config, binary_path)

    if cr_key:
        print(f"Found existing code requirement key: {cr_key}")
        current_cr = config["codeRequirements"][cr_key]

        # Enforce fileHash type.
        # Issue fix: mosh-server was previously set as "trustedAnchor" with a SHA256 hash,
        # which is invalid.
        if current_cr.get("type") != "fileHash":
            print(f"Fixing type: Changing {current_cr.get('type')} to fileHash")
            current_cr["type"] = "fileHash"
            if "authorIdentifier" in current_cr:
                del current_cr["authorIdentifier"]

        if current_cr.get("codeIdentifier") != new_hash:
            print(f"Updating hash from {current_cr.get('codeIdentifier')} to {new_hash}")
            config["codeRequirements"][cr_key]["codeIdentifier"] = new_hash
        else:
            print("Hash matches existing code requirement.")
    else:
        print(
            f"No existing code requirement found. "
            f"Creating new 'fileHash' requirement for {resolved_path}"
        )
        # Ensure codeRequirements dict exists
        if "codeRequirements" not in config:
            config["codeRequirements"] = {}

        config["codeRequirements"][resolved_path] = {"type": "fileHash", "codeIdentifier": new_hash}

    # 2. Add/Update Rule
    # Check if a rule already exists for this process
    rules = config.get("rules", [])

    # Define the new rule object
    new_rule = {
        "action": "allow",
        "process": binary_path,  # Use the path provided (e.g. symlink)
        "ports": args.ports,
        "protocol": args.protocol,
        "direction": args.direction,
        "remote": args.remote,
        "origin": "frontend",
        "creationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modificationDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # Remove existing rules for this process if requested or update them
    # For now, let's just append the new rule if not exact duplicate
    # Or maybe filter out old rules for this process?

    # Simple approach: Remove rules matching this process and add new one
    if args.replace:
        print(f"Removing existing rules for {binary_path}...")
        config["rules"] = [r for r in rules if r.get("process") != binary_path]

    print("Adding new rule...")
    config["rules"].append(new_rule)

    # Save modified config
    with open(modified_file, "w") as f:
        json.dump(config, f, indent=2)

    try:
        restore_config(modified_file)
        print("✅ Configuration updated successfully.")
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        print(f"Attempting to revert to backup: {backup_file}")
        restore_config(backup_file)
        print("Reverted to original configuration.")
        sys.exit(1)

    print("\n----------------------------------------------------------------")
    print("To undo this change, run the following command:")
    print(f'sudo "{LS_CMD}" -u {USER} restore-model "{backup_file}"')
    print("----------------------------------------------------------------")


def main():
    parser = argparse.ArgumentParser(description="Manage Little Snitch rules via CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Update command
    update_parser = subparsers.add_parser("allow", help="Allow a binary")
    update_parser.add_argument("path", help="Path to binary (e.g. /usr/local/bin/mosh-server)")
    update_parser.add_argument("--ports", required=True, help="Port range (e.g. 60000-61000)")
    update_parser.add_argument(
        "--protocol", default="udp", choices=["udp", "tcp"], help="Protocol (udp/tcp)"
    )
    update_parser.add_argument(
        "--direction",
        default="both",
        choices=["incoming", "outgoing", "both"],
        help="Direction",
    )
    update_parser.add_argument("--remote", default="any", help="Remote scope (any, local-net, etc)")
    update_parser.add_argument(
        "--replace", action="store_true", help="Replace existing rules for this binary"
    )

    args = parser.parse_args()

    if args.command == "allow":
        update_rule(args)


if __name__ == "__main__":
    main()

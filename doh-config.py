#!/usr/bin/env python3
"""
doh-config.py - JSON configuration management utilities for doh system
Handles all JSON operations reliably to avoid bash sed/grep corruption issues
"""

import json
import sys
import os
from pathlib import Path

def load_config(config_file):
    """Load and validate config file, return default if corrupted/missing"""
    default_config = {
        "version": "1.0",
        "directories": {},
        "exclusions": {},
        "global_settings": {
            "log_retention_days": 30,
            "default_threshold": 50,
            "check_interval_minutes": 10,
            "git_profile": ""
        }
    }
    
    if not os.path.exists(config_file):
        return default_config
    
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
            
        # Ensure all required sections exist
        if "directories" not in data:
            data["directories"] = {}
        if "exclusions" not in data:
            data["exclusions"] = {}
        if "global_settings" not in data:
            data["global_settings"] = default_config["global_settings"]
        else:
            # Merge with defaults to ensure all fields exist
            for key, value in default_config["global_settings"].items():
                if key not in data["global_settings"]:
                    data["global_settings"][key] = value
        
        return data
    except Exception as e:
        print(f"WARNING: Could not read config ({e}), using defaults", file=sys.stderr)
        return default_config

def save_config(config_file, data):
    """Save config data to file with proper formatting"""
    try:
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"ERROR: Could not save config: {e}", file=sys.stderr)
        return False

def get_config_value():
    """Get a specific config value"""
    if len(sys.argv) < 3:
        print("Usage: get_config_value <config_file> <key> [dir_path]")
        sys.exit(1)
    
    config_file = sys.argv[1]
    key = sys.argv[2]
    dir_path = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "" else None
    
    data = load_config(config_file)
    
    if dir_path:
        # Get directory-specific setting
        if dir_path in data.get('directories', {}):
            directory_data = data['directories'][dir_path]
            if key in directory_data:
                print(directory_data[key])
            else:
                print("")
        else:
            print("")
    else:
        # Get global setting
        if key in data.get('global_settings', {}):
            print(data['global_settings'][key])
        else:
            print("")

def add_directory():
    """Add or update a directory in monitoring"""
    if len(sys.argv) < 6:
        print("Usage: add_directory <config_file> <dir_path> <threshold> <name> <timestamp>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    dir_path = sys.argv[2]
    threshold = int(sys.argv[3])
    name = sys.argv[4]
    timestamp = sys.argv[5]
    
    data = load_config(config_file)
    
    # Ensure directories section exists
    if "directories" not in data:
        data["directories"] = {}
    
    # Add/update the directory entry
    data["directories"][dir_path] = {
        "name": name,
        "threshold": threshold,
        "added": timestamp,
        "last_checked": timestamp
    }
    
    if save_config(config_file, data):
        print("SUCCESS")
    else:
        sys.exit(1)

def remove_directory():
    """Remove directory from config"""
    if len(sys.argv) < 3:
        print("Usage: remove_directory <config_file> <dir_path>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    dir_to_remove = sys.argv[2]
    
    data = load_config(config_file)
    
    # Remove the directory from both directories and exclusions
    if dir_to_remove in data.get('directories', {}):
        del data['directories'][dir_to_remove]
    if dir_to_remove in data.get('exclusions', {}):
        del data['exclusions'][dir_to_remove]
    
    if save_config(config_file, data):
        print("SUCCESS")
    else:
        sys.exit(1)

def add_exclusion():
    """Add directory to exclusions"""
    if len(sys.argv) < 4:
        print("Usage: add_exclusion <config_file> <dir_path> <timestamp>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    dir_path = sys.argv[2]
    timestamp = sys.argv[3]
    
    data = load_config(config_file)
    
    # Ensure exclusions section exists
    if "exclusions" not in data:
        data["exclusions"] = {}
    
    # Add the exclusion entry
    data["exclusions"][dir_path] = {
        "excluded": timestamp
    }
    
    if save_config(config_file, data):
        print("SUCCESS")
    else:
        sys.exit(1)

def remove_exclusion():
    """Remove directory from exclusions"""
    if len(sys.argv) < 3:
        print("Usage: remove_exclusion <config_file> <dir_path>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    dir_to_remove = sys.argv[2]
    
    data = load_config(config_file)
    
    # Remove from exclusions if it exists
    if dir_to_remove in data.get('exclusions', {}):
        del data['exclusions'][dir_to_remove]
    
    if save_config(config_file, data):
        print("SUCCESS")
    else:
        sys.exit(1)

def check_exclusion():
    """Check if directory or parent is excluded"""
    if len(sys.argv) < 3:
        print("Usage: check_exclusion <config_file> <dir_path>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    dir_path = sys.argv[2]
    
    data = load_config(config_file)
    exclusions = data.get('exclusions', {})
    
    # Check if the directory itself is excluded
    if dir_path in exclusions:
        print("EXCLUDED")
        return
    
    # Check if any parent directory is excluded
    current_path = dir_path
    while current_path != "/" and current_path != ".":
        current_path = os.path.dirname(current_path)
        if current_path in exclusions:
            print("EXCLUDED")
            return
    
    print("NOT_EXCLUDED")

def find_excluded_parent():
    """Find which excluded directory is blocking this path"""
    if len(sys.argv) < 3:
        print("Usage: find_excluded_parent <config_file> <dir_path>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    dir_path = sys.argv[2]
    
    data = load_config(config_file)
    exclusions = data.get('exclusions', {})
    
    # Check if the directory itself is excluded
    if dir_path in exclusions:
        print(dir_path)
        return
    
    # Check if any parent directory is excluded
    current_path = dir_path
    while current_path != "/" and current_path != ".":
        current_path = os.path.dirname(current_path)
        if current_path in exclusions:
            print(current_path)
            return
    
    # Not found
    sys.exit(1)

def generate_fresh_config():
    """Generate a fresh config file from existing data"""
    if len(sys.argv) < 3:
        print("Usage: generate_fresh_config <input_config> <output_config>")
        sys.exit(1)
    
    input_config = sys.argv[1]
    output_config = sys.argv[2]
    
    data = load_config(input_config)
    
    if save_config(output_config, data):
        print("SUCCESS")
    else:
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: doh-config.py <command> [args...]")
        print("Commands:")
        print("  get_config_value <config_file> <key> [dir_path]")
        print("  add_directory <config_file> <dir_path> <threshold> <name> <timestamp>")
        print("  remove_directory <config_file> <dir_path>")
        print("  add_exclusion <config_file> <dir_path> <timestamp>")
        print("  remove_exclusion <config_file> <dir_path>")
        print("  check_exclusion <config_file> <dir_path>")
        print("  find_excluded_parent <config_file> <dir_path>")
        print("  generate_fresh_config <input_config> <output_config>")
        sys.exit(1)
    
    command = sys.argv[1]
    # Remove command from argv and shift arguments
    sys.argv = sys.argv[1:]
    
    if command == "get_config_value":
        get_config_value()
    elif command == "add_directory":
        add_directory()
    elif command == "remove_directory":
        remove_directory()
    elif command == "add_exclusion":
        add_exclusion()
    elif command == "remove_exclusion":
        remove_exclusion()
    elif command == "check_exclusion":
        check_exclusion()
    elif command == "find_excluded_parent":
        find_excluded_parent()
    elif command == "generate_fresh_config":
        generate_fresh_config()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

#!/usr/bin/env python3
"""Test script to verify the new default value for temp branch cleanup days"""

from src.doh.config import DohConfig

# Test the default configuration
config = DohConfig()
default_config = config._get_default_config()

print("Default temp branch cleanup days:", 
      default_config["global_settings"]["max_temp_branch_age_days"])

# Test loading config (should use defaults for new installations)
data = config.load()
global_settings = data.get("global_settings", {})
cleanup_days = global_settings.get("max_temp_branch_age_days", "NOT SET")

print("Current config temp branch cleanup days:", cleanup_days)

#!/usr/bin/env python3
"""
Fix YAML rule files to convert conditions from list format to dict format.

The Pydantic RulePattern model expects conditions as Dict[str, Any], but the
YAML files currently have them as List[Dict[str, Any]].
"""

import yaml
from pathlib import Path

def fix_conditions_format(data):
    """
    Recursively fix conditions format from list to dict.

    Converts:
        conditions:
          - has_sukoon: true
          - following_is_throat_letter: true

    To:
        conditions:
          has_sukoon: true
          following_is_throat_letter: true
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'conditions' and isinstance(value, list):
                # Convert list of single-key dicts to flat dict
                new_conditions = {}
                for item in value:
                    if isinstance(item, dict):
                        new_conditions.update(item)
                data[key] = new_conditions
            else:
                fix_conditions_format(value)
    elif isinstance(data, list):
        for item in data:
            fix_conditions_format(item)

    return data

def process_yaml_file(file_path):
    """Process a single YAML file."""
    print(f"Processing: {file_path.name}")

    try:
        # Load YAML
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Fix conditions
        fix_conditions_format(data)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2
            )

        print(f"  ✅ Fixed: {file_path.name}")
        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    # Get all YAML rule files
    rules_dir = Path("data/tajweed_rules")
    yaml_files = list(rules_dir.glob("*.yaml"))

    print(f"Found {len(yaml_files)} YAML files to process\n")

    success_count = 0
    for yaml_file in yaml_files:
        if process_yaml_file(yaml_file):
            success_count += 1

    print(f"\n✅ Successfully processed {success_count}/{len(yaml_files)} files")

if __name__ == "__main__":
    main()

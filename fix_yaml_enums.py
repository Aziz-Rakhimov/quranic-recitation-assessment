#!/usr/bin/env python3
"""
Fix YAML rule files to use correct enum values.

Mappings:
- noon_sakinah -> noon_meem_sakinah
- meem_sakinah -> noon_meem_sakinah
- emphasis -> general (or keep as emphasis if we add it)
- modify -> modify_features
- modify_duration -> modify_features
- add_acoustic_feature -> modify_features
- etc.
"""

import yaml
from pathlib import Path

# Enum value mappings
CATEGORY_MAP = {
    'noon_sakinah': 'noon_meem_sakinah',
    'meem_sakinah': 'noon_meem_sakinah',
    'emphasis': 'general',  # We'll add EMPHASIS to enum later
}

ACTION_TYPE_MAP = {
    'modify': 'modify_features',
    'modify_duration': 'modify_features',
    'insert_and_prolong': 'insert',
    'add_acoustic_feature': 'modify_features',
    'partial_qalqalah': 'modify_features',
    'add_emphatic_quality': 'modify_features',
    'keep_light_quality': 'keep_original',
    'allow_both': 'keep_original',
}

ERROR_CATEGORY_MAP = {
    'noon_sakinah': 'tajweed',
    'meem_sakinah': 'tajweed',
    'raa': 'tajweed',
}

def fix_enum_values(data):
    """Recursively fix enum values in data."""
    if isinstance(data, dict):
        for key, value in data.items():
            # Fix category
            if key == 'category' and isinstance(value, str):
                if value in CATEGORY_MAP:
                    data[key] = CATEGORY_MAP[value]

            # Fix action type
            elif key == 'type' and isinstance(value, str) and 'action' in str(data.get('parent_key', '')).lower():
                if value in ACTION_TYPE_MAP:
                    data[key] = ACTION_TYPE_MAP[value]

            # Fix error category
            elif key == 'category' and 'error' in str(data.get('parent_key', '')).lower():
                if isinstance(value, str) and value in ERROR_CATEGORY_MAP:
                    data[key] = ERROR_CATEGORY_MAP[value]

            else:
                fix_enum_values(value)

    elif isinstance(data, list):
        for item in data:
            fix_enum_values(item)

    return data

def fix_rule_enums(rule_data):
    """Fix enum values in a rule."""
    # Fix rule category
    if 'category' in rule_data:
        if rule_data['category'] in CATEGORY_MAP:
            rule_data['category'] = CATEGORY_MAP[rule_data['category']]

    # Fix action type
    if 'action' in rule_data and 'type' in rule_data['action']:
        action_type = rule_data['action']['type']
        if action_type in ACTION_TYPE_MAP:
            rule_data['action']['type'] = ACTION_TYPE_MAP[action_type]

    # Fix error categories
    if 'error_types' in rule_data:
        for error in rule_data['error_types']:
            if 'category' in error:
                if error['category'] in ERROR_CATEGORY_MAP:
                    error['category'] = ERROR_CATEGORY_MAP[error['category']]

    return rule_data

def process_yaml_file(file_path):
    """Process a single YAML file."""
    print(f"Processing: {file_path.name}")

    try:
        # Load YAML
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Fix rules
        if 'rules' in data:
            for rule in data['rules']:
                fix_rule_enums(rule)

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
        import traceback
        traceback.print_exc()
        return False

def fix_phoneme_yaml():
    """Fix labio-velar to labio_velar in phoneme YAML."""
    file_path = Path("data/pronunciation_dict/base_phonemes.yaml")
    print(f"\nFixing phoneme inventory: {file_path.name}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace labio-velar with labio_velar
        content = content.replace('labio-velar', 'labio_velar')

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"  ✅ Fixed: {file_path.name}")
        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    # Fix rule files
    rules_dir = Path("data/tajweed_rules")
    yaml_files = list(rules_dir.glob("*.yaml"))

    print(f"Found {len(yaml_files)} YAML rule files to process\n")

    success_count = 0
    for yaml_file in yaml_files:
        if process_yaml_file(yaml_file):
            success_count += 1

    print(f"\n✅ Successfully processed {success_count}/{len(yaml_files)} rule files")

    # Fix phoneme file
    if fix_phoneme_yaml():
        print("\n✅ All files fixed!")
    else:
        print("\n⚠️  Phoneme file fix failed")

if __name__ == "__main__":
    main()

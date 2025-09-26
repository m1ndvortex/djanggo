#!/usr/bin/env python
"""
Fix URL namespace issues in templates.
Replace 'core:' with 'admin_panel:' in all template files.
"""
import os
import re
from pathlib import Path

def fix_url_namespaces():
    """Fix URL namespace issues in templates."""
    templates_dir = Path('templates')
    
    # Pattern to match {% url 'core:...' %}
    pattern = r"{% url ['\"]core:([^'\"]+)['\"]"
    replacement = r"{% url 'admin_panel:\1'"
    
    fixed_files = []
    
    for template_file in templates_dir.rglob('*.html'):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file contains the pattern
            if re.search(pattern, content):
                # Replace all occurrences
                new_content = re.sub(pattern, replacement, content)
                
                # Write back to file
                with open(template_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                fixed_files.append(str(template_file))
                print(f"Fixed: {template_file}")
        
        except Exception as e:
            print(f"Error processing {template_file}: {e}")
    
    print(f"\nFixed {len(fixed_files)} files:")
    for file in fixed_files:
        print(f"  - {file}")

if __name__ == '__main__':
    fix_url_namespaces()
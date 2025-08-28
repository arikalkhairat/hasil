#!/usr/bin/env python3

def fix_embed_docx_indentation():
    """Fix indentation for embed_docx_route function"""
    
    with open('/workspaces/hasil/app.py', 'r') as f:
        lines = f.readlines()
    
    fixed_lines = []
    inside_embed_docx = False
    inside_try_block = False
    brace_count = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Detect start of embed_docx_route function
        if 'def embed_docx_route():' in line:
            inside_embed_docx = True
            fixed_lines.append(line)
            i += 1
            continue
        
        # Detect start of next function (end of embed_docx_route)
        if inside_embed_docx and line.startswith('def ') and 'embed_docx_route' not in line:
            inside_embed_docx = False
            inside_try_block = False
            fixed_lines.append(line)
            i += 1
            continue
            
        # Detect start of next route (end of embed_docx_route) 
        if inside_embed_docx and line.startswith('@app.route') and 'embed_docx' not in line:
            inside_embed_docx = False
            inside_try_block = False
            fixed_lines.append(line)
            i += 1
            continue
        
        if inside_embed_docx:
            # Detect try block
            if 'try:' in line and line.strip() == 'try:':
                inside_try_block = True
                fixed_lines.append(line)
                i += 1
                continue
                
            # Detect except block (end try)
            if 'except Exception as e:' in line and inside_try_block:
                inside_try_block = False
                # This except should be at same level as try
                fixed_lines.append(line)
                i += 1
                continue
            
            # If we're inside try block, ensure proper indentation
            if inside_try_block:
                # Skip empty lines
                if line.strip() == '':
                    fixed_lines.append(line)
                    i += 1
                    continue
                
                # If line is not indented enough, add proper indentation
                if not line.startswith('        '):  # 8 spaces for try block content
                    if not line.startswith('    '):  # Already has some indentation
                        line = '        ' + line.lstrip()
                    else:
                        # Add 4 more spaces
                        line = '    ' + line
                
                fixed_lines.append(line)
                i += 1
                continue
        
        # For all other lines, keep as is
        fixed_lines.append(line)
        i += 1
    
    # Write fixed content
    with open('/workspaces/hasil/app.py', 'w') as f:
        f.writelines(fixed_lines)
    
    print("Fixed indentation for embed_docx_route function")

if __name__ == '__main__':
    fix_embed_docx_indentation()
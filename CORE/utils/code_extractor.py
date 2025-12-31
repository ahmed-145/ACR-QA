"""
Code snippet extractor for providing context to LLM
Extracts lines around the detected issue
"""
from pathlib import Path

def extract_code_snippet(file_path, line_number, context_lines=3):
    """
    Extract code snippet around the issue line with context
    
    Args:
        file_path: Path to the file
        line_number: Line number of the issue (1-indexed)
        context_lines: Number of lines before/after to include
        
    Returns:
        String with formatted code snippet
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"# File not found: {file_path}"
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Calculate range (handle edge cases)
        total_lines = len(lines)
        start = max(0, line_number - context_lines - 1)
        end = min(total_lines, line_number + context_lines)
        
        # Build snippet with line numbers
        snippet_lines = []
        for i in range(start, end):
            line_num = i + 1
            line_content = lines[i].rstrip()
            
            # Mark the issue line with >>>
            if line_num == line_number:
                prefix = ">>> "
            else:
                prefix = "    "
            
            snippet_lines.append(f"{prefix}{line_num:4d} | {line_content}")
        
        return "\n".join(snippet_lines)
        
    except Exception as e:
        return f"# Error extracting snippet: {str(e)}"

def extract_function_context(file_path, line_number):
    """
    Extract the entire function containing the issue line
    More context than line-based extraction
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return extract_code_snippet(file_path, line_number)
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Find function/class definition
        def_line = None
        for i in range(line_number - 1, -1, -1):
            stripped = lines[i].strip()
            if stripped.startswith('def ') or stripped.startswith('class '):
                def_line = i
                break
        
        # If found, extract from def to next def or end
        if def_line is not None:
            end_line = len(lines)
            for i in range(def_line + 1, len(lines)):
                stripped = lines[i].strip()
                if (stripped.startswith('def ') or stripped.startswith('class ')) and lines[i][0] not in (' ', '\t'):
                    end_line = i
                    break
            
            snippet_lines = []
            for i in range(def_line, min(end_line, def_line + 30)):  # Max 30 lines
                line_num = i + 1
                prefix = ">>> " if line_num == line_number else "    "
                snippet_lines.append(f"{prefix}{line_num:4d} | {lines[i].rstrip()}")
            
            return "\n".join(snippet_lines)
        
        # Fallback to line-based
        return extract_code_snippet(file_path, line_number)
        
    except Exception as e:
        return extract_code_snippet(file_path, line_number)
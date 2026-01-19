"""Impl-agent instruction executor.

Parses impl-agent output and generates shell scripts for review.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def parse_instruction(instruction: str) -> dict[str, Any]:
    """Parse a single impl-agent instruction into structured data.

    Args:
        instruction: Raw instruction string like "EXTRACT function name (lines 70-92) from x.py → y.py"

    Returns:
        Dict with action, details, and original instruction
    """
    result = {"original": instruction, "action": None, "valid": False}

    # Clean up: remove backticks from file paths
    clean_instr = re.sub(r"`([^`]+)`", r"\1", instruction)

    # EXTRACT single function: EXTRACT function name (lines X-Y) from file.py → new_file.py
    extract_single = re.match(
        r"EXTRACT\s+function\s+(\w+)\s+\(lines?\s+(\d+)-(\d+)\)\s+from\s+([^\s→]+)\s*→\s*(.+)",
        clean_instr,
        re.IGNORECASE,
    )
    if extract_single:
        return {
            "original": instruction,
            "action": "EXTRACT",
            "functions": [extract_single.group(1).strip()],
            "start_line": int(extract_single.group(2)),
            "end_line": int(extract_single.group(3)),
            "source_file": extract_single.group(4).strip().rstrip("."),
            "target_file": extract_single.group(5).strip().rstrip("."),
            "valid": True,
        }

    # EXTRACT multiple functions (legacy): EXTRACT functions [name1, name2] (lines X-Y) from file.py → new_file.py
    extract_match = re.match(
        r"EXTRACT\s+functions?\s+\[([^\]]+)\]\s+\(lines?\s+(\d+)-(\d+)\)\s+from\s+([^\s→]+)\s*→\s*(.+)",
        clean_instr,
        re.IGNORECASE,
    )
    if extract_match:
        funcs = [f.strip().strip("'\"") for f in extract_match.group(1).split(",")]
        return {
            "original": instruction,
            "action": "EXTRACT",
            "functions": funcs,
            "start_line": int(extract_match.group(2)),
            "end_line": int(extract_match.group(3)),
            "source_file": extract_match.group(4).strip().rstrip("."),
            "target_file": extract_match.group(5).strip().rstrip("."),
            "valid": True,
        }

    # DELETE single function: DELETE function name (lines X-Y) in file.py (reason)
    delete_func = re.match(
        r"DELETE\s+function\s+(\w+)\s+\(lines?\s+(\d+)-(\d+)\)\s+in\s+([^\s(]+)(?:\s*\(([^)]+)\))?",
        clean_instr,
        re.IGNORECASE,
    )
    if delete_func:
        return {
            "original": instruction,
            "action": "DELETE",
            "function": delete_func.group(1).strip(),
            "start_line": int(delete_func.group(2)),
            "end_line": int(delete_func.group(3)),
            "file": delete_func.group(4).strip().rstrip("."),
            "reason": delete_func.group(5) if delete_func.group(5) else "",
            "valid": True,
        }

    # DELETE lines (legacy): DELETE lines X-Y in file.py (reason)
    delete_match = re.match(
        r"DELETE\s+lines?\s+(\d+)-(\d+)\s+in\s+([^\s(]+)(?:\s*\(([^)]+)\))?",
        clean_instr,
        re.IGNORECASE,
    )
    if delete_match:
        return {
            "original": instruction,
            "action": "DELETE",
            "start_line": int(delete_match.group(1)),
            "end_line": int(delete_match.group(2)),
            "file": delete_match.group(3).strip().rstrip("."),
            "reason": delete_match.group(4) if delete_match.group(4) else "",
            "valid": True,
        }

    # ADD pattern: ADD import/statement at line X in file.py: 'content'
    add_match = re.match(
        r"ADD\s+(.+?)\s+at\s+line\s+(\d+)\s+in\s+([^\s:]+):\s*['\"`]?(.+?)['\"`]?\s*$",
        clean_instr,
        re.IGNORECASE | re.DOTALL,
    )
    if add_match:
        # Clean content: strip backticks and trailing periods
        content = add_match.group(4).strip()
        content = content.strip("`'\"").rstrip(".")
        return {
            "original": instruction,
            "action": "ADD",
            "what": add_match.group(1).strip(),
            "line": int(add_match.group(2)),
            "file": add_match.group(3).strip().rstrip("."),
            "content": content,
            "valid": True,
        }

    # ADD after line pattern: ADD ... after line X in file.py
    add_after_match = re.match(
        r"ADD\s+(.+?)\s+after\s+line\s+(\d+)\s+in\s+([^\s:]+)",
        clean_instr,
        re.IGNORECASE,
    )
    if add_after_match:
        return {
            "original": instruction,
            "action": "ADD_AFTER",
            "what": add_after_match.group(1).strip(),
            "after_line": int(add_after_match.group(2)),
            "file": add_after_match.group(3).strip().rstrip("."),
            "valid": True,
        }

    # CREATE pattern: CREATE file.py with ...
    create_match = re.match(
        r"CREATE\s+([^\s]+)\s+with\s+(.+)",
        clean_instr,
        re.IGNORECASE | re.DOTALL,
    )
    if create_match:
        return {
            "original": instruction,
            "action": "CREATE",
            "file": create_match.group(1).strip().rstrip("."),
            "content_desc": create_match.group(2).strip(),
            "valid": True,
        }

    # MODIFY pattern: MODIFY function_name (lines X-Y) in file.py: description
    modify_match = re.match(
        r"MODIFY\s+([^\s(]+)\s+\(lines?\s+(\d+)-(\d+)\)\s+in\s+([^\s:]+):\s*(.+)",
        clean_instr,
        re.IGNORECASE | re.DOTALL,
    )
    if modify_match:
        return {
            "original": instruction,
            "action": "MODIFY",
            "function": modify_match.group(1).strip(),
            "start_line": int(modify_match.group(2)),
            "end_line": int(modify_match.group(3)),
            "file": modify_match.group(4).strip().rstrip("."),
            "description": modify_match.group(5).strip(),
            "valid": True,
        }

    # MODIFY without line numbers
    modify_simple = re.match(
        r"MODIFY\s+([^\s]+)\s+to\s+(.+)",
        clean_instr,
        re.IGNORECASE | re.DOTALL,
    )
    if modify_simple:
        return {
            "original": instruction,
            "action": "MODIFY_SIMPLE",
            "target": modify_simple.group(1).strip(),
            "description": modify_simple.group(2).strip(),
            "valid": True,
        }

    # VERIFY pattern
    if instruction.upper().startswith("VERIFY"):
        return {
            "original": instruction,
            "action": "VERIFY",
            "description": instruction[6:].strip(),
            "valid": True,
        }

    # Unrecognized - still include as comment
    return result


def instruction_to_shell(parsed: dict[str, Any], project_root: str = ".") -> str:
    """Convert a parsed instruction to shell commands.

    Args:
        parsed: Parsed instruction dict from parse_instruction()
        project_root: Root directory for file paths

    Returns:
        Shell script snippet with comments and commands
    """
    lines = []
    lines.append(f"\n# {'-' * 70}")

    # Handle multi-line instructions: convert newlines to comment continuations
    original = parsed["original"]
    instr_lines = original.split("\n")
    first_line = instr_lines[0][:100]
    lines.append(f"# INSTRUCTION: {first_line}")

    # Add continuation for long first line
    if len(instr_lines[0]) > 100:
        lines.append(f"#              {instr_lines[0][100:200]}")

    # Add remaining lines as comments (truncate at 5 lines for brevity)
    for extra_line in instr_lines[1:5]:
        lines.append(f"#              {extra_line[:100]}")
    if len(instr_lines) > 5:
        lines.append(f"#              ... ({len(instr_lines) - 5} more lines)")

    lines.append(f"# {'-' * 70}")

    if not parsed.get("valid"):
        lines.append("# ⚠️  Could not parse this instruction - manual review required")
        lines.append(f'echo "MANUAL: {first_line[:60]}..."')
        return "\n".join(lines)

    action = parsed["action"]

    if action == "EXTRACT":
        src = f"{project_root}/{parsed['source_file']}"
        tgt = f"{project_root}/{parsed['target_file']}"
        start = parsed["start_line"]
        end = parsed["end_line"]
        funcs = ", ".join(parsed["functions"])

        lines.append(f"# Extracting: {funcs}")
        lines.append(f"# From: {src} (lines {start}-{end})")
        lines.append(f"# To:   {tgt}")
        lines.append("")
        lines.append(f"# Append lines {start}-{end} from source to target")
        lines.append(f'sed -n \'{start},{end}p\' "{src}" >> "{tgt}"')
        lines.append("")

    elif action == "DELETE":
        file = f"{project_root}/{parsed['file']}"
        start = parsed["start_line"]
        end = parsed["end_line"]
        reason = parsed.get("reason", "")

        lines.append(
            f"# Delete lines {start}-{end}" + (f" ({reason})" if reason else "")
        )
        lines.append("# Creating backup first")
        lines.append(f'cp "{file}" "{file}.bak"')
        lines.append(f"# Delete lines {start} to {end}")
        lines.append(f"sed -i '' '{start},{end}d' \"{file}\"")
        lines.append("")

    elif action == "ADD":
        file = f"{project_root}/{parsed['file']}"
        line = parsed["line"]
        content = parsed["content"].replace("'", "'\"'\"'")  # Escape single quotes

        lines.append(f"# Add content at line {line}")
        lines.append(f"# Content: {parsed['content'][:50]}...")
        lines.append(f"sed -i '' '{line}i\\")
        lines.append(f"{content}")
        lines.append(f'\' "{file}"')
        lines.append("")

    elif action == "ADD_AFTER":
        file = f"{project_root}/{parsed['file']}"
        after = parsed["after_line"]

        lines.append(f"# Add after line {after} in {file}")
        lines.append(f"# What: {parsed['what']}")
        lines.append(
            f'echo "MANUAL: Add {parsed["what"]} after line {after} in {file}"'
        )
        lines.append("")

    elif action == "CREATE":
        file = f"{project_root}/{parsed['file']}"

        lines.append(f"# Create new file: {file}")
        lines.append(f"# Content: {parsed['content_desc'][:60]}...")
        lines.append(f'mkdir -p "$(dirname "{file}")"')
        lines.append(f'touch "{file}"')
        lines.append(f'echo "CREATED: {file} - populate with extracted content"')
        lines.append("")

    elif action == "MODIFY":
        file = f"{project_root}/{parsed['file']}"
        start = parsed["start_line"]
        end = parsed["end_line"]

        lines.append(f"# Modify {parsed['function']} (lines {start}-{end})")
        lines.append(f"# Change: {parsed['description'][:60]}...")
        lines.append(f'echo "MANUAL MODIFY: {parsed["function"]} in {file}"')
        lines.append(f'echo "  Lines: {start}-{end}"')
        lines.append(f'echo "  Change: {parsed["description"][:60]}..."')
        lines.append("")

    elif action == "MODIFY_SIMPLE":
        lines.append(f"# Modify: {parsed['target']}")
        lines.append(f"# Description: {parsed['description'][:60]}...")
        lines.append(f'echo "MANUAL: Modify {parsed["target"]}"')
        lines.append("")

    elif action == "VERIFY":
        lines.append("# Verification step")
        lines.append(f"echo 'VERIFY: {parsed['description'][:60]}...'")
        lines.append("")

    return "\n".join(lines)


def generate_refactor_script(
    instructions: list[str],
    output_path: str | None = None,
    project_root: str = ".",
) -> str:
    """Generate a shell script from impl-agent instructions.

    Args:
        instructions: List of instruction strings from implementation_plan.instructions
        output_path: Where to save the script (auto-generates if None)
        project_root: Root directory for file paths

    Returns:
        Path to the generated script
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_path is None:
        output_dir = Path(project_root) / "outputs" / "scripts"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"refactor_{timestamp}.sh")

    script_lines = [
        "#!/bin/bash",
        f"# Generated by impl-agent executor on {timestamp}",
        "# Review carefully before running!",
        "",
        "set -e  # Exit on error",
        "",
        f'PROJECT_ROOT="{project_root}"',
        'cd "$PROJECT_ROOT"',
        "",
        "# ==========================================================================",
        f"# REFACTOR SCRIPT - {len(instructions)} instructions",
        "# ==========================================================================",
        "",
    ]

    # Parse all instructions first
    parsed_instructions = []
    for i, instr in enumerate(instructions, 1):
        # Clean up instruction (remove markdown artifacts)
        clean_instr = instr.strip()
        if clean_instr.startswith("```"):
            continue  # Skip code blocks

        parsed = parse_instruction(clean_instr)
        parsed["index"] = i
        parsed_instructions.append(parsed)

    # CRITICAL: Reorder DELETEs to process highest line numbers first per file
    # This prevents line number shifts from breaking subsequent deletes
    delete_instructions = [
        p for p in parsed_instructions if p.get("action") == "DELETE"
    ]
    non_delete_instructions = [
        p for p in parsed_instructions if p.get("action") != "DELETE"
    ]

    # Sort DELETEs by (file, -start_line) so highest lines deleted first
    delete_instructions.sort(
        key=lambda x: (x.get("file", ""), -(x.get("start_line", 0)))
    )

    # Group: non-deletes first (in original order), then sorted deletes
    reordered = non_delete_instructions + delete_instructions

    # Add warning about reordering if we had deletes
    if delete_instructions:
        script_lines.append(
            "# ⚠️  DELETE instructions reordered: highest line numbers first"
        )
        script_lines.append(
            "#    This prevents line shift issues during multi-delete operations"
        )
        script_lines.append("")

    # Convert to shell commands with new step numbers
    for i, parsed in enumerate(reordered, 1):
        script_lines.append(f"# Step {i}/{len(reordered)}")
        script_lines.append(instruction_to_shell(parsed, "$PROJECT_ROOT"))

    # Add summary
    valid_count = sum(1 for p in reordered if p.get("valid"))
    manual_count = len(reordered) - valid_count

    script_lines.extend(
        [
            "",
            "# ==========================================================================",
            "# SUMMARY",
            "# ==========================================================================",
            f"# Total instructions: {len(instructions)}",
            f"# Automated: {valid_count}",
            f"# Manual review needed: {manual_count}",
            "",
            'echo ""',
            'echo "Refactor script completed."',
            f'echo "  {valid_count} automated steps"',
            f'echo "  {manual_count} manual steps (marked with MANUAL:)"',
            "",
        ]
    )

    # Write script
    script_content = "\n".join(script_lines)
    Path(output_path).write_text(script_content)
    Path(output_path).chmod(0o755)  # Make executable

    # Generate companion tasks file for manual/LLM handling
    tasks_path = output_path.replace(".sh", "_tasks.md")
    tasks_content = generate_tasks_file(reordered, project_root, timestamp)
    Path(tasks_path).write_text(tasks_content)

    logger.info(f"Generated refactor script: {output_path}")
    logger.info(f"Generated tasks file: {tasks_path}")
    return output_path


def generate_tasks_file(
    parsed_instructions: list[dict[str, Any]],
    project_root: str,
    timestamp: str,
) -> str:
    """Generate a markdown file with full task details for manual/LLM handling.

    Args:
        parsed_instructions: List of parsed instruction dicts (already reordered)
        project_root: Root directory for file paths
        timestamp: Timestamp for the file header

    Returns:
        Markdown content as string
    """
    lines = [
        f"# Refactor Tasks - {timestamp}",
        "",
        "Tasks for manual review or LLM execution. Full instruction text preserved.",
        "",
        "---",
        "",
    ]

    # Separate automated vs manual tasks
    automated = [p for p in parsed_instructions if p.get("valid")]
    manual = [p for p in parsed_instructions if not p.get("valid")]

    # Summary
    lines.extend(
        [
            "## Summary",
            "",
            f"- **Total tasks**: {len(parsed_instructions)}",
            f"- **Automated** (in shell script): {len(automated)}",
            f"- **Manual/LLM** (below): {len(manual)}",
            "",
            "---",
            "",
        ]
    )

    # Manual tasks section (full detail)
    if manual:
        lines.extend(
            [
                "## Manual Tasks",
                "",
                "These tasks require manual implementation or LLM assistance.",
                "",
            ]
        )

        for i, task in enumerate(manual, 1):
            # Extract action keyword from instruction start
            original = task.get("original", "")
            action = task.get("action")
            if not action:
                # Try to extract from first word
                first_word = original.split()[0].upper() if original else "UNKNOWN"
                action = first_word.rstrip(":")
            lines.append(f"### Task {i}: {action}")
            lines.append("")
            lines.append("**Full Instruction:**")
            lines.append("```")
            lines.append(task["original"])
            lines.append("```")
            lines.append("")

            # Add helpful context based on action type
            if "file" in task:
                lines.append(f"**Target file**: `{project_root}/{task['file']}`")
            if "line" in task:
                lines.append(f"**At line**: {task['line']}")
            lines.append("")
            lines.append("---")
            lines.append("")

    # Automated tasks reference (brief)
    if automated:
        lines.extend(
            [
                "## Automated Tasks (Reference)",
                "",
                "These are handled by the shell script. Listed here for completeness.",
                "",
                "| # | Action | Target | Lines |",
                "|---|--------|--------|-------|",
            ]
        )

        for i, task in enumerate(automated, 1):
            action = task.get("action", "?")
            target = task.get("file", task.get("source_file", "?"))
            if len(target) > 40:
                target = "..." + target[-37:]
            start = task.get("start_line", "")
            end = task.get("end_line", "")
            line_range = f"{start}-{end}" if start and end else ""
            lines.append(f"| {i} | {action} | `{target}` | {line_range} |")

        lines.append("")

    return "\n".join(lines)


def extract_instructions_from_output(output_text: str) -> list[str]:
    """Extract instructions list from impl-agent raw output.

    Args:
        output_text: Raw output from impl-agent run

    Returns:
        List of instruction strings
    """
    # Try to find implementation_plan.instructions in the output
    # Format: instructions=['...', '...'] test_instructions=[...]

    # Look for instructions= and capture until '] test_instructions=' or '] risks='
    # Use non-greedy matching and explicit field boundary
    match = re.search(
        r"instructions=(\[.*?\])\s+(?:test_instructions=|risks=)",
        output_text,
        re.DOTALL,
    )
    if match:
        # Parse the list content (remove outer brackets)
        list_str = match.group(1)
        # Split by quoted strings - handle escaped quotes
        instructions = re.findall(r"'((?:[^'\\]|\\.)*)'", list_str)
        if instructions:
            # Unescape newlines and quotes
            return [i.replace("\\n", "\n").replace("\\'", "'") for i in instructions]

    # Alternative: look for numbered instructions
    numbered = re.findall(r"^\d+\.\s*(.+)$", output_text, re.MULTILINE)
    if numbered:
        return numbered

    return []


def main():
    """CLI entry point for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python impl_executor.py <impl-agent-output.txt>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_text = Path(input_file).read_text()

    instructions = extract_instructions_from_output(output_text)
    if not instructions:
        print("No instructions found in output")
        sys.exit(1)

    print(f"Found {len(instructions)} instructions")

    script_path = generate_refactor_script(
        instructions,
        project_root=str(Path.cwd()),
    )
    print(f"Generated script: {script_path}")


if __name__ == "__main__":
    main()

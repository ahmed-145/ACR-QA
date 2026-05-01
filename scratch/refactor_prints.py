import os
import glob
import re

files_to_process = ["CORE/config_loader.py", "CORE/utils/rate_limiter.py"] + glob.glob("scripts/*.py")

for file_path in files_to_process:
    if not os.path.exists(file_path):
        continue
    with open(file_path, "r") as f:
        content = f.read()

    # If no print statement or it's console.print
    # Actually just replace `print(` with `logger.info(` if it's not `console.print(`

    # Simple check
    if not re.search(r"(^|[^a-zA-Z0-9_.])print\(", content):
        continue

    print(f"Processing {file_path}")

    lines = content.split("\n")
    new_lines = []
    has_print = False

    for line in lines:
        # replace `print(` with `logger.info(` if not preceded by word or dot
        new_line = re.sub(r"(^|[^a-zA-Z0-9_.])print\(", r"\1logger.info(", line)

        # specific cases like error prints
        if (
            'logger.info(f"❌' in new_line
            or 'logger.info("❌' in new_line
            or 'logger.info(f"⚠️' in new_line
            or 'logger.info("⚠️' in new_line
            or "error" in new_line.lower()
            and "logger.info" in new_line
        ):
            new_line = new_line.replace("logger.info(", "logger.error(")

        if new_line != line:
            has_print = True
        new_lines.append(new_line)

    if has_print:
        # Add import logging and logger setup if not present
        new_content = "\n".join(new_lines)
        if "import logging" not in new_content:
            # find first import
            insert_idx = 0
            for i, line in enumerate(new_lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_idx = i
                    break

            # insert there
            imports = ["import logging", "", "logger = logging.getLogger(__name__)", ""]
            new_lines = new_lines[:insert_idx] + imports + new_lines[insert_idx:]

        elif "logger = logging.getLogger" not in new_content:
            # logging is imported but logger is not defined
            # find import logging
            insert_idx = 0
            for i, line in enumerate(new_lines):
                if "import logging" in line:
                    insert_idx = i + 1
                    break
            new_lines.insert(insert_idx, "logger = logging.getLogger(__name__)")

        with open(file_path, "w") as f:
            f.write("\n".join(new_lines))

print("Done")

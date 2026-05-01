import glob
import re

for file_path in glob.glob("scripts/*.py") + ["CORE/config_loader.py", "CORE/utils/rate_limiter.py"]:
    with open(file_path, "r") as f:
        lines = f.read().split("\n")

    logger_line_idx = -1
    last_import_idx = -1

    for i, line in enumerate(lines):
        if line.startswith("logger = logging.getLogger"):
            logger_line_idx = i
        elif line.startswith("import ") or line.startswith("from "):
            last_import_idx = i

    if logger_line_idx != -1 and last_import_idx != -1 and logger_line_idx < last_import_idx:
        # We need to move logger_line to after last_import
        # Wait, if there are multiple imports interspersed, let's just find all logger lines, remove them, and insert one after the last import.
        logger_lines = [line for line in lines if line.startswith("logger = logging.getLogger")]
        lines = [line for line in lines if not line.startswith("logger = logging.getLogger")]

        # recalculate last import
        last_import_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                last_import_idx = i

        lines.insert(last_import_idx + 1, "")
        lines.insert(last_import_idx + 2, logger_lines[0])
        lines.insert(last_import_idx + 3, "")

        with open(file_path, "w") as f:
            f.write("\n".join(lines))

print("Fixed E402")

import glob
import json
import sys

if len(sys.argv) < 2:
    print(f"Usage: python {sys.argv[0]} <file_path>")
    sys.exit(1)
file_path = sys.argv[1]

print(f"Loading glob list from {file_path}")
with open(file_path, "r") as f:
    data = json.load(f)

print(f"Searching for {len(data['items'])} service configs...")
for i, item in enumerate(data['items']):
    print(f"[{i+1}] {item['name']} ({item['type']})", end='')
    paths = [glob.glob(pattern) for pattern in item['glob']]
    paths = [path for sublist in paths for path in sublist]  # Flatten
    paths = list(set(paths))  # Remove duplicates
    if paths:
        print(f" - {len(paths)}:")
        for path in paths:
            print(f"  - {path}")
    else:
        print(" - 0")
import yaml
import json
import csv
import os

target_dir = 'lib'

# Get all glob files
globs = []
for file in os.listdir("globs"):
    if file.endswith(".yaml"):
        globs.append(file.split(".")[0])
print(f'Loaded {len(globs)} glob files:')
print('- ' + '\n- '.join(globs))


def generate_alternatives(glob_file):
    source_path = f"globs/{glob_file}.yaml"
    with open(f"{source_path}", "r") as f:
        data = yaml.safe_load(f)
        
    count = len(data['items'])
    max_globs = max(len(item['glob']) for item in data['items'])

    # YAML
    with open(f"{target_dir}/{glob_file}.yaml", "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    # JSON
    with open(f"{target_dir}/{glob_file}.json", "w") as f:
        json.dump(data, f, indent=4, sort_keys=False)

    # TXT lines
    with open(f"{target_dir}/{glob_file}.txt", "w") as f:
        for item in data['items']:
            for glob in item['glob']:
                f.write(glob + "\n")

    # CSV
    with open(f"{target_dir}/{glob_file}.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(['name', 'type'] + [f'glob {i+1}' for i in range(max_globs)])
        for item in data['items']:
            w.writerow([item['name'], item['type']] + [glob for glob in item['glob']])

    # Toml
    with open(f"{target_dir}/{glob_file}.toml", "w") as f:
        f.write("[items]\n")
        for item in data['items']:
            f.write(f'[[items]]\n')
            f.write(f'name = "{item["name"]}"\n')
            f.write(f'type = "{item["type"]}"\n')
            f.write(f'glob = [\n')
            for glob in item['glob']:
                f.write(f'    "{glob}",\n')
            f.write(f']\n\n')
    print(f"{source_path} -> {count} (YAML, JSON, CSV, TXT, TOML)")
            
for glob in globs:
    generate_alternatives(glob)
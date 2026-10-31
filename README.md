# GlobLib

A list of glob search patterns for finding files on Linux systems.

Getting a list of installed applications for example on Linux can be a useful source of information on CTFs and penetration testing engagements. However, it's not trivial to find all of them, as they can be scattered in many places: installed via the default package manager, snap, flatpak, dpkg, custom installer. In some cases we might even be interested in applications that used to be installed but have been removed and their configuration or backup remains. This library contains lists of glob patterns in 5 formats to be loaded into custom software or ran using `globlib.py`.

## Usage

Download
```sh
git clone https://github.com/dubniczky/GlobLib
cd GlobLib
```

Run
```sh
python globlib.py secrets
python globlib.py secrets databases -r /home -e node_modules
python globlib.py all --readable --newest -q
```
```
  GigaGlobs  /  ·  secrets  · 38 entries

  secrets  Common files used to store secrets
  ● AWS  ini · 1 match
       116 B  /home/user/.aws/credentials
  ● SSH keys  custom · 2 matches
       411 B  /home/user/.ssh/id_ed25519
        98 B  /home/user/.ssh/id_ed25519.pub

  ✓ 3 matches in 2 entries  · 812,331 paths scanned in 4.1s
```

| Option | Description |
|---|---|
| `-r`, `--root DIR` | Folder to search from (default: `/`) |
| `-e`, `--exclude TEXT` | Drop matches whose path contains `TEXT` (repeatable) |
| `-E`, `--regex REGEX` | Drop matches whose path matches `REGEX` (repeatable) |
| `-n`, `--name TEXT` | Only run entries whose name contains `TEXT` |
| `-t`, `--type TYPE` | Only run entries of this type (repeatable) |
| `-l`, `--list` | Show available lists, or the entries of the given lists, without searching |
| `-q`, `--quiet` | Print only the matched paths |
| `-f`, `--format` | Output format: `text` (default), `json` or `csv` |
| `--readable` / `--writable` | Only show paths the current user can read / write |
| `--min-size` / `--max-size SIZE` | Skip files smaller / larger than `SIZE` (e.g. `1K`, `10M`) |
| `--newest` | Sort matches from newest to oldest and show when they were last modified |
| `--no-default-excludes` | Also search `/proc`, `/sys`, `/dev` and `/run` |
| `--no-color` | Disable colored output (also respects `NO_COLOR`) |

## How it works

The `lib` folder contains a list of globs in multiple formats. These specify the patterns to search. Current formats:
- `yaml` (original)
- `csv`
- `json`
- `toml`
- `txt` (one glob each line)


Example glob in YAML:

```yaml
- name: "Apache2"
  type: ini
  glob:
  - "**/apache2/**/apache2.conf"
  - "**/apache2/**/httpd.conf"
  - "**/httpd/**/httpd.conf"
```

These can be ran on Linux systems via code or bash. Running on bash:

```sh
# start bash
bash
# enable ** recursive glob search in current shell
shopt -s globstar
# search for a glob
ls **/httpd/**/httpd.conf
```

Each `*` matches any character except `/`, while `**` matches any character, effectively traversing all directories. These patterns can be ran on the system searching for files that the current user has access to.
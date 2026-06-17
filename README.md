# GlobLib

A list of glob search patterns for finding files in Linux systems.

Getting a list of installed applications on Linux can be a useful source of information on CTFs and peentration testing engagements. However, it's not trivial to find all the installed applications, as they can be scattered in many places. Installed via the default package manager, snap, flatpak, dpkg, custom installer. In some cases we might even be interested in applications that used to be installed but have been removed and their configuration remains. This library contains more than 150 glob patterns to find such configuration files. These files may also contain useful information themselves.

## Usage

The `globs` folder contains a list of globs in YAML format. These specify search patterns to find configuration files of many applications. The `alternates` folder has the same patterns in different formats converted from the YAML. Current formats:
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

Alternatively, you can use the python script that loads the glob and performs the search:
```sh
python search.py alternates/config.json
```
```
Loading glob list from globs/config.json
Searching for 157 service configs...
[1] Lampp (ini) - 0
[2] Apache2 (ini) - 0
[3] NGINX (dsl) - 0
[4] WordPress (php) - 0
[5] MySQL (ini) - 0
[6] Redis (ini) - 0
[7] PostreSQL (ini) - 0
[8] SSH (custom) - 0
[9] Samba (ini) - 0
[10] Confluence (xml) - 0
[11] Tomcat (xml) - 0
[12] Docker (json) - 0
[13] Docker Compose (yaml) - 0
[14] Memcached (ini) - 0
[15] PHP (ini) - 0
[16] PHP-FPM (ini) - 0
[17] Postfix (ini) - 1:
  - /etc/postfix/main.cf
[18] Dovecot (ini) - 0
...
```

# config_file_compare
FACT_core comparison plugin for configuration files

## About
This plugin allows comparison of two (or more) configuration files. It handles identifying, parsing, and displaying config file key/value pairs for a variety of configuration file types.

### Planned supported file types
- generic config files (key with value separated by space or simple lists)
- conf, cnf
- ini
- toml
- xml
- json

### Comment identification
Automatically handles comments by ignoring lines starting with `#` or `;`

## Installation and updates
This is specific for the compare plugin, not for the FACt install!  
Can be added as a submodule to an existing FACT_core installation:
```bash
git submodule add git@github.com:f-ame/FACT_plugin_compare_config.git src/plugins/compare/config_file_compare
```
*\*Can't use https password authentication for submodules, so you may need to set up SSH keys*

Afterwards, when pulling, use `--recurse-submodules` to also pull the latest changes for the plugin:
```bash
git pull --recurse-submodules
```

Or alternatively pull the plugin separately:
```bash
cd src/plugins/compare/config_file_compare
git pull
```

## Resources
- FACT_core repository https://github.com/fkie-cad/FACT_core
- Coding guidelines https://github.com/fkie-cad/FACT_core/wiki/coding-guidelines
- FACT_core compare plugin development documentation https://github.com/fkie-cad/FACT_core/wiki/compare-plugin-development
- Jinja Templating for view/ https://jinja.palletsprojects.com/en/stable/
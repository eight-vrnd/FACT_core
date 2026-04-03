# config_file_compare
FACT_core comparison plugin for configuration files

## About
This plugin allows comparison of configuration files. It handles identifying, parsing, and displaying config file key/value pairs for a variety of configuration file types.

### Supported file types
- generic config files (key=value pairs)
- composite (dual key) config files (key1 key2=value)
- yaml
- toml
- json
- csv
- lists

### Comment identification
Automatically handles comments by ignoring lines starting with `#` or `;`

## Installation
This plugin requires placement in the directory `src/plugins/compare/file_config/` of the FACT_core directory. It contains the following files and directories:
```
.
├── code
│   ├── file_config.py
│   ├── __init__.py
│   ├── internal
│   │   └── ac.py
├── __init__.py
├── README.md
├── test
│   ├── data
│   │   └── <test data files>
│   ├── __init__.py
│   └── test_plugin_file_config.py
└── view
    └── file_config.html
```
Additionally, it uses jinja templates implemented in the following files which have to either be merged or replaced using the files from this repository:
- `src/web_interface/filter.py`
- `src/web_interface/components/jinja_filter.py`

(Adds function for unsorted collapsible list display in the front end)

## Resources
- FACT_core repository https://github.com/fkie-cad/FACT_core
- Coding guidelines https://github.com/fkie-cad/FACT_core/wiki/coding-guidelines
- FACT_core compare plugin development documentation https://github.com/fkie-cad/FACT_core/wiki/compare-plugin-development
- Jinja Templating for view/ https://jinja.palletsprojects.com/en/stable/
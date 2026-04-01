from __future__ import annotations

import os
import json
import re

import toml

from itertools import combinations
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from compare.PluginBase import CompareBasePlugin
from helperFunctions.compare_sets import iter_element_and_rest, remove_duplicates_from_list
from helperFunctions.data_conversion import convert_uid_list_to_compare_id
from helperFunctions.uid import is_uid, is_list_of_uids
from objects.firmware import Firmware
from objects.file import FileObject

if TYPE_CHECKING:
    from objects.file import FileObject

# IDE specific settings
# pyright: reportOperatorIssue=false
# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

class ComparePlugin(CompareBasePlugin):
    '''
    This plugin allows comparison of two (or more) configuration files. It handles identifying, parsing, and displaying config file key/value pairs for a variety of configuration file types
    '''

    NAME = 'file_config'
    DEPENDENCIES = ['file_type']
    VERSION = '0.0.3'
    FILE = os.path.basename(__file__)

    def compare_function(self, fo_list, dependency_results: dict[str, dict]) -> dict[str, dict]:
        all_uids = self._get_included_uids(fo_list)
        file_objects = self._get_objects_from_uids(all_uids)
        config_files = self._filter_config_files(file_objects)
        config_file_uids = self._get_uid_list_from_file_objects(config_files)
        parsed_config_parameters = self._parse_config_from_fo_list(config_files)
        
        #  get virtual file paths for all uids of filtered config files
        config_file_uids_with_vfps = self._get_file_vfp_from_uid_list(config_file_uids)
        # {<uid>: {<rootuid>: [list of vfp strings]}}
        
        results = {}
        # config_file_uids_with_vfps = {'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855_0': {'firmware1/config/example.config': [...]}}
        for uid, vfp_dict in config_file_uids_with_vfps.items():
            for vfp, rootuid_list in vfp_dict.items():
                # table row title should be the vfp of this config file
                table_row_title = vfp
                if results[table_row_title] is None:
                    results[table_row_title] = {}
                fo = self._get_objects_from_uids([uid])[0]
                firmware_rootuid = self._get_rootuid_for_file_object(fo)
                # transform parsed_config_parameters[uid] to list of strings, each string being "key: value" for table view display
                if uid in parsed_config_parameters:
                    config_parameters_str_list = [f"{key}: {value}" for key, value in parsed_config_parameters[uid].items()]
                else:
                    config_parameters_str_list = []
                results[table_row_title][firmware_rootuid] = config_parameters_str_list
                results[table_row_title].update({'collapse': 'True'}) # collapse config parameters in table view by default since there can be a lot of them
        
        # strip vfp key down to just the file name for display in the view, but keep the full vfp in the debug info
        results_stripped_vfp = {}
        for vfp, firmware_dict in results.items():
            file_name = vfp.split('/')[-1]
            results_stripped_vfp[file_name] = firmware_dict
        results = results_stripped_vfp

        # # Debug - output all function outputs to compare with test setup
        debug = {
            'config_file_uids': {
                'all': ['config file uids:', str(config_file_uids)],
                'collapse': False
            },
            'all_uids': {
                'all': ['all uids:', str(all_uids)],
                'collapse': False
            },
            'config_file_uids_with_vfps': {
                'all': ['config file uids with vfps:', str(config_file_uids_with_vfps)],
                'collapse': False
            },
             'parsed_config_parameters': {
                'all': ['parsed config:', str(parsed_config_parameters)],
                'collapse': False
            }
        }
        return results_stripped_vfp
    
    def _get_rootuid_for_file_object(self, fo: FileObject) -> str | None:
        """Get the rootuid of the firmware object that a file object belongs to

        Args:
            fo (FileObject): File object to get rootuid for

        Returns:
            str | None: Rootuid of the firmware object that the file object belongs to, or None if it cannot be determined
        """
        # Check if root_uid attribute is set on file object
        if hasattr(fo, 'root_uid') and fo.root_uid:
            return fo.root_uid
    
    def _parse_config_from_fo_list(self, fo_list: list[FileObject]) -> dict[str, dict[str, str]]:
        """Parse config parameters from a list of file objects and return a dict of file object uid to dict of key value strings

        Args:
            fo_list (list[FileObject]): List of file objects to parse

        Returns:
            dict[str, dict[str, str]]: Dict of file object uid to dict of key value strings
                e.g. {
                    'uid_1': {'key1': 'value1', 'key2': 'value2'},
                    'uid_2': {'key1': 'value3', 'key2': 'value4'}
                }
        """
        uid_with_contents = {}
        
        for fo in fo_list:            
            # Check which config type the file is
            config_file_type = self._determine_config_type(fo)
            
            # Parse config parameters from file binary using the appropriate parsing strategy for the config type
            # keys: fo.uid: self._parse_config_from_binary(fo.binary, filetype=config_file_type)
            uid_with_contents[fo.uid] = self._parse_config_from_binary(fo.binary, filetype=config_file_type)
        
        return uid_with_contents

    def _determine_config_type(self, fo: FileObject) -> str | None:
        """Determine the config file type based on file extension and file type analysis results

        Args:
            fo (FileObject): File object to determine config type for

        Returns:
            str | None: Config file type. Options: 'toml', 'xml', 'dualkey', or None if type cannot be determined
        """
        # Check file extension first
        if fo.file_name.endswith('.toml'):
            return 'toml'
        elif fo.file_name.endswith('.xml'):
            return 'xml'
        elif fo.file_name.endswith('.csv'): 
            return 'csv'
        
        # Check file type analysis results for indicators of config file type (e.g. "application/toml" mime type or "xml" in file type strings)
        # file_type ends in xml or csv or toml? set type based on that
        if 'file_type' in fo.processed_analysis and 'mime' in fo.processed_analysis['file_type']:
            mime = fo.processed_analysis['file_type']['mime']
            if mime.endswith('toml'):
                return 'toml'
            elif mime.endswith('xml'):
                return 'xml'
            elif mime.endswith('csv'):
                return 'csv'
            
        # Regex for file content indicators of config file type (e.g. presence of "<tags>" for xml files or presence of "[headers]" for toml files)
        if fo.binary is None and fo.file_path is not None:
            fo.create_binary_from_path() # if only a path is given, create binary using the built-in method
        elif fo.file_path is None:
            return None # no file contents to analyze

        file_content_ascii = fo.binary.decode('ascii', errors='ignore')
        if re.search(r'<\s*[^>]+>', file_content_ascii): # crude regex to check for presence of <tags> which may indicate an xml file
            return 'xml'
        elif re.search(r'^\s*\[.*\]\s*$', file_content_ascii, re.MULTILINE): # crude regex to check for presence of [headers] which may indicate a toml file
            return 'toml'
        # csv
        elif re.search(r'^[^#;\s]+?,[^#;\s]+', file_content_ascii, re.MULTILINE): # crude regex to check for presence of key,value pairs separated by a comma which may indicate a csv file
            return 'csv'
        
        # Dual key
        # Check for lines which match "key1 key2 value" or "key1 key2=value" pattern which may indicate a dual key config file
        # value may contain spaces, but key1 and key2 should not contain spaces
        # if there are multiple lines without comment indicators that do not match, use default parsing strategy instead because it might be a config file with values that contain spaces
        invalid_lines = 0 # e.g. "key value" with no third part
        dualkey_lines = 0
        comment_lines = 0
        for line in file_content_ascii.splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line:
                continue
            elif line.startswith(('#', ';')):
                comment_lines += 1
                continue
            # check for just "key value" lines
            # careful not to match "key1 key2=value"
            # also include quoted values with ' or " e.g. k1 "value with spaces"  key1 ='value with spaces'
            if (re.match(r'^[^\s]+?\s+[^\s]+?$', line) or re.match(r'^[^\s]+?\s+[^\s]+?\s+["\'].*["\']$', line)) and not re.match(r'^\s*(\S+)\s+([^=\s]+)=(.+)$', line): # crude regex to check for "key value" pattern without an equals sign which may indicate a dual key config file, but exclude lines that match the "key1 key2=value" pattern
                invalid_lines += 1
                break
            elif re.match(r'^[^\s]+?\s+[^\s]+?\s+.+$', line): # crude regex to check for "key1 key2 value" pattern
                dualkey_lines += 1
            elif re.match(r'^[^\s]+?\s+[^\s]+?=.+$', line): # crude regex to check for "key1 key2=value" pattern
                dualkey_lines += 1
        
        if invalid_lines == 0 and dualkey_lines > 0:
            return 'dualkey'

        # Fallback to default parsing strategy
        return None

    def _filter_config_files(self, file_objects: list[FileObject]) -> list[FileObject]:
        """Return a list of file objects that are considered a config file

        Args:
            file_objects (list[FileObject]): File objects to check for config files

        Returns:
            list[FileObject]: File objects that are considered config files
        """
        config_files = []
        for fo in file_objects:
            if self._is_config_file(fo):
                config_files.append(fo)
        return config_files

    def _get_uid_list_from_file_objects(self, file_objects: list[FileObject]) -> list[str]:
        """Return a list of uid strings from a list of file

        Args:
            file_objects (list[FileObject]): List of file ob

        Returns:
            list[str]: List of uids of file objects
        """
        return [fo.uid for fo in file_objects]

    @staticmethod
    def _get_included_uids(fo_list: list[FileObject]) -> list[str]:
        """Returns a list of uids of all included files of all firmware objects

        Args:
            fo_list (list[FileObject]): Firmware object list.

        Returns:
            list[str]: List of uids of all included files of all firmware objects
        """
        if not fo_list:
            return []
        all_uids = set()
        #FIXME Firmware objects contain list_of_all_included_files which is a list of uids of all included files in the firmware object. If it's not set, use recursive method to get files from files_included instead.
        for fo in fo_list:
            if hasattr(fo, 'list_of_all_included_files'):
                all_uids.update(fo.list_of_all_included_files)
        return list(all_uids)

    def _get_objects_from_uids(self, uid_list: list[str]) -> list[FileObject]:
        """Get list of file objects from a list of sets of uids

        Args:
            uid_list (list[str]): List of uids

        Returns:
            list[FileObject]: List of file objects each with their respective attributes
        """
        file_objects = self.database.get_objects_by_uid_list(uid_list)
        return file_objects

    def _get_file_vfp_from_uid_list(self, uid_list: list[str]) -> dict[str, dict[str, list[str]]]:
        uid_vfp = self.database.get_vfps_for_uid_list(uid_list)
        return uid_vfp
    
    def _is_config_file(self, fo: FileObject) -> bool:
        # File extension
        extension_whitelist = ['config', 'conf', 'cfg', 'ini', 'toml', 'yaml', 'yml', 'xml']
        extension_blacklist = ['exe', 'dll', 'bin', 'so', 'dylib', 'elf', 'py', 'js', 'c', 'cpp', 'h', 'sh', 'bat']
        if any(fo.file_name.endswith(ext) for ext in extension_whitelist):
            return True
        elif any(fo.file_name.endswith(ext) for ext in extension_blacklist):
            return False
        
        # Check MIME type and filter out application/* file types
        # Whitelist is checked before blacklist!
        mime_whitelist_startswith = []
        mime_whitelist = ['text/plain', 'text/x-ini', 'text/csv', 'application/toml', 'application/xml', ' application/json', 'text/xml', 'application/xml']
        mime_blacklist_startswith = ['application/','image/', 'audio/', 'video/', 'font/']
        mime_blacklist = ['text/css', 'text/html', 'text/javascript']
        if 'file_type' in fo.processed_analysis and 'mime' in fo.processed_analysis['file_type']:
            mime = fo.processed_analysis['file_type']['mime']
            if any(mime.startswith(prefix) for prefix in mime_whitelist_startswith) or mime in mime_whitelist:
                return True
            elif any(mime.startswith(prefix) for prefix in mime_blacklist_startswith) or mime in mime_blacklist:
                return False
        
        # Ensure binary 
        if fo.binary is None and fo.file_path is not None:
            fo.create_binary_from_path() # if only a path is given, create binary using the built-in method
        elif fo.file_path is None:
            return False # no file contents to analyze

        # Get file content as ascii string
        file_content_binary = fo.binary
        try:
            file_content_ascii = file_content_binary.decode('ascii', errors='ignore')
        except:
            return False

        # Empty file handling
        if file_content_ascii.strip() == '':
            return False

        # Comment indicator characters for ignored lines
        comment_indicator_characters = ['#', ';']
        
        # Prevent script files (e.g. python or C programming snippets) from being identified as a false positive
        # get first 10 lines excluding comment lines
        first_lines = []
        for line in file_content_ascii.splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or any(line.startswith(char) for char in comment_indicator_characters):
                continue
            first_lines.append(line)
            if len(first_lines) >= 10:
                break
            
        # Check for common script file syntax that may indicate a script
        common_script_syntax = ['def ', 'function ', '#include ', 'import ', '{', '}', 'public ', 'private ', 'class ', 'console.log', 'printf(', 'System.out.println', 'echo ']
        if any(syntax in line for line in first_lines for syntax in common_script_syntax):
            return False
        
        # Parse key/value
        valid_key_value_pattern = re.compile(r'^[^#;\s]+?\s*[:=]\s*.+$')
        for line in file_content_ascii.splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or any(line.startswith(char) for char in comment_indicator_characters):
                continue
            if valid_key_value_pattern.match(line):
                return True

        # Parse dual key/value (e.g. "key1 key2 value")
        valid_key_value_pattern_no_first_word = re.compile(r'^[^\s]+?\s+[^#;\s]+?\s+.+$')
        for line in file_content_ascii.splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or any(line.startswith(char) for char in comment_indicator_characters):
                continue
            if valid_key_value_pattern_no_first_word.match(line):
                return True

        # Fallback
        return False

    def _parse_config_from_binary(self, binary_data: bytes, filetype: str | None = None) -> dict:
        """Return a dict of key value strings for a given binary string

        Args:
            binary_data (bytes): Binary data
            filetype (str | None): Optional file type to use for parsing strategy. Options: 'toml', 'xml', 'dualkey'

        Returns:
            dict: Dict of key value strings
        """
        # Empty file handling
        if binary_data == b'':
            return {}
        
        if binary_data is None:
            return {}
        
        try:
            file_content_ascii = binary_data.decode('ascii', errors='ignore')
        except:
            return {'Error': 'Unable to decode file content'}

        # Use best parsing strategy based on type
        if filetype == 'toml':
            return self._parse_helper_toml(binary_data)
        elif filetype == 'xml':
            return self._parse_helper_xml(binary_data)
        elif filetype == 'dualkey':
            return self._parse_helper_dualkey(binary_data)
        else:
            return self._parse_helper_default(binary_data)

    def _parse_helper_xml(self, binary_data: bytes) -> dict:
        """Parse an xml config file from binary data and return a dict of key value strings

        Args:
            binary_data (bytes): Binary data of the xml file

        Returns:
            dict: Dict of key value strings
        """
        # when the key is nested, include all parent keys in the key name (e.g. "parentkey childkey1 childkey2" for <parentkey><childkey1><childkey2>value</childkey2></childkey1></parentkey>)
        # also prevent order from being flipped by using a list of values for each key and keeping the order of the keys as they appear in the file
        try:
            file_content_ascii = binary_data.decode('ascii', errors='ignore')
            root = ET.fromstring(file_content_ascii)
            config_dict = {}
            def recursive_parse(element, parent_keys=[]):
                current_keys = parent_keys + [element.tag]
                if element.text and element.text.strip():
                    config_dict[' '.join(current_keys)] = element.text.strip()
                for child in element:
                    recursive_parse(child, current_keys)
            recursive_parse(root)
            return config_dict
        except Exception as e:
            print(f"Error parsing xml file: {e}")
            return {}

    def _parse_helper_toml(self, binary_data: bytes) -> dict:
        """Parse a toml config file from binary data and return a dict of key value strings

        Args:
            binary_data (bytes): Binary data of the toml file

        Returns:
            dict: Dict of key value strings
        """
        try:
            file_content_ascii = binary_data.decode('ascii', errors='ignore')
            parsed_toml = toml.loads(file_content_ascii)
            # flatten nested dicts by concatenating keys with a space (e.g. {'network': {'port': 8080}} becomes {'network port': 8080})
            def flatten_dict(d, parent_key=''):
                items = {}
                for k, v in d.items():
                    new_key = f"{parent_key} {k}".strip() if parent_key else k
                    if isinstance(v, dict):
                        items.update(flatten_dict(v, new_key))
                    else:
                        items[new_key] = v
                return items
            flattened_toml = flatten_dict(parsed_toml)
            # convert all values to strings for consistency with other parsing methods
            flattened_toml_str_values = {k: str(v) for k, v in flattened_toml.items()}
            return flattened_toml_str_values
        except Exception as e:
            print(f"Error parsing toml file: {e}")
            return {}

    def _parse_helper_default(self, binary_data: bytes) -> dict:
        """Parse a config file from binary data using the default parsing strategy and return a dict of key value strings

        Args:
            binary_data (bytes): Binary data of the config file

        Returns:
            dict: Dict of key value strings
        """
        # Comment indicator characters for ignored lines
        comment_indicator_characters = ['#', ';']

        config_dict = {}
        valid_key_value_pattern = re.compile(r'^[^#;\s]+?\s*[:=]\s*.+$')
        for line in binary_data.decode('ascii', errors='ignore').splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or any(line.startswith(char) for char in comment_indicator_characters):
                continue
            match = valid_key_value_pattern.match(line)
            if match:
                key, value = re.split(r'\s*[:=]\s*', line, maxsplit=1)
                config_dict[key] = value

        return config_dict

    def _parse_helper_dualkey(self, binary_data: bytes) -> dict:
        """Parse a config file from binary data using the default parsing strategy for dual key/value pairs and return a dict of key value strings

        Args:
            binary_data (bytes): Binary data of the config file

        Returns:
            dict: Dict of key value strings
        """
        # Comment indicator characters for ignored lines
        comment_indicator_characters = ['#', ';']

        config_dict = {}
        pattern_1 = re.compile(r'^[^\s]+?\s+[^#;\s]+?\s+.+$') # e.g. network key value potentially with spaces
        pattern_2 = re.compile(r'^\s*(\S+)\s+([^=\s]+)=(.+)$') # e.g. network key=value potentially with spaces
        for line in binary_data.decode('ascii', errors='ignore').splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or any(line.startswith(char) for char in comment_indicator_characters):
                continue
            match = pattern_2.match(line)
            if match:
                key1, key2, value = match.group(1), match.group(2), match.group(3).strip()
                config_dict[f"{key1} {key2}"] = value
            else:
                match = pattern_1.match(line)
                if match:
                    parts = line.split()
                    key1, key2, value = parts[0], parts[1], ' '.join(parts[2:])
                    config_dict[f"{key1} {key2}"] = value

        return config_dict

    def _parse_helper_csv(self, binary_data: bytes) -> dict:
        """Parse a csv config file from binary data and return a dict of key value strings

        Args:
            binary_data (bytes): Binary data of the csv file

        Returns:
            dict: Dict of key value strings
        """
        config_dict = {}
        for line in binary_data.decode('ascii', errors='ignore').splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line:
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                key = parts[0].strip()
                value = ','.join(parts[1:]).strip() # In case there are additional commas in the value
                config_dict[key] = value
        return config_dict

    def _parse_helper_yaml(self, binary_data: bytes) -> dict:
        """Parse a yaml config file from binary data and return a dict of key value strings

        Args:
            binary_data (bytes): Binary data of the yaml file

        Returns:
            dict: Dict of key value strings
        """
        # treats nestes keys as a composite key (e.g. "parentkey childkey1 childkey2" for parentkey:\n  childkey1:\n    childkey2: value)
        config_dict = {}
        current_parent_keys = []
        for line in binary_data.decode('ascii', errors='ignore').splitlines():
            line = line.rstrip() # Remove trailing whitespace but keep leading whitespace for indentation
            if not line or line.lstrip().startswith(('#', ';')):
                continue
            indent_level = len(line) - len(line.lstrip())
            key_value_part = line.lstrip()
            if ':' in key_value_part:
                key, value = key_value_part.split(':', 1)
                key = key.strip()
                value = value.strip()
                # Update current parent keys based on indentation level
                while current_parent_keys and current_parent_keys[-1][1] >= indent_level:
                    current_parent_keys.pop()
                current_parent_keys.append((key, indent_level))
                composite_key = ' '.join(k for k, _ in current_parent_keys)
                config_dict[composite_key] = value
        return config_dict
    
    def _parse_helper_list(self, binary_data: bytes) -> dict:
        """Parse a config file from binary data that does not contain key value pairs but rather a list of values (e.g. for config files that just contain a list of enabled features or filepaths) and return a dict with the list of values under a generic "list" key

        Args:
            binary_data (bytes): Binary data of the config file

        Returns:
            dict: Dict of key value strings
        """
        raise NotImplementedError()
from __future__ import annotations

import re
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

import toml
from pprint import pprint

from compare.PluginBase import CompareBasePlugin
from storage.binary_service import BinaryService

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
    VERSION = '0.1.0'
    FILE = __file__

    def compare_function(self, fo_list, dependency_results: dict[str, dict]) -> dict[str, dict]:
        self.binary_service = BinaryService()
        all_uids = self._get_included_uids(fo_list)
        file_objects = self._get_objects_from_uids(all_uids)
        config_files = self._filter_config_files(file_objects)
        parsed_config_parameters = self._parse_config_from_fo_list(config_files)
                
        results = {}
        for file_object in config_files: # file_object is a config file
            for root_uid, vfp in file_object.virtual_file_path.items(): # get vfps for all roots
                firmware_root_uid = root_uid
                local_file_path = None
                for vfp_as_uid_list in self.database.get_file_tree_path(file_object.uid): # returns list of lists of uids for file_object.uid
                    
                    if root_uid in vfp_as_uid_list and vfp_as_uid_list[0] in [fo.uid for fo in fo_list]: # if the root_uid of our current config file is in the vfp path and the first uid in the vfp path is one of our firmware objects
                        local_file_path = file_object.virtual_file_path[root_uid].pop().split('|')[-1]
                        firmware_root_uid = vfp_as_uid_list[0]
                        break # we found the vfp path that corresponds to the current root_uid, so we can stop looking through the vfp paths for this file_object
                    else: 
                        continue # if not, check other vfp paths
                
                if local_file_path is None:
                    continue
                
                if local_file_path not in results.keys():
                    results[local_file_path] = {'collapse': 'True'}
                    
                if file_object.uid in parsed_config_parameters:
                    config_parameters_str_list = [f"{self._to_safe_str(key)}: {self._to_safe_str(value)}" for key, value in parsed_config_parameters[file_object.uid].items()]
                else:
                    config_parameters_str_list = []
                # first line/entry is the file uid as this will be clickable in the UI
                results[local_file_path][firmware_root_uid] = [f"{file_object.uid}"] 
                # add config_parameters_str_list
                results[local_file_path][firmware_root_uid].extend(config_parameters_str_list)
                
        # if all config files for one local file path contain no parsed parameters, collapse=False
        for local_file_path in results.keys():
            total_parameters = 0
            for firmware_root_uid in results[local_file_path].keys():
                if firmware_root_uid == 'collapse': # don't count collapse key
                    continue
                total_parameters += len(results[local_file_path][firmware_root_uid]) - 1 # subtract 1 to not count the file uid entry
            if total_parameters == 0:
                results[local_file_path]['collapse'] = 'False'
        
        return results
        
    def _to_safe_str(self, s: str) -> str:
        """Convert a string to a safe string that can be displayed in the view without causing encoding issues

        Args:
            s (str): String to convert

        Returns:
            str: Safe string that can be displayed in the view without causing encoding issues
        """
        return s.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        
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
        
            if not fo.binary:
                binary, _ = self.binary_service.get_binary_and_file_name(fo.uid)
                # Check which config type the file is
                config_file_type = self._determine_config_type(fo, binary)
                print(f"Parsing --> FO: {fo.file_name} UID: {fo.uid} TYPE: {config_file_type}")
                uid_with_contents[fo.uid] = self._parse_config_from_binary(binary, filetype=config_file_type)
            else:
                config_file_type = self._determine_config_type(fo)
                print(f"Parsing --> FO: {fo.file_name} UID: {fo.uid} TYPE: {config_file_type}")
                uid_with_contents[fo.uid] = self._parse_config_from_binary(fo.binary, filetype=config_file_type)
        
        return uid_with_contents

    def _determine_config_type(self, fo: FileObject, binary: bytes = None) -> str | None:
        """Determine the config file type based on file extension and file type analysis results

        Args:
            fo (FileObject): File object to determine config type for
            binary (bytes): optional if fo has no binary set

        Returns:
            str | None: Config file type. Options: 'toml', 'xml', 'dualkey', 'csv or None if type cannot be determined
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
            
        if binary is not None:
            file_content_ascii = binary.decode('ascii', errors='ignore')
        else:
            file_content_ascii = fo.binary.decode('ascii', errors='ignore')
        if re.search(r'<\s*[^>]+>', file_content_ascii): # crude regex to check for presence of <tags> which may indicate an xml file
            # check for closing tags as well to reduce false positives
            if re.search(r'<\s*/\s*[^>]+>', file_content_ascii):
                return 'xml'
        elif re.search(r'^\s*\[.*\]\s*$', file_content_ascii, re.MULTILINE): # crude regex to check for presence of [headers] which may indicate a toml file
            return 'toml'
        
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

    def _is_config_file(self, fo: FileObject) -> bool:        
        # Check MIME type and filter out application and other non-parsable file types
        mime_whitelist = ['text/x-ini', 'text/csv', 'application/toml', 'application/xml', ' application/json', 'text/xml']
        mime_blacklist_startswith = ['application/','image/', 'audio/', 'video/', 'font/']
        mime_blacklist = ['text/css', 'text/html', 'text/javascript','inode/symlink', 'text/x-shellscript', 'text/x-python', 'text/x-c', 'text/x-c++']
        full_blacklist = ['certificate', 'archive', 'compressed', 'executable', 'shared object', 'dll', 'library', 'object file']
        # results e.g.
        # {
        #     "full": "ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /lib/ld-musl-aarch64.so.1, no section header",
        #     "mime": "application/x-pie-executable"
        # }
        
        if 'file_type' in fo.processed_analysis:
            mime = fo.processed_analysis['file_type']['result']['mime']
            if mime in mime_whitelist:
                if mime == 'text/plain':
                    full = fo.processed_analysis['file_type']['result']['full']
                    if any(keyword in full for keyword in full_blacklist):
                        return False
                else:
                    return True
            elif any(mime.startswith(prefix) for prefix in mime_blacklist_startswith) or mime in mime_blacklist:
                return False
            
        # File extension
        extension_whitelist = ['config', 'conf', 'cfg', 'ini', 'toml', 'yaml', 'yml', 'xml']
        extension_blacklist = ['exe', 'dll', 'bin', 'so', 'dylib', 'elf', 'py', 'js', 'c', 'cpp', 'h', 'sh', 'bat', 'html', 'css', 'jar', 'zip', 'rar', '7z', 'gz', 'tar']
        if any(fo.file_name.endswith(ext) for ext in extension_whitelist):
            return True
        elif any(fo.file_name.endswith(ext) for ext in extension_blacklist):
            return False
        
        # Ensure binary 
        if fo.binary is None and fo.file_path is not None:
            fo.create_binary_from_path() # if only a path is given, create binary using the built-in method
        elif fo.file_path is None:
            return False # no file contents to analyze

        # Get file content as string
        file_content_binary = fo.binary
        try:
            if 'UTF-8' in fo.analysis_results['file_type']['result']['full']:
                file_content_decoded = file_content_binary.decode('utf-8', errors='ignore')
            else:
                file_content_decoded = file_content_binary.decode('ascii', errors='ignore')
        except:
            return False

        # Empty file handling
        if file_content_decoded.strip() == '':
            return False

        # Comment indicator characters for ignored lines
        comment_indicator_characters = ['#', ';']
        
        # Prevent script files (e.g. python or C programming snippets) from being identified as a false positive
        # get first 10 lines excluding comment lines
        first_lines = []
        for line in file_content_decoded.splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or any(line.startswith(char) for char in comment_indicator_characters):
                continue
            first_lines.append(line)
            if len(first_lines) >= 10:
                break
            
        # Check for common script file syntax that may indicate a script
        # Note: MIME blacklist filters out most scripts
        common_script_syntax = ['def ', 'function ', '#include ', '{', '}', 'public ', 'private ', 'class ']
        if any(syntax in line for line in first_lines for syntax in common_script_syntax):
            return False
        
        # Parse key/value
        valid_key_value_pattern = re.compile(r'^[^#;\s]+?\s*[:=]\s*.+$')
        for line in file_content_decoded.splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or any(line.startswith(char) for char in comment_indicator_characters):
                continue
            if valid_key_value_pattern.match(line):
                return True

        # Parse dual key/value (e.g. "key1 key2 value")
        valid_key_value_pattern_no_first_word = re.compile(r'^[^\s]+?\s+[^#;\s]+?\s+.+$')
        for line in file_content_decoded.splitlines():
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
            filetype (str | None): Optional file type to use for parsing strategy. Options: 'toml', 'xml', 'dualkey', 'csv', 'yaml' None for default parsing strategy

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
        elif filetype == 'csv':
            return self._parse_helper_csv(binary_data)
        elif filetype == 'yaml':
            return self._parse_helper_yaml(binary_data)
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
            def parse_element(element, parent_keys=[]): 
                key = ' '.join(parent_keys + [element.tag])
                if element.text and element.text.strip():
                    config_dict[key] = element.text.strip()
                for child in element:
                    parse_element(child, parent_keys + [element.tag])
            parse_element(root)
            return config_dict
        except Exception as e:
            print(f"Error parsing xml file: {e}")
            print(f"Attempting rugged xml parsing strategy...")
            return self._parse_helper_xml_rugged(binary_data)
        
    def _parse_helper_xml_rugged(self, binary_data: bytes) -> dict:
        """Fallback xml parsing for invalid xmls using regex instead of xml library

        Args:
            binary_data (bytes): Binary data of the xml file

        Returns:
            dict: Dict of key value strings
        """
        config_dict = {}
        parent_keys = []
        for line in binary_data.decode('ascii', errors='ignore').splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line:
                continue
            # check for opening tags and closing tags
            opening_tag_match = re.match(r'^<(\w+)>$', line)
            closing_tag_match = re.match(r'^</(\w+)>$', line)
            if opening_tag_match:
                parent_keys.append(opening_tag_match.group(1))
            elif closing_tag_match:
                if parent_keys and parent_keys[-1] == closing_tag_match.group(1):
                    parent_keys.pop()
            else:
                # check for key value pairs in the form of <key>value</key> on the same line
                inline_tag_match = re.match(r'^<(\w+)>(.*?)</\1>$', line)
                if inline_tag_match:
                    key = ' '.join(parent_keys + [inline_tag_match.group(1)])
                    value = inline_tag_match.group(2).strip()
                    config_dict[key] = value
        print(f"Got {len(config_dict)} key value pairs from rugged xml parsing strategy")
        return config_dict

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
            print(f"Error parsing toml file using toml library: {e}")
            print(f"Attempting custom rugged toml parsing strategy...")
            return self._parse_helper_toml_rugged(binary_data)
    
    def _parse_helper_toml_rugged(self, binary_data: bytes) -> dict:
        """Fallback toml parsing for invalid tomls e.g. du to no = sign after key (e.g. for lines like key values instead of key=value)

        Args:
            binary_data (bytes): Binary data of the toml file

        Returns:
            dict: Dict of key value strings
        """
        config_dict = {}
        current_parent_keys = []
        for line in binary_data.decode('ascii', errors='ignore').splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or line.startswith('#'):
                continue
            if re.match(r'^\s*\[.*\]\s*$', line): # section header
                section_name = line.strip('[]').strip()
                current_parent_keys = section_name.split('.')
            elif re.match(r'^[^\s]+?\s*[:=]?\s*.+$', line): # key value pair with optional = or : separator
                if '=' in line:
                    key, value = line.split('=', 1)
                elif ':' in line:
                    key, value = line.split(':', 1)
                else:
                    parts = line.split()
                    key, value = parts[0], ' '.join(parts[1:])
                key = key.strip()
                value = value.strip()
                composite_key = ' '.join(current_parent_keys + [key]) if current_parent_keys else key
                config_dict[composite_key] = value
        print(f"Got {len(config_dict)} key value pairs from rugged toml parsing strategy")
        return config_dict

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
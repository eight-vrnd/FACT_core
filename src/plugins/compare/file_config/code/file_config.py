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

class ComparePlugin(CompareBasePlugin):
    '''
    This plugin allows comparison of two (or more) configuration files. It handles identifying, parsing, and displaying config file key/value pairs for a variety of configuration file types
    '''

    NAME = 'file_config'
    DEPENDENCIES = ['file_type']
    VERSION = '0.0.3'

    def compare_function(self, fo_list, dependency_results: dict[str, dict]) -> dict[str, dict]:
        # get all uids from all firmware objects' included files
        included_file_uids = self._get_included_file_sets(fo_list)

        #  get full file object for all uids
        file_objects = self._get_included_file_objects_from_uid_list(included_file_uids)

        # only keep config files - filter out non config files based on extension and file type
        config_files = self._filter_config_files(file_objects)

        # get uid list for filtered config files
        config_file_uids = self._get_uid_list_from_file_objects(config_files)

        #  get virtual file paths for all uids of filtered config files
        config_file_uids_with_vfps = self._get_file_vfp_from_uid_list(config_file_uids)

        # transform to list of vfp + uids that share that vfp
        shared_vfps = self._get_shared_vfps(config_file_uids_with_vfps)

        # Debug
        results = {
            'config_file_uids': {
                'all': config_file_uids,
                'collapse': True
            },
            'config_file_uids_with_vfps': {
                fo.uid: config_file_uids_with_vfps for fo in fo_list
            },
        }

        return results

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

    def _get_shared_vfps(self, config_file_uids_with_vfps: dict[str, dict[str, list[str]]]) -> dict[str, list[str]]:
        """Return a dict of vfps that are shared across config files with the list of uids that share that vfp

        Args:
            config_file_uids_with_vfps (dict[str, str]): Dict of file object uids with their respective vfps

        Returns:
            dict[str, list[str]]: Dict of vfps that are shared across config files with the list of uids that share that vfp
        """

        # config_file_uids_with_vfps = {
        #   'uid_1': {'firmware1/config/example.config': ['example.config']},
        #   'uid_2': {'firmware2/config/example.config': ['example.config']}
        # }
        vfp_to_uids = {}
        for uid, vfps in config_file_uids_with_vfps.items():
            for vfp in vfps.keys():
                if vfp not in vfp_to_uids:
                    vfp_to_uids[vfp] = []
                vfp_to_uids[vfp].append(uid)

        # only keep vfps that are shared across multiple config files
        shared_vfps = {vfp: uids for vfp, uids in vfp_to_uids.items() if len(uids) > 1}
        return shared_vfps

    @staticmethod
    def _get_included_file_sets(fo_list: list[FileObject]) -> list[set[str]]:
        """Returns a set for each firmware object containing the uids of all included file objects of that firmware object

        Args:
            fo_list (list[FileObject]): Firmware object list

        Returns:
            list[set[str]]: List of sets of file object uids, one set per firmware object
        """
        return [set(file_object.list_of_all_included_files) for file_object in fo_list]

    def _get_included_file_objects_from_uid_list(self, uid_list: list[set[str]]) -> list[FileObject]:
        """Generate a list of file objects for all uids of all firmware objects

        Args:
            uid_list (list[set[str]]): List of sets of file object uids, one set per firmware object

        Returns:
            list[FileObject]: List of file objects each with their respective attributes
        """
        included_file_uids_flat = set().union(*uid_list)
        file_objects = self.database.get_objects_by_uid_list(included_file_uids_flat)
        return file_objects

    def _get_file_vfp_from_uid_list(self, uid_list: list[str]) -> dict[str, dict[str, list[str]]]:
        uid_vfp = self.database.get_vfps_for_uid_list(uid_list)
        return uid_vfp

    def _is_config_file(self, fo: FileObject) -> bool:
        if fo.processed_analysis.get('file_type', {}).get('mime', '').startswith('text/'):
            return False

        # File extension
        valid_file_extensions = ['config', 'conf', 'cfg', 'ini', 'toml', 'yaml', 'yml', 'xml']
        if any(fo.file_name.endswith(ext) for ext in valid_file_extensions):
            return True

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
        if binary_data.strip() == b'':
            return {}

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
        valid_key_value_pattern_no_first_word = re.compile(r'^[^\s]+?\s+[^#;\s]+?\s+.+$')
        for line in binary_data.decode('ascii', errors='ignore').splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or any(line.startswith(char) for char in comment_indicator_characters):
                continue
            match = valid_key_value_pattern_no_first_word.match(line)
            if match:
                parts = line.split()
                key1, key2, value = parts[0], parts[1], ' '.join(parts[2:])
                config_dict[f"{key1} {key2}"] = value

        return config_dict
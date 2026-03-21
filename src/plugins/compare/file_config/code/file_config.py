from __future__ import annotations

import re

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
    DEPENDENCIES = []
    VERSION = '0.0.1'

    def compare_function(self, fo_list, dependency_results: dict[str, dict]):
        """__compares configuration files__

        Args:
            fo_list (_type_): 
            
        Returns:
            _dict: Returns a dict structured as follows:
            ```
            {
                SECTION_ONE:
                    {
                        FIRST_FILE_OBJECT_ID: Value
                        SECOND_FILE_OBJECT_ID: Value
                        ...
                        'collapse': True/False
                    }
                SECTION_TWO:
                    {
                        'all': Value
                        'collapse': True/False
                    }
            }
            ```
        """
        
        # uid list
        included_file_uids = self._get_included_file_sets(fo_list)

        included_file_vfps = set()
        for fo in fo_list:
            included_file_vfps.update(self._get_vfp_of_included_text_files(fo.root_uid))
            
        result = {}
        return result

    @staticmethod
    def _get_included_file_sets(fo_list: list[FileObject]) -> list[set[str]]:
        return [set(file_object.list_of_all_included_files) for file_object in fo_list]

    def _get_vfp_of_included_text_files(self, root_uid, blacklist=None):
        return self.database.get_vfp_of_included_text_files(root_uid)
    
    def _is_config_file(self, fo: FileObject) -> bool:
        # Filename checks - does the extension match common config file extensions?
        valid_file_extensions = ['config', 'conf', 'cfg', 'ini', 'toml', 'yaml', 'yml', 'xml']
        if any(fo.file_name.endswith(ext) for ext in valid_file_extensions):
            return True

        # prep content 
        file_content_ascii = fo.binary
        
        # Content checks - does the file have lines not starting with ; or # that contain key-value structure?
        comment_indicator_characters = ['#', ';']
        valid_key_value_separators = ['=', ':', ' ']
        valid_key_value_pattern = re.compile(r'^[^#;\s]+?\s*[:=]\s*.+$')
        
        for line in file_content_ascii.splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or any(line.startswith(char) for char in comment_indicator_characters):
                continue
            if valid_key_value_pattern.match(line):
                return True
        
        # Attempt matching again without first word for triple key value pairs (e.g. "key1 key2 value")
        valid_key_value_pattern_no_first_word = re.compile(r'^[^\s]+?\s+[^#;\s]+?\s+.+$')
        for line in file_content_ascii.splitlines():
            line = line.strip() # Remove leading/trailing whitespace
            if not line or any(line.startswith(char) for char in comment_indicator_characters):
                continue
            if valid_key_value_pattern_no_first_word.match(line):
                return True

    def _parse_config(self, fo: FileObject) -> dict:
        return {'key': 'value'} #FIXME

    def _compare_parameters(self, fo_list: list[FileObject]) -> dict:
        raise NotImplementedError() #FIXME
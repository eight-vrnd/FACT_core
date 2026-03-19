from __future__ import annotations

import config
import configparser
import json
import networkx
import pprint
import re
import ssdeep
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
        
        # gather all candidate file uids from the firmware objects
        all_candidate_uids = set()
        for fo in fo_list:
            if fo.list_of_all_included_files:
                all_candidate_uids.update(fo.list_of_all_included_files)
        
        if not is_list_of_uids(all_candidate_uids):
            raise ValueError('Expected list of uids, got something else')
        
        # Check all_candidate_uids for config files
        config_files = {}
        for fo in fo_list:
            if self._is_config_file(fo):
                config_files[fo.uid] = self._parse_config(fo)
                
        result = {
            'config_parameters': config_files,
        }

        return result

    def _is_config_file(self, fo: FileObject) -> bool:
        return True

    def _parse_config(self, fo: FileObject) -> dict:
        return {'key': 'value'}

    def _compare_parameters(self, fo_list: list[FileObject]) -> dict:
        raise NotImplementedError()
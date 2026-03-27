from __future__ import annotations

import re
import os

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
            fo_list (_type_):  Firmware objects list
            
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
        
        # # for each vfp, parse the all config files and save to [uid, parsed config dict]
        # parsed_configs_by_vfp = self._parse_configs_by_vfp(shared_vfps)
        
        # result set should be a list of config files with parse parameters for each config file
        # combine to achieve the following structure:
        #   {
        #         get filename with extension from vfp1:
        #             {
        #                 uid1: {'key1': 'value', ...}
        #                 uid2: {'key1': 'value', ...}
        #                 'collapse': True
        #             }
        #         get filename with extension from vfp2:
        #             {
        #                 uid3: {'key1': 'value', ...}
        #                 uid4: {'key1': 'value', ...}
        #                 'collapse': True
        #             }
        #     }
        # result = self._combine_parsed_configs(parsed_configs_by_vfp)

        result = {}
        return result

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
        #   'uid_1': {'firmware1/example.config': [...]},
        #   'uid_2': {'firmware2/example.config': [...]}
        # }
        vfp_to_uids: dict[str, list[str]] = {}
        for uid, vfp_dict in config_file_uids_with_vfps.items():
            for vfp, paths in (vfp_dict or {}).items():
                filename = os.path.basename(vfp)
                vfp_to_uids.setdefault(filename, []).append(uid)
        
        # only keep vfps that are shared across multiple config files
        shared_vfps = {vfp: uids for vfp, uids in vfp_to_uids.items() if len(uids) > 1}
        return shared_vfps

    def _parse_configs_by_vfp(self, shared_vfps: dict[str, list[str]]) -> dict[str, list[tuple[str, dict]]]:
        raise NotImplementedError() #FIXME
        # parsed_configs_by_vfp = {}
        # for vfp, uids in shared_vfps.items():
        #     parsed_configs_by_vfp[vfp] = []
        #     for uid in uids:
        #         file_object = self.database.get_objects_by_uid_list([uid])[0]
        #         parsed_config = self._parse_config(file_object)
        #         parsed_configs_by_vfp[vfp].append((uid, parsed_config))
        # return parsed_configs_by_vfp
    
    def _combine_parsed_configs(self, parsed_configs_by_vfp: dict[str, list[tuple[str, dict]]]) -> dict:
        raise NotImplementedError() #FIXME
        # combined_result = {}
        # for vfp, parsed_configs in parsed_configs_by_vfp.items():
        #     filename = vfp.split('/')[-1] # get filename with extension from vfp
        #     combined_result[filename] = {}
        #     for uid, parsed_config in parsed_configs:
        #         combined_result[filename][uid] = parsed_config
        #     combined_result[filename]['collapse'] = True # default to collapsing all config files with same vfp, can be set to False in UI if desired
        # return combined_result

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
    
    def _get_file_vfp_from_uid_list(self, uid_list: list[str]) -> dict[str, str]:
        # included_file_uids_flat = set().union(*uid_list)
        file_vfpgs = self.database.get_vfps_for_uid_list(uid_list)
        return file_vfpgs
    
    def _is_config_file(self, fo: FileObject) -> bool:
        # Filename checks - does the extension match common config file extensions?
        valid_file_extensions = ['config', 'conf', 'cfg', 'ini', 'toml', 'yaml', 'yml', 'xml']
        if any(fo.file_name.endswith(ext) for ext in valid_file_extensions):
            return True

        # remove/filter out scripting files based on file type?
        
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
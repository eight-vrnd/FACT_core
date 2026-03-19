from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

import networkx
import ssdeep

import config
from compare.PluginBase import CompareBasePlugin
from helperFunctions.compare_sets import iter_element_and_rest, remove_duplicates_from_list
from helperFunctions.data_conversion import convert_uid_list_to_compare_id
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
        
        compare_result = {
            'files_in_common': self._get_intersection_of_files(fo_list),
        }

        result = {}

        # your code...

        return result

    def _get_intersection_of_files(self, fo_list: list[FileObject]) -> dict[str, list[str]]:
        intersection_of_files = set.intersection(*self._get_included_file_sets(fo_list))
        return {'all': list(intersection_of_files)}
    
    @staticmethod
    def _get_included_file_sets(fo_list: list[FileObject]) -> list[set[str]]:
        return [set(file_object.list_of_all_included_files) for file_object in fo_list]

    def _get_exclusive_files(self, fo_list: list[FileObject]) -> dict[str, list[str]]:
        result = {}
        for current_element, other_elements in iter_element_and_rest(fo_list):
            exclusive_files = set.difference(
                set(current_element.list_of_all_included_files), *self._get_included_file_sets(other_elements)
            )
            result[current_element.uid] = list(exclusive_files)
        return result

    def _find_changed_text_files(
        self, fo_list: list[FileObject], common_files: list[str]
    ) -> dict[str, list[tuple[str, str]]]:
        """
        Find text files that have the same path but different content for the file objects that are compared. The idea
        is to find config files that were changed between different versions of a firmware. Only works if two firmware
        objects are compared (and returns an empty result otherwise).
        :param fo_list: the list of compared file objects
        :param common_files: list of UIDs that are in both file objects
        :return: a dict with paths as keys and a list of UID pairs (tuples) as values
        """
        changed_text_files = {}
        vfp_a = self.database.get_vfp_of_included_text_files(fo_list[0].uid, blacklist=common_files)
        vfp_b = self.database.get_vfp_of_included_text_files(fo_list[1].uid, blacklist=common_files)
        for common_path in set(vfp_a).intersection(set(vfp_b)):
            # vfp_x[common_path] should usually contain only 1 element (except if there are multiple files with the same
            # path, e.g. if the FW contains multiple file systems, in which case all combinations are added)
            for uid_1 in vfp_a[common_path]:
                for uid_2 in vfp_b[common_path]:
                    changed_text_files.setdefault(common_path, []).append((uid_1, uid_2))
        return changed_text_files
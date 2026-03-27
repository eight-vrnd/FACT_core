import pytest
import os

from common_helper_files import get_dir_of_file
from objects.file import FileObject
from plugins.compare.file_config.code.file_config import ComparePlugin
from test.common_helper import CommonDatabaseMock, create_test_file_object, create_test_firmware
from test.unit.compare.compare_plugin_test_class import ComparePluginTest
from helperFunctions.uid import create_uid

class DbMock:
    def get_objects_by_uid_list(
        self, uid_list: list[str] | set[str], analysis_filter: list[str] | None = None
    ) -> list[FileObject]:
        file_objects = []
        for uid in uid_list:
            if uid == 'uid_1':
                file_object = create_test_file_object(uid='uid_1', bin_path='firmware1/config/example.config')
                file_objects.append(file_object)
            elif uid == 'uid_2':
                file_object = create_test_file_object(uid='uid_2', bin_path='firmware2/config/example.config')
                file_objects.append(file_object)
            elif uid == 'uid_3':
                file_object = create_test_file_object(uid='uid_3', bin_path='firmware2/config/example.config')
                file_objects.append(file_object)
        
        return file_objects

    def get_vfps_for_uid_list(
        self, uid_list: list[str] | set[str], root_uid: str | None = None
    ) -> dict[str, dict[str, list[str]]]:
        """
        Gets all virtual file paths (see `get_vfps()`) for a list of UIDs. Returns a dictionary with key=uid and
        value=vfp_dict for that file (vfp_dict is the same as the output of `get_vfps()` for that file). If `root_uid`
        is set, only return the paths inside the firmware with UID `root_uid`.
        """
        # return virtual file paths for each uid/root_uid combo
        # dev_1_firmware_1 root uid: '34d7e9d95a3896f445e438037e5d03c98b4b5097b14c8c5521eb83105c569709_61'
        # dev_1_firmware_2 root uid: '6bcbfafd4affeb5d5657653566c06420e5961d9712f5b5774094ce0c5f2763c7_61'
        vfps = {}
        for uid in uid_list:
            if uid == 'uid_1':
                vfps[uid] = {
                    'firmware1/config/example.config': ['example.config']
                }
            elif uid == 'uid_2':
                vfps[uid] = {
                    'firmware2/config/example.config': ['example.config']
                }
            elif uid == 'uid_3':
                vfps[uid] = {
                    'firmware2/config/example.config': ['example.config']
                }
        return vfps
        
    
class TestComparePluginFileConfig(ComparePluginTest):
    # An initialized plugin instance is available at self.c_plugin
    PLUGIN_NAME = 'file_config'
    PLUGIN_CLASS = ComparePlugin
    TEST_DATA_DIR = os.path.join(get_dir_of_file(__file__), 'data')
    
    def setup_plugin(self):
        
        # Plugin initialization
        return ComparePlugin(db_interface=DbMock(), view_updater=CommonDatabaseMock())

    def setup_test_fw(self):
        """
        Mockup firmware files with included config files similar to each other for testing of identification, parsing, and comparison
        """
        
        self.fw_one = create_test_firmware(device_name='dev_1_firmware_1', bin_path='firmware1/firmware1.zip', all_files_included_set=True)
        self.fw_one.add_included_file(create_test_file_object(uid='uid_1', bin_path='firmware1/config/example.config'))
        self.fw_one.list_of_all_included_files = ['uid_1']
        self.fw_one.root_uid = create_uid(self.fw_one.file_path)
        
        self.fw_two = create_test_firmware(device_name='dev_1_firmware_2', bin_path='firmware2/firmware2.zip', all_files_included_set=True)
        self.fw_two.add_included_file(create_test_file_object(uid='uid_2', bin_path='firmware2/config/example.config'))
        self.fw_two.list_of_all_included_files = ['uid_2']
        self.fw_two.root_uid = create_uid(self.fw_two.file_path)
        
        self.fw_three = create_test_firmware(device_name='dev_1_firmware_2', bin_path='firmware2/firmware2.zip', all_files_included_set=True)
        self.fw_three.add_included_file(create_test_file_object(uid='uid_3', bin_path='firmware2/config/example.config'))
        self.fw_three.list_of_all_included_files = ['uid_3']
        self.fw_three.root_uid = create_uid(self.fw_three.file_path)
        
    def test_compare_function(self):
        result = self.c_plugin.compare_function([self.fw_one, self.fw_two], {})
        assert isinstance(result, dict), 'result is not a dict'
        assert 'config_parameters' in result, 'config_parameters field not present in result'
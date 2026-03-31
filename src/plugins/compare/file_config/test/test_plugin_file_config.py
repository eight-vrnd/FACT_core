import pytest
import os

from common_helper_files import get_dir_of_file
from objects.file import FileObject
from objects.firmware import Firmware
from plugins.compare.file_config.code.file_config import ComparePlugin
from test.common_helper import CommonDatabaseMock, create_test_file_object, create_test_firmware
from test.unit.compare.compare_plugin_test_class import ComparePluginTest
from helperFunctions.uid import create_uid, is_list_of_uids, is_uid

# Setting up test firmware objects to allow DbMock class to access file objects
FW_ONE = create_test_firmware(device_name='dev_1_firmware_1', bin_path='firmware1/firmware1.zip', all_files_included_set=True)
FW_ONE.add_included_file(create_test_file_object(bin_path='firmware1/config/example.config'))

FW_TWO = create_test_firmware(device_name='dev_1_firmware_2', bin_path='firmware2/firmware2.zip', all_files_included_set=True)
FW_TWO.add_included_file(create_test_file_object(bin_path='firmware2/config/example.config'))

FW_THREE = create_test_firmware(device_name='dev_1_firmware_2', bin_path='firmware2/firmware2.zip', all_files_included_set=True)
FW_THREE.add_included_file(create_test_file_object(bin_path='firmware2/config/example.config'))

class DbMock:
        
    def get_objects_by_uid_list(
        self, uid_list: list[str] | set[str], analysis_filter: list[str] | None = None
    ) -> list[FileObject]:
        file_objects = []
        
        for uid in uid_list:
            # Check which test firmware the uid belongs to and return the corresponding file object
            if uid in FW_ONE.list_of_all_included_files:
                file_objects.append(create_test_file_object(bin_path='firmware1/config/example.config', uid=uid))
            elif uid in FW_TWO.list_of_all_included_files:
                file_objects.append(create_test_file_object(bin_path='firmware2/config/example.config', uid=uid))
            elif uid in FW_THREE.list_of_all_included_files:
                file_objects.append(create_test_file_object(bin_path='firmware2/config/example.config', uid=uid))
        
        return file_objects

    def get_vfps_for_uid_list(
        self, uid_list: list[str] | set[str], root_uid: str | None = None
    ) -> dict[str, dict[str, list[str]]]:
        """
        Gets all virtual file paths (see `get_vfps()`) for a list of UIDs. Returns a dictionary with key=uid and
        value=vfp_dict for that file (vfp_dict is the same as the output of `get_vfps()` for that file). If `root_uid`
        is set, only return the paths inside the firmware with UID `root_uid`.
        """
        
        # vfps[uid] = {
        #     'firmware1/config/example.config': ['example.config']
        # }
        
        vfps = {}
        
        for uid in uid_list:
            if uid in FW_ONE.list_of_all_included_files:
                vfps[uid] = {
                    'firmware1/config/example.config': ['example.config']
                }
            elif uid in FW_TWO.list_of_all_included_files:
                vfps[uid] = {
                    'firmware2/config/example.config': ['example.config']
                }
            elif uid in FW_THREE.list_of_all_included_files:
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
        return ComparePlugin(db_interface=DbMock(), view_updater=CommonDatabaseMock())
    
    def test_setup_selfcheck(self):
        # Check firmware objects
        assert isinstance(self.fw_one, FileObject), 'fw_one is not a FileObject'
        assert isinstance(self.fw_two, FileObject), 'fw_two is not a FileObject'
        assert isinstance(self.fw_three, FileObject), 'fw_three is not a FileObject'
        assert isinstance(self.fw_one, Firmware), 'fw_one is not a Firmware'
        assert isinstance(self.fw_two, Firmware), 'fw_two is not a Firmware'
        assert isinstance(self.fw_three, Firmware), 'fw_three is not a Firmware'
        
        # Check contents
        assert len(self.fw_one.list_of_all_included_files) == 1, 'fw_one should have 1 included file'
        assert len(self.fw_two.list_of_all_included_files) == 1, 'fw_two should have 1 included file'
        assert len(self.fw_three.list_of_all_included_files) == 1, 'fw_three should have 1 included file'
        
        # Check UIDs
        assert is_uid(self.fw_one.root_uid), 'fw_one root uid is not a valid uid'
        assert is_uid(self.fw_one.uid), 'fw_one root uid is not a valid uid'
        assert is_uid(self.fw_two.root_uid), 'fw_two root uid is not a valid uid'
        assert is_uid(self.fw_two.uid), 'fw_two uid is not a valid uid'
        assert is_uid(self.fw_three.root_uid), 'fw_three root uid is not a valid uid'
        assert is_uid(self.fw_three.uid), 'fw_three uid is not a valid uid'
        assert is_list_of_uids(self.fw_one.list_of_all_included_files), 'List of included files should be a list of uids'
        assert is_list_of_uids(self.fw_two.list_of_all_included_files), 'List of included files should be a list of uids'
        assert is_list_of_uids(self.fw_three.list_of_all_included_files), 'List of included files should be a list of uids'

    def setup_test_fw(self):
        """
        Mockup firmware files with included config files similar to each other for testing of identification, parsing, and comparison
        """
        self.fw_one = FW_ONE
        self.fw_two = FW_TWO
        self.fw_three = FW_THREE
        
    def test_compare_function(self):
        result = self.c_plugin.compare_function([self.fw_one, self.fw_two], {})
        assert isinstance(result, dict), 'result is not a dict'
    
    def test_parse_config_from_binary_empty_file(self):
        # Empty file should return empty dict
        example_content = b""
        expected_output = {}
        output = self.c_plugin._parse_config_from_binary(example_content)
        assert output == expected_output, f'Unexpected output for empty file'
        
    def test_parse_config_from_binary(self):
        # Example config content
        example_content_dual_key = b"""
        type key value
        
        ; network config
        network port 8080
        network bind 0.0.0.0
        network protocol tcp
        
        ; database config
        database host localhost
        database port 3306
        """
        expected_output = {
            'type key': 'value',
            'network port': '8080',
            'network bind': '0.0.0.0',
            'network protocol': 'tcp',
            'database host': 'localhost',
            'database port': '3306'
        }
        output = self.c_plugin._parse_config_from_binary(example_content_dual_key, filetype='dualkey')
        assert output == expected_output, f'Unexpected output'
    
    def test_parse_helper_dualkey(self):
        # Example dualkey config content
        example_content = b"""
        type key value
        
        ; network config
        network port 8080
        network bind 0.0.0.0
        network protocol tcp
        
        ; database config
        database host localhost
        database port 3306
        """
        expected_output = {
            'type key': 'value',
            'network port': '8080',
            'network bind': '0.0.0.0',
            'network protocol': 'tcp',
            'database host': 'localhost',
            'database port': '3306'
        }
        output = self.c_plugin._parse_helper_dualkey(example_content)
        assert output == expected_output, f'Unexpected output'
        
    def test_parse_helper_default(self):
        # Example default config content
        example_content = b"""
        # This is a comment
        port=8080
        bind=0.0.0.0
        protocol=tcp
        """
        expected_output = {
            'port': '8080',
            'bind': '0.0.0.0',
            'protocol': 'tcp'
        }
        
        output = self.c_plugin._parse_helper_default(example_content)
        assert output == expected_output, f'Unexpected output'

    def test_parse_helper_toml(self):
        # Example toml config content
        example_content = b"""
        [network]
        port = 8080
        bind = "0.0.0.0"
        
        [database]
        host = "localhost"
        port = 3306
        """
        expected_output = {
            'network port': '8080',
            'network bind': '0.0.0.0',
            'database host': 'localhost',
            'database port': '3306'
        }
        output = self.c_plugin._parse_helper_toml(example_content)
        assert output == expected_output, f'Unexpected output'
        
    def test_parse_helper_xml(self):
        # Example xml config content
        example_content = b"""
        <config>
            <network>
                <port>8080</port>
                <bind>0.0.0.0</bind>
            </network>
            <database>
                <host>localhost</host>
                <port>3306</port>
            </database>
        </config>
        """
        expected_output = {
            'config network port': '8080',
            'config network bind': '0.0.0.0',
            'config database host': 'localhost',
            'config database port': '3306'
        }
        output = self.c_plugin._parse_helper_xml(example_content)
        assert output == expected_output, f'Unexpected output'
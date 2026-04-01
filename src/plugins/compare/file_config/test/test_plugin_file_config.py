import pytest
import os

from common_helper_files import get_dir_of_file, get_binary_from_file
from objects.file import FileObject
from objects.firmware import Firmware
from plugins.compare.file_config.code.file_config import ComparePlugin
from test.common_helper import CommonDatabaseMock, create_test_file_object, create_test_firmware
from test.unit.compare.compare_plugin_test_class import ComparePluginTest
from helperFunctions.uid import create_uid, is_list_of_uids, is_uid

# IDE specific settings
# pyright: reportOperatorIssue=false
# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportOptionalMemberAccess=false

# Setting up test firmware objects to allow DbMock class to access file objects
# Manually add binaries to included file objects due to paths being different from live system
TEST_DATA_DIR = os.path.join(get_dir_of_file(__file__), 'data')

FW_ONE = create_test_firmware(device_name='dev_1_firmware_1', bin_path='firmware1/firmware1.zip', all_files_included_set=True)
FO_ONE = create_test_file_object(bin_path='firmware1/config/example.config')
FO_ONE.binary = get_binary_from_file(f'{TEST_DATA_DIR}/firmware1/config/example.config')
FO_ONE.root_uid = FW_ONE.root_uid
FW_ONE.add_included_file(FO_ONE)

FW_TWO = create_test_firmware(device_name='dev_1_firmware_2', bin_path='firmware2/firmware2.zip', all_files_included_set=True)
FO_TWO = create_test_file_object(bin_path='firmware2/config/example.config')
FO_TWO.binary = get_binary_from_file(f'{TEST_DATA_DIR}/firmware2/config/example.config')
FO_TWO.root_uid = FW_TWO.root_uid
FW_TWO.add_included_file(FO_TWO)

FW_THREE = create_test_firmware(device_name='dev_1_firmware_3', bin_path='firmware3/firmware3.zip', all_files_included_set=True)
FO_THREE = FO_TWO
FW_THREE.add_included_file(FO_THREE)

FW_FOUR = create_test_firmware(device_name='dev_2_firmware_1', bin_path='firmware4/firmware_nested_1.zip', all_files_included_set=True)
FW_FOUR_FOLDER = create_test_file_object(bin_path='firmware4/folder')
# create file objects for all files in firmware4/folder/
FO_FOUR_LIST = []
FO_FOUR_LIST.append(FW_FOUR_FOLDER)
for root, dirs, files in os.walk(f'{TEST_DATA_DIR}/firmware4/folder'):
    for file in files:
        file_path = os.path.join(root, file)
        fo = create_test_file_object(bin_path=file_path)
        fo.binary = get_binary_from_file(file_path)
        fo.root_uid = FW_FOUR_FOLDER.root_uid
        fo.depth = 2
        FW_FOUR.add_included_file(fo)
        FO_FOUR_LIST.append(fo)

FW_FIVE = create_test_firmware(device_name='dev_2_firmware_2', bin_path='firmware5/firmware_nested_2.zip', all_files_included_set=True)
FW_FIVE_FOLDER = create_test_file_object(bin_path='firmware5/folder')
# create file objects for all files in firmware5/folder/
FO_FIVE_LIST = []
FO_FIVE_LIST.append(FW_FIVE_FOLDER)
for root, dirs, files in os.walk(f'{TEST_DATA_DIR}/firmware5/folder'):
    for file in files:
        file_path = os.path.join(root, file)
        fo = create_test_file_object(bin_path=file_path)
        fo.binary = get_binary_from_file(file_path)
        fo.root_uid = FW_FIVE_FOLDER.root_uid
        fo.depth = 2
        FW_FIVE.add_included_file(fo)
        FO_FIVE_LIST.append(fo)

class DbMock:
        
    def get_objects_by_uid_list(
        self, uid_list: list[str] | set[str], analysis_filter: list[str] | None = None
    ) -> list[FileObject]:
        file_objects = []
        
        for uid in uid_list:
            # Check which test firmware the uid belongs to and return the corresponding file object
            if uid in FW_ONE.list_of_all_included_files:
                file_objects.append(FO_ONE)
            elif uid in FW_TWO.list_of_all_included_files:
                file_objects.append(FO_TWO)
            elif uid in FW_THREE.list_of_all_included_files:
                file_objects.append(FO_THREE)
            elif uid in FW_FOUR.list_of_all_included_files:
                # find the file object in FW_FOUR with the matching uid
                for fo in FO_FOUR_LIST:
                    if fo.uid == uid:
                        file_objects.append(fo)
                        break
            elif uid in FW_FIVE.list_of_all_included_files:
                # find the file object in FW_FIVE with the matching uid
                for fo in FO_FIVE_LIST:
                    if fo.uid == uid:
                        file_objects.append(fo)
                        break
        
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
    
    def setup_plugin(self):
        return ComparePlugin(db_interface=DbMock(), view_updater=CommonDatabaseMock())
    
    def setup_test_fw(self):
        """
        Mockup firmware files with included config files similar to each other for testing of identification, parsing, and comparison
        """
        self.fw_one = FW_ONE
        self.fo_one = FO_ONE
        self.fw_two = FW_TWO
        self.fw_three = FW_THREE
        
    def test_setup_selfcheck(self):        
        # Check file and firmware objects
        assert isinstance(self.fw_one, FileObject), 'fw_one is not a FileObject'
        assert isinstance(self.fw_two, FileObject), 'fw_two is not a FileObject'
        assert isinstance(self.fw_three, FileObject), 'fw_three is not a FileObject'
        assert isinstance(FW_FOUR, FileObject), 'FW_FOUR is not a FileObject'
        assert isinstance(FW_FIVE, FileObject), 'FW_FIVE is not a FileObject'
        assert isinstance(FO_FOUR_LIST[0], FileObject), 'FO_FOUR_LIST[0] is not a FileObject'
        assert isinstance(FO_FIVE_LIST[0], FileObject), 'FO_FIVE_LIST[0] is not a FileObject'
        
        assert isinstance(self.fw_one, Firmware), 'fw_one is not a Firmware'
        assert isinstance(self.fw_two, Firmware), 'fw_two is not a Firmware'
        assert isinstance(self.fw_three, Firmware), 'fw_three is not a Firmware'
        assert isinstance(FW_FOUR, Firmware), 'FW_FOUR is not a Firmware'
        assert isinstance(FW_FIVE, Firmware), 'FW_FIVE is not a Firmware'
        
        # Check contents
        assert len(self.fw_one.list_of_all_included_files) == 1, 'fw_one should have 1 included file'
        assert len(self.fw_two.list_of_all_included_files) == 1, 'fw_two should have 1 included file'
        assert len(self.fw_three.list_of_all_included_files) == 1, 'fw_three should have 1 included file'
        assert len(FW_FOUR.list_of_all_included_files) == 5, 'FW_FOUR should have 5 included files'
        assert len(FW_FIVE.list_of_all_included_files) == 5, 'FW_FIVE should have 5 included files'
        
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
    
    def test_compare_function_components(self):
        # fo_list is the list of firmware objects to be compares
        fo_list = [self.fw_one, self.fw_two, self.fw_three]
        
        # get all uids
        included_file_uids = self.c_plugin._get_included_uids(fo_list)
        
        #  get full file object for all uids
        file_objects = self.c_plugin._get_objects_from_uids(included_file_uids)
        assert all(isinstance(fo, FileObject) for fo in file_objects), 'All returned objects should be FileObjects'

        # only keep config files - filter out non config files based on extension and file type
        config_files = self.c_plugin._filter_config_files(file_objects)
        assert all(isinstance(fo, FileObject) for fo in config_files), 'All returned objects should be FileObjects'

        # get uid list for filtered config files
        config_file_uids = self.c_plugin._get_uid_list_from_file_objects(config_files)
        assert is_list_of_uids(config_file_uids), 'Config file uids should be a list of uids'

        # transform to list of vfp + uids that share that vfp
        # shared_vfps = self.c_plugin._get_shared_vfps(config_file_uids_with_vfps)
        # assert isinstance(shared_vfps, dict), 'Shared vfps should be a dict'

        # parse configs
        parsed_config_parameters = self.c_plugin._parse_config_from_fo_list(config_files)
        assert isinstance(parsed_config_parameters, dict), 'Parsed config parameters should be a dict'
    
    def test_compare_function(self):
        result = self.c_plugin.compare_function([self.fw_one, self.fw_two, self.fw_three], {})
        # result == dict[str, dict]
        assert isinstance(result, dict), 'Result should be a dictionary'
        assert all(isinstance(value, dict) for value in result.values()), 'Each value in result should be a dictionary'
    
    def test_identification(self):
        # Create file objects with different extensions and file type analysis results to test config type determination
        fo_dualkey = create_test_file_object(bin_path='firmware1/config/example.config')
        fo_dualkey.binary = get_binary_from_file(f'{TEST_DATA_DIR}/firmware1/config/example.config')
        fo_dualkey.processed_analysis['file_type'] = {'mime': 'text/plain'}
        
        fo_dualkey_b = create_test_file_object(bin_path='firmware1/config/example.b.config')
        fo_dualkey_b.binary = get_binary_from_file(f'{TEST_DATA_DIR}/firmware1/config/example.b.config')
        fo_dualkey_b.processed_analysis['file_type'] = {'mime': 'text/plain'}
        
        fo_xml = create_test_file_object(bin_path='firmware1/config/example.xml')
        fo_xml.binary = get_binary_from_file(f'{TEST_DATA_DIR}/firmware1/config/example.xml')
        fo_xml.processed_analysis['file_type'] = {'mime': 'text/plain'}
        
        fo_toml = create_test_file_object(bin_path='firmware1/config/example.toml')
        fo_toml.binary = get_binary_from_file(f'{TEST_DATA_DIR}/firmware1/config/example.toml')
        fo_toml.processed_analysis['file_type'] = {'mime': 'text/plain'}
        
        fo_general_config = create_test_file_object(bin_path='firmware1/config/example')
        fo_general_config.binary = get_binary_from_file(f'{TEST_DATA_DIR}/firmware1/config/example')
        fo_general_config.processed_analysis['file_type'] = {'mime': 'text/plain'}
        
            # false positives
        fo_js = create_test_file_object(bin_path='firmware1/config/example.js')
        fo_js.binary = get_binary_from_file(f'{TEST_DATA_DIR}/firmware1/config/example.js')
        fo_js.processed_analysis['file_type'] = {'mime': 'application/javascript'}
        
        # is config file?
        assert self.c_plugin._is_config_file(fo_dualkey) == True, 'Should identify .config file as config file'
        assert self.c_plugin._is_config_file(fo_dualkey_b) == True, 'Should identify .b.config file as config file'
        assert self.c_plugin._is_config_file(fo_xml) == True, 'Should identify .xml file as config file'
        assert self.c_plugin._is_config_file(fo_toml) == True, 'Should identify .toml file as config file'
        assert self.c_plugin._is_config_file(fo_general_config) == True, 'Should identify file with no extension as config file'
        assert self.c_plugin._is_config_file(fo_js) == False, 'Should not identify application/javascript file as config file' 
    
        # what type?
        assert self.c_plugin._determine_config_type(fo_dualkey) == 'dualkey', 'Config type should be dualkey for .config files with dual key content'
        assert self.c_plugin._determine_config_type(fo_dualkey_b) == 'dualkey', 'Config type should be dualkey for .b.config files with dual key content'
        assert self.c_plugin._determine_config_type(fo_xml) == 'xml', 'Config type should be xml for .xml files'
        assert self.c_plugin._determine_config_type(fo_toml) == 'toml', 'Config type should be toml for .toml files'
        assert self.c_plugin._determine_config_type(fo_general_config) == None, 'Config type should be None for unknown file types'
        assert self.c_plugin._determine_config_type(fo_js) == None, 'Config type should be None for application/javascript files'
    
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
        example_content_spaces = b"""
        type key value
        
        ; network config
        network port 8080
        network bind 0.0.0.0
        network protocol tcp
        
        ; database config
        database host localhost
        database port 3306
        """
        expected_output_spaces = {
            'type key': 'value',
            'network port': '8080',
            'network bind': '0.0.0.0',
            'network protocol': 'tcp',
            'database host': 'localhost',
            'database port': '3306'
        }
        example_content_equals = b"""
        type key value
        
        ; network config
        network port=8080
        network bind=0.0.0.0
        network protocol=tcp
        
        ; database config
        database host=localhost
        database port=3306
        database description=main database
        """
        expected_output_equals = {
            'type key': 'value',
            'network port': '8080',
            'network bind': '0.0.0.0',
            'network protocol': 'tcp',
            'database host': 'localhost',
            'database port': '3306',
            'database description': 'main database'
        }
        output = self.c_plugin._parse_helper_dualkey(example_content_spaces)
        assert output == expected_output_spaces, f'Unexpected output'
        output = self.c_plugin._parse_helper_dualkey(example_content_equals)
        assert output == expected_output_equals, f'Unexpected output'
        
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
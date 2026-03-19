import pytest

from test.common_helper import CommonDatabaseMock
from plugins.compare.file_config.code.file_config import ComparePlugin
from test.unit.compare.compare_plugin_test_class import ComparePluginTest

class DbMock:
    def get_entropy_for_uid_list(self, uid_list):
        return {uid: 0.2 for uid in uid_list}

    def get_ssdeep_hash_for_uid_list(self, uid_list):
        return {uid: '42' for uid in uid_list}

    def get_vfp_of_included_text_files(self, root_uid, blacklist=None):
        if root_uid == '418a54d78550e8584291c96e5d6168133621f352bfc1d43cf84e81187fef4962_787':
            return {'/foo': {'uid_1'}, '/bar': {'uid_2', 'uid_3'}}
        if root_uid == 'd38970f8c5153d1041810d0908292bc8df21e7fd88aab211a8fb96c54afe6b01_319':
            return {'/foo': {'uid_4'}, '/bar': {'uid_5'}}
        return {}

class TestComparePluginFileConfig(ComparePluginTest):
    # An initialized plugin instance is available at self.c_plugin
    PLUGIN_NAME = 'file_config'
    PLUGIN_CLASS = ComparePlugin
    
    def setup_plugin(self):
        """
        This function must be overwritten by the test instance.
        In most cases it is sufficient to copy this function.
        """
        return ComparePlugin(db_interface=DbMock(), view_updater=CommonDatabaseMock())
    
    def test_compare_function(self):
        result = self.c_plugin.compare_function([self.fw_one, self.fw_two], {})
        assert isinstance(result, dict), 'result is not a dict'
        assert 'config_parameters' in result, 'config_parameters field not present in result'
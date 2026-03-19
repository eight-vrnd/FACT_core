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
    PLUGIN_NAME = 'file_config'
    PLUGIN_CLASS = ComparePlugin
    
    def setup_plugin(self):
        """
        This function must be overwritten by the test instance.
        In most cases it is sufficient to copy this function.
        """
        return ComparePlugin(db_interface=DbMock(), view_updater=CommonDatabaseMock())
    
    # def test_basic(self):
    #     '''
    #     An initialized plugin instance is available at self.c_plugin
    #     '''
    #     result = self.c_plugin.compare_function([self.fw_one, self.fw_two, self.fw_three], {})
        
    def test_get_exclusive_files(self):
        result = self.c_plugin._get_exclusive_files([self.fw_one, self.fw_two])
        assert isinstance(result, dict), 'result is not a dict'
        assert self.fw_one.uid in result, 'fw_one entry not found in result'
        assert self.fw_two.uid in result, 'fw_two entry not found in result'
        assert self.fw_one.uid in result[self.fw_one.uid], 'fw_one not exclusive to one'
        assert self.fw_two.uid not in result[self.fw_one.uid], 'fw_two in exclusive file of fw one'
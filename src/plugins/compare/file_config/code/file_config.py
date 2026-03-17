from compare.PluginBase import CompareBasePlugin


class ComparePlugin(CompareBasePlugin):
    '''
    This plugin allows comparison of two (or more) configuration files. It handles identifying, parsing, and displaying config file key/value pairs for a variety of configuration file types
    '''

    NAME = 'file_config'
    DEPENDENCIES = []
    VERSION = '0.0.1'

    def compare_function(self, fo_list):
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


        
        result = {}

        # your code...

        return result
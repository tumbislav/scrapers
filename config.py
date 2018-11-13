# encoding: utf-8

"""
File: config.py

Configuration handler for the scrapers package.
"""
__author__ = 'Marko Čibej'

import pkg_resources
import logging
import yaml
from typing import Union, List, Any
from helper import ScraperException


logger = logging.getLogger('scr')


class Configuration:
    """
    Contains the current configuration parameters.
    """

    def __init__(self, config_file_name: str):
        """
        Sets the starting parameters and loads the configurations

        :param config_file_name: the name of the initial config file
        """
        self.config_file_name = config_file_name
        self.maps: dict = None
        self.load_config()

    def load_config(self):
        """
        Open and load the config file. Do some top-level validation to make sure it's a valid YAML and
        that the expected top elements are present. Also initializes the GLOBAL branch
        """
        self.maps = self.load_yaml(self.config_file_name)

        # process includes, if any
        if 'include' in self.maps:
            for k, v in self.maps['include'].items():
                if k in self.maps:
                    raise ScraperException('Configuration.load', 'duplicate section name {}, on include'.format(k))
                else:
                    self.maps[k] = self.load_yaml(v)

        if 'sites' not in self.maps or not isinstance(self.maps['sites'], dict):
            logger.error('"sites" section of the configuration is missing or is not a map')
            raise ScraperException('Configuration.load', 'missing sites section, or section is not a map')

        if 'GLOBAL' not in self.maps:
            self.maps['GLOBAL'] = {}

    @staticmethod
    def load_yaml(filename: str):
        """
        Load a yaml file into a Python dictionary and do the preliminary sanity check

        :param filename: the filename, including the 'yaml' extension
        :return: the parsed dictionary
        """
#            raise ScraperException('Configuration.load_yaml', 'file {} not found'.format(full_path))

        # get the file contents and run them through yaml
        try:
            yaml_string = pkg_resources.resource_string(__name__, 'assets/' + filename).decode('utf-8')
            the_map = yaml.load(yaml_string)
        except yaml.YAMLError as ye:
            raise ScraperException('Configuration.load_yaml', ye)

        if not isinstance(the_map, dict):
            raise ScraperException('Configuration.load_yaml', 'file contents should map to a dictionary')
        logger.debug('Loaded configuration file {}.'.format(filename))

        return the_map

    def get_section(self, section: List[str], must_exist=False) -> Union[str, dict]:
        """
        Get a section of the configuration, potentially many levels deep.

        :param section: a section name or an array of section names, the path to the section sought
        :param must_exist: whether the method throws an exception if the section is not found
        :return: the section found or None
        """
        found = self.maps
        if not isinstance(section, list):
            section = [section]
        for s in section:
            if s in found:
                found = found[s]
            else:
                found = None
                break

        if must_exist and found is None:
            raise ScraperException('Configuration.get_section', 'section {} not found'.format(section))

        return found

    def get_value(self, section: List[str], key: str, default=None) -> Any:
        """
        Get a  parameter within a section.

        :param section: the path to the section
        :param key: the key of the section
        :param default: the default value, if the section or the key is not found
        :return: the value found or default
        """
        sect = self.get_section(section)
        if sect is not None:
            if key in sect:
                return sect[key]

        return default

    def get_site(self, site: str) -> dict:
        """
        Get a site definition.

        :param site: the name of the site
        :return: a dictionary containing the site setup
        """
        return self.get_section(['sites', site], True)

    def set_global(self, param: str, value: Any) -> Any:
        """
        Set the value of a global parameter.
        :param param: the parameter name
        :param value: the parameter value
        :return: the previous value of the parameter, if any
        """
        previous = self.maps['GLOBAL'][param] if param in self.maps['GLOBAL'] else None
        self.maps['GLOBAL'][param] = value
        return previous

    def get_global(self, param: str, default: Any=None) -> Any:
        """
        Retrieve the value of a global parameter.
        :param param: the parameter name
        :param default: the default value; if it is None and if the parameter is not present, an exception is raised
        :return: the value of the parameter or the default
        """
        if param not in self.maps['GLOBAL'] and default is None:
            raise ScraperException('get_global', 'parameter {} not set and no default given'.format(param))
        return self.maps['GLOBAL'][param] if param in self.maps['GLOBAL'] else default
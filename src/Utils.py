"""
Utility Functions and Helper Classes

This module provides various utility functions and helper classes used throughout
the Topology Alchemy framework, including:

- Logger configuration and initialization
- Text transliteration for special characters (e.g., Greek characters)
- ID sanitization for different output formats
- Singleton pattern implementation

These utilities ensure consistent handling of identifiers, logging, and special
characters across all importers and exporters.

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.

Classes:
    Transliterate: Static class for character transliteration
    SingletonMeta: Metaclass for implementing singleton pattern
    Sanitizer: ID sanitization and formatting utility

Functions:
    getLogger: Legacy logger initialization (deprecated, use alchemist.get_logger instead)
"""

import logging,coloredlogs
import sys

def getLogger(args):  
  coloredlogs.install()
  logger = logging.getLogger("TopologyAlchemy")
  logger.setLevel(logging._nameToLevel[args.log])
  logger.info("Current parameters:")
  for arg in [a for a in dir(args) if not a.startswith('_')]:
      logger.info("  {} -> {}".format(arg,getattr(args,arg)))
  logger.debug("verbosity turned on")
  logger.debug('> Parsing settings file..')
  return logger

class Transliterate:
  activeTranslit = None

  translitDicts = {
      'greek': {
        '\u0392': 'B',
        '\u039C': 'M'
      }
  }

  @staticmethod
  def activateTranslit(translit):
    Transliterate.activeTranslit = translit

  @staticmethod
  def process(word):
    if Transliterate.activeTranslit is None:
      return word
    
    if not isinstance(word, str):
      word=str(word)
    
    converted_word = ''
    for char in word:
        transchar = ''
        if char in Transliterate.translitDicts[Transliterate.activeTranslit]:
            transchar = Transliterate.translitDicts[Transliterate.activeTranslit][char]
        else:
            transchar = char
        converted_word += transchar
    return converted_word

class SingletonMeta(type):
    """
    The Singleton class can be implemented in different ways in Python. Some
    possible methods include: base class, decorator, metaclass. We will use the
    metaclass because it is best suited for this purpose.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

class Sanitizer():
  def __init__(self,system="",prefix=""):       
    self.system = system
    self.prefix = prefix if prefix != None else ""
      
  def setPrefix(self, prefix):
    self.prefix = prefix

  def setSystem(self, system):
    self.system = system
    
  def sanitizeId(self, s):
    rules = {
      ' ': '%20',
      '#': '%23',
      '&': '%26',
      '*': '%2A',
      '.': '%2E',
      '/': '%2F',
      '>': '%3E'
    }
    prefix = self.prefix+"_" if self.prefix != "" else ""
    system= self.system+"_" if self.system != "" else ""
    
    s = '{0}{1}{2}'.format(system,prefix, s)
    for key in rules:
        value = rules.get(key)
        s = s.replace(key, value)
    return s
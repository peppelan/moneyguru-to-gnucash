#!/usr/bin/env python
import logging
import sys
import xml.etree.cElementTree as ET

from gnucash import Session, Transaction, Split, GncNumeric

unrecognisedDict = dict()

# Use this to remember missed stuff
def warnUnrecognised(thing):
  if thing in unrecognisedDict.keys():
     unrecognisedDict[thing] = unrecognisedDict[thing] + 1
  else:
     unrecognisedDict[thing] = 1

# Main
if __name__ == '__main__':
  # Set up:
  if len(sys.argv) != 3:
    logging.fatal('Wrong arguments. Usage: ./script.py [input_moneyguru_file] [output_gnucash_file]')
    sys.exit(1)

  # - source file
  root = ET.parse(sys.argv[1]).getroot()
  if root.tag != 'moneyguru-file':
    logging.fatal('Urecognized file format')
    sys.exit(1)

  # - destination file
  session = Session(sys.argv[2])

  # The parsing itself
  for child in root: 
    # TODO do something
    
    # Don't know what to do with it
    warnUnrecognised(child.tag)

  # Wrap up
  session.end()
  for thing, count in unrecognisedDict.items():
     print "Missed " + str(count) + " entities of type " + thing

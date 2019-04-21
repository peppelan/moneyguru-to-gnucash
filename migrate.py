#!/usr/bin/env python
from unidecode import unidecode
import logging
import sys

import gnucash
import xml.etree.cElementTree as ET

unrecognisedDict = dict()
migratedDict = dict()

moneyGuruToGnuCashAccountType = {
  'asset' : gnucash.ACCT_TYPE_ASSET,
  'liability' : gnucash.ACCT_TYPE_LIABILITY,
  'income' : gnucash.ACCT_TYPE_INCOME,
  'expense' : gnucash.ACCT_TYPE_EXPENSE,
}

# Use this to remember missed stuff
def warnUnrecognised(thing):
  if thing in unrecognisedDict.keys():
     unrecognisedDict[thing] = unrecognisedDict[thing] + 1
  else:
     unrecognisedDict[thing] = 1

# Use this to remember migrated stuff
def markMigrated(thing):
  if thing in migratedDict.keys():
     migratedDict[thing] = migratedDict[thing] + 1
  else:
     migratedDict[thing] = 1

# Main
if __name__ == '__main__':
  # Set up:
  logging.basicConfig(level=logging.INFO)

  if len(sys.argv) != 3:
    logging.fatal('Wrong arguments. Usage: ./script.py [input_moneyguru_file] [output_gnucash_file]')
    sys.exit(1)

  # - source file
  root = ET.parse(sys.argv[1]).getroot()
  if root.tag != 'moneyguru-file':
    logging.fatal('Urecognized file format')
    sys.exit(1)

  # - destination file
  session = gnucash.Session(sys.argv[2], is_new=True)

  # The parsing itself
  for child in root: 
    if child.tag == 'group': # Groups
      groupName = unidecode(unicode(child.attrib['name']))
      groupType = child.attrib['type']

      acc = gnucash.Account(session.book)
      acc.SetName(groupName)
      acc.SetType(moneyGuruToGnuCashAccountType[groupType]) 
      acc.SetCommodity(session.book.get_table().lookup("CURRENCY", "EUR")) # TODO: default ccy

      session.book.get_root_account().append_child(acc)

      markMigrated(child.tag)
    elif child.tag == 'account': # Accounts
      # account currency="EUR" group="Chiusi" name="Bollette" type="expense"
      acctName = unidecode(unicode(child.attrib['name']))
      acctType = child.attrib['type']
      acctCcy  = child.attrib['currency']
      if 'group' in child.attrib.keys():
        acctGroup = unidecode(unicode(child.attrib['group']))
      else:
        acctGroup = None

      acc = gnucash.Account(session.book)
      acc.SetName(acctName)
      acc.SetType(moneyGuruToGnuCashAccountType[acctType]) 
      acc.SetCommodity(session.book.get_table().lookup("CURRENCY", acctCcy))

      if None != acctGroup:
        session.book.get_root_account().lookup_by_name(acctGroup).append_child(acc)
      else:
        session.book.get_root_account().append_child(acc)

      markMigrated(child.tag)

    else: # Don't know what to do with it
      warnUnrecognised(child.tag)

  # Wrap up
  session.save()
  session.end()
  for thing, count in unrecognisedDict.items():
     logging.warn("Missed " + str(count) + " entities of type " + thing)

  for thing, count in migratedDict.items():
     logging.info("Migrated " + str(count) + " entities of type " + thing)

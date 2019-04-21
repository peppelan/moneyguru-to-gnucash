#!/usr/bin/env python
import datetime
from decimal import Decimal
import logging
import sys
import time
from unidecode import unidecode

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
  DEFAULT_CCY = session.book.get_table().lookup("CURRENCY", "EUR")

  # The parsing itself
  for child in root: 
    if child.tag == 'group': # Groups
      groupName = unidecode(unicode(child.attrib['name']))
      groupType = child.attrib['type']

      acc = gnucash.Account(session.book)
      acc.SetName(groupName)
      acc.SetType(moneyGuruToGnuCashAccountType[groupType]) 
      acc.SetCommodity(DEFAULT_CCY)

      session.book.get_root_account().append_child(acc)

      markMigrated(child.tag)
    elif child.tag == 'account': # Accounts
      acctName = unidecode(unicode(child.attrib['name']))
      acctType = child.attrib['type']
      acctCcy  = child.attrib['currency']

      acc = gnucash.Account(session.book)
      acc.SetName(acctName)
      acc.SetType(moneyGuruToGnuCashAccountType[acctType]) 
      acc.SetCommodity(session.book.get_table().lookup("CURRENCY", acctCcy))

      if 'group' in child.attrib.keys():
        acctGroup = unidecode(unicode(child.attrib['group']))
        session.book.get_root_account().lookup_by_name(acctGroup).append_child(acc)
      else:
        session.book.get_root_account().append_child(acc)

      markMigrated(child.tag)
    elif child.tag == 'transaction': # Transactions
      txDescription = unidecode(unicode(child.attrib['description']))
      year, month, day = map(int, child.attrib['date'].split('-'))

      if 'payee' in child.attrib.keys():
        memo = unidecode(unicode(child.attrib['description']))
      else:
        memo = None

      tx = gnucash.Transaction(session.book)
      tx.BeginEdit()
      tx.SetDateEnteredSecs(float(child.attrib['mtime']))
      tx.SetDate(day, month, year)
      tx.SetDescription(txDescription)

      # Apparently, MoneyGuru supports transactions in multiple currencies (the currency is defined at split level),
      # while GnuCash does not (the currency is defined at transaction level).
      # For this reason, we'll put all transactions on the default currency and warn the users to fix the cases when
      # this is not the right choice
      tx.SetCurrency(DEFAULT_CCY)

      for grandchild in child: # Splits (also called legs)
        if grandchild.tag == 'split':
           splAccount = unidecode(unicode(grandchild.attrib['account'])) # This is empty string for imbalances in MoneyGuru
           splAmountStr = grandchild.attrib['amount'].split()[-1]

           if not grandchild.attrib['amount'] == '0.00' and \
                not grandchild.attrib['amount'].startswith(DEFAULT_CCY.get_mnemonic()):
             logging.warn("Leg of transaction \"" + txDescription + "\" on account \"" + splAccount + "\" for date " + 
                child.attrib['date'] + " has been added in " + DEFAULT_CCY.get_mnemonic() + " but in MoneyGuru is of " +
                grandchild.attrib['amount'])

           amount = int(Decimal(splAmountStr) * DEFAULT_CCY.get_fraction())
           spl = gnucash.Split(session.book)
           spl.SetParent(tx)
           if "" != splAccount:
             spl.SetAccount(session.book.get_root_account().lookup_by_name(splAccount))
           spl.SetValue(gnucash.GncNumeric(amount, DEFAULT_CCY.get_fraction()))
           spl.SetAmount(gnucash.GncNumeric(amount, DEFAULT_CCY.get_fraction()))

           if 'reconciliation_date' in grandchild.attrib.keys():
             recYear, recMonth, recDay = map(int, grandchild.attrib['reconciliation_date'].split('-'))
             recDate = datetime.datetime(day=recDay, month=recMonth, year=recYear)
             spl.SetDateReconciledSecs(int(time.mktime(recDate.timetuple())))
             spl.SetReconcile('y')
             
           if memo != None:
             spl.SetMemo(memo)
        else:
          warnUnrecognised(grandchild.tag)

      tx.CommitEdit()
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

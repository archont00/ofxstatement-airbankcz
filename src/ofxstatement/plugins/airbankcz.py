import csv
from datetime import datetime
import re

from ofxstatement import statement
from ofxstatement.parser import CsvStatementParser
from ofxstatement.plugin import Plugin
from ofxstatement.statement import Statement


class AirBankCZPlugin(Plugin):
    """Airbank a.s. (CZ) plugin (CSV, UTF-8)
    Note that it cannot deal with fee ("Poplatek v měně účtu"), which is ignored for now
    """

    def get_parser(self, filename):
        # Encoding may be set in Air Bank internet banking (Settings / Applications)
        AirBankCZPlugin.encoding = self.settings.get('charset', 'utf-8')
        f = open(filename, "r", encoding=AirBankCZPlugin.encoding)
        parser = AirBankCZParser(f)
        parser.statement.currency = self.settings.get('currency', 'CZK')
        parser.statement.bank_id = self.settings.get('bank', 'AIRACZPP')
        parser.statement.account_id = self.settings.get('account', '')
        parser.statement.account_type = self.settings.get('account_type', 'CHECKING')
        parser.statement.trntype = "OTHER"
        return AirBankCZParser(filename)


class AirBankCZParser(CsvStatementParser):

    # The columns are:
    # 01 Datum provedení
    # 02 Směr platby
    # 03 Typ platby
    # 04 Skupina plateb
    # 05 Měna účtu
    # 06 Částka v měně účtu
    # 07 Poplatek v měně účtu
    # 08 Původní měna platby
    # 09 Původní částka platby
    # 10 Název protistrany
    # 11 Číslo účtu protistrany
    # 12 Název účtu protistrany
    # 13 Variabilní symbol
    # 14 Konstantní symbol
    # 15 Specifický symbol
    # 16 Zdrojová obálka
    # 17 Cílová obálka
    # 18 Poznámka pro mne
    # 19 Zpráva pro příjemce
    # 20 Poznámka k platbě
    # 21 Název karty
    # 22 Číslo karty
    # 23 Držitel karty
    # 24 Obchodní místo
    # 25 Směnný kurz
    # 26 Odesílatel poslal
    # 27 Poplatky jiných bank
    # 28 Datum a čas zadání
    # 29 Datum splatnosti
    # 30 Datum schválení
    # 31 Datum zaúčtování
    # 32 Referenční číslo
    # 33 Způsob zadání
    # 34 Zadal
    # 35 Zaúčtováno
    # 36 Pojmenování příkazu
    # 37 Název, adresa a stát protistrany
    # 38 Název, adresa a stát banky protistrany
    # 39 Typ poplatku
    # 40 Účel platby
    # 41 Zvláštní pokyny k platbě
    # 42 Související platby

    mappings = {"date_user": 31,
                "date": 1,
                "memo": 20,
                "payee": 10,
                "amount": 6,
                "check_no": 13,
                "refnum": 32, }

    date_format = "%d/%m/Y"

    def split_records(self):
        """Return iterable object consisting of a line per transaction
        """
        # Field delimiter may be set in Air Bank internet banking (Settings / Applications)
        return csv.reader(self.fin, delimiter=',', quotechar='"')

    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object
        """

        # Ignore the 1st line of CSV
        if self.cur_record <= 1:
            return None

        StatementLine = super(AirBankCZParser, self).parse_record(line)
        StatementLine.date_user = datetime.strptime(StatementLine.date_user, self.date_format)
        StatementLine.id = statement.generate_transaction_id(StatementLine)

        # Manually set some of the known transaction types
        if line[3].startswith("Daň z úroku"):
            StatementLine.trntype = "DEBIT"
        if line[3].startswith("Kreditní úrok"):
            StatementLine.trntype = "INT"
        if line[3].startswith("Poplatek za "):
            StatementLine.trntype = "FEE"

        # .payee is imported as "Description" in GnuCash
        # .memo  is imported as "Notes"       in GnuCash
        # When .payee is empty, GnuCash imports .memo to "Description" and keeps "Notes" empty

        # StatementLine.payee = "Název protistrany" + "Číslo účtu protistrany"
        if not line[11]:
            StatementLine.payee = StatementLine.payee + line[11]

        # StatementLine.memo = "Poznámka k platbě" + the payment identifiers
        if not line[13]:
            StatementLine.memo = sl.memo + "|VS: " + line[13]
        if not line[14]:
            StatementLine.memo = sl.memo + "|KS: " + line[14]
        if not line[15]:
            StatementLine.memo = sl.memo + "|SS: " + line[15]

        if StatementLine.amount == 0:
            return None

        return StatementLine

    def __init__(self, filename):
        self.filename = filename

    def parse(self):
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        with open(self.filename, "r") as f:
            self.input = f
            return super(AirBankCZParser, self).parse()

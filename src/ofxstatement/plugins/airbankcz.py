import csv
from datetime import datetime
import re

from ofxstatement import statement
from ofxstatement.parser import CsvStatementParser
from ofxstatement.plugin import Plugin


class AirBankCZPlugin(Plugin):
    """Air Bank a.s. (Czech Republic) (CSV, UTF-8)
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
        return parser


class AirBankCZParser(CsvStatementParser):
    date_format = "%d/%m/%Y"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.columns = None
        self.mappings = None

    def split_records(self):
        """Return iterable object consisting of a line per transaction
        """
        # Field delimiter may be set in Air Bank internet banking (Settings / Applications)
        return csv.reader(self.fin, delimiter=',', quotechar='"')

    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object
        """

        # First line of CSV file contains headers, not an actual transaction
        if self.cur_record == 1:
            # Prepare columns headers lookup table for parsing
            self.columns = {v: i for i,v in enumerate(line)}
            self.mappings = {
                "date": self.columns['Datum provedení'],
                "memo": self.columns['Poznámka k úhradě'],
                "payee": self.columns['Název protistrany'],
                "amount": self.columns['Částka v měně účtu'],
                "check_no": self.columns['Variabilní symbol'],
                "refnum": self.columns['Referenční číslo'],
            }
            # And skip further processing by parser
            return None

        # Shortcut
        columns = self.columns

        # Normalize string
        for i,v in enumerate(line):
            line[i] = v.strip()

        if line[columns["Částka v měně účtu"]] == '':
            line[columns["Částka v měně účtu"]] = "0"
        if line[columns["Poplatek v měně účtu"]] == '':
            line[columns["Poplatek v měně účtu"]] = "0"

        StatementLine = super(AirBankCZParser, self).parse_record(line)

        # Ignore lines, which do not have posting date yet (typically pmts by debit cards
        # have some delays).
        if not line[columns["Datum zaúčtování"]]:
            return None
        else:
            StatementLine.date_user = line[columns["Datum zaúčtování"]]
            StatementLine.date_user = datetime.strptime(StatementLine.date_user, self.date_format)

        StatementLine.id = statement.generate_transaction_id(StatementLine)

        # Manually set some of the known transaction types
        payment_type = line[columns["Typ úhrady"]]
        if payment_type.startswith("Daň z úroku"):
            StatementLine.trntype = "DEBIT"
        elif payment_type.startswith("Kreditní úrok"):
            StatementLine.trntype = "INT"
        elif payment_type.startswith("Poplatek za "):
            StatementLine.trntype = "FEE"
        elif payment_type.startswith("Příchozí úhrada"):
            StatementLine.trntype = "XFER"
        elif payment_type.startswith("Vrácení peněz"):
            StatementLine.trntype = "XFER"
        elif payment_type.startswith("Odchozí úhrada"):
            StatementLine.trntype = "XFER"
        elif payment_type.startswith("Výběr hotovosti"):
            StatementLine.trntype = "ATM"
        elif payment_type.startswith("Platba kartou"):
            StatementLine.trntype = "POS"
        elif payment_type.startswith("Inkaso"):
            StatementLine.trntype = "DIRECTDEBIT"
        elif payment_type.startswith("Trvalý"):
            StatementLine.trntype = "REPEATPMT"
        else:
            print("WARN: Unexpected type of payment appeared - \"{}\". Using XFER transaction type instead".format(payment_type))
            StatementLine.trntype = "XFER"

        # .payee becomes OFX.NAME which becomes "Description" in GnuCash
        # .memo  becomes OFX.MEMO which becomes "Notes"       in GnuCash
        # When .payee is empty, GnuCash imports .memo to "Description" and keeps "Notes" empty

        # StatementLine.payee = "Název protistrany" + "Číslo účtu protistrany"
        if line[columns["Číslo účtu protistrany"]] != "":
            StatementLine.payee += "|ÚČ: " + line[columns["Číslo účtu protistrany"]]

        # StatementLine.memo = "Poznámka k úhradě" + the payment identifiers
        if line[columns["Variabilní symbol"]] != "":
            StatementLine.memo += "|VS: " + line[columns["Variabilní symbol"]]

        if line[columns["Konstantní symbol"]] != "":
            StatementLine.memo += "|KS: " + line[columns["Konstantní symbol"]]

        if line[columns["Specifický symbol"]] != "":
            StatementLine.memo += "|SS: " + line[columns["Specifický symbol"]]

        if line[columns["Název karty"]] != "":
            StatementLine.memo += "|Název karty: " + line[columns["Název karty"]]

        # Some type of fee is standalone, not related to transaction amount. Add it to amount field.only
        if float(line[columns["Poplatek v měně účtu"]]) != 0 and StatementLine.amount == 0:
            StatementLine.amount = float(line[columns["Poplatek v měně účtu"]])

        # Air Bank may show various fees on the same line as the underlying transaction.
        # In case there is a fee connected with the transaction, the fee is added as different transaction
        elif float(line[columns["Poplatek v měně účtu"]]) != 0 and StatementLine.amount != 0:
            fee_line = list(line)
            fee_line[columns['Částka v měně účtu']] = fee_line[columns["Poplatek v měně účtu"]]
            fee_line[columns['Poplatek v měně účtu']] = '0'
            fee_line[columns['Kategorie plateb']] = "Poplatek za transakci"
            fee_line[columns["Poznámka k úhradě"]] = "Poplatek: " + fee_line[columns["Poznámka k úhradě"]]

            # parse the newly generated fee_line and append it to the rest of the statements
            stmt_line = self.parse_record(fee_line)
            if stmt_line:
                stmt_line.assert_valid()
                self.statement.lines.append(stmt_line)

        if StatementLine.amount == 0:
            return None

        return StatementLine

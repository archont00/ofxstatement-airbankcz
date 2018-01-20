import csv
from datetime import datetime
import re

from ofxstatement import statement
from ofxstatement.parser import CsvStatementParser
from ofxstatement.plugin import Plugin
from ofxstatement.statement import Statement


class AirBankCZPlugin(Plugin):
    """Air Bank a.s. (Czech Republic) (CSV, UTF-8)
    NB: if there are any transaction related fees (column 06), a new CSV
        file is created and it has to be processed again:
        $ ofxstatement convert -t airbankcz in-fees.csv out-fees.ofx
    """

    def get_parser(self, filename):
        # .csvfile is a work-around and is used for exporting fees to a new CSV file
        AirBankCZPlugin.csvfile = re.sub(".csv", "", filename) + "-fees.csv"

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

        # Ignore the 1st line of CSV
        if self.cur_record == 1:
            # Create a heading line for the -fees.csv file
            with open(AirBankCZPlugin.csvfile, "w", encoding=AirBankCZPlugin.encoding) as output:
                writer = csv.writer(output, lineterminator='\n', delimiter=',', quotechar='"')
                writer.writerow(line)
                output.close()

                # Prepare columns headers lookup table for parsing
                self.columns = {v: i for i,v in enumerate(line)}
                self.mappings = {
                    "date": self.columns['Datum provedení'],
                    "memo": self.columns['Poznámka k platbě'],
                    "payee": self.columns['Název protistrany'],
                    "amount": self.columns['Částka v měně účtu'],
                    "check_no": self.columns['Variabilní symbol'],
                    "refnum": self.columns['Referenční číslo'],
                }
            # And skip further processing by parser
            return None

        # shortcut
        columns = self.columns

        #Normalize string
        line = list(map(lambda s: s.strip() if isinstance(s, str) else s, line))


        if line[columns["Částka v měně účtu"]] == '':
            line[columns["Částka v měně účtu"]] = "0"
        if line[columns["Poplatek v měně účtu"]] == '':
            line[columns["Poplatek v měně účtu"]] = "0"

        StatementLine = super(AirBankCZParser, self).parse_record(line)

        # Ignore lines, which do not have posting date yet (typically pmts by debet cards
        # have some delays).
        if not line[columns["Datum zaúčtování"]]:
            return None
        else:
            StatementLine.date_user = line[columns["Datum zaúčtování"]]
            StatementLine.date_user = datetime.strptime(StatementLine.date_user, self.date_format)

        StatementLine.id = statement.generate_transaction_id(StatementLine)

        # Manually set some of the known transaction types
        payment_type = columns["Typ platby"]
        if line[payment_type].startswith("Daň z úroku"):
            StatementLine.trntype = "DEBIT"
        elif line[payment_type].startswith("Kreditní úrok"):
            StatementLine.trntype = "INT"
        elif line[payment_type].startswith("Poplatek za "):
            StatementLine.trntype = "FEE"
        elif line[payment_type].startswith("Příchozí platba"):
            StatementLine.trntype = "XFER"
        elif line[payment_type].startswith("Odchozí platba"):
            StatementLine.trntype = "XFER"
        elif line[payment_type].startswith("Výběr hotovosti"):
            StatementLine.trntype = "ATM"
        elif line[payment_type].startswith("Platba kartou"):
            StatementLine.trntype = "POS"
        elif line[payment_type].startswith("Inkaso"):
            StatementLine.trntype = "DIRECTDEBIT"
        elif line[payment_type].startswith("Trvalý"):
            StatementLine.trntype = "REPEATPMT"
        else:
            StatementLine.trntype = "XFER"

        # .payee becomes OFX.NAME which becomes "Description" in GnuCash
        # .memo  becomes OFX.MEMO which becomes "Notes"       in GnuCash
        # When .payee is empty, GnuCash imports .memo to "Description" and keeps "Notes" empty

        # StatementLine.payee = "Název protistrany" + "Číslo účtu protistrany"
        if line[columns["Číslo účtu protistrany"]] != "":
            StatementLine.payee += "|ÚČ: " + line[columns["Číslo účtu protistrany"]]

        # StatementLine.memo = "Poznámka k platbě" + the payment identifiers
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

        # Air Bank may show various fees on the same line  as the underlying transaction
        # For now, we simply create a new CSV file with the fee amount moved to "Částka v měně účtu".
        # This new file -fees.csv needs to be processed again manually:
        #     $ ofxstatement convert -t airbankcz in-fees.csv out-fees.ofx

        # ToDo: instead of exporting the above to CSV, try to add the exportline to
        #       the end of statement (from imported input.csv).
        if float(line[columns["Poplatek v měně účtu"]]) != 0 and StatementLine.amount != 0:
            exportline = list(line)
            exportline[columns['Částka v měně účtu']] = exportline[columns["Poplatek v měně účtu"]]
            exportline[columns['Poplatek v měně účtu']] = ''
            exportline[columns['Původní částka platby']] = ''
            exportline[columns['Skupina plateb']] = "Poplatek za transakci"
            exportline[columns["Poznámka k platbě"]] = "Poplatek: " + exportline[columns["Poznámka k platbě"]]

            with open(AirBankCZPlugin.csvfile, "a", encoding=AirBankCZPlugin.encoding) as output:
                writer = csv.writer(output, lineterminator='\n', delimiter=',', quotechar='"')
                writer.writerow(exportline)

        if StatementLine.amount == 0:
            return None

        return StatementLine

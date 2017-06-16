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

    # The columns are:
    # 00 Datum provedení
    # 01 Směr platby
    # 02 Typ platby
    # 03 Skupina plateb
    # 04 Měna účtu
    # 05 Částka v měně účtu
    # 06 Poplatek v měně účtu
    # 07 Původní měna platby
    # 08 Původní částka platby
    # 09 Název protistrany
    # 10 Číslo účtu protistrany
    # 11 Název účtu protistrany
    # 12 Variabilní symbol
    # 13 Konstantní symbol
    # 14 Specifický symbol
    # 15 Zdrojová obálka
    # 16 Cílová obálka
    # 17 Poznámka pro mne
    # 18 Zpráva pro příjemce
    # 19 Poznámka k platbě
    # 20 Název karty
    # 21 Číslo karty
    # 22 Držitel karty
    # 23 Obchodní místo
    # 24 Směnný kurz
    # 25 Odesílatel poslal
    # 26 Poplatky jiných bank
    # 27 Datum a čas zadání
    # 28 Datum splatnosti
    # 29 Datum schválení
    # 30 Datum zaúčtování
    # 31 Referenční číslo
    # 32 Způsob zadání
    # 33 Zadal
    # 34 Zaúčtováno
    # 35 Pojmenování příkazu
    # 36 Název, adresa a stát protistrany
    # 37 Název, adresa a stát banky protistrany
    # 38 Typ poplatku
    # 39 Účel platby
    # 40 Zvláštní pokyny k platbě
    # 41 Související platby

    mappings = {"date": 0,
                "memo": 19,
                "payee": 9,
                "amount": 5,
                "check_no": 12,
                "refnum": 31, }

    date_format = "%d/%m/%Y"

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
            # And skip further processing by parser
            return None

        if line[5] == '':
            line[5] = "0"
        if line[6] == '':
            line[6] = "0"

        StatementLine = super(AirBankCZParser, self).parse_record(line)

        # Ignore lines, which do not have posting date yet (typically pmts by debet cards
        # have some delays.
        if not line[30]:
            return None
        else:
            StatementLine.date_user = line[30]
            StatementLine.date_user = datetime.strptime(StatementLine.date_user, self.date_format)

        StatementLine.id = statement.generate_transaction_id(StatementLine)

        # Manually set some of the known transaction types
        if line[3].startswith("Daň z úroku"):
            StatementLine.trntype = "DEBIT"
        elif line[3].startswith("Kreditní úrok"):
            StatementLine.trntype = "INT"
        elif line[3].startswith("Poplatek za "):
            StatementLine.trntype = "FEE"
        elif line[3].startswith("Příchozí platba"):
            StatementLine.trntype = "XFER"
        elif line[3].startswith("Odchozí platba"):
            StatementLine.trntype = "XFER"
        elif line[3].startswith("Výběr hotovosti"):
            StatementLine.trntype = "ATM"
        elif line[3].startswith("Platba kartou"):
            StatementLine.trntype = "POS"
        elif line[3].startswith("Inkaso"):
            StatementLine.trntype = "DIRECTDEBIT"
        elif line[3].startswith("Trvalý"):
            StatementLine.trntype = "REPEATPMT"
        else:
            StatementLine.trntype = "XFER"

        # .payee is imported as "Description" in GnuCash
        # .memo  is imported as "Notes"       in GnuCash
        # When .payee is empty, GnuCash imports .memo to "Description" and keeps "Notes" empty

        # StatementLine.payee = "Název protistrany" + "Číslo účtu protistrany"
        if not line[10]:
            StatementLine.payee = StatementLine.payee + line[10]

        # StatementLine.memo = "Poznámka k platbě" + the payment identifiers
        if not (line[12] == "" or line[12] == " "):
            StatementLine.memo = StatementLine.memo + "|VS: " + line[12]

        if not (line[13] == "" or line[13] == " "):
            StatementLine.memo = StatementLine.memo + "|KS: " + line[13]

        if not (line[14] == "" or line[14] == " "):
            StatementLine.memo = StatementLine.memo + "|SS: " + line[14]

        # Some type of fee is standalone, not related to transaction amount. Add it to amount field.only
        if float(line[6]) != 0 and StatementLine.amount == 0:
            StatementLine.amount = float(line[6])

        # Air Bank may show various fees on the same line  as the underlying transaction
        # For now, we simply create a new CSV file with the fee (and only the fee) moved to line[5].
        # This new file -fees.csv needs to be processed again manually:
        #     $ ofxstatement convert -t raiffeisencz in-fees.csv out-fees.ofx

        # ToDo: instead of exporting the above to CSV, try to add the exportline to
        #       the end of statement (from imported input.csv).
        if float(line[6]) != 0 and StatementLine.amount != 0:
            exportline = line[:]
            exportline[5] = line[6]
            exportline[6] = ''
            exportline[3] = "Poplatek za transakci"
            exportline[19] = "Poplatek: " + exportline[19]

            with open(AirBankCZPlugin.csvfile, "a", encoding=AirBankCZPlugin.encoding) as output:
                writer = csv.writer(output, lineterminator='\n', delimiter=',', quotechar='"')
                writer.writerow(exportline)

        if StatementLine.amount == 0:
            return None

        return StatementLine

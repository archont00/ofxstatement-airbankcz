This is a parser for CSV transaction history exported from Air Bank a.s. (CZ)
from within the report in Account History (CSV).

Ideally, the field separator is set to comma "," and character encoding to UTF-8
(this can be done in Settings / Applications) of the internet banking.

It is a plugin for `ofxstatement`_.

.. _ofxstatement: https://github.com/kedder/ofxstatement

Usage:

    ofxstatement convert -t airbankcz airbank_1102207023_2017-06-04_12-42.csv airbank_1102207023_2017-06-04_12-42.ofx

    ofxstatement convert -t airbank:EUR airbank_1102207023_2017-06-04_12-42.csv airbank_1102207023_2017-06-04_12-42.ofx

Configuration:

    ofxstatement edit-config

and set e.g. the following

    [airbankcz:EUR]

    plugin = airbankcz

    currency = EUR

    account = Air Bank EUR

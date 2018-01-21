This is a parser for CSV transaction history exported from Air Bank a.s. (Czech Republic)
from within the report in Account History (CSV).

The expected field separator is comma (",") and character encoding UTF-8
(have a look at Settings / Applications of the internet banking).

It is a plugin for `ofxstatement`_.

.. _ofxstatement: https://github.com/kedder/ofxstatement

Usage:
======
::

$ ofxstatement convert -t airbankcz airbank_1102207023_2017-06-04_12-42.csv airbank_1102207023_2017-06-04_12-42.ofx
$ ofxstatement convert -t airbankcz:EUR airbank_1102207023_2017-06-04_12-42.csv airbank_1102207023_2017-06-04_12-42.ofx

Configuration:
==============
::

$ ofxstatement edit-config

and set e.g. the following:
::

[airbankcz]
plugin = airbankcz
currency = CZK
account = Air Bank CZK
 
[airbankcz:EUR]
plugin = airbankcz
currency = EUR
account = Air Bank EUR

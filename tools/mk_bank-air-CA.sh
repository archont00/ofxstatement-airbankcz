#!/bin/bash

# This is a wrapper for
#   ofxstatement convert -t airbankcz input.csv output.ofx
# which:
# - reformats output.ofx to be human readable (structured and in UTF-8)

# Dependency:
# - bash
# - ofxstatement
# - ofxstatement-airbankcz (plugin)
# - uuidgen
# - xmllint

if [[ "x$1" = "x" ]]; then
  echo "Expects bank statement history CSV file as input."
  echo "Usage:"
  echo "  $0 input.csv"
  exit 1
fi

if [[ ! -f "${1}" ]]; then
  echo "File ${1} does not exist or is not readable"
  exit 1
fi

inputf="$(basename "${1}" .csv)"
inputd="$(dirname "${1}")"

# Run ofxstatement 
ofxstatement convert -t airbankcz:CA "${1}" "${inputd}/${inputf}.ofx" \
  || { echo "ofxstatement for ${1} failed."; exit 1; }


tmpf="$(uuidgen)"
cat "${inputd}/${inputf}.ofx" | xmllint --format --encode UTF-8 - > "${inputd}/${tmpf}"
mv "${inputd}/${tmpf}" "${inputd}/${inputf}.ofx"

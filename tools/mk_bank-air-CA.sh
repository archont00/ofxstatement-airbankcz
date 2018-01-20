#!/bin/bash

# This is a wrapper for
#   ofxstatement convert -t airbankcz input.csv output.ofx
# which:
# - if there is any input-fees.csv, it runs again
# - reformats output.ofx to be human readable

# ToDo:
# - merge input-fees.ofx with output.ofx

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
  || { echo "ofxstatement 1 failed."; exit 1; }


tmpf="$(uuidgen)"
cat "${inputd}/${inputf}.ofx" | xmllint --format --encode UTF-8 - > "${inputd}/${tmpf}"
mv "${inputd}/${tmpf}" "${inputd}/${inputf}.ofx"

feesf="${inputd}/${inputf}-fees.csv"
if [[ -f "${feesf}" ]]; then
  if [[ $(cat "${feesf}" | wc -l) -gt 1 ]]; then
    ofxstatement convert -t airbankcz:CA "${feesf}" "${inputd}/${inputf}-fees.ofx" \
      || { echo "ofxstatement 2 failed."; exit 1; }
  fi
  rm "${feesf}" "${inputd}/${inputf}-fees-fees.csv"
  tmpf="$(uuidgen)"
  cat "${inputd}/${inputf}-fees.ofx" | xmllint --format --encode UTF-8 - > "${inputd}/${tmpf}"
  mv "${inputd}/${tmpf}" "${inputd}/${inputf}-fees.ofx"
fi

<?
# Author: andrew.galloway@nexenta.com
# contact with questions or additions/changes (use Github)

# this file contains generic functions for use in other ingestion scripts

function expiryTimestamp($lic) {
  $parts = explode('-', $lic);

  $ts1_obf = $parts[3];
  $ts2 = substr($parts[1], 6);

  $ts1 = '';

  $ts1_obf_chars = str_split($ts1_obf);
  $ts2_chars = str_split($ts2);

  $idx = 0;

  foreach ($ts1_obf_chars as $char1) {
    $char2 = $ts2_chars[$idx++];

    if ($idx >= count($ts2_chars)) { $idx = 0; }

    $code = ord($char1) - 17 - (ord($char2) - ord('0'));
    $ts1 .= chr($code);
  }

  return $ts1 . $ts2;
}

?>

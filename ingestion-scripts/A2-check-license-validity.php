#!/usr/bin/env php

<?
# Author: andrew.galloway@nexenta.com
# Created On: 2013-09-26
# Last Updated On: 2013-09-26
# Description:
#   checks if license is expired or not

# include generic functions file
#include '/root/Collector/Ingestor/ingestion-scripts/functions.php';
include '/home/rmesta/ws/src/Ingestor/Ingestor/ingestion-scripts/functions.php';

# name of this script - could be filename, or something unique people will recognize
$SCRIPT_NAME = "A2-check-license-validity.php";

# put your actual code within this function, be sure to exit 0 if successful and
# exit 1 if not
function main($BUNDLE_DIR) {
    $WARN_FILE = $BUNDLE_DIR . "/ingestor/warnings/check-license-validity";
    $CHECK_FILE = $BUNDLE_DIR . "/ingestor/checks/check-license-validity";

    file_put_contents($CHECK_FILE, "License Support Validity Check | licenseexpirycheck\n");

    if (is_file($BUNDLE_DIR . "/appliance/nlm.key")) {
        $license_key = file_get_contents($BUNDLE_DIR . "/appliance/nlm.key");
        $license_key = trim($license_key);

        $expires = expiryTimestamp($license_key);

        if (time() > $expires) {
            file_put_contents($WARN_FILE, "<li>License key support length is expired</li>\n", FILE_APPEND);
        } else {
            $left = $expires - time();
            $left_days = $left / 60 / 60 / 24;
            file_put_contents($CHECK_FILE, "<li>License key support valid for ". number_format($left_days, 2) ." more days</li>\n", FILE_APPEND);
    } else {
        file_put_contents($WARN_FILE, "<li>Could not find nlm.key file</li>.\n", FILE_APPEND);

    exit(0);
}

# this runs first, and does sanity checking before invoking main() function

# check for necessary directory argument and runtime
if (php_sapi_name() != 'cli') {
    print "Must be run from commandline!\n";
    exit(1);
} else {
    if (!array_key_exists(1, $argv)) {
        print "Must be passed directory as argument!\n";
        exit(1);
    } else {
        if (!is_dir($argv[1])) {
            print "Directory invalid!\n";
            exit(1);
        } else {
            main($argv[1]);
        }
    }
}

?>

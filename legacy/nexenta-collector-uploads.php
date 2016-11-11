<?php
# simple script to take any uploaded form files and put them in caselogs
# no validation is done at this time (can't think of any that is needed), other
# than that it doesn't bother to save '.test' files
#
# for this to work, permissions are important on upload_dir and what user apache is running as!
# for questions email andrew.galloway@nexenta.com

$upload_dir = '/mnt/carbon-steel/upload/caselogs/';
$upload_file = $upload_dir . basename($_FILES['uploaded_file']['name']);

if (strpos(basename($_FILES['uploaded_file']['name']), "collector") !== false) {
    if (strpos(basename($_FILES['uploaded_file']['name']), ".test") == false) {
        if (move_uploaded_file($_FILES['uploaded_file']['tmp_name'], $upload_file)) {
            echo 'success';

            chmod($upload_file, 0660);
        } else {
            echo 'failure';
        }
    } else {
        echo 'success';
    }
} else {
    echo 'failure';
}

?>

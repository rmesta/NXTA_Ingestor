#!/bin/bash
# Ben Hodgens
# needs tsconv
db="sqlite3 /home/support/bah/panichash.db "
$1=$(pwd $1)
my_hostname=$(grep ^Host $1/collector.stats | awk '{print $2}' | sed 's/.*/\L&/') # TODO put this in library
#my_time=$(echo $1 | sed -e 's/.*_//' -e 's/[[:alpha:]]*$//g' -e 's/-/:/3g' -e 's/\./T/') # collector time in db format

my_license=$(echo $1 | sed -e 's/.*collector-//1' -e 's/_[0-9]\{4\}-.*//')
my_name=$(grep License $1/collector.stats | cut -f 3 -d "-")
PANICS=($(grep Mpanic $1/kernel/messages* | sed "s/^.*$my_hostname //" | cut -f 2 -d =))
for panic in ${PANICS[@]}; do 
    stacktrace=$(sed \
        -e "1,/$panic/d" \
        -e '/syncing/,$d' \
        -e '/dumping/,$d' \
        -e 's/.*] //' \
        -e 's/.*Disk: //' \
        -e 's/[[:xdigit:]]\{16\}//g' \
        -e 's/^[[:space:]]*//g' \
        -e 's/([a-z,0-9]* == [a-z,0-9]*)//g' \
        -e 's/^[a-z,0-9]\{3\}: .*//' \
        -e 's/^[a-z,0-9]\{2\}: .*//' \
        -e 's/^.*:[[:space:]]$//' \
        -e 's/^.*:[[:space:]]*//' \
        -e 's/[p,P]ool '.*\'/POOLNAME/ \
        -e 's/\+[[:digit:]]*//' \
        -e 's/addr=[a-z,0-9]*//g' \
        -e 's/^pid=.*//' \
        -e '/^\s*$/d' \
        $1/kernel/messages* \
    )
    panic_string=$(printf "$stacktrace" | head -n1)
    panic_time=$(echo $panic | tsconv -msgs | awk '{print $1}')
    mdhash=$(printf "$stacktrace" | md5sum | awk {'print $1'})
    echo "recent panic in thread $panic stacktrace md5sum of $mdhash"
    if [[ ! -z $2 ]]; then
        printf "$stacktrace"
        echo
        echo HASH: $mdhash
        echo STRING: $panic_string
        echo STACKTRACE: $stacktrace
        echo TIME: $my_time
    fi
    # TODO need table for NEX-identified stacktrace hashes
    # something weird going on with time and panicstring /home/support/ingested/2016-10-24/collector-P128-ECEBB00490-63IB58KIG-BIRCJK_a2pnexplnas04_2016-10-24.10-45-38MST
    # check if there's a hash present then... 
    hash_present=$($db "select hash from stacktraces where hash='$mdhash' limit 1;")
    if [[ $mdhash == $hash_present ]]; then
        echo $mdhash present
        $db "update stacktraces set latest_date = '$my_time' where hash = '$mdhash';"
    else 
        $db "insert into stacktraces (hash, description, content, first_date, latest_date) values ('$mdhash','$panic_string','$stacktrace','$my_time','$my_time')";
    fi
    $db "insert into collectors (name, license, panichash, date) values ('$my_name','$my_license','$mdhash', '$my_time') on conflict ignore;"
    
done 


#!/bin/bash
# Ben Hodgens
# needs tsconv
# unique system panic tracking into a database, run on ingestion
# TODO - do we need this to be using csum_functions.sh ? 
REPO_ROOT="/mnt/carbon-steel/ingested"
dbpath="$REPO_ROOT/collector_db/panichash.db"
#messages="$1/kernel/messages" # Don't use this, need to accomodate old collectors with os/messages*
#outfile="$1/ingestor/tests/A9480-panichash.out" #TODO 
db="sqlite3 $dbpath"
usage="$0 <collector path>" 

DEBUG=0
output="stdout" # MUST DEFINE: one of stdout, debug, outfile, squelch
function output () { 
    case $output in 
        debug)
            echo "$0 LOG line ${BASH_LINENO[*]}: $1"
        ;;
        outfile)
            if [[ ! -z $outfile ]]; then 
                echo "$1" &> $outfile
            else 
                echo "outfile is not defined"
            fi
        ;;
        squelch)
            echo "$1" > /dev/null 
        ;;
        stdout)
            echo "$1"
        ;;
        *)
            echo "$0: ERROR: please define output type. "
        ;;
    esac
}
# schema creation for testing reiteration laziness
if [[ $DEBUG == "1" ]]; then # DEBUG TODO remove for prod
    output "removing $dbpath"
    rm $dbpath
fi 
if [[ ! -f $dbpath ]]; then
    output "Database doesn't exist yet; creating."
    $db "CREATE TABLE stacktraces (
            hash STRING UNIQUE NOT NULL PRIMARY KEY, 
            description STRING NOT NULL, 
            content TEXT UNIQUE NOT NULL, 
            first_date DATE NOT NULL, 
            latest_date DATE, 
            total INTEGER
    );"
    $db "CREATE TABLE collectors (
            machinesig STRING NOT NULL, 
            name STRING NOT NULL, 
            date DATE NOT NULL, 
            panichash STRING NOT NULL REFERENCES stacktraces(hash),
            version STRING NOT NULL,
            PRIMARY KEY (machinesig, panichash, date) ON CONFLICT IGNORE)
    ;"
    # TODO to eventually populate with NEX-associations
    $db "CREATE TABLE bugs (
            id string unique not null primary key,
            panichash STRING NOT NULL REFERENCES stacktraces(hash));"
    output "done."
fi
if [[ -z $1 ]]; then 
    output "$usage"
fi 
my_relpath=$(echo $1 | sed -e 's/.*\///g') 
my_machinesig=$(echo $my_relpath | cut -f4 -d-) 
my_hostname=$(grep ^Host $1/collector.stats | awk '{print $2}' | sed 's/.*/\L&/') # TODO put this in library
echo HOSTNAME $my_hostname
my_version=$(grep version $1/collector.stats | cut -f 2 -d "(" | cut -f 1 -d ")")
for message_file in $(ls $1/{os,kernel}/messages* 2> /dev/null); do 
    PANICS=($(grep Mpanic $message_file | sed -e 's/ /!/g'))
    for panic in ${PANICS[@]}; do 
        tmp_panic=$(echo $panic | sed -e 's/!/ /g')
#        panic_time=$(grep "$tmp_panic" $message_file | tsconv -msgs | awk {'print $1'} ) 
        panic_fhalf=$(echo $tmp_panic | sed -e "s/$my_hostname.*=//i" | awk {'print $1, $2, $3'})
        panic_lhalf=$(echo $tmp_panic | sed -e "s/$my_hostname.*=//i" | awk {'print $4'})
        panic_time=$(echo $panic_fhalf | tsconv -msgs)
#        echo first $panic_fhalf
#        echo last $panic_lhalf
        stacktrace=$( sed \
            -e "1,/$panic_fhalf.*=$panic_lhalf/d" \
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
            $message_file \
        )
        panic_string=$(printf "$stacktrace" | head -n1)
        mdhash=$(printf "$stacktrace" | md5sum | awk {'print $1'})
        output --------------------------
        output "recent panic in thread $tmp_panic stacktrace md5sum of $mdhash"
        if [[ ! -z $2 ]]; then # DEBUG
            output "HASH: $mdhash"
#            output "PANIC: $panic"
#            output "TMPPANIC $tmp_panic"
            output "STRING: $panic_string"
            output "TIME: $panic_time"
#            output "STACKTRACE: $stacktrace"
        fi
        # TODO need table for NEX-identified stacktrace hashes
        # something weird going on with time and panicstring /home/support/ingested/2016-10-24/collector-P128-ECEBB00490-63IB58KIG-BIRCJK_a2pnexplnas04_2016-10-24.10-45-38MST
        # check if there's a hash present then... 
        # need to accomodate for re-ingestion 
        hash_present=$($db "select hash from stacktraces where hash='$mdhash' limit 1;")
        if [[ $mdhash == $hash_present ]]; then
            output "** unique panic $mdhash present already, updating"
            $db "update stacktraces set latest_date = '$panic_time' where hash = '$mdhash';"
        else 
            $db "insert into stacktraces (hash, description, content, first_date, latest_date) values ('$mdhash','$panic_string','$stacktrace','$panic_time','$panic_time')";
        fi
        collector_present=$($db "select * from collectors where name is '$my_relpath' and date is '$panic_time' limit 1";)
        if [[ -z $collector_present ]]; then
            output "collector not present, inserting"
            $db "insert into collectors (machinesig, name, panichash, date, version) values ('$my_machinesig','$my_relpath','$mdhash', '$panic_time', '$my_version');" # on conflict ignore;" # seems to not work for this version of sqlite3?
        else 
            output "$mdhash for $my_relpath at $panic_time already exists"
        fi
        output "panichash: processed $1 "
    done 
done

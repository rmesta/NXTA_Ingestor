#!/usr/bin/perl

#
# Name          : nic-check.pl
# Author        : Jason.Banham@nexenta.com
# Date          : 29th July 2016 | 12th August 2016
# Usage         : nic-check.pl { -d dladm-show-phys.out -k kstat-p-td-10-6.out } { -c collector_directory }
# Purpose       : Check for signs of a failing network HBA/nic
# Version       : 0.07
# Legal         : Copyright 2016, Nexenta Systems, Inc.
# History       : 0.01 - Initial version
#		  0.02 - Added the help option
#		  0.03 - Now looks for TCP retransmit issues
#		  0.04 - Now with added colour (where possible)
#                 0.05 - Now we look for the MTU and advise if this looks under spec'd (Jumbo Frames)
#                 0.06 - Now prints ICMP in/out statistics for possible ICMP packet loss
#                 0.07 - Reworked the TCP retransmit code to use deltas between samples due to the overflowing
#                        32bit kstat counter, plus high counters that might have shown a historical problem
#                        that has since been fixed and thus would skew results.
#
# http://www.nntp.perl.org/group/perl.beginners/2007/09/msg95440.html
# http://www.rhyshaden.com/eth_err.htm
#

use strict;
use Getopt::Std;
use Class::Struct;
use Math::BigFloat ':constant';
use Term::ANSIColor;

my $DLADM_PHYS_FILENAME = "dladm-show-phys.out";
my $DLADM_LINK_FILENAME = "dladm-show-link.out";
my $KSTAT_FILENAME = "kstat-p-td-10-6.out";
my $DLADM_PHYS_FILE = $DLADM_PHYS_FILENAME;
my $DLADM_LINK_FILE = "/dev/null";
my $KSTAT_FILE = $KSTAT_FILENAME;
my $MAX_32BIT_INT = 4294967296;

#
# Show how to run the program, if no arguments/file supplied
#
sub usage{
    print color('bold blue');
    print "Usage: nic-check.pl { -d dladm-show-phys.out -k kstat.out } { -c collector_path }\n";
    print color('reset');
}


#
# Show the help page
#
sub help{
    usage();
    printf("\n");
    printf("This utility processes a \'dladm show phys\' output and a \'kstat -p -td\' output, or\n"); 
    printf("the same files in a specified collector bundle, in order to look for possible hardware\n"); 
    printf("and/or configuration issues for the network interfaces.\n");
    printf("It will also highlight any TCP retransmission concerns and display any ixgbe interfaces\n");
    printf("that have an MTU of < 9000, where the lack of Jumbo Frames may affect performance.\n");
    printf("Be aware however that other hosts and switches will also need to have Jumbo Frames\n");
    printf("enabled, otherwise this can introduce problems!\n\n");
    printf("If it finds any non-zero error counters, it will display these and tell you\n");
    printf("about any counters that were increasing during the sample.\n\n");
    printf("It looks for the following error counters:\n\n");
    printf("  align errors  : Received packets with framing errors, non-integral number of octets\n");
    printf("                  Usually caused by electrical interference, cables and bad HBAs.\n");
    printf("  collisions    : When more than one device transmits at the same time.  Usually\n");
    printf("                  caused when a network link is running at half duplex.\n");
    printf("  input errors  : Counter is increased when any inbound packet has an error.\n");
    printf("                  Check duplex settings, CRC errors, cables, HBA, switch.\n");
    printf("  jabber errors : If the received packed is too long it is discarded.\n");
    printf("                  ..With Jumbo frames    : Any packet > 9018 bytes (9022 for VLAN)\n");
    printf("                  ..Without Jumbo frames : Any packet > 1518 bytes (1522 for VLAN)\n");
    printf("                  Usually caused by a device having electrical issues.\n");
    printf("  macrcv errors : Received packets with MAC errors (excluding alignment, fcs and also\n");
    printf("                  too long errors.\n");
    printf("  output errors : Increased when there was a problem sending a packet.\n");
    printf("                  Check duplex mismatch, collisions, cables, HBA, switch.\n");
    printf("  overflows     : Usually a sign that packet processing is unable to keep up with the\n");
    printf("                  arrival of new packets.  The device may be in an incorrect PCI slot\n");
    printf("                  or there may be too much work to handle.\n");
    printf("  runt errors   : If the delivered packet is < 64bytes, it is considered too short\n");
    printf("                  and discarded.  Usually caused by collisions/bad wiring and also\n");
    printf("                  electrical interference.\n");
    printf("  length errors : Received packets are either undersized or oversized\n");
    printf("\n");
    printf("  retrans       : Display the TCP retransmission rate as a percentage\n");
    printf("                    - moderate retransmissions < 10%\n");
    printf("                    - warning > 15% ( > 2/sec )\n");
    printf("                    - excessive retransmissions > 25%\n");
    printf("                    - action required > 40%\n");
    printf("                  High retrans may indicate network saturation or a host not responding\n");
    printf("                  within a given time period.\n");
    printf("\n");
    printf("EXAMPLES:\n\n");
    printf("o) Half duplex interface leading to collisions and input errors\n\n");
    printf("igb0         Ethernet             up         ");
    print color('red');
    printf("100    half");
    print color('reset');
    printf("      igb0\n");
    printf("igb1         Ethernet             up         1000   full      igb1\n");
    printf("ixgbe0       Ethernet             up         10000  full      ixgbe0\n");
    printf("ixgbe1       Ethernet             up         10000  full      ixgbe1\n\n");
    printf("Displaying interfaces with non-zero error counts\n");
    printf("igb#0 collisions = 351623\n");
    printf("igb#0 input errors = 13584\n\n");
    printf("We can also see that igb0 should be running at 1000Mbit but is only running at 100Mbit!\n");
}

#
# Scan for arguments and process accordingly
#

# declare the perl command line flags/options we want to allow

my $got_collector = 0;
my $got_kstat = 0;
my $got_dladm = 0;

my %options=();
getopts("c:d:hk:", \%options);

if (defined $options{c}) {
    $KSTAT_FILE = $options{c} . "/kernel/" . $KSTAT_FILENAME;
    $DLADM_PHYS_FILE = $options{c} . "/network/" . $DLADM_PHYS_FILENAME;
    $DLADM_LINK_FILE = $options{c} . "/network/" . $DLADM_LINK_FILENAME;
    $got_collector = 1;
}
if (defined $options{d}) {
    $DLADM_PHYS_FILE = $options{d};
    $got_dladm = 1;
}
if (defined $options{h}) {
    help();
    exit;
}
if (defined $options{k}) {
    $KSTAT_FILE = $options{k};
    $got_kstat = 1;
}

#
# Check we've actually supplied the two files for processing
#
#my $num_args = $#ARGV + 1;
#if ( $num_args < 2 ) {
if ($got_collector == 0) {
    if (($got_kstat == 0) && ($got_dladm == 0)) {
        usage;
        exit;
    }
}
if (($got_kstat == 0) || ($got_dladm == 0)) {
    if ($got_collector == 0) {
	usage;
	exit;
    }
}


#
# Open the physical interface file and pull it into a large array
#
open (my $file, "<", $DLADM_PHYS_FILE) || die "Can't read file: $DLADM_PHYS_FILE";
my (@nic_list) = <$file>;
close($file);

chomp(@nic_list);
my ($nic_lines) = scalar @nic_list;

#
# Open the kstat file and pull it into a large array
#
open (my $file, "<", $KSTAT_FILE) || die "Can't read file: $KSTAT_FILE";
my (@kstat_list) = <$file>;
close($file);

chomp(@kstat_list);
my ($kstat_lines) = scalar @kstat_list;

#
# If we have the extra dladm show link data, let's use it
#
my %link_mtu;
if ($DLADM_LINK_FILE !~ /null/) {
    open(my $file, "<", $DLADM_LINK_FILE) || die "Can't read file: $DLADM_LINK_FILE";
    my (@link_list) = <$file>;
    close($file);

    chomp(@link_list);
    my ($link_lines) = scalar @link_list;

    my $index = 0;
    while ($index < $link_lines) {
        if ( $link_list[$index] =~ /up/ ) {
            my ($link, $class, $mtu, $state, $bridge, $over) = split /\s+/, $link_list[$index];
            @link_mtu{$link} = $mtu;
        }
        $index++;
    }
}

#
# Define the bit patterns to determine which of the error counts are increasing
#
my $alignment_bit = 0x1;
my $collision_bit = 0x2;
my $ierror_bit    = 0x4;
my $jabber_bit    = 0x8;
my $macrcv_bit    = 0x10;
my $oerror_bit	  = 0x20;
my $oflo_bit	  = 0x40;
my $runt_bit	  = 0x80;
my $length_bit	  = 0x100;


#
# Elements of the kstat <nic>:<instance>:mac and <nic>:<instance>:statistics kstat data we're interested in
# Store any values we find using this structure definition
#
struct Nic_Stat => {
    align_err	=> '$',		# alignment errors
    collisions  => '$',		# collisions
    ierrors	=> '$',		# input errors
    jabber_err	=> '$',		# jabber errors
    macrcv_err	=> '$',		# receive errors
    oerrors	=> '$',		# output errors
    oflo	=> '$',		# overflows
    runt_err	=> '$',		# runt errors
    length_err  => '$',		# length errors
    increasing  => '$',		# OR in one or more of the above bit patterns to determine which error counters are increasing
};

my %nic_table;

my $index = 1;
my $instance = 0;
my $nicname = "";
my $mac = "";
my $errname = "";
my $maxinstance = 0;
my $nic = "";
my $mtu_undersized = 0;
my $inechos = 0;
my $outechoreps = 0;
my $linebreak = "--------------------------------------------------------------------------------";

#
# Common network adaptors on NexentaStor:
#
# bge     : Driver for Broadcom 1Gbit BCM57xx adaptor
# bnx     : Driver for Broadcom 10Gbit/1Gbit NetExtreme II adaptor
# e1000g  : Driver for Intel 1Gbit adaptor
# hxge    : Driver for Sun 10Gbit network adaptor
# igb     : Driver for Intel 1Gbit adaptor
# ixgbe   : Driver for Intel 10Gbit adaptor
# ntxn    : Driver for Netxen 10Gbit network adaptor
# nxge    : Driver for Sun NIU 10Gbit/1Gbit network adaptor
#
# For NexentaStor 3.x and 4.x, to see a full list, gather the output from:
# 
# dpkg -l | grep driver-network
#
# NOTE: Not all of the drivers will be supported under NexentaStor
#
# In practice and experience it is the Intel drivers that have been found to work most reliably
#
my @nics_supplied = ("bge", "bnx", "bnxe", "e1000g", "igb", "nxge", "aggr", "ipmp");
my %nic_kstats;
my $outdatabytes;
my $retransbytes;
my @retransbytes_array;
my @outdatabytes_array;

#
# Something pretty but not entirely relevant
# ... this prints a list of NIC drivers.
#
#printf("Supplied NIC drivers are: ");
#foreach $nic (@nics_supplied) {
#    printf("%s ", $nic);
#}
#printf("\n");

#
# Display the list of NICs that are UP
#
#printf("%-13s%-21s%-11s%-7s%-10s%-10s\n", "le0", "Ethernoodle", "up", "500", "half", "le0" );

printf("Looking for NICs that are in an UP state:\n\n");
printf("LINK         MEDIA                STATE      SPEED  DUPLEX    DEVICE    MTU\n");
while ($index < $nic_lines) {
    if ( $nic_list[$index] =~ /up/ ) {
        my ($link, $media, $state, $speed, $duplex, $device) = split /\s+/, $nic_list[$index];
        printf("%-13s%-21s%-11s%-7s", $link, $media, $state, $speed);

        #
        # If we find a NIC in half duplex, display this in red as a warning
        #
        if ( $duplex =~ /half/ ) {
            print color('red');
	    printf("%-10s", $duplex);
	    print color('reset');
        }
        else {
            printf("%-10s", $duplex);
        }
        printf("%-10s", $device);

        #
        # If we find a capable NIC, not using Jumbo Frames, display a warning
        #
        if ($link =~ /ixgbe/ && $link_mtu{$link} < 9000) {
            $mtu_undersized++;
            print color('magenta');
            printf("%-10s\n", $link_mtu{$link});
            print color('reset');
        }
        else {
            printf("%-10s\n", $link_mtu{$link});
        }
        my ($input, $guff) = split /\s+/, $nic_list[$index];
 	($instance) = ($input =~ /(\d+)/);
        my ($nic, $guff) = split /\d+/, $input;
	$nic_table{$nic}{$instance} = 1;
    }
    $index++;
}

#
# Not all NICs will be mis-configured, so only print the warning if we find a potential problem
#
if ($mtu_undersized > 0) {
    print color('magenta');
    printf("\nNOTE:\n");
    print color('reset');
    printf("  ixgbe interfaces not running with jumbo frames (MTU = 9000) may see worse performance\n\n");
}
else {
    printf("\n");
}


#
# Process the kstat data, searching for specific (non-zero) error counters and record that data in the structure
# based on interface type (eg: bge, ixgbe) and instance (usually starts at zero and increases)
# For each interface and instance, use those as indexes into a hash of structures for recording the actual data
#
my %nics_found;
$index = 0;

#
# In theory we could write a progress meter to show how far we are reading the kstat data
# however in practice because the data is relatively small, a progress bar is printing almost
# instantly, making this somewhat pointless.
# If we ever need to revisit this, the following is a 5% update point in the kstat data, which we 
# could then modulus with the index value and print an update each time that is zero.
#
#my $perc = sprintf("%d", ($kstat_lines / 100) * 5);

printf("%s\n", $linebreak);
while ($index < $kstat_lines) {
    if ( $kstat_list[$index] =~ /.*:.*:mac:align_errors/ ) {
        my ($stat, $errcount) = split /\s+/, $kstat_list[$index];
        ($nicname, $instance, $mac, $errname) = split /:/, $kstat_list[$index];
        @nics_found{$nicname} = $instance;
        if ($errcount > 0) {
            if ($instance > $maxinstance) {
                $maxinstance = $instance;
            }
	    if (($errcount > $nic_kstats{$nicname}{$instance}->{align_err}) && ($nic_kstats{$nicname}{$instance}->{align_err} > 0)) {
		$nic_kstats{$nicname}{$instance}->{increasing} |= $alignment_bit;
	    }
	    $nic_kstats{$nicname}{$instance}->{align_err} = $errcount;
	}
    }
    if ( $kstat_list[$index] =~ /.*:.*:mac:collisions/ ) {
        my ($stat, $errcount) = split /\s+/, $kstat_list[$index];
        ($nicname, $instance, $mac, $errname) = split /:/, $kstat_list[$index];
        @nics_found{$nicname} = $instance;
        if ($errcount > 0) {
            if ($instance > $maxinstance) {
                $maxinstance = $instance;
            }
	    if (($errcount > $nic_kstats{$nicname}{$instance}->{collisions}) && ($nic_kstats{$nicname}{$instance}->{collisions} > 0)) {
		$nic_kstats{$nicname}{$instance}->{increasing} |= $collision_bit;
	    }
	    $nic_kstats{$nicname}{$instance}->{collisions} = $errcount;
	}
    }
    if ( $kstat_list[$index] =~ /.*:.*:mac:ierrors/ ) {
        my ($stat, $errcount) = split /\s+/, $kstat_list[$index];
        ($nicname, $instance, $mac, $errname) = split /:/, $kstat_list[$index];
        @nics_found{$nicname} = $instance;
        if ($errcount > 0) {
            if ($instance > $maxinstance) {
                $maxinstance = $instance;
            }
	    if (($errcount > $nic_kstats{$nicname}{$instance}->{ierrors}) && ($nic_kstats{$nicname}{$instance}->{ierrors} > 0)) {
		$nic_kstats{$nicname}{$instance}->{increasing} |= $ierror_bit;
	    }
	    $nic_kstats{$nicname}{$instance}->{ierrors} = $errcount;
	}
    }
    if ( $kstat_list[$index] =~ /.*:.*:mac:jabber_errors/ ) {
 	my ($stat, $errcount) = split /\s+/, $kstat_list[$index];
	($nicname, $instance, $mac, $errname) = split /:/, $kstat_list[$index];
        @nics_found{$nicname} = $instance;
	if ($errcount > 0) {
	    if ($instance > $maxinstance) {
		$maxinstance = $instance;
	    }
	    if (($errcount > $nic_kstats{$nicname}{$instance}->{jabber_err}) && ($nic_kstats{$nicname}{$instance}->{jabber_err} > 0)) {
		$nic_kstats{$nicname}{$instance}->{increasing} |= $jabber_bit;
	    }
	    $nic_kstats{$nicname}{$instance}->{jabber_err} = $errcount;
  	}
    }
    if ( $kstat_list[$index] =~ /.*:.*:mac:macrcv_errors/ ) {
        my ($stat, $errcount) = split /\s+/, $kstat_list[$index];
        ($nicname, $instance, $mac, $errname) = split /:/, $kstat_list[$index];
        @nics_found{$nicname} = $instance;
        if ($errcount > 0) {
            if ($instance > $maxinstance) {
                $maxinstance = $instance;
            }
	    if (($errcount > $nic_kstats{$nicname}{$instance}->{macrcv_err}) && ($nic_kstats{$nicname}{$instance}->{macrcv_err} > 0)) {
		$nic_kstats{$nicname}{$instance}->{increasing} |= $macrcv_bit;
	    }
	    $nic_kstats{$nicname}{$instance}->{macrcv_err} = $errcount;
	}
    }
    if ( $kstat_list[$index] =~ /.*:.*:mac:oerrors/ ) {
        my ($stat, $errcount) = split /\s+/, $kstat_list[$index];
        ($nicname, $instance, $mac, $errname) = split /:/, $kstat_list[$index];
        @nics_found{$nicname} = $instance;
        if ($errcount > 0) {
            if ($instance > $maxinstance) {
                $maxinstance = $instance;
	    }
	    if (($errcount > $nic_kstats{$nicname}{$instance}->{oerrors}) && ($nic_kstats{$nicname}{$instance}->{oerrors} > 0)) {
		$nic_kstats{$nicname}{$instance}->{increasing} |= $oerror_bit;
	    }
	    $nic_kstats{$nicname}{$instance}->{oerrors} = $errcount;
	}
    }
    if ( $kstat_list[$index] =~ /.*:.*:mac:oflo/ ) {
        my ($stat, $errcount) = split /\s+/, $kstat_list[$index];
        ($nicname, $instance, $mac, $errname) = split /:/, $kstat_list[$index];
        @nics_found{$nicname} = $instance;
        if ($errcount > 0) {
            if ($instance > $maxinstance) {
                $maxinstance = $instance;
            }
	    if (($errcount > $nic_kstats{$nicname}{$instance}->{oflo}) && ($nic_kstats{$nicname}{$instance}->{oflo} > 0)) {
		$nic_kstats{$nicname}{$instance}->{increasing} |= $oflo_bit;
	    }
	    $nic_kstats{$nicname}{$instance}->{oflo} = $errcount;
	}
    }
    if ( $kstat_list[$index] =~ /.*:.*:mac:runt_errors/ ) {
        my ($stat, $errcount) = split /\s+/, $kstat_list[$index];
        ($nicname, $instance, $mac, $errname) = split /:/, $kstat_list[$index];
        @nics_found{$nicname} = $instance;
        if ($errcount > 0) {
            if ($instance > $maxinstance) {
                $maxinstance = $instance;
            }
	    if (($errcount > $nic_kstats{$nicname}{$instance}->{runt_err}) && ($nic_kstats{$nicname}{$instance}->{runt_err} > 0)) {
		$nic_kstats{$nicname}{$instance}->{increasing} |= $runt_bit;
	    }
	    $nic_kstats{$nicname}{$instance}->{runt_err} = $errcount;
	}
    }
    if ( $kstat_list[$index] =~ /.*:.*:statistics:recv_length_errors/ ) {
        my ($stat, $errcount) = split /\s+/, $kstat_list[$index];
        ($nicname, $instance, $mac, $errname) = split /:/, $kstat_list[$index];
        @nics_found{$nicname} = $instance;
        if ($errcount > 0) {
            if ($instance > $maxinstance) {
                $maxinstance = $instance;
            }
	    if (($errcount > $nic_kstats{$nicname}{$instance}->{length_err}) && ($nic_kstats{$nicname}{$instance}->{length_err} > 0)) {
		$nic_kstats{$nicname}{$instance}->{increasing} |= $length_bit;
	    }
	    $nic_kstats{$nicname}{$instance}->{length_err} = $errcount;
	}
    }

    #
    # Look for TCP retransmission issues
    #
    if ( $kstat_list[$index] =~ /tcp:0:tcp:outDataBytes/ ) {
	my ($stat, $value) = split /\s+/, $kstat_list[$index];
	$outdatabytes = $value;
        push(@outdatabytes_array, $outdatabytes);
    }
    if ( $kstat_list[$index] =~ /tcp:0:tcp:retransBytes/ ) {
	my ($stat, $value) = split /\s+/, $kstat_list[$index];
	$retransbytes = $value;
        push(@retransbytes_array, $retransbytes);
    }

    #
    # Look for IP/ICMP dropped packets
    #
    if ( $kstat_list[$index] =~ /ip:0:icmp:inEchos/ ) {
        my ($stat, $value) = split /\s+/, $kstat_list[$index];
        $inechos += $value;
    }
    if ( $kstat_list[$index] =~ /ip:0:icmp:outEchoReps/ ) {
        my ($stat, $value) = split /\s+/, $kstat_list[$index];
        $outechoreps += $value;
    }

    $index++;
}

#dump %nic_kstats;


#
# Once we've processed the kstat data, walk the hash and dump out the error counters
#
printf("Displaying interfaces with non-zero error counts\n");
printf("(see nic-check.pl -h output for a description of each error counter)\n\n");

print color('cyan');
for my $nicname (keys %nics_found) {
#    printf("nic %s max instance = %d\n", $nicname, $nics_found{$nicname});
    $instance = 0;
    while ($instance <= $nics_found{$nicname}) {
	my $found = 0;
        if ($nic_kstats{$nicname}{$instance}->{align_err} > 0) {
	    $found = 1;
            printf("%s#%d align errors = %d ", $nicname, $instance, $nic_kstats{$nicname}{$instance}->{align_err});
	    if ($nic_kstats{$nicname}{$instance}->{increasing} & $alignment_bit) {
	        printf("... and increasing");
 	    }
	    printf("\n");
	}
        if ($nic_kstats{$nicname}{$instance}->{collisions} > 0) {
	    $found = 1;
            printf("%s#%d collisions = %d ", $nicname, $instance, $nic_kstats{$nicname}{$instance}->{collisions});
	    if ($nic_kstats{$nicname}{$instance}->{increasing} & $collision_bit) {
	        printf("... and increasing");
 	    }
	    printf("\n");
	}
        if ($nic_kstats{$nicname}{$instance}->{ierrors} > 0) {
	    $found = 1;
            printf("%s#%d input errors = %d ", $nicname, $instance, $nic_kstats{$nicname}{$instance}->{ierrors});
	    if ($nic_kstats{$nicname}{$instance}->{increasing} & $ierror_bit) {
	        printf("... and increasing");
 	    }
	    printf("\n");
	}
        if ($nic_kstats{$nicname}{$instance}->{oerrors} > 0) {
	    $found = 1;
            printf("%s#%d output errors = %d ", $nicname, $instance, $nic_kstats{$nicname}{$instance}->{oerrors});
	    if ($nic_kstats{$nicname}{$instance}->{increasing} & $oerror_bit) {
	        printf("... and increasing");
 	    }
	    printf("\n");
	}
        if ($nic_kstats{$nicname}{$instance}->{jabber_err} > 0) {
	    $found = 1;
            printf("%s#%d jabber errors = %d ", $nicname, $instance, $nic_kstats{$nicname}{$instance}->{jabber_err});
	    if ($nic_kstats{$nicname}{$instance}->{increasing} & $jabber_bit) {
	        printf("... and increasing");
 	    }
	    printf("\n");
	}
        if ($nic_kstats{$nicname}{$instance}->{macrvc_err} > 0) {
	    $found = 1;
            printf("%s#%d macrcv errors = %d ", $nicname, $instance, $nic_kstats{$nicname}{$instance}->{macrcv_err});
	    if ($nic_kstats{$nicname}{$instance}->{increasing} & $macrcv_bit) {
	        printf("... and increasing");
 	    }
	    printf("\n");
	}
        if ($nic_kstats{$nicname}{$instance}->{oflo} > 0) {
	    $found = 1;
            printf("%s#%d overflow errors = %d ", $nicname, $instance, $nic_kstats{$nicname}{$instance}->{oflo});
	    if ($nic_kstats{$nicname}{$instance}->{increasing} & $oflo_bit) {
	        printf("... and increasing");
 	    }
	    printf("\n");
	}
        if ($nic_kstats{$nicname}{$instance}->{runt_err} > 0) {
	    $found = 1;
            printf("%s#%d runt errors = %d ", $nicname, $instance, $nic_kstats{$nicname}{$instance}->{runt_err});
	    if ($nic_kstats{$nicname}{$instance}->{increasing} & $runt_bit) {
	        printf("... and increasing");
 	    }
	    printf("\n");
	}
        if ($nic_kstats{$nicname}{$instance}->{length_err} > 0) {
	    $found = 1;
            printf("%s#%d length errors = %d ", $nicname, $instance, $nic_kstats{$nicname}{$instance}->{length_err});
	    if ($nic_kstats{$nicname}{$instance}->{increasing} & $length_bit) {
	        printf("... and increasing");
 	    }
	    printf("\n");
	}
	if ($found == 1) {
	    printf("\n");
        }
	$instance++;
    }
}
print color('reset');

#
# Display any TCP retransmission issues
# - The documented method for working out retransmission issues is to do the following:
#   (retransBytes / outDataBytes) * 100 = retrans%
#
# However in practice on a very busy system, we routinely overflow the 32bit kstat counter, particularly on the
# outDataBytes value, which makes for some very odd statistics with retransmissions being several hundred %
# To address this problem we need to calculate the deltas between two samples, then work out the percentages
# based on this new value.
# As such we now push each of the retransBytes and outDataBytes values into an array so we can then work out
# the deltas.
#
# Be warned that if the kstat counters ever change (32bit -> 64bit or 128bit even!) then the MAX_32BIT_INT
# variable will cause problems.  Alas there's no way to tell the data type from the kstat sample, so we would
# probably have to compare the statistic to see if it's > 2^32 and < 2^64 to then use an appropriate 
# scaling integer.
#

my $outdatabytes_entries = scalar @outdatabytes_array;
my $retransbytes_entries = scalar @retransbytes_array;
my $outdatabytes_delta = 0;
my $retransbytes_delta = 0;

printf("%s\n", $linebreak);
if ($outdatabytes_entries == $retransbytes_entries) {
    printf("TCP retransmission rates (%d samples): ", ($outdatabytes_entries - 1));
    my $index = 1;
    my $counter = 0;
    while ($index < $outdatabytes_entries) {
        $outdatabytes_delta = 0;            # Always initialise to zero to prevent previous value being used
        if ($outdatabytes_array[$index] > $outdatabytes_array[$counter]) {
            $outdatabytes_delta = $outdatabytes_array[$index] - $outdatabytes_array[$counter];
        }
        if ($outdatabytes_array[$index] < $outdatabytes_array[$counter]) {
            $outdatabytes_delta = ($outdatabytes_array[$index] + $MAX_32BIT_INT) - $outdatabytes_array[$counter];
        }

        $retransbytes_delta = 0;            # Always initialise to zero to prevent previous value being used
        if ($retransbytes_array[$index] > $retransbytes_array[$counter]) {
            $retransbytes_delta = $retransbytes_array[$index] - $retransbytes_array[$counter];
        }
        if ($retransbytes_array[$index] < $retransbytes_array[$counter]) {
            $retransbytes_delta = ($retransbytes_array[$index] + $MAX_32BIT_INT) - $retransbytes_array[$counter];
        }

        my $tcp_retrans_rate = sprintf("%.3f", (($retransbytes_delta / $outdatabytes_delta) * 100));
        if ( $tcp_retrans_rate < 10.0) {
            print color('green');
        }
        if ( $tcp_retrans_rate > 15.0 && $tcp_retrans_rate < 25.0) {
        print color('blue');
        }
        if ( $tcp_retrans_rate > 25.0 && $tcp_retrans_rate < 40.0) {
            print color('magenta');
        }
        if ( $tcp_retrans_rate > 40.0) {
            print color('red');
        }
        printf("%.3f%% ", $tcp_retrans_rate);
        print color('reset');
        $index++;
        $counter++;
    }
}
printf("\n");


#
# Inform if there the ICMP in echos does not match the out responses
#
if ( $inechos != $outechoreps ) {
    my $drop_perc = sprintf("%.5f", (100 - (($outechoreps / $inechos) * 100)));
    printf("%s\n", $linebreak);
    printf("Observed possible problems with ICMP packet drops: ");
    if ( $drop_perc > 5 ) {
        print color('red');
    }
    if ( $drop_perc > 2 && $drop_perc <= 5 ) {
        print color('magenta');
    }
    if ( $drop_perc <= 2 ) {
        print color('green');
    }
    printf("%.5f%%", $drop_perc);
    print color('reset');
    printf("\n  (total inEchos = %d != outEchoReps = %d)\n\n", $inechos, $outechoreps);
}
print color('reset');

printf("<FIN>\n");

#!/usr/bin/perl -w
use POSIX qw(strftime);


$DIGEST_LEN = 6;

sub _key_2_ts {

        my ($kp1, $kp3) = @_;

        my $ts1_obf = $kp3;
        my $ts2 = substr($kp1, $DIGEST_LEN);
        my $ts1 = '';
        my @ts1_obf_chars = split(//, $ts1_obf);
        my @ts2_chars = split(//, $ts2);
        my $idx = 0;
        for my $c1 (@ts1_obf_chars) {
                my $c2 = $ts2_chars[$idx++];
                $idx = 0 if ($idx >= scalar @ts2_chars);
                my $code = ord($c1) - 17 - (ord($c2) - ord('0'));
                $ts1 .= chr($code);
        }

        my $ts = $ts1 . $ts2;
        if ($ts !~ /^\d+$/) {
                return 0;
        }
        return $ts;
}

$key = shift(@ARGV);
unless($key) {
  print "Usage: keycheck.pl LICENSE\n";
  exit();
}

@tmp = split('-',$key);

$expire= _key_2_ts($tmp[1],$tmp[3]);

print "expires on: " . strftime("%m/%d/%Y %H:%M:%S",localtime($expire)) . "\n";

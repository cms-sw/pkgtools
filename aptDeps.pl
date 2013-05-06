#!/usr/bin/env perl
#
# 
#
# David Lange, LLNL.
#

use strict;

my $path=$ENV{'PATH'};

my @sp0=split(':',$path);
my $aptcacheInPath=0;
foreach my $p (@sp0) {
    if ( -e "${p}/apt-cache" ) {
	$aptcacheInPath=1;
	last;
    }
}

if ( $aptcacheInPath == 0 ) {
    print "can not find apt-cache in PATH. Do you need to setup apt?\n";
    exit;
}

my $narg=@ARGV;
if ( $narg == 0 ) {
    print "usage: aptDeps.pl <rpm name1> .... <rpm nameN>\n";
    print " returns the list of rpms that would be installed by apt\n";
}

my %deps;

my $nrpm=0;
foreach my $rpm (@ARGV) {
    $deps{$rpm}=1;
    $nrpm++;
}

my $nrpmlast=0;

while ( $nrpmlast != $nrpm ) {
    $nrpmlast=$nrpm;
    foreach my $rpm (keys %deps) {
	
	my $newpacks=`apt-cache depends $rpm | grep Depends`;
	
	my @sp1=split('\n',$newpacks);
	foreach my $line (@sp1) {
	    if ( $line =~ /lcg\+/ || $line =~ /cms\+/ || $line =~ /external\+/ ) { 
		my @sp2=split(' ',$line);
		my $newrpm=$sp2[1];
		if ( !($deps{$newrpm}) ) {
		    $nrpm++;
		    $deps{$newrpm}=1;
		}
	    }
	}
    }
}    

foreach my $rpm (sort keys %deps) {
    print "$rpm\n";
}





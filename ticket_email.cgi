#!/usr/bin/perl 

use strict;
use CGI;
use CGI::Carp qw ( fatalsToBrowser );
use File::Basename;

### declare some variables upfront
my $attach_option;
my $filename;
my $upload_dir;
my $safe_filename;
my $sendmail = "/usr/sbin/sendmail -f 'XXXXXXXX' -F 'XXXXXXXX'";
## text file containing a list of valid email recipients and the web pages to which the user should be redirected after email is sent
my $emailConfPath = "/some/path/email.conf";

## get cert common name
my $q = CGI->new;
$ENV{ 'PATH' } = '/bin:/usr/bin:/usr/local/bin';
my $key1 = $ENV{SSL_CLIENT_S_DN_CN};
## added 5/6/16 to account for user certs using full middle name instead of middle initial in AD 
my $Searchfilter = `echo $key1 | awk -F"." '{b=\$1"."\$2"*"\$(NF-0)"*"; print b}'`; 
$Searchfilter =~ s/\r|\n//g;
## added 5/18/16 to account for users with spaces in their name entries
$Searchfilter =~ s/ .*\./\./g;
#print "$Searchfilter\n";


## ldap search - error messages left in for command line usage
## change "cn=$key1.*" to a client cn + e/c to test 
use Net::LDAP;
use Net::LDAP::LDIF;
use Net::LDAP::Util qw(ldap_error_text);

my $userDN = 'XXXXXXXX';
my $PASSWORD = 'XXXXXXXX';
my $LDAP_SERVER = 'XXXXXXXX';
my $LDAP_PORT = 'XXX';
my $LDAP_BASE = 'XXXXXXXX';

my $ldap = Net::LDAP->new($LDAP_SERVER, port => $LDAP_PORT)
                        or die "Coult not create LDAP object because:\n$!";

my $ldapMsg = $ldap->bind($userDN, password => $PASSWORD);

die $ldapMsg->error if $ldapMsg->is_error;

my $ldapSearch = $ldap->search(
                                base => $LDAP_BASE,
                                filter => "(&(cn=$Searchfilter)(!(cn=$Searchfilter.V)) (!(cn=$Searchfilter.ADM)))"
);

die "There was an error during search:\n\t" . ldap_error_text($ldapSearch->code) 
        if $ldapSearch->code;

print "No results returned\n" and exit 
        if( (!$ldapSearch) || ($ldapSearch->count == 0) );

my @emailaddy = ();
foreach my $entry ($ldapSearch->entries) {
        push @emailaddy, $entry->get_value("mail");
}

my @longname = ();
foreach my $entry ($ldapSearch->entries) {
        push @longname, $entry->get_value("displayName");
}
## end ldap search

my $query = new CGI;

## added for attach
my $attach_option = $query->param('attachment');
if ( $attach_option ) {
$CGI::POST_MAX = 1024 * 5000;
my $safe_filename_characters = "a-zA-Z0-9_.-";
my $upload_dir = "/some/path/shots";
my $filename = $query->param('attachment');
if ( !$filename )
{
print $query->header ( );
print "There was a problem uploading your attachment (try a smaller file).";
exit;
}
fileparse_set_fstype("MSDOS");
my ( $name, $path, $extension ) = fileparse ( $filename, '..*' );
$filename = $name . $extension;
$filename =~ tr/ /_/;
$filename =~ s/[^$safe_filename_characters]//g;
if ( $filename =~ /^([$safe_filename_characters]+)$/ )
{
$filename = $1;
}
else
{
die "Filename contains invalid characters";
}
my $upload_filehandle = $query->upload("attachment");
open ( UPLOADFILE, ">$upload_dir/$filename" ) or die "$!";
binmode UPLOADFILE;

while ( <$upload_filehandle> )
{
print UPLOADFILE;
}

close UPLOADFILE;
#chmod(0755, "$upload_dir/$filename") or die "Couldn't set the permission to $upload_dir/$filename: $!";
}
## close attach upload ##

## parse any submitted form fields and return an object we can use to retrieve them
my $recipient = &veryclean($query->param('recipient'));
my $subject = &veryclean($query->param('subject'));
my $web = &veryclean($query->param('web'));
my $sgml = &veryclean($query->param('sgml'));
my $frame = &veryclean($query->param('frame'));
my $host = &veryclean($query->param('host'));
my $tonum = &veryclean($query->param('tonum'));
my $change = &veryclean($query->param('change'));
my $toma = &veryclean($query->param('toma'));
my $content = &clean($query->param('content'));

## required fields
if (($subject eq "") || ($host eq "") || ($tonum eq "") || ($change eq "") || ($content eq "") || ($recipient eq ""))
{
        &error("XXXXXXXX",
                "<div class='rcorners1'><h2 align='center'>XXXXXXXX</h2><center>Unable to send ticket. Please fill out all fields provided.<br /><br /><a href='javascript:history.back()'>Go Back</a></center>");
}

if (!open(IN, "$emailConfPath")) {
        &error("XXXXXXXX",
                "<div class='rcorners1'><h2 align='center'>XXXXXXXX</h2><center>The file $emailConfPath does not exist or cannot be opened.<br /><br /><a href='javascript:history.back()'>Go Back</a></center>");
}

my $returnpage;

my $ok = 0;
while (1) {
        my $recipientc = <IN>;
        $recipientc =~ s/\s+$//;
        if ($recipientc eq "") {
                last;
        }
        my $returnpagec = <IN>;
        $returnpagec =~ s/\s+$//;
        if ($returnpagec eq "") {
                last;
        }
        if ($recipientc eq $recipient) {
                $ok = 1;
                $returnpage = $returnpagec;
                last;
        }
}
close(IN);
if (!$ok) {
        &error("XXXXXXXX",
                "<div class='rcorners1'><h2 align='center'>XXXXXXXX</h2><center>The requested destination address is not one of the permitted email recipients.<br /><br /><a href='javascript:history.back()'>Go Back</a></center>");
}

## open a pipe to the sendmail program
open(OUT, "|$sendmail -t");
## use <<EOM notation to include the message in this script more or less as it will actually appear
if ( $attach_option ) {
print OUT <<EOM
To: $recipient,@emailaddy
Subject: $subject XXXXXXXX
Reply-To: @emailaddy
A ticket has been submitted to the XXXXXXXX support team with the following information. This is an automatically generated email, please do not reply.

USER NAME - @longname

USER EMAIL - @emailaddy

CONTENTA SCHEMA - $subject

ISSUE WITH:
$web $sgml $frame

PC/HOSTNAME - $host

TO NUMBER - $tonum

CHANGE LEVEL - $change

TOMA NAME - $toma

DESCRIPTION:
$content

ATTACHMENT:

EOM
;
my $safe_filename_characters = "a-zA-Z0-9_.-";
my $upload_dir = "/some/path/shots";
my $filename = $query->param('attachment');
fileparse_set_fstype("MSDOS");
my ( $name, $path, $extension ) = fileparse ( $filename, '..*' );
$filename = $name . $extension;
$filename =~ tr/ /_/;
$filename =~ s/[^$safe_filename_characters]//g;
my $upfile = "$upload_dir/$filename";
open(FILE, "uuencode $upfile $filename| ") or die;
while( <FILE>) {print OUT};
close(FILE);
close(OUT);
}

else {
print OUT <<EOM
To: $recipient,@emailaddy
Subject: $subject XXXXXXXX
Reply-To: @emailaddy
A ticket has been submitted to the XXXXXXXX support team with the following information. This is an automatically generated email, please do not reply.

USER NAME - @longname

USER EMAIL - @emailaddy

CONTENTA SCHEMA - $subject

ISSUE WITH:
$web $sgml $frame

PC/HOSTNAME - $host

TO NUMBER - $tonum

CHANGE LEVEL - $change

TOMA NAME - $toma

DESCRIPTION:
$content

EOM
;

close(OUT);
}
## redirect to landing page for this recipient
print $query->redirect($returnpage);

exit 0;

sub clean
{
        ## clean up any leading and trailing whitespace using regular expressions
        my $s = shift @_;
        $s =~ s/^\s+//;
        $s =~ s/\s+$//;
        return $s;
}

sub veryclean
{
        ## forbid newlines by folding all internal whitespace to single spaces
        ## this prevents faking extra headers to cc extra people
        my $s = shift @_;
        $s = &clean($s);
        $s =~ s/\s+$/ /g;
        return $s;
}

sub error
{
        ## output a valid html page as an error message
        my($title, $content) = @_;
        print $query->header;
        print <<EOM
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
<meta http-equiv="X-UA-Compatible" content="IE=EmulateIE10">
<title>$title</title>
<link rel='stylesheet' type='text/css' href='https://XXXXXXXX/XXXX/style.css'>
</head>
<body>
$content
EOM
;
        exit 0;
}

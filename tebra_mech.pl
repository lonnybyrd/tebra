#!/usr/bin/perl
use strict;
use warnings;
use Selenium::Chrome;
use JSON;
use Time::HiRes qw(sleep);
use Spreadsheet::ParseXLSX;
use Excel::Writer::XLSX;

# copy latest chromedriver from https://googlechromelabs.github.io/chrome-for-testing/#stable to 
# /usr/local/bin/chromedriver

# Replace these with actual credentials
my $login = '';
my $password = '';

# Input and output file paths
my $input_file = 'encounters.csv';
my $output_file = 'supervision_sep30.html';
open(OUTPUTFILE, '>', $output_file) or die $!;

print OUTPUTFILE qq ~
<html>
<head>
  <title>Supervision Links</title>
  <style>
    a:link {
      color: blue;
    }
    a:visited {
      color: purple;
    }
    a:hover {
      color: darkblue;
    }
    a:active {
      color: red;
    }
  </style>
    <script>
  document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll("a").forEach(function(link) {
      link.addEventListener("click", function() {
        link.style.color = "purple"; // Manually simulate visited color
      });
    });
  });
  </script>
</head>
<title>Sept 2025 Supervision</title>
<h1>Sept 2025 Supervision</h1>
<h2>Neighborhood Urgent Care</h2>
Links are opened in new tabs.<br><br>
<body>~;

# Create new workbook to write output
#my $writer = Excel::Writer::XLSX->new($output_file);
#my $out_sheet = $writer->add_worksheet();

# Read spreadsheet
my $i = 0;
my $file = $input_file; 
my @data;
my @encounter_id;
open(my $fh, '<', $file) or die "Can't read file '$file' [$!]\n";
while (my $line = <$fh>) {
    chomp $line;
	$i++;
	next if($i == 1); # don't process the first line, because it has the headings in it
    my @fields = split(/,/, $line);
    push @data, \@fields;
	push @encounter_id, $fields[1];
	print "Encounter: $fields[1]\n";
#	last if($i > 2);
}

# Start Selenium
my $driver = Selenium::Chrome->new( extra_capabilities => {
    'goog:chromeOptions' => { args => ['--disable-gpu', '--window-size=1200,800'] }
});

# Log into Kareo
$driver->get('https://app.kareo.com/v2/#/sign-in');
sleep(2);
$driver->find_element('userName', 'id')->send_keys($login);
$driver->find_element('password', 'id')->send_keys($password);
$driver->find_element('sign-in', 'id')->click();
sleep(6);  # Adjust if needed

# Process each encounter
for my $eid (@encounter_id) {
    my $encounter_id = $eid;

    print "Processing encounter: $encounter_id\n";

    my $json_url = "https://app.kareo.com/charge-capture-ui/api/Encounter/$encounter_id/";
    $driver->get($json_url);
    sleep(3);

    my $json_text = $driver->execute_script('return document.body.innerText');
    my $json;
    eval { $json = decode_json($json_text); };
    if ($@ || !$json->{encounterClinicalNote}->{clinicalNoteId}) {
        warn "Failed to get note for encounter $encounter_id\n";
#        $out_sheet->write($row, $encounter_col, "ERROR");
        next;
    }
	
	my $ehrPatientId = $json->{encounter}->{ehrPatientId};
    my $clinicalNoteId = $json->{encounterClinicalNote}->{clinicalNoteId};

    my $link = "https://app.kareo.com/patients/$ehrPatientId/notes/$clinicalNoteId";
    
	print OUTPUTFILE "<a target=\"_blank\" href=\"$link\">$encounter_id.</a> $json->{encounterDiagnoses}->[0]{diagnosisCodeDictionary}{officialName}<br>\n";
	

    sleep(1.5);  # Be kind to the server
}
print OUTPUTFILE "</body></html>";
close(OUTPUTFILE);
$driver->quit;
print "Done! Output saved to $output_file\n";

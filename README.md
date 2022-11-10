# NYC-BOE Parser

### A scraper( called it a parser as a joke :D ) for the board of elections in the city of new york, unofficial election night results webpage.

To display the elections that the parser can print out use the command below:

`nyc_boe_parser.py -s`

To print the results of an election to the standard output use the number that corresponds to that election name that was shown with the command above and use the following command:

`nyc_boe_parser.py -e <election_number>`

The election results can also be formatted to json with the following command:

`nyc_boe_parser.py -e <election_number> -f json`

# NYC-BOE Parser

### A parser for the board of elections in the city of new york, unofficial election night results webpage.

### To show the elections that the parser can show use the command below:

`nyc_boe_parser.py -s`

### To print the results of an election to the standard output use the number that corresponds to that election name that was shown above and the following command:

`nyc_boe_parser.py -e <election_number>`

### The election results can also be formatted to json with the following command:

`nyc_boe_parser.py -e <election_number> -f json`
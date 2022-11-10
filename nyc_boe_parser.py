
#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

# The MIT License (MIT)
# Copyright (c) 2020 Michael M (mike.brooklyn525@gmail.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all 
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
# SOFTWARE.

from bs4 import BeautifulSoup
import argparse
import sys
import requests
import json
import csv

BASE_URL = 'https://web.enrboenyc.us/'

def get_assembly_district(url, percentage_reported="NA"):
	response = requests.get(url)
	soup = BeautifulSoup(response.text, 'html.parser')
	results = {}
	results['Total'], results['Candidates'] = get_meta_data(soup)
	results['Total']['Reporting'] = percentage_reported
	results['Detailed'] = {}
	a_tags = list(soup.findAll('a'))
	for a in a_tags:
		if a.string.strip().startswith('AD'):
			ad_num = int(a.string.replace('AD', '').strip())
			if a.get('href'):
				results['Detailed'][ad_num] = get_election_district(BASE_URL + a['href'])
	return results

def get_election_district(url):
	response = requests.get(url)
	soup = BeautifulSoup(response.text, 'html.parser')
	table = soup.findAll('table')[2]
	tbody = [node for node in list(table) if str(node).strip()]
	election_data = {}
	candidates = [node.string for node in list(tbody[0]) if str(node).strip() and node.string.replace('\xa0','')]
	for data in tbody[2:-1]:
		row_data = [node.string for node in list(data) if str(node).strip() and node.string.replace('\xa0','')]
		if row_data[0].strip().startswith('ED'):
			election_district = str(int(row_data[0].replace('ED', '').strip())).zfill(3)
			election_data[election_district] = {'Reporting': row_data[1]}
			# for fusion candidate, combines votes from different parties
			for candidate in set(candidates):
				election_data[election_district][candidate] = 0
			for i, candidate in enumerate(candidates):
				if row_data[2+i].isdigit():
					election_data[election_district][candidate] += int(row_data[2+i])
	return election_data

def get_meta_data(soup):
	total ={}
	table = soup.findAll('table')[2]
	tbody = [node for node in list(table) if str(node).strip()]
	row_data = [node.string for node in list(tbody[-1]) if str(node).strip() and node.string.replace('\xa0','')]
	candidates = [node.string for node in list(tbody[0]) if str(node).strip() and node.string.replace('\xa0','')]
	candidates_set = set(candidates)
	for candidate in candidates_set:
		total[candidate] = 0
	for i, candidate in enumerate(candidates):
		if row_data[1+i].isdigit():
			total[candidate] += int(row_data[1+i])
	return total, list(candidates_set)
	

def convert_json(filename, results):
	sys.stdout.write(json.dumps(results))

def convert_csv(filename, results):
	detailed_results = results['Detailed']
	cleaned_results = []
	for ad_key in detailed_results.keys():
		for ed_key in detailed_results[ad_key].keys():
			temp = {'AD-ED': str(ad_key)+"-"+ ed_key, **detailed_results[ad_key][ed_key]}
			cleaned_results.append(temp)
	cleaned_results.append({'AD-ED': "Total", **results['Total']})
	writer = csv.DictWriter(sys.stdout, fieldnames=cleaned_results[0].keys())
	writer.writeheader()
	for row in cleaned_results:
		writer.writerow(row)
	
def get_total_percentage_reported(url):
	response = requests.get(url)
	soup = BeautifulSoup(response.text, 'html.parser')
	table = soup.findAll('table')[2]
	reporting_label = table.find_all('label')
	if not len(reporting_label):
		return url
	return reporting_label[-1].string.strip()

def get_district_total_percentage_reported(url, position):
	response = requests.get(url)
	soup = BeautifulSoup(response.text, 'html.parser')
	table = soup.findAll('table')[2]
	a_tag_list = table.find_all('a')
	return get_total_percentage_reported(BASE_URL+a_tag_list[position]['href'])

def gather_information():
	response = requests.get(BASE_URL)
	soup = BeautifulSoup(response.text, 'html.parser')
	table = soup.findAll('table')[2]
	row_list = [[*node.find_all('td')] for node in list(table) if str(node).strip()][:-4]
	elections =  {}

	for row in row_list:
		if len(row) > 3:
			party = ""
			if row[3].string:
				party = row[3].string.strip()
			name = "%s %s" % (row[2].string.strip(), party)
			election_summary = ""
			for item in row[4:]:
				if item.a and item.a.string and item.a.string == "Summary":
					election_summary = BASE_URL+item.a['href']
				if item.a and item.a.string and item.a.string == "AD Details":
					if not elections.get(name, None):
						elections[name] ={}
					elections[name] = {
						'url': BASE_URL+item.a['href'].replace('ADI0.html','AD0.html'), 
						'district_race': not item.a['href'].endswith('ADI0.html'), 
						'party': party,
						'total_reported': election_summary
					}
	election_names = [*elections.keys()]
	for election_name in election_names:
		if elections[election_name]['district_race']:
			response = requests.get(elections[election_name]['url'])
			soup = BeautifulSoup(response.text, 'html.parser')
			links_list = soup.find_all('a')
			district_race_counter = 0
			for a_tag in links_list:
				if a_tag['href'].endswith('ADI0.html'):
					district_race = a_tag.string.strip()
					if elections[election_name]['party'] and not elections[election_name]['party'] in district_race:
						district_race = "%s %s" % (district_race, elections[election_name]['party'])
					elections[district_race] = {
						'url': BASE_URL+a_tag['href'].replace('ADI0.html', 'AD0.html'), 
						'district_race': True, 
						'party': elections[election_name]['party'],
						'total_reported': get_district_total_percentage_reported(elections[election_name]['total_reported'], district_race_counter)
					}
					district_race_counter+=1
			del elections[election_name]
	return elections


def main(show, election, output_format):
	elections = gather_information()
	selection_options = []
	for count, name in enumerate(elections.keys()):
		selection_options.append(name)
		if show:
			sys.stdout.write("%s: %s\n" % (str(count+1), name))
	if show:
		exit()
	selection = None
	while selection is None:
		try:
			selection = int(election)
		except Exception as e:
			print("Invalid entry, must use -e option followed by number corresponding to election!")
			selection=None
			exit()
		if selection > 0 and selection <= len(selection_options):
			selection -= 1
			url_download = elections[selection_options[selection]]['url']
			percentage_reported = elections[selection_options[selection]]['total_reported']
			if output_format == "json":
				convert_json(selection_options[selection], get_assembly_district(url_download, percentage_reported))
			else:
				convert_csv(selection_options[selection], get_assembly_district(url_download, percentage_reported))
		else:
			selection = None
			
	
if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--format", help="Format of the output file (json or csv only).")
	parser.add_argument("-s", "--show", action="store_true", default=False, help="Show all elections that can be shown.")
	parser.add_argument("-e", "--election", help="The number corresponding to election", type=int)
	args = parser.parse_args()
	output_format = args.format
	show_options = args.show
	election = args.election
	if output_format == None:
		output_format = "csv"
	main(show_options, election, output_format)

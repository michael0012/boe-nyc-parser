
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
from datetime import datetime
import argparse
import sys
import requests
import json
import csv

BASE_URL = 'https://web.enrboenyc.us/'

def get_assembly_district(url):
	response = requests.get(url)
	soup = BeautifulSoup(response.text, 'html.parser')
	results = {}
	results['Total'], results['Candidates'] = get_meta_data(soup)
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
		total[candidate] += int(row_data[1+i])
	return total, list(candidates_set)
	

def convert_json(filename, results):
	try:
		now = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
		filename = '%s_%s.json' % ( "_".join(filename.split()), now)
		with open(filename, 'w') as jsonfile:
			jsonfile.write(json.dumps(results))
	except IOError:
		print("I/O error")

def convert_csv(filename, results):
	results = results['Detailed']
	cleaned_results = []
	now = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
	filename = '%s_%s.csv' % ( "_".join(filename.split()), now)
	for ad_key in results.keys():
		for ed_key in results[ad_key].keys():
			temp = {'AD-ED': str(ad_key)+"-"+ ed_key, **results[ad_key][ed_key]}
			cleaned_results.append(temp)
	try:
		with open(filename , 'w') as csvfile:
			writer = csv.DictWriter(csvfile, fieldnames=cleaned_results[0].keys())
			writer.writeheader()
			for row in cleaned_results:
				writer.writerow(row)
	except IOError:
		print("I/O error")

def gather_information():
	print("Requesting data from BOE servers....")
	response = requests.get(BASE_URL)
	soup = BeautifulSoup(response.text, 'html.parser')
	table = soup.findAll('table')[2]
	row_list = [[*node.find_all('td')] for node in list(table) if str(node).strip()][:-4]
	Elections =  {}

	for row in row_list:
		if len(row) > 3:
			party = row[3].string.strip()
			name = "%s %s" % (row[2].string.strip(), party)
			for item in row[4:]:
				if item.a and item.a.string and item.a.string == "AD Details":
					if not Elections.get(name, None):
						Elections[name] ={}
					Elections[name] = {'url': BASE_URL+item.a['href'].replace('ADI0.html', 'AD0.html'), 'district_race': not item.a['href'].endswith('ADI0.html'), 'party': party}
	print("Expanding list of election races....")			
	election_names = [*Elections.keys()]
	for election_name in election_names:
		if Elections[election_name]['district_race']:
			response = requests.get(Elections[election_name]['url'])
			soup = BeautifulSoup(response.text, 'html.parser')
			links_list = soup.find_all('a')
			for a_tag in links_list:
				if a_tag['href'].endswith('ADI0.html'):
					district_race = a_tag.string.strip()
					if Elections[election_name]['party'] and not Elections[election_name]['party'] in district_race:
						district_race = "%s %s" % (district_race, Elections[election_name]['party'])
					Elections[district_race] = {'url': BASE_URL+a_tag['href'].replace('ADI0.html', 'AD0.html'), 'district_race': True, 'party': Elections[election_name]['party']}
			del Elections[election_name]
	return Elections


def main(output_format):
	Elections = gather_information()
	selection_options = []
	print("Displaying all election races...")
	for count, name in enumerate(Elections.keys()):
		selection_options.append(name)
		print("%s: %s" % (str(count+1), name))
	selection = None
	while selection is None:
		try:
			selection = int(input("Enter integer corresponding to election name... \n"))
		except ValueError:
			print("Invalid entry... please try again!")
			selection=None
		if selection > 0 and selection <= len(selection_options):
			selection -= 1
			url_download = Elections[selection_options[selection]]['url']
			if output_format == "json":
				convert_json(selection_options[selection], get_assembly_district(url_download))
			else:
				convert_csv(selection_options[selection], get_assembly_district(url_download))
		else:
			selection = None
			print("Selection number does not fall within range.")
	
if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--format", help="Format of the file output.")
	args = parser.parse_args()
	output_format = args.format
	if output_format == None:
		output_format = "csv"
	main(output_format)

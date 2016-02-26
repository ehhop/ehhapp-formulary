import re
import csv
from statistics import mean
from fuzzywuzzy import fuzz
from datetime import datetime
from collections import namedtuple, OrderedDict
import os


"""
###########################################################################
## Part1: Functions for updating the pricetable based on lastest invoice ##
###########################################################################
"""
# Classes and Functions for reading and parsing invoices
InvRec = namedtuple('InvoiceRecord', ['NAMEDOSE', 'NAME', 'DOSE', 'COST', 'CATEGORY', 'ITEMNUM',\
		'REQDATE'])
FuzzyMatch = namedtuple('FuzzyMatch', ['MD_NAMEDOSE', 'MD_PRICE', 'INV_NAMEDOSE', 'INV_PRICE', 'INV_ITEMNUM'])

def read_csv(filename):
	"""Read and filter a csv to create a list of drug and price records.
	"""
	# Open, read, and filter
	with open(filename, 'rU') as f:
 
		# Instantiate csv.reader
		readerobj = csv.reader(f)
		csvlines = [i for i in readerobj]

		# Filter for drug entries
		drugitemnumpatt = "\d{5}"
		itemnumcolumnindex = 2
		
		invoice = [i for i in csvlines if re.fullmatch(drugitemnumpatt,\
			i[itemnumcolumnindex])]

		return invoice

def read_pricetable(pricetable_path):
	"""Import unique drug and price records from a persistent pricetable.

	Load drug and price records from a persistent pricetable as InvRec(Collections.namedtuple) instances.
	Store uniquely in a dictionary by using the NAMEDOSE field as a key and the InvRec 
	instance as the value. If an entry with a more recent price is encountered, update the dictionary entry. 
	"""

	# Open, read, and filter
	with open(pricetable_path, 'rU') as f:
		
		# Instantiate csv.reader
		readerobj = csv.reader(f, delimiter='\t')
		next(readerobj) # Skip line with column headings
		csvlines = [i for i in readerobj]

		# Iterate over and parse each drug and price record
		pricetable = {}
		for item in csvlines:

			# Convert date string to datetime object
			dtformat = '%Y-%m-%d %H:%M:%S'
			datestr = item[4]
			converteddatetime = datetime.strptime(datestr, dtformat)

			# Instantiate namedtuple from using values returned by list indices
			entry = InvRec(
					NAMEDOSE = item[0], \
					NAME = "NaN", \
					DOSE = "NaN", \
					COST = item[1], \
					ITEMNUM = item[2], \
					CATEGORY = item[3], \
					REQDATE = converteddatetime)

			# Use NAMEDOSE field as the key 'k' for our dictionary of InvRec objects
			k = entry.NAMEDOSE

			# All keys will be stored immediately with their corresponding values.
			pricetable[k] = entry
		
		return pricetable

def compare_pricetable(pricetable, invoice):
	"""Update pricetable using only unique and most recent drug and price records from medication invoice.
	
	Parse drug and price records and load them as InvRec(Collections.namedtuple) instances.
	Store uniquely in a dictionary by using the NAMEDOSE field as a key and the InvRec 
	instance as the value. If an entry with a more recent price is encountered, update the dictionary entry. 
	"""

	# Iterate over and parse each drug and price record
	for item in invoice:

		# Convert date string to datetime object
		dtformat = '%m/%d/%y %H:%M'
		datestr = item[12]
		converteddatetime = datetime.strptime(datestr, dtformat)

		# Instantiate namedtuple from using values returned by list indices
		entry = InvRec(NAMEDOSE = item[3], \
				NAME = "NaN", \
				DOSE = "NaN", \
				COST = item[15], \
				ITEMNUM = item[2], \
				CATEGORY = item[8], \
				REQDATE = converteddatetime)
		
		# Use NAMEDOSE field as the key 'k' for our dictionary of InvRec objects
		k = entry.NAMEDOSE

		# New keys will be stored immediately with their corresponding values.
		# Otherwise, check incoming entry's requisition date and only update the
		# dictionary value if it is more recent than the current one.
		if k not in pricetable:
			pricetable[k] = entry
		else:
			if entry.REQDATE > pricetable[k].REQDATE:
				pricetable[k] = entry
	
	return pricetable

def write_pricetable(pricetable, pricetable_path):
	""" Write as pricetable based on Invoice Records in CSV format.
	"""

	with open(pricetable_path, "w") as f:
		header_str = "\t".join(['NAME DOSE', 'COST', 'ITEM NUM', 'CATEGORY', 'REQDATE'])
		writeList = [header_str]

		for k, v in pricetable.items(): 
			row = "{}\t{}\t{}\t{}\t{}".format(v.NAMEDOSE, v.COST, v.ITEMNUM, v.CATEGORY, v.REQDATE)
			writeList.append(row)

		writeString = "\n".join(writeList)
		
		# Write to file
		f.write(writeString)

# ---
# ---

"""
########################################################################################
## Part2: Functions for updating the EHHapp formulary based on the updated pricetable ##
########################################################################################
"""
# Classes and functions for reading and parsing the current EHHOP Formulary
class FormularyRecord:
	"""Define a class that corresponds to a formulary entry.

	Each formulary entry has the following instance attributes:
	
	* DRUG_NAME
	* DOSE, COST_pD - dosage size and price per dose
	* CATEGORY - e.g. ANALGESICS
	* BLACKLISTED - whether the drug is blacklisted or not
	* SUBCATEGORY - e.g. Topical, i.e. "Route of administration"
	"""

	_BLACKLIST_ = '~'
	_DOSECOSTPATT_ = re.compile(r"""
	(\$\d+[.0-9]?\d*-\$\d+[.0-9]?\d*
				|\$\d+[.0-9]?\d*)
			(?:\s)
			(?:\()
			([^\n]*?)
			(?:\))""", re.X)
	_NAMEGARBAGE_ = re.compile(r'(.+)(\s\(.+\).*)|(.+)(\s-.*)')
	_FEATURES_ = []

	def __init__(self, record):
		self.NAME = self._set_NAMEandBLACKLISTED(record)
		self.DOSECOST = self._get_DOSECOST(record)
		self.PRICETABLE = {}
		self.SUBCATEGORY = record[2]
		self.CATEGORY = record[3]
	
	def _set_NAMEandBLACKLISTED(self, record):
		"""Sets the NAME and BLACKLISTED attribute.

		Uses regex pattern to find the name.
		Sniffs for the _BLACKLIST_ and strips it - 
		and sets the BLACKLISTED attribute to true.
		"""

		namestring = record[0]
		m = self._NAMEGARBAGE_.match(namestring)
		
		if namestring[0] == self._BLACKLIST_:
			self.BLACKLISTED = True
			name = namestring.lstrip(self._BLACKLIST_)
		elif m:
			self.BLACKLISTED = False
			name = m.group(1)
			print('{} came from {}'.format(name, namestring))

			if bool(name) == False:
				name = m.group(3)
				print('What was once None is now {}'.format(name))

		else:
			self.BLACKLISTED = False
			name = namestring

		return name

	def _get_DOSECOST(self, record):
		"""Sets the DOSECOST attribute.

		Uses regex pattern to find prices and associated doses.
		The method re.findall is called so that multiple dose/cost
		pairs for a given drug are returned in a list.
		If no dose/cost matches are found, an empty list is returned.
		"""
		
		dosecoststring = record[1]
		match = self._DOSECOSTPATT_.findall(dosecoststring)

		return match

	def _get_SUBCATEGORY(self, record):
		"""Sets the SUBCATEGORY attribute.
		"""
		subcategory = ''

		return subcategory

	# Public Instance Methods

	def _set_PRICETABLE(self):
		"""Produce a dictionary to assist price check.
		"""
		for dosecost in self.DOSECOST:
			dose = dosecost[1]
			cost = dosecost[0]
			namedose = '{} {}'.format(self.NAME, dose)
			# self.PRICETABLE[namedose] = [cost, self.NAME, dose, str(self.BLACKLISTED), self.CATEGORY, self.SUBCATEGORY]
			self.PRICETABLE[namedose] = InvRec(
					NAMEDOSE = namedose,\
					NAME = self.NAME,\
					DOSE = dose,\
					COST = cost,\
					CATEGORY = self.CATEGORY,\
					ITEMNUM = "NaN",\
					REQDATE = "NaN")

	def _to_csv(self):
		"""Generate CSV from PRICETABLE.
		"""
		ndc_list = []

		for k, v in self.PRICETABLE.items():
			output_str = '{}\t{}\t{}\t{}\t{}'.format(k, v.COST, v.CATEGORY, v.ITEMNUM, v.REQDATE)
			ndc_list.append(output_str)

		write_str = '\n'.join(ndc_list)

		return write_str
		
	def _to_markdown(self):
		""" Generate output string.

		* CATEGORY
		> ~DRUG_NAME | COST_pD (DOSE) | SUBCATEGORY
		"""

		if self.BLACKLISTED == True:
			prefix = '~'
		else:
			prefix = ''


		dosesanmdcosts_list = []
		
		for k, v in self.PRICETABLE.items():
			output_str = '{} ({})'.format(v.COST, v.DOSE)
			dosesanmdcosts_list.append(output_str)

		dosesanmdcosts_str = ', '.join(dosesanmdcosts_list)

		markdown = '> {}{} | {} | {}'.format(prefix, self.NAME, dosesanmdcosts_str, self.SUBCATEGORY)
 
		return markdown

def read_md(filename):
	'''Read Markdown Formulary and parse into a list containing strings for each drug.

	Each list item is a string in EHHapp Markdown format:

	A line that denotes the drug category of all drug lines following it looks like this:

		* CATEGORY

	A line that contains a drug, its prices, doses, subcategories, blacklisted status, and potentially other metadata looks like this.

		> ~DRUGNAME (brandname) - other metadata | COSTpD (DOSE) | SUBCATEGORY
	'''
	with open(filename, 'rU') as f:
		rxlines = f.readlines()
		
		rxfiltered = []

		# Provide a match string and variable to keep track of lines denoting drug classes
		CATEGORY_mdown = '*'
		category = None
		
		# Provide strings to match lines corresponding to drugs 
		DRUG_mdown = '>'
		beginningoflinestrindex = 0
		
		for l in rxlines:
			if l[beginningoflinestrindex] == CATEGORY_mdown:
				category = l.lstrip('\* ').rstrip()
				continue
			elif l[beginningoflinestrindex] == DRUG_mdown:
				rxfiltered.append(l + ' | ' + category)
			else:
				continue

		return rxfiltered

def parse_mddata(rxfiltered, delimiter="|"):
	"""Parse a list of Markdown strings (lomd) to return list of lists (lol).
	"""
	mdlol = [string.lstrip("> ").rstrip().split(delimiter) for string in rxfiltered]

	parsedformulary = []
	for item in mdlol:
		item = [s.strip() for s in item]
		parsedformulary.append(item)

	return parsedformulary

def store_formulary(parsedformulary):
	"""Store a bunch of formulary record objects in a list.
	"""

	formulary = []

	for record in parsedformulary:
		formulary.append(FormularyRecord(record))

	return formulary

"""
All of these functions should keep track of differences between new and old data
"""
def match_string(string, phrase):
	'''Determines if any of the full words in 'string' match any of the full words in the phrase
	Returns True or False
	'''
	string_split = string.split()
	phrase_split = phrase.split()
	is_match = set(string_split) < set(phrase_split)

	return is_match

def match_string_fuzzy(string, phrase, set_similarity_rating):
	'''Determines if any of the full words in 'string' match any of the full words in the phrase
	Returns True or False
	'''
	string_split = string.split()
	phrase_split = phrase.split()
	overall_match = []

	for s in string_split:
		highest_match = 0
		# Find highest match for each single word in the formulary drug name
		s = s.lower()
		for p in phrase_split:
			p = p.lower()
			percent_match = fuzz.partial_ratio(s, p)
			if percent_match > highest_match:
				highest_match = percent_match

		overall_match.append(highest_match)

	if mean(overall_match) > set_similarity_rating:
		is_fuzzy_match = True
	else:
		is_fuzzy_match = False

	return is_fuzzy_match

def price_disc(mdcost, invcost):
	if mdcost != invcost:
		new_price = True
	else:
		new_price = False
	return new_price

def formulary_update_from_pricetable(formulary, pricetable, set_similarity_rating=100):
	"""Update drugs in formulary with prices from invoice.
	"""
	# Keeps track of soft matches
	smatchcount = 0

	# Keeps track of the number of matches
	mcount = 0

	# Keeps track of the number of price changes
	pricechanges = 0

	# Keeps track of pricetable medications without a match in the pricetable
	pricetable_unmatched_meds = []

	# Captures fuzzy matches between invoice and formulary medications
	fuzzymatches = {}

	# Loop through each FormularyRecord
	for record in formulary:
		# Set the PRICETABLE attribute
		record._set_PRICETABLE()

	# Look up a matching record stored in the invoice-derived pricetable
	for nd, ir in pricetable.items():
		invnamedose = nd.lower()
		invcost = ir.COST.lower()
		itemnum = ir.ITEMNUM

		# Keeps track of whether there a match for each pricetable medication
		has_pricetable_match = False

		# Loop through each FormularyRecord
		for record in formulary:

			# Then loop through each dose/cost pair for the given record
			for k, v in record.PRICETABLE.items():
				mdcost = v.COST.lower()
				mdnamedose = k.lower()
				mdname = v.NAME.lower()
				mddose = v.DOSE.lower()

				dosepatt = re.compile(r"\b{}".format(mddose))

				# Use fuzzy matching to capture edge cases
				if match_string_fuzzy(mdname, invnamedose, set_similarity_rating=70):
					
					# Is soft match if formulary name is similar of pricetable name of same dose
					if dosepatt.search(invnamedose):
						softmatch = True
						smatchcount += 1
						has_pricetable_match = True

					# Is match formulary name is subset of pricetable name and doses are same
					if match_string(mdname, invnamedose):

						if dosepatt.search(invnamedose):
							mcount += 1
							
							if price_disc(mdcost, invcost):
								pricechanges += 1
								record.PRICETABLE[k] = v._replace(COST = invcost, ITEMNUM = itemnum)
								print("New price found for {} a.k.a. {}\nFormulary price: {}\nInvoice price: {}".format(invnamedose, k, mdcost, invcost))
								print("Formulary updated so price is now {}".format(record.PRICETABLE[k].COST))
					
					# Is partial match if formulary name is not subset of pricetable name,
					# formulary name is similar to pricetable name, and doses are same
					else:
						if dosepatt.search(invnamedose):
							fuzzymatches[invnamedose] = FuzzyMatch(
								MD_NAMEDOSE = mdnamedose,\
								MD_PRICE = mdcost,\
								INV_NAMEDOSE = invnamedose,\
								INV_PRICE = invcost,\
								INV_ITEMNUM = itemnum)
							'''
							print('\nFound a poor match...')
							print('Formulary name and dose is: '+str(mdname)+' '+ str(mddose))
							print('Invoice name and dose is: '+str(invnamedose))
							
							user_input = input('Are these the same medication?\nPlease type \'y\' or \'n\': ')

							while not user_input == 'y' and not user_input == 'n':
								user_input = input('Please try again. Are these the same medication?\nPlease type \'y\' or \'n\': ') # error check for user input

							if user_input == 'y':
								has_pricetable_match = True
								mcount += 1
								if price_disc(mdcost, invcost):
									pricechanges += 1
									record.PRICETABLE[k] = v._replace(COST = invcost, ITEMNUM = itemnum)
									print("New price found for {} a.k.a. {}\nFormulary price: {}\nInvoice price: {}".format(invnamedose, k, mdcost, invcost))
									print("Formulary updated so price is now {}".format(record.PRICETABLE[k].COST))
							elif user_input == 'n':
								print('This medication price will not be changed.')
							'''
		if has_pricetable_match == False:
			capture = invnamedose
			pricetable_unmatched_meds.append(capture)

	return mcount, pricechanges, formulary, smatchcount, pricetable_unmatched_meds, fuzzymatches

def formulary_update_from_usermatches(formulary, usermatches, pricetable_unmatched_meds):
	"""Update drugs in formulary with prices from user.
	"""
	# Keeps track of the number of matches
	newmcount = 0

	# Keeps track of the number of price changes
	newpricechanges = 0

	# Keeps track of pricetable medications without a match in the pricetable
	new_pricetable_unmatched_meds = []

	# Add fuzzy matches info to a dictionary
	matches = {}
	for line in usermatches:

		# Divide each line into items deliminated by ":"
		item = line.split(':')

		# Instantiate namedtuple from using values returned by list indices
		entry = FuzzyMatch(
			MD_NAMEDOSE = item[0],\
			MD_PRICE = item[1],\
			INV_NAMEDOSE = item[2],\
			INV_PRICE = item[3],\
			INV_ITEMNUM = item[4]
			)

		# Use markdown formulary NAMEDOSE field as the key 'k' for our dictionary of InvRec objects
		k = entry.NAMEDOSE

		# All keys will be stored immediately with their corresponding values.
		matches[k] = entry

	# Loop through each FormularyRecord
	for record in formulary:
		# Set the PRICETABLE attribute
		record._set_PRICETABLE()

		# Loop through the fuzzy matches
		for k, v in matches.items():
			md_namedose = k.lower()
			inv_namedose = v.INV_NAMEDOSE
			inv_price = v.INV_PRICE
			inv_itemnum = v.INV_ITEMNUM

			# Find formulary medication with same namedose as fuzzy match
			md_medication = record.PRICETABLE[MD_NAMEDOSE]
			
			newmcount += 1
			
			# Update formulary medication price if there is price difference
			if md_medication.COST != inv_price:
				newpricechanges += 1
				record.PRICETABLE[k] = v._replace(COST = inv_price, ITEMNUM = inv_itemnum)
				print("New price found for {} a.k.a. {}\nFormulary price: {}\nInvoice price: {}".format(invnamedose, k, mdcost, invcost))
				print("Formulary updated so price is now {}".format(record.PRICETABLE[k].COST))

		if has_pricetable_match == False:
			capture = invnamedose
			pricetable_unmatched_meds.append(capture)

	return newmcount, newpricechanges, formulary, pricetable_unmatched_meds

"""
### WORK-IN-PROGRESS
These functions control output to Markdown
"""
def formulary_to_Markdown(formulary, updated_markdown_filename):
	'''Outputs updated Formulary database to Markdown.
	'''
	output = []
	
	category = formulary[0].CATEGORY
	output.append("* {}".format(category))
	
	for record in formulary:
		if record.CATEGORY != category:
			category = record.CATEGORY
			output.append("* {}".format(category))

		output.append(record._to_markdown())

	with open(updated_markdown_filename, "w") as f:
		f.write('\n'.join(output))

def formulary_to_TSV(formulary, updated_pricetable_path):
	'''Outputs updated Formulary database to CSV
	'''
	output = []

	for record in formulary:
		output.append(record._to_csv())

	with open(updated_pricetable_path, "w") as f:
		f.write('\n'.join(output))

"""
Janky ass debug functions
"""
'''
def screen_and_console_print(output, screen_output):
	print(output)
	screen_output.append(output)
	return screen_output
'''
def process_pricetable(invoice_path, pricetable_path, verbose_debug=False):
	'''Main function of script. Creates updated formulary markdown and pricetable.

	Data files need to be place in a subfolder named "input".
	Input varibles are filenames without the file path prefix.
	Verbose output displays subsets of data during each step of processing.
	'''
	# Process FileIO
	output_filename_list = []

	pricetable_filename = pricetable_path.split('/')[-1] #remove directory from filename
	pricetable_filename_no_extension = pricetable_filename.split('.', 1)[0]

	current_script_path = os.path.realpath(__file__)[:-len('/rxparse.py')]
	pricetable_updated_path = current_script_path+'/output/'+pricetable_filename_no_extension+'_UPDATED.tsv'
	
	output_filename_list.append(pricetable_filename_no_extension+'_UPDATED.tsv')

	# Create container for webpage output
	screen_output = []

	# Processing Invoice
	print('\nProcessing Invoice...')
	
	recordlist = read_csv(str(invoice_path))
	print('Number of invoice entries: {}'.format(len(recordlist)))
	screen_output.append(['Number of invoice entries',len(recordlist)])

	if verbose_debug:
		print('Sample Invoice:')
		print(recordlist[0])

	pricetable = read_pricetable(pricetable_path)
	pricetable_updated = compare_pricetable(pricetable, recordlist)
	write_pricetable(pricetable, pricetable_updated_path)

	print('Number of price table entries: {}'.format(len(pricetable)))
	screen_output.append(['Number of price table entries',len(pricetable)])
	print('Each Entry is a: {}'.format(type(next(iter(pricetable.values())))))
	return(pricetable_updated_path, screen_output, output_filename_list)

def process_formulary(pricetable_updated_path, formulary_md_path, output_filename_list, screen_output, verbose_debug=False):
	# Load updated pricetable
	pricetable = read_pricetable(pricetable_updated_path)

	# Processing formulary
	print('\nProcessing Formulary Markdown...')
	formularylist = read_md(str(formulary_md_path))
	formularyparsed = parse_mddata(formularylist)

	print('Number of EHHapp formulary medications: {}'.format(len(formularyparsed)))
	screen_output.append(['Number of EHHapp formulary medications',len(formularyparsed)])

	if verbose_debug:
		print('Extracted Formulary Entries:')
		print(formularyparsed[0])
		for i in range(0,4):
			print('from Formulary: NAME:{} DOSECOST:{}'.format(FormularyRecord(formularyparsed[i]).NAME, FormularyRecord(formularyparsed[i]).DOSECOST))

	formulary = store_formulary(formularyparsed)
	
	# Updating Formulary Against Invoice
	print('\nFinding Matches...')
	mcount, pricechanges, updatedformulary, softmatch, pricetable_unmatched_meds, fuzzymatches = formulary_update_from_pricetable(formulary, pricetable)

	print('Number of partial medication matches: {}'.format(softmatch))
	screen_output.append(['Number of partial medication matches',softmatch])

	print('Number of medication matches: {}'.format(mcount))
	screen_output.append(['Number of medication matches',mcount])

	print('Number of EHHapp formulary price changes: {}'.format(pricechanges))
	screen_output.append(['Number of EHHapp formulary price changes',pricechanges])

	print('Number of invoice medications without match: {}'.format(len(pricetable_unmatched_meds)))
	screen_output.append(['Number of invoice medications without match',pricetable_unmatched_meds])

	if verbose_debug:
		print('Number of invoice medications without match')
		for med in pricetable_unmatched_meds:
			print(med)

		for i in range(0,4):
			print('updated Formulary markdown: {}'.format(updatedformulary[i]._to_markdown()))
	
	# Test BLACKLISTED attribute
	blacklisted = [d for d in updatedformulary if d.BLACKLISTED]

	print('Number of blacklisted drugs: {}'.format(len(blacklisted)))
	screen_output.append(['Number of blacklisted drugs',len(blacklisted)])

	return pricetable_unmatched_meds, output_filename_list, screen_output, fuzzymatches

def process_usermatches(usermatches, formulary_md_path, pricetable_unmatched_meds, output_filename_list, screen_output):
	# Process FileIO
	formulary_md_filename = formulary_md_path.split('/')[-1] #remove directory from filename
	formulary_md_filename_no_extension = formulary_md_filename.split('.', 1)[0]

	current_script_path = os.path.realpath(__file__)[:-len('/rxparse.py')]

	formulary_update_rm_path = current_script_path+'/output/'+formulary_md_filename_no_extension+'_UPDATED.markdown'
	output_filename_list.append(formulary_md_filename_no_extension+'_UPDATED.markdown')
	formulary_update_tsv_path = current_script_path+'/output/'+formulary_md_filename_no_extension+'_UPDATED.tsv'
	output_filename_list.append(formulary_md_filename_no_extension+'_UPDATED.tsv')

	# Processing formulary
	print('\nProcessing Formulary Markdown...')
	formularylist = read_md(str(formulary_md_path))
	formularyparsed = parse_mddata(formularylist)
	formulary = store_formulary(formularyparsed)

	newmcount, newpricechanges, updatedformulary, pricetable_unmatched_meds = formulary_update_from_usermatches(formulary, usermatches, pricetable_unmatched_meds)

	# Save updated formulary as markdown and tsv
	formulary_to_Markdown(updatedformulary, formulary_update_rm_path)
	formulary_to_TSV(updatedformulary, formulary_update_tsv_path)

	print('Number of partial medication matches: {}'.format(softmatch))
	screen_output.append(['Number of partial medication matches',softmatch])

	print('Number of medication matches: {}'.format(mcount))
	screen_output.append(['Number of medication matches',mcount])

	print('Number of EHHapp formulary price changes: {}'.format(pricechanges))
	screen_output.append(['Number of EHHapp formulary price changes',pricechanges])

	print('Number of invoice medications without match: {}'.format(len(pricetable_unmatched_meds)))
	screen_output.append(['Number of invoice medications without match',pricetable_unmatched_meds])

	#TODO update the screen output
	return pricetable_unmatched_meds, screen_output

if __name__ == "__main__":
	from sys import argv
	update_rx(argv[1], argv[2], argv[3])
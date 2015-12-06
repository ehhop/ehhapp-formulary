import re
import csv
from datetime import datetime
from collections import namedtuple
import pprint

# Classes and Functions for reading and parsing invoices
InvRec = namedtuple('InvoiceRecord', ['NAMEDOSE', 'COST', 'CATEGORY', 'ITEMNUM', 'REQDATE'])

def read_csv(filename):
    """Read and filter a csv to create a list of drug and price records.
    """

    with open(filename, 'rU') as f:
        
        # Instantiate csv.reader
        readerobj = csv.reader(f)
        csvlines = [i for i in readerobj]

        # Filter for drug entries
        drugitemnumpatt = "\d{5}"
        itemnumcolumnindex = 2
        recordlist = [i for i in csvlines if re.fullmatch(drugitemnumpatt, i[itemnumcolumnindex])]
        
        return recordlist

def store_pricetable(recordlist):
    """Store only unique and most recent drug and price records.
 
    Parse drug and price records and load them as InvRec(Collections.namedtuple) instances.
    Store uniquely in a dictionary by using the ITEMNUM field as a key and the InvRec 
    instance as the value. If an entry with a more recent price is encountered, update the dictionary entry. 
    """

    # Iterate over and parse each drug and price record
    pricetable = {}
    for record in recordlist:

        # Convert date string to datetime object
        dtformat = '%m/%d/%y %H:%M'
        datestr = record[12]
        converteddatetime = datetime.strptime(datestr, dtformat)


        # Instantiate namedtuple from using values returned by list indices
        entry = InvRec(NAMEDOSE = record[3], \
                COST = record[15], \
                CATEGORY = record[8], \
                ITEMNUM = record[2], \
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

def write_pricetable(pricetable):
    """ Write as pricetable based on Invoice Records in CSV format.
    """

    with open("pricetable.tsv", "w") as f:
        header_str = "\t".join(list(InvRec._fields))
        writeList = [header_str]

        for k, v in pricetable.items():
            row = "{}\t{}\t{}\t{}\t{}".format(v.ITEMNUM, v.CATEGORY, k, v.COST, v.REQDATE)
            writeList.append(row)

        writeString = "\n".join(writeList)
        f.write(writeString)

# Classes and functions for reading and parsing the current EHHOP Formulary
def read_md(filename):
    """Make md files available as a list of strings (yes these are enumerable).
    """
    with open(filename, 'rU') as f:
        rxlines = f.readlines()

        # Provide a regex and variable to keep track of lines denoting drug categories
        CATEGORYPATT = re.compile('(^\*.+)')
        category = None

        rxfiltered = []
        CATEGORY_mdown = '*'
        DRUG_mdown = '>'
        beginningoflinestrindex = 0
        
        for l in rxlines:
            if l[beginningoflinestrindex] == CATEGORY_mdown:
                category = l.lstrip('\* ').rstrip
                continue
            elif l[beginningoflinestrindex] == formularyrecmarker:
                rxfiltered.append(l + ' | ' + category)
            else:
                continue

        return rxfiltered

def parse_mddata(lomd, delimiter="|"):
    """Parse a list of Markdown strings (lomd) to return list of lists (lol).
    """
    mdlol = [string.lstrip("> ").rstrip().split(delimiter) for string in lomd]

    parsedformulary = []
    for item in mdlol:
        item = [s.strip() for s in item]
        parsedformulary.append(item)

    return parsedformulary

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
            self.PRICETABLE[namedose] = [cost, self.NAME, dose, str(self.BLACKLISTED), self.CATEGORY, self.SUBCATEGORY]

    def _to_csv(self):
        """Generate CSV from PRICETABLE.
        """
        ndc_list = []

        for k, v in self.PRICETABLE.items():
            output_str = '{}\t{}\t{}\t{}\t{}\t{}'.format(k, v[1], v[2], v[0], v[3], v[4], v[5])
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


        dosesandcosts_list = []
        
        for k, v in self.PRICETABLE.items():
            output_str = '{} ({})'.format(v[0], v[2])
            dosesandcosts_list.append(output_str)

        dosesandcosts_str = ', '.join(dosesandcosts_list)

        markdown = '> {}{} | {} | {}'.format(prefix, self.NAME, dosesandcosts_str, self.SUBCATEGORY)
 
        return markdown

def store_formulary(parsedformulary):
    """Store a bunch of formulary record objects in a list.
    """

    formulary = []

    for record in parsedformulary:
        formulary.append(FormularyRecord(record))

    return formulary

RxRec = namedtuple('FormularyRecord', ['NAMEDOSE', 'BLACKLISTED', 'DOSE', 'COST', 'CATEGORY', 'SUBCATEGORY'])

def expand_formulary(formulary):
    '''Expand list of formulary record objects into useful name dose entries.
    '''

    formularyexpanded = []

    for record in formulary:
        record._set_PRICETABLE()

    return formularyexpanded

"""
All of these functions should keep track of differences between new and old data
"""
def match_word(word, phrase):
    '''Determines if 'word' matches any of the full words in the phrase
    
    Returns True or False
    '''
    return word in phrase.split()

def match_string(string, phrase):
    '''Determines if any of the full words in 'word_string' match any of the full words in the phrase
    Returns True or False
    '''
    string_split = string.split()
    for part in string_split:
        if not match_word(part, phrase):
            # when a word in the word_string does not have a match in the phrase, is_match returns as False
            # the loop then moves on to the next word_string
            is_match = False
            continue
        else:
            is_match = True
            # if all the words in world_string have a match in the phrase, is_match remains true
    return is_match

def formulary_update(formulary, pricetable):
    """Update drugs in formulary with prices from invoice.
    """
    # Keeps track of soft matches
    smatchcount = 0

    # Keeps track of the number of matches
    mcount = 0

    # Match Dictionary
    matchdict = {}

    # Loop through each FormularyRecord
    for record in formulary:

        # Set the PRICETABLE attribute
        record._set_PRICETABLE()

        # Then loop through each dose/cost pair for the given record
        for k, v in record.PRICETABLE.items():
            dcost = v[0].lower()
            dnamedose = k.lower()
            dname = v[1].lower()
            ddose = v[2].lower()

            dosepatt = re.compile(r"\b{}".format(ddose))

            # Look up a matching record stored in the invoice-derived pricetable
            for nd, ir in pricetable.items():
                invnamedose = nd.lower()
                invcost = ir.COST.lower()

                # If the name and dose are a substring of the pricetable key then we have a match
                if re.match(dname, invnamedose):
                    if match_string(dname, invnamedose): # debugging edge phrases
                        softmatch = True
                        smatchcount += 1
                        
                        if dosepatt.search(invnamedose):

                            match = True
                            mcount += 1
                            
                            matchdict[k] = (record, ir)
                    else: # debugging edge phrases
                        print('matching...')
                        print('dname is: ' + str(dname))
                        print('ddose is: ' + str(ddose))
                        print('invnamedose is: ' + str(invnamedose))
    pricechanges = 0

    for m, n in matchdict.items():
        frec, irec = n
        
        if frec.PRICETABLE[m][0].lower() != irec.COST:
            print("New price found for {} a.k.a. {}\nFormulary price: {}\nInvoice price: {}".format(irec.NAMEDOSE, m, frec.PRICETABLE[m][0], irec.COST))
            pricechanges += 1

            frec.PRICETABLE[m][0] = irec.COST

    return mcount, pricechanges, formulary, smatchcount

"""
### WORK-IN-PROGRESS
These functions control output to Markdown
"""
def to_Markdown(formulary):
    output = []
    
    category = formulary[0].CATEGORY
    output.append("* {}".format(category))
    
    for record in formulary:
        if record.CATEGORY != category:
            category = record.CATEGORY
            output.append("* {}".format(category))

        output.append(record._to_markdown())

    with open("invoice-extract.markdown", "w") as f:
        f.write('\n'.join(output))

def to_CSV(formulary):
    output = []

    for record in formulary:
        output.append(record._to_csv())

    with open("formulary_pricetable.csv", "w") as f:
        f.write('\n'.join(output))
"""
Janky ass debug functions
"""

if __name__ == "__main__":
    import sys
    
    # Processing Invoice
    print('Processing Invoice...\n')
    recordlist = read_csv(str(sys.argv[1]))
    print('Number of Invoice Entries: {}'.format(len(recordlist)))
    print(recordlist[0])
    
    pricetable = store_pricetable(recordlist)
    print('Number of Price Table Entries: {}\nEach Entry is a: {}'.format(len(pricetable), type(next(iter(pricetable.values())))))

    # Processing Formulary
    print('Processing Formulary...\n')
    formularylist = read_md(str(sys.argv[2]))
    formularyparsed = parse_mddata(formularylist)
    print('Number of Formulary Records: {}'.format(len(formularyparsed)))
    print(formularyparsed[0])
    for i in range(0,4):
        print('from Formulary: NAME:{} DOSECOST:{}'.format(FormularyRecord(formularyparsed[i]).NAME, FormularyRecord(formularyparsed[i]).DOSECOST))

    formulary = store_formulary(formularyparsed)
    
    # Updating Formulary Against Invoice
    mcount, pricechanges, updatedformulary, softmatch  = formulary_update(formulary, pricetable)
    print('Number of medication matches found: {}\nNumber of price changes found: {}\nNumber of soft matches made: {}'.format(mcount, pricechanges, softmatch))

    for i in range(0,4):
        print('updated Formulary markdown: {}'.format(updatedformulary[i]._to_markdown()))

    to_Markdown(updatedformulary)
    to_CSV(updatedformulary)
    write_pricetable(pricetable)

    # Test BLACKLISTED attribute

    blacklisted = [d for d in updatedformulary if d.BLACKLISTED]
    print('The number of drugs are blacklisted: {}'.format(len(blacklisted)))

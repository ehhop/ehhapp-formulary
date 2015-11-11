import re
import csv
from datetime import datetime
from collections import namedtuple

# Functions for reading anding parsing invoices
def read_csv(filename):
    """A csv file becomes a list.
    
    Each element of the list \
            is a list corrsponding to a row \
            containing elements which are \
            is a strings corresponding to values \
            for a given row and column.
    """

    with open(filename, 'rU') as f:
        readerobj = csv.reader(f)
        csvlines = []
        
        for item in readerobj:
            csvlines.append(item)
        
        return csvlines

def filter_loe(loe, value="\d{5}", index=2):
    """Filters list of enumerables (loe) by value and index.

    A list comprehension is used to check each list at
    position specified by index for a full match with
    the regular expression pattern specified by value
    argument.

    value = "\d{5}" by default.
    """

    filteredlist = [l for l in loe if re.fullmatch(value, l[index])]
    return filteredlist

# Returns a tuple subclass named InvoiceRecord with named fields NAMEDOSE, etc.
InvRec = namedtuple('InvoiceRecord', ['NAMEDOSE', 'COST', 'CATEGORY', 'ITEMNUM', 'REQDATE'])

def store_pricetable(recordlist):
    """For each drug record, generate an instance of InvoiceRecord with relevant parameters.
    
    Remove duplicates by generating a dictionary based on item number keys.
    """

    pricetable = {}

    for record in recordlist:

        # Convert date string to datetime object
        dtformat = '%m/%d/%y %H:%M'
        converteddatetime = datetime.strptime(record[12], dtformat)
        
        entry = InvRec(NAMEDOSE = record[3], \
                COST = record[15], \
                CATEGORY = record[8], \
                ITEMNUM = record[2], \
                REQDATE = converteddatetime)                

        drugname = entry.NAMEDOSE

        if drugname not in pricetable:
            pricetable[drugname] = entry
        else:
            if entry.REQDATE > pricetable[drugname].REQDATE:
                pricetable[drugname] = entry
    
    return pricetable

"""
Create FormularyRecord objects from EHHapp Markdown so names of drugs and prices can be compared
"""
def read_md(filename):
    """Make md files available as a list of strings (yes these are enumerable).
    """
    with open(filename, 'rU') as f:
        mdlines = f.readlines()
        return mdlines

def filter_rx(loe, value=">", index=0):
    """Filter list of enumerables (lol) by value and index.

    A list comprehension is used to check each list at
    position specified by index for a full match with
    the regular expression pattern specified by value
    argument.

    value = "\d{5}" by default.
    """

    CATEGORYPATT = re.compile('(^\*.+)') 

    filteredlist = []
    
    category = None

    for l in loe:
        if CATEGORYPATT.match(l):
            category = CATEGORYPATT.match(l).groups()[0].lstrip('\* ')
            continue
        elif l[index] == value:
            filteredlist.append(l + ' | ' + category)
        else:
            continue

    return filteredlist

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
            self.PRICETABLE[namedose] = [cost, self.NAME, dose]

    def _to_csv(self):
        """Generate CSV from PRICETABLE.
        """
        ndc_list = []

        for k, v in self.PRICETABLE.items():
            output_str = '{},{},{},{}'.format(k, v[1], v[2], v[0])
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

"""
All of these functions should keep track of differences between new and old data
"""
def formulary_update(formulary, pricetable):
    """Update drugs in formulary with prices from invoice.
    
    Called when formulary is a parsed list of lists,
    and most recent drug prices per DOSENAME are stored in a dictionary.
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

                    softmatch = True
                    smatchcount += 1

                    if dosepatt.search(invnamedose):

                        match = True
                        mcount += 1

                        matchdict[k] = (record, ir)

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
    csvdata = read_csv(str(sys.argv[1]))
    print(len(csvdata))
    print(csvdata[0])
    recordlist = filter_loe(csvdata)
    print('Number of Invoice Entries: {}'.format(len(recordlist)))
    print(recordlist[0])
    
    pricetable = store_pricetable(recordlist)
    print('Number of Price Table Entries: {}\nEach Entry is a: {}'.format(len(pricetable), type(next(iter(pricetable.values())))))

    # Processing Formulary
    print('Processing Formulary...\n')
    mddata = read_md(str(sys.argv[2]))
    print(len(mddata))
    print(mddata[0])
    formularylist = filter_rx(mddata)
    print(len(formularylist))
    print(formularylist[0])
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

    # Test BLACKLISTED attribute

    blacklisted = [d for d in updatedformulary if d.BLACKLISTED]
    print('The number of drugs are blacklisted: {}'.format(len(blacklisted)))

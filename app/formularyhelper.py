import re
from collections import namedtuple

# Classes and Functions for reading and parsing invoices
InvRec = namedtuple('InvoiceRecord', ['NAMEDOSE', 'NAME', 'DOSE', 'COST', 'CATEGORY', 'ITEMNUM',
                                      'ON_FORMULARY','REQDATE'])
FuzzyMatch = namedtuple('FuzzyMatch', ['MD_NAMEDOSE', 'MD_PRICE', 'INV_NAMEDOSE', 'INV_PRICE', 'INV_ITEMNUM'])


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
            #self.PRICETABLE[namedose] = [cost, self.NAME, dose, str(self.BLACKLISTED), self.CATEGORY, self.SUBCATEGORY]
            self.PRICETABLE[namedose] = InvRec(
                NAMEDOSE=namedose, \
                NAME=self.NAME, \
                DOSE=dose, \
                COST=cost, \
                CATEGORY=self.CATEGORY, \
                ITEMNUM="NaN", \
                ON_FORMULARY="NaN", \
                REQDATE="NaN")

    def _to_csv(self):
        """Generate CSV from PRICETABLE.
        """
        ndc_list = []

        for k, v in self.PRICETABLE.items():
            output_str = '{}\t{}\t{}\t{}\t{}'.format(k, v.COST, v.CATEGORY, v.ITEMNUM, v.ON_FORMULARY, v.REQDATE)
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

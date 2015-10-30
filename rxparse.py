"""
# How to Automatically Update the EHHOP Formulary

## Goal: Compare existing EHHapp Formulary data against new invoices and update prices/costs when necessary.

EHHapp Formulary Template: This is how we display information about drugs in the EHHapp.

* CATEGORY
> ~DRUG_NAME | COST_pD (DOSE) | SUBCATEGORY

Invoice Template: This is how information is recorded in monthly invoices.

[Insert Headers Here]

The relevant data fields in the EHHapp Formulary are:

* CATEGORY - e.g. ANALGESICS
* SUBCATEGORY - e.g. Topical, i.e. "Route of administration"
* DRUG_NAME
* APPROVED - if the drug is blacklisted
* DOSE - dose information, if any
* COST_pD - cost per dose

### N.B. Some drugs have multiple DOSE and corresponding COST_pD values
"""

import re
import csv

def read_csv(filename):
    """Make csv files available as csv.reader objects.
    """

    with open(filename, 'rU') as f:
        iterablething = csv.reader(f)
        csvlines = []
        for item in iterablething:
            csvlines.append(item)
        return csvlines

# Define a pattern to match an Item Number in one of these lines

def filter_loe(loe, value="\d{5}", index=2):
    """Filter list of enumerables (lol) by value and index.

    A list comprehension is used to check each list at
    position specified by index for a full match with
    the regular expression pattern specified by value
    argument.

    value = "\d{5}" by default
    """

    filteredlist = [l for l in loe if re.fullmatch(value, l[index])]
    return filteredlist

"""
Create drug objects from EHHapp Markdown so names of drugs and prices can be compared
"""
def read_md(filename):
    """Make md files available as a list of strings (yes these are enumerable).
    """
    with open(filename, 'rU') as f:
        mdlines = f.readlines()
        return mdlines

def parse_mddata(lomd, delimiter="|"):
    """Parse a list of Markdown strings (lomd) to return list of lists (lol).
    """
    mdlol = [string.lstrip("> ").rstrip().split(delimiter) for string in lomd]

    mdlolclean = []
    for item in mdlol:
        item = [s.strip() for s in item]
        mdlolclean.append(item)

    return mdlolclean

class FormularyRecord:
    """Define a class that corresponds to a formulary entry.

    Each formulary entry has the following instance attributes:
    
    * DRUG_NAME
    * DOSE, COST_pD - dosage size and price per dose
    * CATEGORY - e.g. ANALGESICS
    * APPROVED - whether the drug is blacklisted or not
    * SUBCATEGORY - e.g. Topical, i.e. "Route of administration"
    """

    _BLACKLIST_ = '~'
    _DOSEPATT_ = '(\()(.+)(\))'
    _COSTPATT_ = '\$\d+[.0-9]?[0-9]?[0-9]?'
    _DOSECOSTPATT_ = re.compile(r"""
    (\$\d+[.0-9]?\d*-\$\d+[.0-9]?\d*
                |\$\d+[.0-9]?\d*)
            (?:\s)
            (?:\()
            ([^\n]*?)
            (?:\))""", re.X)

    def __init__(self, record):
        self.NAME = self._get_NAME(record)
        self.DOSECOST = self._get_DOSECOST(record)
        self.CATEGORY = None
        self.SUBCATEGORY = None
        self.BLACKLISTED = False

    def _get_NAME(self, record):
        """Sets the name attribute.

        Uses regex pattern to find the name.
        Sniffs for the _BLACKLIST_ and strips it - 
        and sets the BLACKLISTED attribute to true.
        """

        namestring = record[0]
        if namestring[0] == self._BLACKLIST_:
            self.BLACKLISTED = True
            name = namestring.lstrip(self._BLACKLIST_)
        else:
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

"""
Some functions convert Tabular data to EHHapp Markdown 
"""

class drug:
    """A data structure in which to store relevant output attributes
    """

    dosepattern1 = re.compile('(\d+MG)')

    def __init__(self, record):
        self.name = record[3]
        self.cost = record[15]
        self.category = record[8]
        self.dose = ""
        self.subcategory = ""
        self.itemnum = record[2]

    def dosefind(self):
        if self.dosepattern1.search(self.name):
            self.dose = self.dosepattern1.search(self.name).groups()[0]
            print("Match found")
        return self

def parse_classify(recordlist):
    """For each drug record, generate an instance of drug with relevant parameters
    """

    druglist = [drug(record).dosefind() for record in recordlist]
    return druglist

def classify_rmvdups(druglist):
    """Remove duplicates by generating a dictionary based on item number keys
    """
    nodup_drugdict = {drug.itemnum: drug for drug in druglist}
    return nodup_drugdict

"""
These functions control output to Markdown
"""
# Any dictionary with drug objects as values to Markdown
def to_Markdown(drugdict):
    output = []
    category = "Uncategorized"
    output.append("* {}".format(category))
    for itemnum, drug in drugdict.items():
        output.append("> {} | {} ({})| {}".format(drug.name, drug.cost, drug.dose, drug.subcategory))

    with open("invoice-extract.markdown", "w") as f:
        f.write('\n'.join(output))
"""
All of these functions should keep track of differences between new and old data
"""

"""
Janky debug functions
"""

def debug(datastructure):
    print(len(datastructure))

if __name__ == "__main__":
    import sys
    csvdata = read_csv(str(sys.argv[1]))
    print(len(csvdata))
    print(csvdata[0])
    recordlist = filter_loe(csvdata)
    print(len(recordlist))
    print(recordlist[0])
    mddata = read_md(str(sys.argv[2]))
    print(len(mddata))
    print(mddata[0])
    formularylist = filter_loe(mddata, value=">", index=0)
    print(len(formularylist))
    print(formularylist[0])
    formularyparsed = parse_mddata(formularylist)
    print(len(formularyparsed))
    print(formularyparsed[0])
    for record in formularyparsed:
        if FormularyRecord(record).DOSECOST == []:
            print(FormularyRecord(record).NAME)
    """
    print(dataread[0])
    recordlist = read_parse(dataread)
    print(recordlist[0])
    druglist = parse_classify(recordlist)
    print(druglist[0].name)
    debug(druglist)
    nddd = classify_rmvdups(druglist)
    debug(nddd)
    to_Markdown(nddd)
    """

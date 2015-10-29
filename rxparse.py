"""
# How to Automatically Update the EHHOP Formulary

## Goal: Automatically produce EHHapp-compatible HTML/Markdown from 
spreadsheets containing drug-level data on a monthly basis.

The relevant data fields we want to parse and make available for display are:

    * CATEGORY - e.g. ANALGESICS
    * SUBCATEGORY - e.g. Topical, i.e. "Route of administration"
    * DRUG_NAME
    * APPROVED - if the drug is blacklisted
    * DOSE
    * COST_pD
    * COST_pRx (NEW AS OF 2015)
    * Rx_COUNT (NEW AS OF 2015)

    ## EHHapp Formulary Template: This is how we display information about drugs in the EHHapp.

    * CATEGORY
    > ~DRUG_NAME | COST_pD (DOSE) | SUBCATEGORY

    ### N.B. Some drugs have multiple DOSE and corresponding COST_pD values
"""

import re

"""
Some functions convert EHHapp Markdown to Tabular data
"""

"""
Some functions convert Tabular data to EHHapp Markdown 
"""
# Read the data in as a list of lines
def data_read(tabulardata):
    with open(tabulardata, 'rU') as f:
        data_read = f.readlines()
        return data_read

# Define a pattern to match an Item Number in one of these lines
ItemNum = '\d{5}' 

# Use matching pattern to extract list of lines including only drug records
def read_parse(dataread):
    recordlist = [line.strip().split(',') for line in dataread if re.fullmatch(ItemNum, line.split(',')[2])]
    return recordlist

# Define a class drug in which to store relevant output attributes
class drug:
    dosepattern1 = re.compile("(\d+\.?\d+[%MG][ MGL][ ]?)")

    def __init__(self, record):
        self.name = record[3]
        self.cost = record[15]
        self.category = "Uncategorized"
        self.subcategory = ""
        self.dose = ""
        self.itemnum = record[2]

    def dosefind(self):
        if self.dosepattern1.match(self.name):
            self.dose = self.dosepattern1.match.groups()[0]
        return self

# For each drug record, generate an instance of drug with relevant parameters
def parse_classify(recordlist):
    druglist = [drug(record).dosefind() for record in recordlist]
    return druglist

def classify_rmvdups(druglist):
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
    dataread = data_read(str(sys.argv[1]))
    print(dataread[0])
    recordlist = read_parse(dataread)
    print(recordlist[0])
    druglist = parse_classify(recordlist)
    print(druglist[0].name)
    debug(druglist)
    nddd = classify_rmvdups(druglist)
    debug(nddd)
    to_Markdown(nddd)

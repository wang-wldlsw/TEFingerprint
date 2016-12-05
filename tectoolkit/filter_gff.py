#! /usr/bin/env python

import sys
import re
import argparse
import gffutils


class FilterGffProgram(object):
    """Main class for the filter_gff program"""
    def __init__(self, arguments):
        """
        Init method for :class:`FilterGffProgram`.

        :param arguments: A list of commandline arguments to be parsed for the filter_gff program
        """
        self.args = self.parse_args(arguments)

    def parse_args(self, args):
        """
        Defines an argument parser to handle commandline inputs for the filter_gff program.

        :param args: A list of commandline arguments for the filter_gff program

        :return: A dictionary like object of arguments and values for the filter_gff program
        """
        parser = argparse.ArgumentParser('Identify potential TE flanking regions')
        parser.add_argument('input_gff',
                            nargs=1,
                            help='A single gff file to be filtered')
        parser.add_argument('-f','--filters',
                            nargs='+',
                            help=("List of filters to apply.\n"
                                  "A valid filter takes the form '<attribute><operator><value>'"
                                  "where <attribute> is the name of a GFF attribute, "
                                  "<operator> is one of '=', '==', '!=', '>=', '<=', '>' or '<' "
                                  "and the value of the GFF attribute is compared to <value> using the operator\n"
                                  "The list of filters is applied additively (i.e. a feature must meet all filters) "
                                  "and, if a feature is selected, all of it's ancestors and descendants "
                                  "will also be included in the output.\n"
                                  "Operators '=', '==' and '!=' will attempt to compare values as floating point "
                                  "numbers if possible and otherwise compare values as strings. "
                                  "Operators '>=', '<=', '>' and '<' will coerce values "
                                  "to floating point numbers before comparison."))
        try:
            arguments = parser.parse_args(args)
        except:
            parser.print_help()
            sys.exit(0)
        else:
            return arguments

    def _parse_filter(self, string):
        """
        Parse a filter string to identify the attribute, operator and value

        :param string: A valid filter string in the form '<attribute><operator><value>'
        :type string: str

        :return: A dictionary with the keys 'attribute', 'operator' and 'value'
        :rtype: dict[str, str]
        """
        operator = re.findall(">=|<=|==|!=|>|<|=", string)
        if len(operator) > 1:
            raise ValueError('There is more than one operator in filter: "{0}"'.format(string))
        elif len(operator) < 1:
            raise ValueError('Could not find a valid operator in filter: "{0}"'.format(string))
        else:
            filt = {}
            operator = operator[0]
            filt['operator'] = operator
            filt['attribute'], filt['value'] = string.split(filt['operator'])
            return filt

    def run(self):
        """
        Run the filter_gff program with parameters specified in an instance of :class:`FilterGffProgram`.
        Imports the target gff file, subsets it by specified filters, and prints subset to stdout.
        """
        db = gffutils.create_db(self.args.input_gff[0],
                                dbfn=':memory:',
                                keep_order=True,
                                merge_strategy='merge',
                                sort_attribute_values=True)
        filters = [self._parse_filter(string) for string in self.args.filters]
        filter_by_attributes(db, filters)
        print('\n'.join([str(feature) for feature in db.all_features()]))


def descendants(feature, db):
    """
    Recursively find all descendants of a feature.

    :param feature: Feature to find descendants of
    :type feature: :class:`gffutils.feature.Feature`
    :param db: Feature database to search
    :type db: :class:`gffutils.interface.FeatureDB`

    :return: A generator of descendant features
    :rtype: generator[:class:`gffutils.feature.Feature`]
    """
    for child in db.children(feature):
        yield child
        descendants(child, db)


def ancestors(feature, db):
    """
    Recursively find all ancestors of a feature.

    :param feature: Feature to find ancestors of
    :type feature: :class:`gffutils.feature.Feature`
    :param db: Feature database to search
    :type db: :class:`gffutils.interface.FeatureDB`

    :return: A generator of ancestors features
    :rtype: generator[:class:`gffutils.feature.Feature`]
    """
    for child in db.parents(feature):
        yield child
        ancestors(child, db)


def matches_filter(feature, filt):
    """
    Ascertains whether a feature meets the requirements of a single filter.
    A filter is a dictionary with the keys 'attribute', 'operator' and 'value' and values are strings.
    The 'value' of 'attribute' will be compared against the value of the gff features attribute of the same name.
    The 'operator' determines the manor of comparison.
    Operators '=', '==' and '!=' will attempt to coerce values to floats before comparison and fall back to
    comparing values as strings.
    Operators '>=', '<=', '>' and '<' will coerce values to floats before comparison.

    :param feature: the feature to be tested
    :type feature: :class:`gffutils.feature.Feature`
    :param filt: A dictionary with the keys 'attribute', 'operator' and 'value'
    :type filt: dict[str, str]

    :return: Boolean value indicating whether the feature meets the filter criteria
    :rtype: bool
    """
    if filt['operator'] == '==' or filt['operator'] == '=':
        try:
            return float(feature.attributes[filt['attribute']][0]) == float(filt['value'])
        except ValueError:
            return feature.attributes[filt['attribute']][0] == filt['value']
    elif filt['operator'] == '!=':
        try:
            return float(feature.attributes[filt['attribute']][0]) != float(filt['value'])
        except ValueError:
            return feature.attributes[filt['attribute']][0] != filt['value']
    elif filt['operator'] == '==':
        return float(feature.attributes[filt['attribute']][0]) == float(filt['value'])
    elif filt['operator'] == '>=':
        return float(feature.attributes[filt['attribute']][0]) >= float(filt['value'])
    elif filt['operator'] == '<=':
        return float(feature.attributes[filt['attribute']][0]) <= float(filt['value'])
    elif filt['operator'] == '>':
        return float(feature.attributes[filt['attribute']][0]) > float(filt['value'])
    elif filt['operator'] == '<':
        return float(feature.attributes[filt['attribute']][0]) < float(filt['value'])


def matches_filters(feature, filters):
    """
    Ascertains whether a feature meets the requirements of each of a list of filters.

    :param feature: the feature to be tested
    :type feature: :class:`gffutils.feature.Feature`
    :param filters: A list of dictionaries with the keys 'attribute', 'operator' and 'value'
    :type filters: list[dict[str, str]]

    :return: Boolean value indicating whether the feature meets all of the filter criteria
    :rtype: bool
    """
    if {filt['attribute'] for filt in filters}.issubset(feature.attributes.keys()):
        return all([matches_filter(feature, filt) for filt in filters])
    else:
        return False


def relative_matches_filters(feature, filters, db):
    """
    Ascertains whether a feature or any of its relatives meets the requirements of each of a list of filters.

    :param feature: the feature to have itself and all ancestors and descendants tested
    :type feature: :class:`gffutils.feature.Feature`
    :param filters: A list of dictionaries with the keys 'attribute', 'operator' and 'value'
    :type filters: list[dict[str, str]]
    :param db: Feature database
    :type db: :class:`gffutils.interface.FeatureDB`

    :return: Boolean value indicating whether the feature or any relative meets all of the filter criteria
    :rtype: bool
    """
    return any([matches_filters(feature, filters),
                any([matches_filters(f, filters) for f in descendants(feature, db)]),
                any([matches_filters(f, filters) for f in ancestors(feature, db)])])


def filter_by_attributes(db, filters):
    """
    For every feature in the database of :class:`GffFilterDB`, checks if the feature or any of its relatives meets
    the requirements of each of a list of filters. If not, the feature is dropped from the database.

    :param db: Feature database
    :type db: :class:`gffutils.interface.FeatureDB`
    :param filters: A list of dictionaries with the keys 'attribute', 'operator' and 'value'
    :type filters: list[dict[str, str]]
    """
    for feature in db.all_features():
        if relative_matches_filters(feature, filters, db):
            pass
        else:
            db.delete(feature)

if __name__ == '__main__':
    pass

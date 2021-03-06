#! /usr/bin/env python3


import re
import fnmatch
from tefingerprint.util.gff3 import *


COLUMN_NAMES = ["seqid",
                "source",
                "type",
                "start",
                "end",
                "score",
                "strand",
                "phase",
                "attributes"]


def parse_feature(string):
    """
    Parses a feature (line) of a gff3 file.

    Feature is returned as a dictionary of columns and attributes.

    :param string: single line from a gff file
    :type string: str

    :return: dictionary of key value pairs
    :rtype: dict[str, str]
    """
    columns = dict(zip(COLUMN_NAMES,
                       string.strip('\n').split()))
    attributes = columns["attributes"].split(';')
    attributes = {k: v for k, v in (attribute.split('=')
                                    for attribute in attributes)}
    del columns["attributes"]

    columns = {k: decode_column(v)
               for k, v in columns.items()}
    attributes = {decode_attribute(k): decode_attribute(v)
                  for k, v in attributes.items()}

    dictionary = attributes
    dictionary.update(columns)
    return dictionary


def format_feature(dictionary):
    """
    Format a dictionary of feature data to line of a gff file.

    Dictionary must have the following keys: "seqid", "source",
    "type", "start", "end", "score", "strand" and "phase".
    All other keys are treated as attribute fields.

    :param dictionary: dictionary of key value pairs
    :type dictionary: dict[str, str]

    :return: single line for a gff file
    :rtype: str
    """
    column_values = (encode_column(str(dictionary[field]))
                     for field in COLUMN_NAMES[0:8])
    columns = '{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\t'
    columns = columns.format(*column_values)

    attribute_names = [field for field in dictionary.keys()
                       if field not in COLUMN_NAMES]
    attribute_names.sort()
    attributes_pairs = ((encode_attribute(str(field)),
                         encode_attribute(str(dictionary[field])))
                        for field in attribute_names)

    attributes = ':'.join('{}={}'.format(field, value)
                          for field, value in attributes_pairs)

    return columns + attributes


def _eq(x, y):
    """
    Tests a pair of strings for equivalence by attempting to convert
    them to floats and falling back to string comparison.

    :param x: string
    :type x: str
    :param y: string
    :type y: str

    :return: boolean
    :rtype: bool
    """
    try:
        return float(x) == float(y)
    except ValueError:
        return x == y


def _neq(x, y):
    """
    Tests a pair of strings for non-equivalence by attempting to convert
    them to floats and falling back to string comparison.

    :param x: string
    :type x: str
    :param y: string
    :type y: str

    :return: boolean
    :rtype: bool
    """
    try:
        return float(x) != float(y)
    except ValueError:
        return x != y


# Function dispatch based on operator passed as string
_OPERATOR_DISPATCH = {'==': _eq,
                      '=': _eq,
                      '!=': _neq,
                      '>=': lambda x, y: float(x) >= float(y),
                      '>': lambda x, y: float(x) > float(y),
                      '<=': lambda x, y: float(x) <= float(y),
                      '<': lambda x, y: float(x) < float(y)}


def parse_filter_string(string):
    """
    Parse a filter string into a 'field' 'operator' and 'value'

    :param string: stirng with format "<field><operator><value>"
    :type string: str

    :return: dictionary with fields 'field' 'operator' and 'value'
    :rtype: dict[str, str]
    """
    operator = re.findall(">=|<=|==|!=|>|<|=", string)
    if len(operator) > 1:
        message = 'There is more than one operator in filter: "{0}"'
        raise ValueError(message.format(string))
    elif len(operator) < 1:
        message = 'Could not find a valid operator in filter: "{0}"'
        raise ValueError(message.format(string))
    else:
        operator = operator[0]
        field, value = string.split(operator)
        field = field.strip()
        value = value.strip()
        return {'field': field, 'operator': operator, 'value': value}


def apply_filter(feature, filter_, combinator):
    """
    Apply a single (parsed) filter to (parsed) feature.

    If the filter field contains a wildcard (e.g. '?' or '*') then
    the filter is applied to each feature-field matching the expanded
    filter-field and the results are combined based on the combinator
    ("ANY" or "ALL").


    :param feature: key-value pairs for a gff feature
    :type feature: dict[str, str]
    :param filter_: key-value pairs for a gff feature
    :type filter_: dict[str, str]
    :param combinator: "ANY" or "ALL"
    :type combinator: str

    :return: boolean indicating if the feature matches the filter.
    :rtype: bool
    """
    fields = fnmatch.filter(list(feature.keys()), filter_['field'])
    results = [_OPERATOR_DISPATCH[filter_['operator']](feature[field],
                                                       filter_['value'])
               for field in fields]
    if results == []:
        return False  # if there are no fields to match
    elif combinator == 'ANY':
        return any(results)
    elif combinator == 'ALL':
        return all(results)
    else:
        assert False


def apply_filters(feature, filters, combinator):
    """
    Apply a multiple (parsed) filters to (parsed) feature.

    Filters are combined with 'any' or 'all' depending on the combinator.

    :param feature: key-value pairs for a gff feature
    :type feature: dict[str, str]
    :param filters: iterable of dictionaries of a gff features
    :type filters: list[dict[str, str]]
    :param combinator: "ANY" or "ALL"
    :type combinator: str

    :return: boolean indicating if the feature matches the combined filters.
    :rtype: bool
    """
    results = [apply_filter(feature, filt, combinator) for filt in filters]
    if combinator == 'ANY':
        return any(results)
    elif combinator == 'ALL':
        return all(results)
    else:
        assert False

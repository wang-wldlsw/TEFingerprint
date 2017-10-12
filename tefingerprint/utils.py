#! /usr/bin/env python

import numpy as np


def flatten_numpy_element(item):
    """
    Flatten a nested numpy element.

    :param item: a numpy element
    :type item: np.void[any] | any

    :return: A generator
    :rtype: generator[any]
    """
    if isinstance(item, np.void) or isinstance(item, tuple):
        for element in item:
            for item in flatten_numpy_element(element):
                yield item
    else:
        yield item


def flatten_dtype(dtype):
    def flatten_descr(item, prefix=''):
        if isinstance(item, tuple):
            if isinstance(item[1], list):
                prefix += str(item[0]) + '_'
                for item in flatten_descr(item[1], prefix=prefix):
                    yield item
            else:
                yield (prefix + item[0], item[1])
        elif isinstance(item, list):
            for element in item:
                for item in flatten_descr(element, prefix=prefix):
                    yield item
        else:
            pass

    return np.dtype(list(flatten_descr(dtype.descr)))


def flatten_dtype_fields(dtype, prefix=''):

    def flatten_descr_names(item, prefix=''):
        if isinstance(item, list):
            for element in item:
                for item in flatten_descr_names(element, prefix=prefix):
                    yield item
        if isinstance(item, tuple):
            yield prefix + item[0]
            prefix += str(item[0]) + '_'
            for item in flatten_descr_names(item[1], prefix=prefix):
                yield item
        else:
            pass

    return flatten_descr_names(dtype.descr, prefix=prefix)


def quote_str(value):
    if isinstance(value, str):
        return '"{0}"'.format(value)
    else:
        return str(value)
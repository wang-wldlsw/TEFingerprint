#! /usr/bin/env python

import numpy as np
from tectoolkit.cluster import _UnivariateLoci


class ReadGroup(object):
    """"""
    read = np.dtype([('tip', np.int64),
                     ('tail', np.int64),
                     ('strand', np.str_, 1),
                     ('name', np.str_, 254)])

    def __init__(self, reads):
        self.reads = reads

    def __iter__(self):
        for read in self.reads:
            yield read

    def __getitem__(self, item):
        return self.reads[item]

    def __len__(self):
        return len(self.reads)

    def sort(self, order='tip'):
        """

        :param order:
        :return:
        """
        self.reads.sort(order=order)

    def strand(self):
        """

        :return:
        """
        variation = set(self.reads['strand'])
        if len(variation) > 1:
            return '.'
        else:
            return variation.pop()

    def sub_group_by_locus(self, start, stop, margin=0, end='tip'):
        """

        :param start:
        :param stop:
        :param margin:
        :param end:
        :return:
        """
        assert end in {'tip', 'tail'}
        start -= margin
        stop += margin
        reads = self.reads[np.logical_and(self.reads[end] >= start, self.reads[end] <= stop)]
        return ReadGroup(reads)

    @classmethod
    def _parse_sam_flag(cls, flag):
        """

        :param flag:
        :return:
        """
        attributes = np.zeros(12, dtype=np.bool)
        bits = np.fromiter(map(int, tuple(bin(int(flag)))[:1:-1]), dtype=np.bool)
        attributes[:bits.shape[0]] = bits
        return attributes

    @classmethod
    def _flag_orientation(cls, flag):
        """

        :param flag:
        :return:
        """
        attributes = cls._parse_sam_flag(flag)
        if attributes[2]:  # read is unmapped
            return None
        elif attributes[4]:  # read is reversed
            return '-'
        else:  # read is forwards
            return '+'

    @classmethod
    def _flag_attributes(cls, flag):
        attributes = ("read paired",
                      "read mapped in proper pair",
                      "read unmapped mate unmapped",
                      "read reverse strand",
                      "mate reverse strand",
                      "first in pair",
                      "second in pair",
                      "not primary alignment",
                      "read fails platform / vendor quality checks",
                      "read is PCR or optical duplicate",
                      "supplementary alignment")
        values = cls._parse_sam_flag(flag)
        return dict(zip(attributes, values))

    @classmethod
    def _parse_sam_strings(cls, strings, single_strand=None):
        """

        :param strings:
        :param single_strand:
        :return:
        """

        def _parse_sam_string(string, strand):
            """

            :param string:
            :param strand:
            :return:
            """
            attr = string.split("\t")
            name = str(attr[0])
            start = int(attr[3])
            length = len(attr[9])
            end = start + length
            if strand is None:
                strand = cls._flag_orientation(int(attr[1]))
            if strand == '+':
                tip = end
                tail = start
                return tip, tail, strand, name
            elif strand == '-':
                tip = start
                tail = end
                return tip, tail, strand, name
            elif strand is None:
                pass

        assert single_strand in ['+', '-', None]
        reads = (_parse_sam_string(string, single_strand) for string in strings)
        return reads

    @classmethod
    def from_sam_strings(cls, strings, strand=None):
        """

        :param strings:
        :param strand:
        :return:
        """
        reads = cls._parse_sam_strings(strings, single_strand=strand)
        reads = np.fromiter(reads, dtype=ReadGroup.read)
        reads.sort(order=('tip', 'tail'))
        return ReadGroup(reads)


class ReadLoci(_UnivariateLoci):
    """"""
    def __init__(self, loci):
        """"""
        self.loci = loci

    def __iter__(self):
        """"""
        for locus in self.loci:
            yield locus

    def __getitem__(self, item):
        """"""
        return self.loci[item]

    def __len__(self):
        """"""
        return len(self.loci)

    def sort(self, order=('start', 'stop')):
        """

        :param order:
        :return:
        """
        self.loci.sort(order=order)

    def melt(self):
        """

        :return:
        """

        self.sort()
        self.loci = self._melt_uloci(self.loci)

    @classmethod
    def from_iterable(cls, iterable):
        """

        :param iterable:
        :return:
        """
        loci = ReadLoci(np.fromiter(iterable, dtype=ReadLoci._ulocus))
        loci.sort()
        return loci

    @classmethod
    def append(cls, x, y):
        """

        :param x:
        :param y:
        :return:
        """
        loci = ReadLoci(np.append(x.loci, y.loci))
        loci.sort()
        return loci


class GffFeature(object):
    """"""
    def __init__(self,
                 seqid,
                 source='.',
                 ftype='.',
                 start='.',
                 end='.',
                 score='.',
                 strand='.',
                 phase='.',
                 **kwargs):
        self.seqid = seqid
        self.source = source
        self.type = ftype
        self.start = start
        self.end = end
        self.score = score
        self.strand = strand
        self.phase = phase
        self.attributes = kwargs

    def attribute_names(self):
        return set(self.attributes.keys())

    def _parse_attributes(self, attributes):
        if attributes is not None:
            return ';'.join(tuple('{0}={1}'.format(key, value) for key, value in self.attributes.items()))
        else:
            return'.'

    def __str__(self):
        template = "{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\t{8}"
        return template.format(self.seqid,
                               self.source,
                               self.type,
                               self.start,
                               self.end,
                               self.score,
                               self.strand,
                               self.phase,
                               self._parse_attributes(self.attributes))

if __name__ == '__main__':
    pass

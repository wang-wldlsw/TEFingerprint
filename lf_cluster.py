#!/usr/bin/env python

import sys
import numpy as np
import pysam
import argparse
from readcluster import ReadCluster
from sklearn.cluster import DBSCAN


def parse_args(args):
    parser = argparse.ArgumentParser('Identify transposon flanking regions')
    parser.add_argument('input_bam', nargs='?', type=argparse.FileType('r'),
                        default=False)
    parser.add_argument('--reference', nargs='?', default=False)
    parser.add_argument('--strand', nargs='?', default=False)
    parser.add_argument('--read_group', nargs='?', default=False)
    parser.add_argument('--eps', type=int, default=100,
                        help=("When using the DBSCAN method to identify "
                              "read clusters, eps is the minimum distance "
                              "allowable between two points for inclusion "
                              "in the the same neighbourhood"))
    parser.add_argument('--min_tips', type=int, default=5,
                        help=("When using the DBSCAN method to identify "
                              "read clusters, min_tips is the minimum number "
                              "of read tips found in a single neighbourhood "
                              "in order to count as a cluster"))
    return parser.parse_args(args)


def split_references(sam, args):
    """
    Splitting references requires index and will not work from stdin
    """
    if args.input_bam:
        if sam.nreferences == 1:
            yield sam
        else:
            for name in sam.references:
                yield sam.fetch(name)
    else:
        if args.reference:
            yield sam
        else:
            pass  # Should throw error


def tip(read):
    if read.is_reverse:
        return read.pos
    else:
        return read.pos + read.qlen


def tips(sam):
    for read in sam:
        yield tip(read)


def udbscan(points, args):
    points2d = np.column_stack([points, np.zeros(len(points))])
    dbscan = DBSCAN(eps=args.eps, min_samples=args.min_tips).fit(points2d)
    labels = dbscan.labels_.astype(np.int)
    return labels


def read_clusters(sam, args):
    sam_tips = np.fromiter(tips(sam), np.int)
    cluster_labels = udbscan(sam_tips, args)
    for label in np.unique(cluster_labels)[1:]:
        cluster_tips = sam_tips[np.where(cluster_labels == label)]
        read_cluster = ReadCluster(args.reference,
                                   args.read_group,
                                   args.strand,
                                   cluster_tips)
        yield read_cluster


def main():
    args = parse_args(sys.argv[1:])
    if args.input_bam:
        sam = pysam.AlignmentFile(args.input_bam, 'rb')
    else:
        sam = pysam.AlignmentFile("-", "rb")
    sams = split_references(sam, args)
    for sam in sams:
        for cluster in read_clusters(sam, args):
            print(str(cluster))


if __name__ == '__main__':
    main()

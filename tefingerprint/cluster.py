#! /usr/bin/env python

import numpy as np


class UDC(object):
    """
    Univariate Density Cluster analysis: Create a model to calculate density clusters for a univariate array.

    Clusters are identified as suitably dense, continuous regions in the data where the threshold density
    is specified by parameters n (minimum points) and eps (epsilon).
    The range in values among every set of n points in the array is calculated and compared to epsilon.
    Sets of n points with a range equal to, or less than epsilon are classified as subclusters.
    Overlapping subclusters are then merged together to form clusters.
    Points in the array that do not fall inside a cluster are regarded as noise.

    :param n: The minimum number of points allowed in each (sub)cluster
    :type n: int
    :param eps: The maximum distance allowed among each set of n points
    :type eps: int
    """

    _DTYPE_SLICE = np.dtype([('lower', np.int64), ('upper', np.int64)])

    def __init__(self, n, eps):
        self.n = n
        self.eps = eps
        self.slices = np.array([], dtype=UDC._DTYPE_SLICE)
        self.input_array = np.array([], dtype=int)

    @staticmethod
    def _sorted_ascending(array):
        """
        Checks if an array is sorted in ascending order.

        :param array: a 1 dimensional array of numeric values
        :type array: :class:`numpy.ndarray`[int]

        :return: True if array is sorted in ascending order
        :rtype: bool
        """
        return np.sum(array[1:] - array[:-1] < 0) == 0

    @staticmethod
    def _melt_slices(slices):
        """
        Combines overlapping slices assuming half-open intervals.

        :param slices: An array of paired integers representing the lower and upper values of a slice
        :type slices: :class:`numpy.ndarray`[(int, int)]

        :return: An array of paired integers representing the lower and upper values of a slice
        :rtype: :class:`numpy.ndarray`[(int, int)]
        """
        lowers, uppers = slices['lower'], slices['upper']
        lowers.sort()
        uppers.sort()
        splits = np.append(np.array([False]), uppers[:-1] <= lowers[1:])  # True means gap between

        def _melter(lowers, uppers, splits):
            l = lowers[0]
            u = uppers[0]
            for i in range(1, len(lowers)):
                if splits[i]:
                    # there is a gap so yield slice and start new one
                    yield l, u
                    l, u = slices['lower'][i], slices['upper'][i]
                else:
                    # no gap so merge slices
                    u = uppers[i]
            # yield final slice
            yield l, u

        # return slices formatted as a numpy array
        return np.fromiter(_melter(lowers, uppers, splits), dtype=UDC._DTYPE_SLICE)


    @staticmethod
    def _subcluster(array, eps, n):
        """
        Calculate subclusters of an array and return their slice indices.
        The input array must be sorted in ascending order.
        If n is greater than the length of the array, an empty array is returned.

        :param array: An array of ints sorted in ascending order
        :param eps: The number of points in each subcluster
        :param n: The maximum distance allowed in among points of each subcluster

        :return: An array of paired lower and upper indices for each subcluster found in the array
        :rtype: :class:`numpy.ndarray`[(int, int)]
        """
        assert UDC._sorted_ascending(array)
        offset = n - 1
        upper = array[offset:]
        lower = array[:-offset]
        selected = upper - lower <= eps
        lower_index = np.arange(0, len(lower))[selected]
        upper_index = np.arange(offset, len(array))[selected] + 1
        return np.fromiter(zip(lower_index, upper_index), dtype=UDC._DTYPE_SLICE)

    @staticmethod
    def _cluster(array, eps, n):
        """
        Calculate clusters of an array and return their slice indices.
        The input array must be sorted in ascending order.
        If n is greater than the length of the array, an empty array is returned.

        :param array: An array of ints sorted in ascending order
        :param eps: The minimum number of points in each (sub)cluster
        :param n: The maximum distance allowed in among each set of n points

        :return: An array of paired lower and upper indices for each cluster found in the array
        :rtype: :class:`numpy.ndarray`[(int, int)]
        """
        # sorted-ascending checked in method _subcluster
        slices = UDC._subcluster(array, eps, n)
        if len(slices) > 1:
            slices = UDC._melt_slices(slices)
        return slices

    @staticmethod
    def udc(array, n, eps):
        """
        Calculate Density Clusters for a Univariate Array.

        Clusters are identified as suitably dense, continuous regions in the data where the threshold density
        is specified by parameters n (minimum points) and eps (epsilon).
        The range in values among every set of n points in the array is calculated and compared to epsilon.
        Sets of n points with a range equal to, or less than epsilon are classified as subclusters.
        Overlapping subclusters are then merged together to form clusters.
        Points in the array that do not fall inside a cluster are regarded as noise.

        The input array must be sorted in ascending order.
        This method returns pairs of indices representing the (half open) upper and lower bounds of each cluster.

        :param array: An array of ints sorted in ascending order
        :type array: :class:`numpy.ndarray`[int]
        :param n: The minimum number of points in each (sub)cluster
        :type n: int
        :param eps: The maximum distance allowed in among each set of n points
        :type eps: int

        :return: An array of paired lower and upper indices for each cluster found in the array
        :rtype: :class:`numpy.ndarray`[int, int]
        """
        assert UDC._sorted_ascending(array)
        slices = UDC._cluster(array, eps, n)
        return slices

    def fit(self, array):
        """
        Fit an array to a Univariate Density Cluster model.
        The input array must be sorted in ascending order.

        :param array: An array of integers sorted in ascending order
        :type array: :class:`numpy.ndarray`[int]
        """
        self.input_array = np.array(array, copy=True)
        self.slices = UDC.udc(self.input_array, self.n, self.eps)

    def clusters(self):
        """
        Return values from the input array grouped into clusters.
        Points classified as noise are not returned.

        :return: A generator object of subset of the input array
        :rtype: generator[:class:`numpy.ndarray`[int]]
        """
        return (self.input_array[lower:upper] for lower, upper in self.slices)

    def cluster_extremities(self):
        """
        Return minimum and maximum values from the input array found in each cluster.

        :return: A generator object of pairs of lower and upper values found in each cluster
        :rtype: generator[(int, int)]
        """
        return ((self.input_array[lower], self.input_array[upper - 1]) for lower, upper in self.slices)

    def labels(self):
        """
        Return cluster labels for all input values.
        Clusters are labeled in ascending order starting from 0
        Points classified as noise are labeled as -1

        :return: An array of integer labels
        :rtype: :class:`numpy.ndarray`[int]
        """
        labels = np.full(len(self.input_array), -1, int)
        for i, (lower, upper) in enumerate(self.slices):
            labels[lower:upper] += (i + 1)
        return labels


class HUDC(UDC):
    """
    Hierarchical Univariate Density Cluster analysis: A model to calculate density clusters for a univariate array.

    Clusters are identified as suitably dense, continuous regions in the data where the threshold density
    is specified by parameters n (minimum points) and eps (epsilon).
    The range in values among every set of n points in the array is calculated and compared to epsilon.
    Sets of n points with a range equal to, or less than epsilon are classified as subclusters.
    Overlapping subclusters are then merged together to form clusters.
    Points in the array that do not fall inside a cluster are regarded as noise.

    The HUDC algorithm identifies values of epsilon lower than the initial value, at which previously identified
    clusters are separated into smaller 'child' clusters. At each of these splits the 'area' of each parent cluster
    is compared to the combined 'area' of it's descendant clusters where a clusters 'area' is the sum total of data
    points found within that cluster at each value of epsilon for which that cluster persists (i.e. is not split).
    If the area of the parent is larger than that of its combined descendants, then it is selected. If the area of
    combined descendants is larger than the parents area, the algorithm is re-run for each of the immediate
    child clusters. This process continues until a parent cluster is selected or a terminal cluster (a cluster with
    no children) is reached and automatically selected.

    :param n: The minimum number of points allowed in each (sub)cluster
    :type n: int
    :param max_eps: An optional value for maximum distance allowed among each set of n points
    :type max_eps: int
    :param min_eps: An optional value for the minimum value of eps to be used when calculating cluster depth
    :type min_eps: int
    """

    def __init__(self, n, max_eps=None, min_eps=None):
        self.min_pts = n
        self.max_eps = max_eps
        self.min_eps = min_eps
        self.slices = np.array([], dtype=UDC._DTYPE_SLICE)
        self.input_array = np.array([], dtype=int)

    @staticmethod
    def _core_distances(array, min_points):
        """
        Identify the core distance (minimum value of eps) for every point in an array of integers.
        For each point, the minimum eps is calculated among all subclusters containing that point.

        :param array: An array of integers sorted in ascending order
        :type array: :class:`numpy.ndarray`[int]
        :param min_points: number of points used to form a subcluster
        :type n: int

        :return: An array of minimum eps values
        :rtype: :class:`numpy.ndarray`[int]
        """
        assert min_points > 1  # groups must contain at least two points
        offset = min_points - 1  # offset for indexing because the minimum points includes itself
        length = len(array)
        lower = array[0:length - offset]
        upper = array[offset:length]
        eps_values = upper - lower
        eps_2d = np.full((min_points, length), np.max(eps_values), dtype=int)
        for i in range(min_points):
            eps_2d[i, i:length - (offset - i)] = eps_values
        return np.min(eps_2d, axis=0)

    @staticmethod
    def _cluster_forks(array, min_points):
        """
        Identify eps 'splits' in an array by calculating epsilon of the gaps between values in the array.
        This is

        Eps between values must be calculated as eps of the values either side of a gap may be significantly lower.
        For example when clustering the array of vales:
            [0, 0, 3, 4, 4, 6, 26, 28, 28, 29, 32, 32]
        with n = 3 (subclusters of 3 points). The eps calculated for values 6 and 26 is 2 and 2 respectively.
        However the minimum eps value calculated for subclusters that include both values is 21. Therefore, the eps
        split is 'hidden' if eps is only calculated on a per point basis.

        Once eps is calculated for all gaps between values in an array, peaks are identified and classified as 'splits'.
        Splits are points at which a parent clusters are split into child clusters.

        Eps of splits is reduced by a constant of 1 in order to be used as a threshold value. This is because an eps
        value of 21 implies that at eps = 21 a valid subcluster is formed. Therefore eps = 20 is the value at which
        a subcluster cannot be formed ad there is a split.

        :param array: An array of integers sorted in ascending order
        :type array: :class:`numpy.ndarray`[int]
        :param min_points: number of points used to form a subcluster
        :type n: int

        :return: An epsilon value or None
        :rtype: int
        """
        if len(array) <= min_points:
            # no forks possible because all points must have the same eps
            return None

        offset = min_points - 1

        # calculate split eps using the 2d method
        eps_values = array[offset:] - array[:-offset]
        eps_2d = np.full((offset, len(eps_values) + offset - 1), np.max(eps_values), dtype=int)
        for i in range(offset):
            eps_2d[i, i:len(eps_values) + i] = eps_values
        splits = np.min(eps_2d, axis=0)

        # Remove plateaus
        gradients = splits[1:] - splits[:-1]
        splits = splits[np.append(np.array([True]), gradients != 0)]

        # Remove non-peaks
        is_peak = np.logical_and(np.append(np.array([False]), splits[1:] > splits[:-1]),
                                 np.append(splits[:-1] > splits[1:], np.array([False])))
        splits = splits[is_peak]

        # If this method calculates epsilon of 5 it means the child cluster starts at epsilon 4.999...
        if len(splits) == 0:
            # The cluster does not fork into child clusters at all
            return None
        else:
            # We only require the largest fork value
            return np.max(splits)

    @staticmethod
    def _flatten_list(item):
        """
        Flatten a nested list.
        If item is not a list it will be returned inside a list of length one

        :param item: a list or any other object
        :type item: list[any] | any

        :return: A flat list
        :rtype: list[any]
        """
        if isinstance(item, list):
            for element in item:
                for item in HUDC._flatten_list(element):
                    yield item
        else:
            yield item

    @staticmethod
    def _traverse_hudc_tree(points, epsilon_maximum, min_points):
        """
        Traverse a tree of nested density clusters and recursively identify clusters based on their area.
        This method is intimately tied to method 'hudc'.

        :param points: An array of points with the slots 'value', 'index' and 'eps
        :type points: :class:`numpy.ndarray`[(int, int, int)]
        :param epsilon_maximum: Maximum distance allowed in among each set of n points
        :type epsilon_maximum: int
        :param min_points: The minimum number of points allowed in each (sub)cluster
        :type min_points: int

        :return: A nested list of upper and (half-open) indices of selected clusters
        :rtype: list[list[]]
        """
        # Values of epsilon bellow which the cluster forks
        fork_epsilon = HUDC._cluster_forks(points['value'], min_points)

        if fork_epsilon is None:
            # The cluster doesn't fork so it has no children
            # Epsilon_minimum would equal the minimum of core distances but it's not neededE
            return points['index'][0], points['index'][-1] + 1

        # If a cluster forks into children then it's minimum epsilon is the value at which forks
        epsilon_minimum = fork_epsilon

        # Compare support for cluster and its children
        support = np.sum(epsilon_maximum - np.maximum(epsilon_minimum, points['core_dist']))
        support_children = np.sum(np.maximum(0, epsilon_minimum - points['core_dist']))

        if support > support_children:
            # Parent is supported so return slice indices
            return points['index'][0], points['index'][-1] + 1

        else:
            # Combined support of children is larger so divide and repeat recursively:
            # A minimum epsilon of 5 means the child clusters technically starts at epsilon 4.999...
            # we calculate the child clusters using epsilon 4 which will produce the same clusters as 4.999...
            child_cluster_bounds = HUDC._cluster(points['value'], epsilon_minimum - 1,  min_points)
            child_points = (points[left:right] for left, right in child_cluster_bounds)
            # but then use epsilon 5 as the new maximum epsilon so that support is calculated from epsilon 4.999...
            return [HUDC._traverse_hudc_tree(points, epsilon_minimum, min_points) for points in child_points]

    @staticmethod
    def hudc(array, min_points, max_eps=None, min_eps=None):
        """
        Calculate Hierarchical Density Clusters for a Univariate Array.

        Clusters are identified as suitably dense, continuous regions in the data where the threshold density
        is specified by parameters n (minimum points) and eps (epsilon).
        The range in values among every set of n points in the array is calculated and compared to epsilon.
        Sets of n points with a range equal to, or less than epsilon are classified as subclusters.
        Overlapping subclusters are then merged together to form clusters.
        Points in the array that do not fall inside a cluster are regarded as noise.

        The HUDC algorithm identifies values of epsilon lower than the initial value, at which previously identified
        clusters are separated into smaller 'child' clusters. At each of these splits the 'area' of each parent cluster
        is compared to the combined 'area' of it's descendant clusters where a clusters 'area' is the sum total of data
        points found within that cluster at each value of epsilon for which that cluster persists (i.e. is not split).
        If the area of the parent is larger than that of its combined descendants, then it is selected. If the area of
        combined descendants is larger than the parents area, the algorithm is re-run for each of the immediate
        child clusters. This process continues until a parent cluster is selected or a terminal cluster (a cluster with
        no children) is reached and automatically selected.

        The HUDC algorithm is primarily based on HDBSCAN, see: https://hdbscan.readthedocs.io/en/latest/index.html

        The input array must be sorted in ascending order.
        This method returns pairs of indices representing the (half open) upper and lower bounds of each cluster

        :param array: An array of ints sorted in ascending order
        :type array: :class:`numpy.ndarray`[int]
        :param min_points: The minimum number of points allowed in each (sub)cluster
        :type min_points: int
        :param max_eps: An optional value for maximum distance allowed among each set of n points
        :type max_eps: int
        :param min_eps: An optional value for the minimum value of eps to be used when calculating cluster depth
        :type min_eps: int

        :return: An array of paired lower and upper indices for each cluster found in the array
        :rtype: :class:`numpy.ndarray`[(int, int)]
        """
        assert HUDC._sorted_ascending(array)

        if len(array) < min_points:
            # not enough points to form a cluster
            return np.array([], dtype=UDC._DTYPE_SLICE)

        else:
            # create a structured array for tracking value, index and core distance of each individual
            points = np.empty(len(array), dtype=np.dtype([('value', np.int64),
                                                          ('index', np.int64),
                                                          ('core_dist', np.int64)]))
            points['value'] = array
            points['index'] = np.arange(len(array), dtype=int)
            points['core_dist'] = HUDC._core_distances(array, min_points)
            if not max_eps:
                # start at highest observed eps
                max_eps = np.max(points['core_dist'])
            if min_eps:
                # overwrite lower eps
                points['core_dist'][points['core_dist'] < min_eps] = min_eps

            # initial splits based on the specified maximum epsilon
            child_points = (points[left:right] for left, right in HUDC._cluster(points['value'], max_eps, min_points))

            # recursively run on all clusters
            clusters = [HUDC._traverse_hudc_tree(points, max_eps, min_points) for points in child_points]
            return np.fromiter(HUDC._flatten_list(clusters), dtype=UDC._DTYPE_SLICE)

    def fit(self, array):
        """
        Fit an array to a Hierarchical Univariate Density Cluster model.
        The input array must be sorted in ascending order.

        :param array: An array of integers sorted in ascending order
        :type array: :class:`numpy.ndarray`[int]
        """
        self.input_array = np.array(array, copy=True)
        self.slices = HUDC.hudc(self.input_array, self.min_pts, max_eps=self.max_eps, min_eps=self.min_eps)


if __name__ == '__main__':
    pass

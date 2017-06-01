# -*- coding: utf-8 -*-
#
# Author: Taylor Smith <taylor.smith@alkaline-ml.com>
#
# R approx function

from __future__ import absolute_import
from sklearn.utils.validation import check_array, column_or_1d
import numpy as np

from ..utils.array import c
from ..utils import get_callable

# since the C import relies on the C code having been built with Cython,
# and since pyramid never plans to use setuptools for the 'develop' option,
# make this an absolute import.
from pyramid.arima._arima import C_Approx

__all__ = [
    'approx'
]

# the ints get passed to C code
VALID_APPROX = {
    'constant': 2,
    'linear': 1
}

# get the valid tie funcs
VALID_TIES = {
    'ordered': None,  # never really used...
    'mean': np.average
}


def _regularize(x, y, ties):
    """Regularize the values, make them ordered and remove duplicates.
    If the ``ties`` parameter is explicitly set to 'ordered' then order
    is already assumed. Otherwise, the removal process will happen.

    Parameters
    ----------
    x : array-like, shape=(n_samples,)
        The x vector.

    y : array-like, shape=(n_samples,)
        The y vector.

    ties : str
        One of {'ordered', 'mean'}, handles the ties.
    """
    x, y = [
        column_or_1d(check_array(arr, ensure_2d=False,
                                 force_all_finite=False,
                                 dtype=np.float64))
        for arr in (x, y)
    ]

    nx = x.shape[0]
    if nx != y.shape[0]:
        raise ValueError('array dim mismatch: %i != %i' % (nx, y.shape[0]))

    # manipulate x if needed. if ties is 'ordered' we assume that x is
    # already ordered and everything has been handled already...
    if ties != 'ordered':
        o = np.argsort(x)

        # keep ordered with one another
        x = x[o]
        y = y[o]

        # what if any are the same?
        ux = np.unique(x)
        if ux.shape[0] < nx:
            # Do we want to warn for this?
            # warnings.warn('collapsing to unique "x" values')

            # vectorize this function to apply to each "cell" in the array
            def tie_apply(f, u_val):
                vals = y[x == u_val]  # mask y where x == the unique value
                return f(vals)

            # replace the duplicates in the y array with the "tie" func
            func = VALID_TIES.get(ties, lambda t: t)
            y = np.vectorize(tie_apply)(func, ux)
            x = ux

    return x, y


def approx(x, y, xout, method='linear', rule=1, n=50, f=0, yleft=None,
           yright=None, ties='mean'):
    """Linear and Constant Interpolation"""
    if method not in VALID_APPROX:
        raise ValueError('method must be one of %r' % VALID_APPROX)

    # make sure xout is an array
    xout = c(xout).astype(np.float64)  # ensure double

    # check method
    method_key = method
    method = get_callable(method_key, VALID_APPROX)  # not a callable, actually...

    # copy/regularize vectors
    x, y = _regularize(x, y, ties)
    nx = x.shape[0]

    # if len 1?
    if nx <= 1:
        if method_key == 'linear':
            raise ValueError('need at least two points to linearly interpolate')
        if nx == 0:
            raise ValueError('empty array')

    # get yleft, yright
    if yleft is None:
        yleft = y[0] if rule != 1 else np.nan
    if yright is None:
        yright = y[-1] if rule != 1 else np.nan

    # call the C subroutine
    yout = C_Approx(x, y, xout, method, f, yleft, yright)
    return xout, yout

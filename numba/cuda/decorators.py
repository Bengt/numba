from __future__ import print_function, absolute_import, division
from numba import sigutils, types
from .compiler import (compile_kernel, compile_device, declare_device_function,
                       AutoJitCUDAKernel)


def jit(restype=None, argtypes=None, device=False, inline=False, bind=True,
        link=[], debug=False, **kws):
    """JIT compile a python function conforming to
    the CUDA-Python specification.

    To define a CUDA kernel that takes two int 1D-arrays::

        @cuda.jit('void(int32[:], int32[:])')
        def foo(aryA, aryB):
            ...

    .. note:: A kernel cannot have any return value.

    To launch the cuda kernel::

        griddim = 1, 2
        blockdim = 3, 4
        foo[griddim, blockdim](aryA, aryB)


    ``griddim`` is the number of thread-block per grid.
    It can be:

    * an int;
    * tuple-1 of ints;
    * tuple-2 of ints.

    ``blockdim`` is the number of threads per block.
    It can be:

    * an int;
    * tuple-1 of ints;
    * tuple-2 of ints;
    * tuple-3 of ints.

    The above code is equaivalent to the following CUDA-C.

    .. code-block:: c

        dim3 griddim(1, 2);
        dim3 blockdim(3, 4);
        foo<<<griddim, blockdim>>>(aryA, aryB);


    To access the compiled PTX code::

        print foo.ptx


    To define a CUDA device function that takes two ints and returns a int::

        @cuda.jit('int32(int32, int32)', device=True)
        def bar(a, b):
            ...

    To force inline the device function::

        @cuda.jit('int32(int32, int32)', device=True, inline=True)
        def bar_forced_inline(a, b):
            ...

    A device function can only be used inside another kernel.
    It cannot be called from the host.

    Using ``bar`` in a CUDA kernel::

        @cuda.jit('void(int32[:], int32[:], int32[:])')
        def use_bar(aryA, aryB, aryOut):
            i = cuda.grid(1) # global position of the thread for a 1D grid.
            aryOut[i] = bar(aryA[i], aryB[i])

    """
    restype, argtypes = convert_types(restype, argtypes)

    if restype and not device and restype != types.void:
        raise TypeError("CUDA kernel must have void return type.")

    def kernel_jit(func):
        kernel = compile_kernel(func, argtypes, link=link, debug=debug)

        # Force compilation for the current context
        if bind:
            kernel.bind()

        return kernel

    def device_jit(func):
        return compile_device(func, restype, argtypes, inline=True,
                              debug=debug)

    if device:
        return device_jit
    else:
        return kernel_jit


def autojit(func, **kws):
    """JIT at callsite.  Function signature is not needed as this
    will capture the type at call time.  Each signature of the kernel
    is cached for future use.

    .. note:: Can only compile CUDA kernel.

    Example::

        import numpy

        @cuda.autojit
        def foo(aryA, aryB):
            ...

        aryA = numpy.arange(10, dtype=np.int32)
        aryB = numpy.arange(10, dtype=np.float32)
        foo[griddim, blockdim](aryA, aryB)

    In the above code, a version of foo with the signature
    "void(int32[:], float32[:])" is compiled.
    """
    return AutoJitCUDAKernel(func, bind=True, targetoptions=kws)


def declare_device(name, restype=None, argtypes=None):
    restype, argtypes = convert_types(restype, argtypes)
    return declare_device_function(name, restype, argtypes)


def convert_types(restype, argtypes):
    # eval type string
    if sigutils.is_signature(restype):
        assert argtypes is None
        argtypes, restype = sigutils.normalize_signature(restype)

    return restype, argtypes



from collections.abc import Callable

from typing import Any, TypeVar, List, Tuple, Dict, Union, Sequence, MutableSequence

def scriptname():
    print("Hello, world!")


def functionname(x: int=1, y: int=1) -> int:
    """
    The sum of two numbers.

    Parameters
    ----------
    x : 
        The first number
    y :
        The second number.

    Returns
    -------
    :
        Sum of two numbers.

    Examples
    --------
    
    Adding two numbers
    
    ```python
    result = foo(2, 4)
    ```
    
    See Also
    --------
    [](`libraryname.modulename.scriptname`)
    """
    
    return x + y


import pytest
import numpy as np

# %% [markdown]
"""
## Asserting with the assert statement 

pytest allows you to use the standard Python assert for verifying expectations
and values in Python tests. For example, you can write the following:
"""
# %%
# content of test_assert1.py
def f():
    return 4

def test_function():
    assert f() == 4

# %% [markdown]
"""
If a message is specified with the assertion like this it is printed alongside the assertion introspection in the traceback.

```python
assert a % 2 == 0, "value was odd, should be even"
```

## Assertions about approximate equality

When comparing floating point values (or arrays of floats), small rounding
errors are common. Instead of using assert abs(a - b) < tol or numpy.isclose,
you can use pytest.approx(). pytest.approx works with scalars, lists,
dictionaries, and NumPy arrays. It also supports comparisons involving NaNs.

"""
# %%
import pytest
import numpy as np


def test_floats():
    assert (0.1 + 0.2) == pytest.approx(0.3)


def test_arrays():
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([0.9999999, 2.0000001, 3.0000001])
    assert a == pytest.approx(b)


# %% [markdown]
"""
## Assertions about expected exceptions

In order to write assertions about raised exceptions, you can use pytest.raises() as a context manager like this:

"""
# %%
def test_zero_division():
    with pytest.raises(ZeroDivisionError):
        1 / 0

# %% [markdown]
"""
“Requesting” fixtures
At a basic level, test functions request fixtures they require by declaring them as arguments.

When pytest goes to run a test, it looks at the parameters in that test function’s signature, and then searches for fixtures that have the same names as those parameters. Once pytest finds them, it runs those fixtures, captures what they returned (if anything), and passes those objects into the test function as arguments.

Quick example

"""
# %%

class Fruit:
    def __init__(self, name):
        self.name = name
        self.cubed = False

    def cube(self):
        self.cubed = True

class FruitSalad:
    def __init__(self, *fruit_bowl):
        self.fruit = fruit_bowl
        self._cube_fruit()

    def _cube_fruit(self):
        for fruit in self.fruit:
            fruit.cube()

# Arrange
@pytest.fixture
def fruit_bowl():
    return [Fruit("apple"), Fruit("banana")]


def test_fruit_salad(fruit_bowl):
    # Act
    fruit_salad = FruitSalad(*fruit_bowl)

    # Assert
    assert all(fruit.cubed for fruit in fruit_salad.fruit)



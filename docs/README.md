

Install in to make module available

    pip install .

First, build the reference for your own site, which includes an objects.json inventory:

    python -m quartodoc build

Second, retrieve the inventory files for any other sources:

    python -m quartodoc interlinks

Finally you should see the filter run when previewing your docs:

    quarto preview

Uninstall 

    pip uninstall pd-lfs

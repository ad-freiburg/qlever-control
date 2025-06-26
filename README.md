# QLever

QLever is a very fast SPARQL engine, much faster than most existing engines. It
can handle graphs with more than hundred billion triples on a single machine
with moderate resources. See https://qlever.cs.uni-freiburg.de for more
information and many public SPARQL endpoints that use QLever

This project provides a Python script that can control everything that QLever
does, in particular, creating SPARQL endpoints for arbitrary RDF datasets. It
is supposed to be very easy to use and self-explanatory as you use it. In
particular, the tool provides context-sensitive autocompletion of all its
commands and options. If you use a container system (like Docker or Podman),
you don't even have to download any QLever code, but the script will download
the required image for you.

NOTE: There has been a major update on 24.03.2024, which changed some of the
Qleverfile variables and command-line options (all for the better, of course).
If you encounter any problems, please contact us by opening an issue on
https://github.com/ad-freiburg/qlever-control/issues.

# Installation

Simply do `pip install qlever` and make sure that the directory where pip
installs the package is in your `PATH`. Typically, `pip` will warn you when
that is not the case and tell you what to do.

# Usage

Create an empty directory, with a name corresponding to the dataset you want to
work with. For the following example, take `olympics`. Go to that directory
and do the following. After the first call, `qlever` will tell you how to
activate autocompletion for all its commands and options (it's very easy, but
`pip` cannot do that automatically).

```
qlever setup-config olympics                       # Get Qleverfile (config file) for this dataset
qlever get-data                                    # Download the dataset
qlever index                                       # Build index data structures for this dataset
qlever start                                       # Start a QLever server using that index
qlever benchmark-queries --example-queries         # Launch some example queries
qlever ui                                          # Launch the QLever UI
```

This will create a SPARQL endpoint for the [120 Years of
Olympics](https://github.com/wallscope/olympics-rdf) dataset. It is a great
dataset for getting started because it is small, but not trivial (around 2
million triples), and the downloading and indexing should only take a few
seconds.

Each command will also show you the command line it uses. That way you can
learn, on the side, how QLever works internally. If you just want to know the
command line for a particular command, without executing it, you can append
`--show` like this:

```
qlever index --show
```

There are many more commands and options, see `qlever --help` for general help,
`qlever <command> --help` for help on a specific command, or just the
autocompletion.

# Use with your own dataset

To use QLever with your own dataset, you should also write a `Qleverfile`, like
in the example above. The easiest way to write a `Qleverfile` is to get one of
the existing ones (using `qlever setup-config ...` as explained above) and then
change it according to your needs (the variable names should be self-explanatory).
Pick one for a dataset that is similar to yours and when in doubt, pick `olympics`.

# For developers

The (Python) code for the script is in the `*.py` files in `src/qlever`. The
preconfigured Qleverfiles are in `src/qlever/Qleverfiles`.

If you want to make changes to the script, or add new commands, do as follows:

```
git clone https://github.com/ad-freiburg/qlever-control
cd qlever-control
pip install -e .
```

Then you can use `qlever` just as if you had installed it via `pip install
qlever`. Note that you don't have to rerun `pip install -e .` when you modify
any of the `*.py` files and not even when you add new commands in
`src/qlever/commands`. The exceutable created by `pip` simply links and refers
to the files in your working copy.

If you have bug fixes or new useful features or commands, please open a pull
request. If you have questions or suggestions, please open an issue.

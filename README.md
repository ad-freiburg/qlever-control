# QLever Control

This is a small repository, which provides a script `qlever` that can control
everything that QLever does. The script is supposed to be very easy to use and
pretty much self-explanatory as you use it. If you use Docker, you don't even
have to download any QLever code (Docker will pull the required images) and the
script is all you need.

# Installation

Simply do `pip install qlever` and make sure that the directory where pip
installs the package is in your `PATH`. Typically, `pip` will warn you when
that is not the case and tell you what to do.

# Usage

First, create an empty directory, with a name corresponding to the dataset you
want to work with. For the following example, take `olympics`. Go to that
directory, and do the following:

```
qlever                         # Basic help + lists of available pre-configs
qlever setup-config olympics   # Get examplary Qleverfile (config file)
qlever get-data                # Download the dataset (see below)
qlever index                   # Build index data structures for this dataset
qlever start                   # Start a QLever server using that index
qlever test-query              # Launch a test query 
qlever ui                      # Launch the QLever UI
```

This will create a SPARQL endpoint for the [120 Years of
Olympics](https://github.com/wallscope/olympics-rdf) dataset. It is a great
dataset for getting started because it is small, but not trivial (around 2
million triples), and the downloading and indexing should only take a few
seconds.

Each command will also show you the command line it uses. That way you can
learn, on the side, how QLever works internally. If you just want to know the
command line for a particular command, without executing it, you can append
"show" like this:

```
qlever index show
```

There are many more commands and options, see `qlever --help`. The script
supports autocompletion for all its commands and options. You can (and should)
activate it following the instructions given when you just type `qlever`
without any arguments.

# For developers

The (Python) code for the script is in the `*.py` files in `src/qlever`. The
preconfigured Qleverfiles are in `src/qlever/Qleverfiles`.

If you want to make changes to the script, git clone this repository, make any
changes you want, and run `pip install -e .`. Then you can use the script (with
whatever modifications you have made), just as if you had installed it via `pip
install qlever`. Note that unless you change the directory structure, you have
to execute `pip install -e .` only once (this local installation will not copy
your files but link to them).

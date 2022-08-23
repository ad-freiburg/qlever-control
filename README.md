# QLever Control

This is a very small repository. Its main contents is a script `qlever`
that can control everything that QLever does. The script is supposed to be very
easy to use and pretty much self-explanatory as you use it. If you use docker, you
don't even have to download any QLever code (docker will pull anything it needs)
and the script is all you need.

# Directory structure

We recommend that you have a directory "qlever" for all things QLever on your machine,
with subdirectories for the different components, in particular: "qlever-control" (this
repository), "qlever-indices" (with a subfolder for each of your datasets), and "qlever-code"
(only needed if you don't want to use docker, but compile the binaries on your machine).

# Quickstart

Create an empty directory (preferably as a subdirectory of "qlever-indices", go there,
and call the `qlever` script once with its full path and a dot and a space preceding it,
and the name of a preconfiguration as only argument. For example:

```. /path/to/qlever olympics```

This will create a `Qleverfile` preconfigured for the
[120 Years of Olympics](https://github.com/wallscope/olympics-rdf) dataset, which is
a great dataset to get started because it's small. Other options are:
`scientists` (another small test collection), `dblp` (larger), `wikidata` (very large),
and more. If you leave out the argument, you get a default `Qleverfile`, which you need
to edit first to use for your own dataset (it should be self-explanatory, after you have
played around with and looked at one of the preconfigured Qleverfiles).

Now you can call `qlever` without path and without a dot and a space preceding it and
with one or more actions as argument. To see the set of avaiable actions, just use the
autocompletion. When you are a first-timer, execute these commands one after the other
(without the comments):

```
qlever get-data       # Download the dataset
qlever index          # Build a QLever index for your data
qlever start          # Start a QLever server using that index
qlever example-query  # Launch an example query 
```

Each command will not only execute the respective action, but it will also show you
the exact command line it uses. That way you can learn, on the side, how QLever works
internally. If you just want to know the command used for a particular action, but
not execute it, you can append "show" like this:

```
qlever index show
```

You can also perform a sequence of actions with a single call, for example:

```
qlever stop remove-index index start
```

There are many more actions. The script supports autocompletion. Just type "qlever "
and then TAB and you will get a list of all the available actions.

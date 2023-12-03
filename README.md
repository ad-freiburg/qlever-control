# QLever Control

**Important: Use the `python-qlever` branch of this repository. The `main` branch
only works with bash on certain Linux systems and is no longer maintained.**

This is a very small repository. Its main contents is a script `qlever`
that can control everything that QLever does. The script is supposed to be very
easy to use and pretty much self-explanatory as you use it. If you use Docker, you
don't even have to download any QLever code (Docker will pull anything it needs)
and the script is all you need.

# Directory structure

We recommend that you have a directory `qlever` for all things QLever on your machine,
with subdirectories for the different components, in particular: `qlever-control` (this
repository), `qlever-indices` (with a subfolder for each of your datasets), and `qlever-code`
(only needed if you want to compile the QLever binaries on your machine instead of using
Docker).

Make sure that the `qlever-control` directory (which contains the `qlever` script) is in
your `PATH`. If you have compiled QLever binaries, the directory `qlever-code/build`
(which contains these binaries) should also be in your `PATH`. Note that Docker is easier
to use, but typically 10 - 20% slower compared to using the binaries directly.

# Quickstart

Create an empty directory as a subdirectory of `qlever-indices` (see the previous section),
go there, and call 

```
eval "$(qlever setup-autocompletion)"
qlever setup-config olympics
```
The first line will enable autocompletion for the `qlever` script, which is very useful. You can also
put that line in your `.bashrc` (or similar file if you are using another shell). The second
line will create a `Qleverfile` preconfigured for the
[120 Years of Olympics](https://github.com/wallscope/olympics-rdf) dataset, which is a great
dataset to get started because it is small. To see the list of all available configs, type
`qlever help` or just `qlever`. A dataset that is more interesting and larger, but can still
be downloaded and indexed in a matter of minutes is `dblp`. Have a look at the `Qleverfile` and see
whether the entries make sense (most of them are self-explanatory).

Now you can download the data, build an index for it (which QLever then uses to answer queries
efficiently), start the server, and launch a test query as follows:

```
qlever get-data
qlever index
qlever start
qlever test-query
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

There are many more actions. If you have enabled the autocompletion as described above,
you can just type `qlever ` and then TAB and you will get a list of all the available
actions.

# QLever Control

This is a very small repository. Its main contents is a script `qlever`
that can control everything that QLever does. The script is supposed to be very
easy to use and pretty much self-explanatory as you use it. If you use docker, you
don't even have to download any QLever code (docker will pull anything it needs)
and the script is all you need.

# Quickstart

Create a directory and put the RDF file you want to work with in there, for
example this small and neat dataset about [120 Years of Olympics](https://github.com/wallscope/olympics-rdf):

```
wget https://github.com/wallscope/olympics-rdf/raw/master/data/olympics-nt-nodup.zip
unzip olympics-nt-nodup.zip
````

Download the `qlever` script anywhere you like and call it once with the full path.
The script will then tell you what else to do. We recommend that you have a directory
"qlever" for all things QLever on your machine, with subdirectories for the different
components, for example: "qlever-control" (this repository), "qlever-code" (if you want
to download the code), "qlever-indices" (with a subfolder for each of your datasets and
indices), etc. But it's not a must, you can organize your files any way you like.

Once you have the script set up, you can perform "actions" in the directory with your
dataset:

```
qlever index          # Build a QLever index for your RDF data
qlever start          # Start a QLever server using that index
qlever status         # Show the current status
qlever stop           # Stop the current server
qlever ...            # There are many more actions, see below.
```

You can also perform a sequence of actions with a single call, for example:

```
qlever stop remove-index index start
```

If you just want to know what an action or sequence of actions is doing, but not (yet)
execute it, append "show":

```
qlever index start show
```

There are many more actions. The script supports autocompletion. Just type "qlever "
and then TAB and you will get a list of all the available actions. The script is not
perfect yet, but already works quite well and is a great help for all the things one
typically wants to do with Qlever. By showing the commands it executes for each action,
it's also a great way to learn how QLever works internally.

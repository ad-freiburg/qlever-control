# QLever Control

This is a very small repository. Its main contents is a script `qlever`
that can control everything that QLever does. The script is supossed to be very
easy to use. If you use docker, you don't even have to download any QLever code
(docker will pull anything it needs) and the script is all you need.

# Quickstart

Create a directory and put the RDF file you want to work with in there, for
example `olympics.ttl`, which you can download from here: https://github.com/wallscope/olympics-rdf .

Download the `qlever` script anywhere you like. Just make sure that the directory
is in your `PATH` or call the script with its full or relative path. It doesn't
matter from where you call the script, it will always work. For starters, just
put it in the same directory as your data and do `PATH=$PATH:.` so that the
current directory is included in your path.

When you first call `qlever`, it will ask you a few things. Just so them, the
script will tell you exactly what it wants and why. Then you can start working
with it, using its many features. For example:

```
qlever index          # Build a QLever index for your RDF data
qlever start          # Start a QLever server using that index
qlever log            # Follow the log of the current server (Ctrl+C aborts)
qlever stop           # Stop the current server
```

There are many more commands, the autocompletion will show them all to you. The
script also has the option to run everything with docker (either using one of
your own images or using the official QLever images from Dockerhub) or natively,
provided that you have installed your machine accordingly. More instructions on
that soon.

***This script is work in progress, stay tuned for more***

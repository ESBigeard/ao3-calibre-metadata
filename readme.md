
AO3 to Calibre metadata parser

Takes a library of Archive Of Our Own epub files imported into Calibre, parses and imports all tags and metadata of the AO3 work into neat Calibre metadata.

Current status : Works on my computer, still need to do a bunch of initialisation stuff to make it usable by other people. Maybe I'll do it someday. Mostly I'm putting this on GitHub so I can show my code to some people.

Repeat : Don't try to use this, it won't work for you.

What's AO3 ? It's a repository for online publishing of works of fiction. You can learn more about it on their website https://archiveofourown.org It has a very neat metadata system. But I like to hoard epub files on my hard drive where I can't find anything anymore. So I needed a way to sort these files without the help of the website.

What's Calibre ? It's a software that acts as a library for written documents, such as epub files. It also has a neat metadata system.

The scripts presents in this repository will read the metadata informations at the top of AO3-generated epubs and put them in Calibre so you can happily sort through fandoms, characters, tags, etc.

WARNING : In June 2019 AO3 changed the format of the epub files. Files downloaded before will not be correctly processed by this script. You will need to re-download the files for them to work. Sorry about that.


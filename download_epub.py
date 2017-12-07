#!/usr/bin/python
# -*- coding:utf-8 -*-
"""walk through a directory structure containing html AO3 files. reproduce the structure and populates it with the equivalent epub files. this works only for html files produced by AO3 "download/html" tool. This will not work if you directly downloaded the html page of the work. The correct files have on top "Posted originally on the Archive of Our Own at..." """

import os, urllib2,re,codecs,sys, errno
import requests

html_root_dir="html_library" #where your current library is located
epub_root_dir="epub_library" #where to put the new epub files


for root, dirs, files in os.walk(html_root_dir, topdown=False):
	for fname in files:
		if fname.endswith(".html"):
			fname_path=os.path.join(root,fname)
			with codecs.open(fname_path,"r","utf-8") as f1:
				#first step, get the url of the original work
				#this is a very crude parser to get the url of the original work on AO3. this will definitely break at some point.
				url_line=False
				for l in f1:
					if re.search("<p",l):
						url_line=True
						continue
					if url_line:
						url_line=l
						url=re.findall('">(.*?)</a',url_line)[0]
						break


				#second step, download the original work and find the url of the epub
				sys.stderr.write("Downloading "+fname_path+" ...")
				r=requests.get(url)
				work_page=r.text
				sys.stderr.write(" done !\n")
				try:
					link=re.findall('href="(.*?)">EPUB',work_page)[0]
				except IndexError:
					sys.stderr.write("Error : link to the epub file not found. Check if the file is a downloaded html work from AO3. If the file is correct, it might be a problem with the crawler.\n")
					sy.stderr.write("Problematic file : "+fname_path+"\n")
					continue
				link="http://archiveofourown.org"+link

				#third step, create the necessary directories
				out_path=root[len(html_root_dir):]
				out_path=root.strip("/")
				out_file=re.sub("\.html$",".epub",fname)
				if not os.path.exists(os.path.dirname(out_path)):
					try:
						os.makedirs(os.path.dirname(out_path))
					except OSError as exc: # Guard against race condition
						if exc.errno != errno.EEXIST:
							raise

				#fourth step : download the epub and save it in the correct location
				sys.stderr.write("Downloading "+os.path.join(out_path,out_file)+" ...")
				r=requests.get(link)
				epub_file=r.content
				sys.stderr.write(" done !\n")
				with open(os.path.join(out_path,out_file),"wb") as fout:
					fout.write(epub_file)


			exit()

#!/usr/bin/python
# -*- coding:utf-8 -*-
"""walk through a directory structure containing html AO3 files. reproduce the structure and populates it with the equivalent epub files."""

import os, urllib2,re,codecs
import requests

html_root_dir="html_library"
epub_root_dir="epub_library"


#print(os.path.join(root, name))
for root, dirs, files in os.walk(html_root_dir, topdown=False):
	for fname in files:
		if fname.endswith(".html"):
			with codecs.open(os.path.join(root,fname),"r","utf-8") as f1:
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
				r=requests.get(url)
				work_page=r.text
				link=re.findall('href="(.*?)">EPUB',work_page)[0]
				link="http://archiveofourown.org"+link

				#third step, download the actual epub and save it in the correct folder
				f_path=root[len(html_root_dir):]
				f_path=f_path.strip("/")
				fname=re.sub("\.html$",".epub",fname)
				fname_out=os.path.join(epub_root_dir,f_path,fname)
				if not os.path.exists(os.path.dirname(fname_out)):
					try:
						os.makedirs(os.path.dirname(fname_out))
					except OSError as exc: # Guard against race condition
						if exc.errno != errno.EEXIST:
							raise

				r=requests.get(link)
				epub_file=r.content
				with open(fname_out,"wb") as fout:
					fout.write(epub_file)


			exit()

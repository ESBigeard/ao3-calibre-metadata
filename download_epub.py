#!/usr/bin/python
# -*- coding:utf-8 -*-
"""walk through a directory structure containing html AO3 or fimfiction files. reproduce the structure and populates it with the equivalent epub files.
AO3 : this works only for html files produced by AO3 "download/html" tool. This will not work if you directly downloaded the html page of the work. The correct files have on top "Posted originally on the Archive of Our Own at..." 
fimfiction : will also parse tags from the page of the work on fimfiction and exports them in a json. the json contains a dictionary where the key is "name+author" of the work"""

import os, urllib2,re,codecs,sys, errno
import requests

source_site="fimfiction" #ao3 or fimfiction
html_root_dir="html_library/MLP" #where your current library is located
epub_root_dir="epub_library/MLP" #where to put the new epub files

if source_site=="fimfiction":
	from bs4 import BeautifulSoup
	import json
	metadata={}



for html_path, dirs, files in os.walk(html_root_dir, topdown=False):
	for fname in files:
		if fname.endswith(".html"):
			fname_path=os.path.join(html_path,fname)
			with codecs.open(fname_path,"r","utf-8") as f1:

				#first step, create the necessary directories, and check if there is already an .epub with the same name in the same location. if one if found, skip this file

				#compose the paths and filenames
				stripped_path=html_path[len(html_root_dir):]
				stripped_path=stripped_path.strip("/")
				epub_path=epub_root_dir.strip("/")
				epub_path=os.path.join(epub_path,stripped_path)
				if epub_path[-1]!="/":
					epub_path+="/"
				out_file=re.sub("\.html$",".epub",fname)
				complete_out_path=os.path.join(epub_path,out_file)

				#create directories
				if not os.path.exists(os.path.dirname(epub_path)):
					os.makedirs(os.path.dirname(epub_path))

				#check if file already exist
				if os.path.exists(complete_out_path) and source_site=="ao3":
					sys.stderr.write("File skipped (there already is a file with the same name in the same location) : "+complete_out_path+" \n")
					continue


				#second step, get the url of the original work
				url=""
				if source_site=="ao3":
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
				elif source_site=="fimfiction":
					for l in f1:
						if re.search("<h1>",l):
							url=re.findall('href="(.*?)"',l)[0]
				else:
					print "error website "+source_site+" unknown, must be ao3 or fimfiction"
					exit()
				if not url:
					print "impossible to find the url of this work, are you sure the file is from "+source_site+" ?"
					print fname_path



				#third step, download the original work and find the url of the epub
				sys.stderr.write("Downloading "+fname_path+" ...")
				r=requests.get(url)
				work_page=r.text
				sys.stderr.write(" done !\n")

				if source_site=="ao3":

					#find epub link
					try:
						link=re.findall('href="(.*?)">EPUB',work_page)[0]
					except IndexError:
						sys.stderr.write("Error : link to the epub file not found. Check if the file is a downloaded html work from AO3. If the file is correct, it might be a problem with the crawler.\n")
						sys.stderr.write("Problematic file : "+fname_path+"\n")
						continue
					link="http://archiveofourown.org"+link

				elif source_site=="fimfiction":

					#find epub link
					soup=BeautifulSoup(work_page,"lxml")
					a=soup.findAll("link",{"rel":"canonical"})[0]
					a=a["href"]
					work_id=re.sub("^.*story/","",a)
					work_id=re.sub("/.*$","",work_id)
					link="https://www.fimfiction.net/story/download/"+work_id+"/epub"

					#parse tags
					tags={}
					container=soup.findAll("article",{"class":"story_container"})[0]
					try:
						tag_line=container.findAll("ul",{"class":"story-tags"})[0]
						tags_items=tag_line.findAll("a")
						tags["characters"]=[]
						tags["tags"]=[]
						tags["content_rating"]=""
						for tag_item in tags_items:
							type_=tag_item["class"][0]
							content=tag_item.contents[0]
							if type_=="tag-series":
								pass
							elif type_=="tag-character":
								tags["characters"].append(content)
							else:
								tags["tags"].append(content)
								if content.lower()=="sex":
									tags["content_rating"]="E"
					except IndexError:
						print "The tags for the work "+fname_path+" could not be found, sorry."

					#get word count
					tags["word_count"]=""
					words=container.findAll("div",{"class":"word_count"})
					for w in words:
						if not w.findAll("span"):
							#at this point we are down to "<b>123,456</b> words". the next line goes inside the <b> tag to get to the number. this part will break as soon as the formatting of fimfiction changes
							w=w.find("b").contents[0]
							w=re.sub("\D","",w) #deletes the comma
							tags["word_count"]=w

					#get title and author to use as an ID with the tags
					title=soup.find("meta", property="og:title")["content"]
					author=soup.find("h1") #several h1 in the page, the first one is the author. this is definitely going to break at some point
					author=author.find("a").contents[0]

					#stock tags
					tag_id=title+"+"+author
					metadata[tag_id]=tags


				else:
					print "error website "+source_site+" unknown, must be ao3 or fimfiction"
					exit()



				#fourth step : download the epub and save it in the correct location
				if os.path.exists(complete_out_path):
					sys.stderr.write("File skipped (there already is a file with the same name in the same location) : "+complete_out_path+" \n")
					continue
				else:
					sys.stderr.write("Downloading "+complete_out_path+" ...")
					r=requests.get(link)
					epub_file=r.content
					sys.stderr.write(" done !\n")
					with open(complete_out_path,"wb") as fout:
						fout.write(epub_file)



if source_site=="fimfiction":
	with open("fimfiction_tags.json","w") as f:
		f.write(json.dumps(metadata))

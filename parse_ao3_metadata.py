#!/usr/bin/python
# -*- coding:utf-8 -*-
"""after having imported the works into calibre AND imported the custom columns, run this script to populate the custom columns with the AO3 tags and data
for a calibre book folder, created from an AO3 .epub file, parse the metadata in the beginning of the work toward calibre readable metadata in the metadata.opf"""

import os, zipfile, re, codecs,sys
from bs4 import BeautifulSoup
import sqlite3

custom_tags=True #Wether you want to add my custom tags, such as adding the tag "brick" if there is 10k words or more. True to add the tags, False to only keep the original tags

short_fandom={} #each character name is formatted as fandom.character, for example Avatar : The Last Airbender.Zuko This might be too verbose to your liking. Use this dictionnary to define a short name for a fandom. For example if you define short_fandom["Avatar : The Last Airbender"]="ATLA" Zuko will be named "ATLA.Zuko". No correction is performed on the long name, so be careful to type it exactly as it is. This has no effect on the metadata "fandom"
short_fandom["Avatar: The Last Airbender"]="ATLA" #example
short_fandom["The Legend of Korra"]="LoK"

brick_thresold=10000 #how many words are needed to add the tag "brick"

test_file="/home/ezi/Dropbox/save/lecture - fics/calibre_library/Sy_Itha/Conflict Resolution (15)/Conflict Resolution - Sy_Itha.epub"
#must be the file already imported into calibre, with the column already created, but with empty values
test_metadata_file="/home/ezi/Dropbox/save/lecture - fics/calibre_library/Sy_Itha/Conflict Resolution (15)/metadata.opf"

global_genre="fiction.fanfiction" #I like to put all my fanfiction in this sub-genre. you can change the value at will
global_read_status="New" #All fics read status will be "new". you can change this to "On it" or "Read" if you prefer. mind the capital.




#do not touch
custom_columns={}
custom_columns["word_count"]="1"
custom_columns["genre"]="2"
custom_columns["characters"]="3"
custom_columns["fandom"]="4"
custom_columns["pairings"]="5"
custom_columns["status"]="6"
custom_columns["read"]="7"
custom_columns["content_rating"]="8"

rating_conversion={}
rating_conversion["Explicit"]="E"
rating_conversion["Mature"]="A"
rating_conversion["Teen"]="T"
rating_conversion["General Audience"]="G"
rating_conversion["Not Rated"]=""



def parse_ao3_metadata(epub_file):
	"""read and parse metadata from the AO3 header and return a dictionnary of found values
	epub_file argument must be the path+name of a .epub file inside the calibre directory. not the original .epub file"""
	
	metadata={}
	metadata["genre"]=global_genre
	metadata["read"]=global_read_status

	with zipfile.ZipFile(epub_file) as z:
		with z.open("OEBPS/preface.xhtml") as f :
			html=f.readlines()
			html="\n".join(html)
			soup=BeautifulSoup(html,"lxml")

			#work ID
			uri=soup.findAll("a")[1]["href"]
			uri=re.sub("download\.","",uri)

			#metadata
			informations = soup.findAll("div", { "class" : "meta" })[0]
			title=soup.findAll("h1")[0].getText() #used to find the work in the library
			info_text=informations.getText()


			#parsing
			rating=re.findall("Rating:\n(.*?)\n",info_text)[0]
			fandom=re.findall("Fandom:\n(.*?)\n",info_text)[0]
			characters=re.findall("Character:\n(.*?)\n",info_text)[0]
			characters=characters.split(",")
			tags=re.findall("Additional Tags:\n(.*?)\n",info_text)[0]
			tags=tags.split(",")
			word_count=re.findall("Words: (\d+)",info_text)[0]
			chapters=re.findall("Chapters: (.*?)\n",info_text)[0]
			#series informations
			#pairings
			#bonus tags (brick,polyamory)

			#formatting
			metadata["content_rating"]=rating_conversion[rating]


			metadata["fandom"]=fandom
			#TODO what if we have several fandoms ?
			formatted_characters=[]
			for chara in characters:
				fd=metadata["fandom"]
				if fd in short_fandom:
					fd=short_fandom[fd]
				fd=re.sub("\."," ",fd) #to avoid bugs with the hierarchical structure
				chara=chara.strip()
				chara=chara.title()
				chara=re.sub("\."," ",chara) #to avoid bugs with the hierarchical structure
				chara=fd+"."+chara
				if False:
					chara="&quot;"+chara+"&quot;"
				formatted_characters.append(chara)
			#formatted_characters=",".join(formatted_characters)
			#formatted_characters="["+formatted_characters+"]"
			metadata["characters"]=formatted_characters
			
			chapters=chapters.strip()
			chapters=chapters.split("/")
			if chapters[1]=="?" or chapters[1]!=chapters[0]:
				metadata["status"]="Ongoing"
			else:
				metadata["status"]="Completed"

			metadata["tags"]=[]
			for tag in tags:
				tag=tag.strip()
				metadata["tags"].append(tag)

			if custom_tags==True and int(word_count)>brick_thresold:
				metadata["tags"].append("brick")
			metadata["word_count"]=word_count
			
	
	return uri,metadata


def parse_metadata_opf():
	"""unused, old parser for the metadata.opf file. turns out this file is useless."""
	with codecs.open(test_metadata_file,"r","utf-8") as fin, codecs.open(test_metadata_file+"_new","w","utf-8") as fout:
			for l in fin:
				match=re.match('\s+<meta name="calibre:user_metadata:#(.*?)"',l)
				if match:
					
					#get the type and value of the metadata
					data_type=match.group(1)
					try:
						data_value=metadata[data_type]
					except KeyError:
						data_value=""


					match2=re.search("&quot;#value#&quot;:(.*?), &quot;category_sort&quot;:",l)
					if match2:
						l_modified=l[:match2.start(1)]+data_value+l[match2.end(1):]
						if data_type in["characters","read"]:
							fout.write(l_modified)
						else:
							fout.write(l)
					else:
						fout.write(l)


				else: #not a line we need to change
					fout.write(l)

def fetch_value_id(column_number,value_real,create=False):
	"""returns the id of a value for a custom column. with option create, creates the value if it doesn't exist already ; otherwise, raise an error"""

def edit_calibre_database(uri,metadata):
	"""edit the metadata database of calibre
	uri must be the url of the work on AO3. like "http://archiveofourown.org/works/9290123"
	metadata must be a dictionnary produced by parse_ao3_metadata()
	"""
	db=sqlite3.connect("calibre_library/metadata.db")
	cursor=db.cursor()

	#find the book id
	cursor.execute("SELECT book,val FROM identifiers WHERE type='uri'")
	rows=cursor.fetchall()
	for r in rows:
		if r[1]==uri:
			id_=str(r[0])
	print "id:",id_


	#for metadata_type in ["genre","characters","fandom","pairings","status","read","content_rating"]:
	if True:
		metadata_type="status"
		value_real=metadata[metadata_type]
		column_number=custom_columns[metadata_type]

		#find the value id
		
		if metadata_type in ["genre","status","read","content_rating"]:
			#those types have a fixed number of possible values, and should already be in the values table
			cursor.execute("SELECT id FROM custom_column_"+column_number+" WHERE value='"+value_real+"'")
			rows= cursor.fetchall()
			if rows:
				value=str(rows[0][0])
			else:
				#if we're looking for a new value, chances are we made a mistake somewhere
				sys.stderr.write("error : the value "+value_real+" doesn't exist for the column "+metadata_type+". be sure to enter EXACTLY an existing value\n")
				raise TypeError
		else:
			#for those types, we need to check if the value exist and add it otherwise
			#add the new value
			#for now we assume the real_value is a list, but it will break on fandom
			for v in value_real:
				cursor.execute("SELECT id FROM custom_column_"+column_number+" WHERE value='"+v+"'")
				rows=cursor.fetchall()
				print "aaa", rows

			exit()

		#make the change
		cursor.execute("SELECT * FROM books_custom_column_"+column_number+"_link WHERE book="+id_)
		rows=cursor.fetchall()
		if rows:
			#update
			cursor.execute("UPDATE books_custom_column_"+column_number+"_link SET value ="+value+" WHERE book ="+id_)
		else:
			#insert
			cursor.execute("INSERT INTO books_custom_column_"+column_number+"_link (book,value) VALUES(?,?)",(id_,value))


	db.commit()


if __name__=="__main__":
	uri,metadata=parse_ao3_metadata(test_file)
	edit_calibre_database(uri,metadata)





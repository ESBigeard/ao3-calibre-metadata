#!/usr/bin/python
# -*- coding:utf-8 -*-
"""how to use : after having imported the works into calibre AND imported the custom columns, run this script to populate the custom columns with the AO3 tags and data. Reboot Calibre to view changes.
what it does : for a calibre book folder, created from an AO3 .epub file, parse the metadata in the beginning of the work toward calibre readable metadata in the metadata database"""

import os, zipfile, re, codecs,sys
from bs4 import BeautifulSoup
import sqlite3
from HTMLParser import HTMLParser
import argparse


disable_old_epub_warnings=True #option for myself. Silently ignore files that don't have the proper AO3 formatting


columns_to_update=[] #set here so it can be updated as a global variable later
hierarchical_columns=["characters","relationships"] #characters and relationships can be hierarchical or not. don't add any other.

#do not touch
custom_columns={}
custom_columns["word_count"]="1"
custom_columns["genre"]="2"
custom_columns["characters"]="3"
custom_columns["fandom"]="4"
custom_columns["relationships"]="5"
custom_columns["status"]="6"
custom_columns["read"]="7"
custom_columns["content_rating"]="8"
custom_columns["category_relationships"]="10"
custom_columns["series_ao3"]="12"
custom_columns["tags"]="tags"
#custom_columns["series"]="series"

rating_conversion={}
rating_conversion["Explicit"]="E"
rating_conversion["Mature"]="M"
rating_conversion["Teen And Up Audiences"]="T"
rating_conversion["General Audiences"]="G"
rating_conversion["Not Rated"]=""

#global variables regarding preferences. set by load_preferences()
calibre_library_location=""
calibre_database_location=""
short_fandom={}
short_ship={}
short_character={}
global_genre=""
global_read_status=""
shorten_fandom_itself=True

class AO3FormatError(Exception):
	pass

def load_preferences(fname):

	
	current_list=""
	with codecs.open(fname,"r","utf-8") as f:
		for l in f:
			if l.startswith("#"):
				continue
			l=l.strip()
			if len(l)>0:
				if l=="==FANDOM==":
					current_list="fandom"
					continue
				elif l=="==CHARACTER==":
					current_list="character"
					continue
				elif l=="==RELATIONSHIP==":
					current_list="relationship"
					continue
				elif l=="==PREFERENCES==":
					current_list="preferences"
					continue
				if not current_list:
					raise TypeError

				if current_list=="preferences":
					entry,value=l.split("=",1)
					entry=entry.strip()
					value=value.strip()

					if entry=="library_location":
						global calibre_library_location
						global calibre_database_location
						calibre_library_location=value
						calibre_database_location=calibre_library_location+"/metadata.db"


					elif entry=="genre":
						global global_genre
						global_genre=value
					if entry=="read_status":
						global global_read_status
						global_read_status=value
					
				else:
					short_name,long_name=l.split("=",1)
					short_name=short_name.strip()
					long_name=long_name.strip()
					if current_list=="fandom":
						short_fandom[long_name]=short_name
					elif current_list=="character":
						short_character[long_name]=short_name
					elif current_list=="relationship":
						short_ship[long_name]=short_name

	return #all infos are stored in global values, nothing to return



def format_relationship(ship):
	"""for a relationship name, puts the characters in alphabetical order, format/shorten the name of the characters (capitalisation etc) or the relationship if necessary (like wolfstar)"""
	#avoid duplicates due to different order
	#assumes that 3+ relationships have all the same separator (& or /)

	ship=re.sub(" - Relationship","",ship)
	separator=""
	if re.search("/",ship):
		separator="/"
	elif re.search("&",ship):
		separator="&"
	if separator:
		names=re.split("[/&]",ship)
		ship=[]
		for name in names:
			name=name.strip()
			name=format_character_name(name)
			ship.append(name)
		ship.sort()
		ship=separator.join(ship)
	else:
		#weird formatting, do nothing
		return ship
	if ship in short_ship:
		ship=short_ship[ship]
	else:
		ship2=[]
		for name in ship.split(separator):
			if name in short_character:
				name=short_character[name]
			ship2.append(name)
		ship=separator.join(ship2)

		
	return ship

def format_character_name(name):
	""" on a character name, corrects capitalisation and deletes parenthesis content"""
	name=re.sub("\(.*?\)","",name) #delete parenthesis content, such as "Draco Malfoy (Harry Potter)"
	name=re.split("( )",name) #split on space, keep the spaces
	#correct capitalisation
	for i,a in enumerate(name):
		if a !="'s":
			if len(a)>1:
				name[i]=a[0].upper()+a[1:]
			else:
				name[i]=a.upper()
	name="".join(name)
	name=name.strip()
	return name

def build_work_list(directory):
	"""recursively finds the location of all epub files in a directory"""
	list_=[]
	for root, dirs, files in os.walk(directory, topdown=False):
		for fname in files:
			if fname.endswith(".epub"):
				list_.append( os.path.join(root,fname) )
	return list_

def parse_ao3_metadata(epub_file):
	"""read and parse metadata from the AO3 header and return a dictionary of found values
	epub_file argument must be the path+name of a .epub file inside the calibre directory. not the original .epub file
	all modifications made to the data (such as ship names shortening) is done here
	"""
	
	metadata={}
	metadata["genre"]=global_genre
	if global_read_status:
		metadata["read"]=global_read_status
	source_site=""



	with zipfile.ZipFile(epub_file) as z:
		try:
			z_list=z.namelist()
			#first, we open "content.opf" to get the title, author and date. Those infos are already parsed by Calibre without our help, this will help up identify the bood in Calibre's database
			with z.open("content.opf") as f:
				html=f.readlines()
				html="\n".join(html)
				soup=BeautifulSoup(html,"lxml-xml")
				#Updating my computer led to an updating of python and of the default "lxml" parser. This created a bug where "dc:title" and other "dc:" tags were not properly processed (seen correctly in soup.find_all() but not found with soup.findAll("dc:title") ). I switched to "lxml_xml" parser which ignores the dc:" entirely and works. For future reference the tags below should be "dc:title" "dc:creator" "opf:file-as" and "dc:date".
				title=soup.findAll("title")[0].getText()
				author=soup.findAll("creator")[0]
				author=author["file-as"]
				date=soup.findAll("date")[0].getText()
				identifier=(title,author,date)
				

			#second, we open "[title]_split_00.xhtml" where the metadata we want to import is situated
			for z_name in z_list:
				if "split_000.xhtml" in z_name:
					correct_file=z_name
					break
			with z.open(correct_file) as f :
				source_site="ao3"
				html=f.readlines()
				html="\n".join(html)
				soup=BeautifulSoup(html,"lxml")

				#work ID
				uri=soup.findAll("a")[1]["href"]

				#metadata
				informations = soup.findAll("dl", { "class" : "tags" })[0]
				info_text=informations.getText()
		except KeyError:

			if not disable_old_epub_warnings :
				sys.stderr.write("Error : could not find AO3 formatting in the epub file. Are you sure this is an epub file generated by AO3 after spring 2019 ? (if your file is older you need to re-download it)\n")
			raise AO3FormatError

			return False #not an AO3 file




		#parsing of the metadata in the html
		#variable "info_text" contains the relevant part of the html in a string
		raw_data={}
		for data in ["Rating"]:
			try :
				raw_data[data]=re.findall(data+":\n(.*?)\n",info_text)[0]
			except IndexError:
				raw_data[data]=""
		for data in ["Fandom","Character","Relationship","Category","Additional Tags"]:
			try :
				s=re.findall(data+":\n(.*?)\n",info_text)[0]
				s=s.split(",")
				
				#special case, relationship like char1name1 / char2name1 | char1name2 / char2name2
				#doesn't work properly because i can't guess between the example previous line and char1name1 | char1name2 / char2
				#chose to just keep the relationship raw if a | is detected
				if False: # data=="Relationship" and "|" in "".join(s):
					s2=[]
					for relationship in s:
						if "|" in relationship :
							relationships=relationship.split("|")
							s2+=relationships
						else:
							s2.append(relationship)
					s=s2


				s=[x.strip() for x in s]
				raw_data[data]=s
			except IndexError:
				raw_data[data]=""

		word_count=re.findall("Words: (\d+)",info_text)[0]
		try:
			chapters=re.findall("Chapters: (.*?)\n",info_text)[0]
		except IndexError:
			chapters="1/1"

		series_match=re.findall("Series:\nPart (\d+) of\n\n(.*?)\n",info_text)
		if series_match:
			raw_data["series_n"],raw_data["series"]=series_match[0]
		else:
			raw_data["series"]=False #name of the series
			raw_data["series_n"]=False #number of the work in the series


		#formatting
		#metadata is a dictionary containing the final, clean values of all found metadata, and will be returned at the end
		metadata["content_rating"]=rating_conversion[raw_data["Rating"]]
		
		metadata["category_relationships"]=raw_data["Category"]
		metadata["word_count"]=word_count
		if raw_data["series"]:
			metadata["series_ao3"]=re.sub("[\.,']"," ",raw_data["series"])
			#I made this when I tried to use calibre native "series" metadata, that didn't work like the others. could probably delete this now.
		else:
			metadata["series_ao3"]=False
		metadata["series_number"]=raw_data["series_n"]


		if shorten_fandom_itself:
			metadata["fandom"]=[]
			for item in raw_data["Fandom"]:
				if item in short_fandom:
					metadata["fandom"].append(short_fandom[item])
				else:
					metadata["fandom"].append(item)
		else:
			metadata["fandom"]=raw_data["Fandom"]

		metadata["tags"]=[]
		for column_name,column_list in {"characters": raw_data["Character"], "relationships":raw_data["Relationship"]}.iteritems():

			#column_name = "characters", "relationships"...
			#column_list = ["harry potter","draco malfoy"] ...
				
			formatted_list=[]
			for item in column_list:
				item=item.strip()
				if column_name == "characters":
					item=format_character_name(item)

				elif column_name =="relationships":
					if not "|" in item: #weird stuff like character1name1 | character1name2 / character2, better not try to format it
						item=format_relationship(item)
					#if not "|" in item and ( len(re.findall("/",item))>1 and "threesome" in custom_tags_list):
					#	metadata["tags"].append("threesome")
						#TODO missing an option to not do this
					

				if column_name in hierarchical_columns:
					fd=metadata["fandom"][0] #TODO hack, if there is several fandoms, just associate the characters with the first fandom
					if fd in short_fandom:
						fd=short_fandom[fd]
					fd=re.sub("\."," ",fd) #to avoid bugs with the hierarchical structure
					item=re.sub("\."," ",item)
					item=fd+"."+item
				formatted_list.append(item)
			metadata[column_name]=formatted_list



		
		chapters=chapters.strip()
		chapters=chapters.split("/")
		if chapters[1]=="?" or chapters[1]!=chapters[0]:
			metadata["status"]="Ongoing"
		else:
			metadata["status"]="Complete"


	
	return identifier,metadata


def fetch_value_id(table_name,value_real,create_missing=False,):
	"""returns the id of a value for a custom column. with option create_missing, creates the value if it doesn't exist already ; otherwise, raise an error"""

	value_column_name="value" #name of the column where we want to find value_real
	if table_name in ["tags"]:
		value_column_name="name" #histoire de faire chier


	cursor.execute("SELECT id FROM "+table_name+" WHERE "+value_column_name+"= ?", (value_real,))
	rows= cursor.fetchone()
	if rows:
		value_id=str(rows[0])
	else:
		if create_missing:
			max_id=cursor.execute("SELECT MAX(id) FROM "+table_name)
			max_id=cursor.fetchone()[0]
			if max_id:
				value_id=max_id+1
			else:
				value_id=1
			cursor.execute("INSERT INTO "+table_name+" (id, '"+value_column_name+"') VALUES (?,?)" , (value_id,value_real) )
		else:
			sys.stderr.write("error : the value "+value_real+" doesn't exist for the column "+table_name+". be sure to enter EXACTLY an existing value\n")
			raise ValueError
	return str(value_id)

def fetch_canonical_tag(tag,tag_type):
	"""Given a name of fandom, character of relationship, fetches on AO3 the canonical tag. For example turns "Harry Potter" into "Harry Potter - J.K. Rowling" This is used to index correctly fandoms/characters/relationships that AO3 considers synonyms"""


	return canonical_tag


def edit_calibre_database(identifier,metadata,update_mode="new_only"):
	"""edit the metadata database of calibre
	Identifier is a tuple (title,author,date of publication). It is used to find the book in calibre's database. If you have two books by the same author with the same title published the same day you will have a collision and one of the two books will not be correctly processed. I used to use the URI of the book for that, but AO3 updated the format of the epubs and now calibre can't find the URI by itself :( But well if this happens scold the author, not me, I mean come on.
	metadata must be a dictionnary produced by parse_ao3_metadata()
	update_mode : "new_only" : process new books, normal use. "update" : re-tag everything. "update_tags" re-generate characters, relationships and fandom for books that were already processed. Useful if changes have been made to shortened tags.
	"""


	if update_mode=="update_tags":
		columns_to_update=["fandom","relationships","characters"]
		#besoin de run une première fois les delete, puis de les commenter et rerun pour re-populer. si on le fait en une seule fois, les tables restent vides
		#cursor.execute("DELETE FROM books_custom_column_3_link ") #character
		#cursor.execute("DELETE FROM books_custom_column_4_link ") #fandom
		#cursor.execute("DELETE FROM books_custom_column_5_link ") #relationships
	elif update_mode=="new_only":
		columns_to_update=["tags","series_ao3","word_count","content_rating","status","category_relationships","fandom","genre","relationships","characters","read"]
	elif update_mode=="update":
		columns_to_update=["tags","series_ao3","word_count","content_rating","status","category_relationships","fandom","genre","relationships","characters"]



	#find the book from the identifier
	title,author,date=identifier
	date=re.sub("T"," ",date)
	query="SELECT id FROM books WHERE title= ? and author_sort=? and pubdate=?"
	cursor.execute(query,(title,author,date))
	rows=cursor.fetchone()
	if rows:
		id_=str(rows[0])
	else:
		#can't find the book in calibre db
		sys.stderr.write("error : book "+title+" not found. have you first imported the work into calibre ?\n")
		return 0


	#check if fandom is already set, to know if this is a new book. if fandom is set, stop here
	if update_mode == "new_only":
		cursor.execute("SELECT * from books_custom_column_"+custom_columns["fandom"]+"_link WHERE book="+id_) 
		if cursor.fetchone():
			#print "Skipped this work (already tagged)"
			return
	

	print "processing ",title


	for metadata_type in columns_to_update:
		try:
			value_real_list=metadata[metadata_type] #the real, textual values of the metadata
		except KeyError :
			continue #no value set for this metadata
		column_number=custom_columns[metadata_type] #identifier of the type of metadata

		#determine table name
		column_name="custom_column_"+column_number
		if metadata_type=="tags":
			column_name="tags"
		column_name_link="books_"+column_name+"_link"
		if metadata_type=="word_count":
			column_name_link=column_name

		#determine the name of the column where the real values are in the table custom_column_N or tags
		value_column_name="value"
		if column_name=="tags":
			value_column_name="tag"


		create_missing=True
		if metadata_type in ["genre","status","read","content_rating"]:
			#create_missing=False #those have a fixed number of possible values. will return an error if we ask for a value that doesn't exist TODO remove that safeguard at the end for usability
			pass


		#fetch value id
		is_list=True
		if type(value_real_list)!=list:
			value_real_list=[value_real_list]
			is_list=False

		for value_real in value_real_list:

			if not value_real:
				continue

			if metadata_type=="word_count":
				value_id=value_real
			else:
				value_id=fetch_value_id(column_name,value_real,create_missing)


			#update the database

			if is_list :
			#if the metadata is list-like (tag-like) we don't want to replace an existing value, we want to add a new row
				#check if the specific pair of book and value already exist, create it if not
				cursor.execute("SELECT * FROM "+column_name_link+" WHERE book='"+id_+"' and "+value_column_name+"='"+value_id+"'")
				row=cursor.fetchone()
				if not row:
					cursor.execute("INSERT INTO "+column_name_link+" (book,"+value_column_name+") VALUES(?,?)",(id_,value_id))
				else:
					pass #the information is already in the db, do nothing

			else:
				#check if there is already a value for that work and metadata in the db
				cursor.execute("SELECT * FROM "+column_name_link+" WHERE book="+id_)
				rows=cursor.fetchall()

				if rows:
					#update
					if metadata_type=="series_ao3":
						cursor.execute("UPDATE "+column_name_link+" SET value = "+value_id+" , extra = "+metadata["series_number"]+" WHERE book ="+id_ )
					else:
						cursor.execute("UPDATE "+column_name_link+" SET "+value_column_name+" ="+value_id+" WHERE book ="+id_)
				else:
					#insert
					if metadata_type=="series_ao3":
						cursor.execute("INSERT INTO "+column_name_link+" (book,value,extra) VALUES(?,?,?)",(id_,value_id,metadata["series_number"]))
					else:
						cursor.execute("INSERT INTO "+column_name_link+" (book,"+value_column_name+") VALUES(?,?)",(id_,value_id))


	db.commit()


if __name__=="__main__":
	load_preferences("config.txt")
	works=build_work_list(calibre_library_location)

	db=sqlite3.connect(calibre_database_location)
	cursor=db.cursor()

	parser = argparse.ArgumentParser(description='Integrates AO3 tags into Calibre. You first need to import AO3 epub books into Calibre before running this script. Restart Calibre to see changes.')
	parser.add_argument("-m",'--mode', choices={"new_only","update","update_tags"},  default="new_only",help='')
	parser.add_argument('--debug',  action='store_true', help='If encounters a problem on a book, halts and prints relevant error instead of skipping')
	args = parser.parse_args()

	#TODO : 
	#formats the ship names provided by the user in order to match the formatting of ships extracted from the epub
	#avoids errors if there's a . somewhere in the name


	for work in works:
		try :
			data=parse_ao3_metadata(work)
		except AO3FormatError :
			if not disable_old_epub_warnings:
				sys.stderr.write("Error while processing "+work+" this file has been ignored.\n")
			continue
		except Exception :
			if args.debug:
				sys.stderr.write("Error while processing "+work+"\n")
				raise
			else:
				sys.stderr.write("Error while processing "+work+" this file has been ignored.\n")
				continue

		edit_calibre_database(data[0],data[1],args.mode) #may return 0 if there was an error






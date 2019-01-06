#!/usr/bin/env python3

from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
import tkinter.font as tkfont
import os
import pickle
import subprocess
import re
import datetime

ROOTPATH = os.getcwd()
lib_file = "papers.dat"
conference_file = "./conference.dat"
DEFAULT_YEAR = 1900
MAX_RATING = 5
OTHERS_CONFERENCE = 'others'

# Build a list of tuples for each file type the file dialog should display
my_filetypes = [('all files', '.*'), ('pdf files', '.pdf'), ('text files', '.txt')]

class Category:
    def __init__(self, label):
        self.label = label
        self.papers = set()     # paper ids

    # category_str: gui_input, multiple category separated by ';'
    @classmethod
    def parse(cls, category_str):
        items = category_str.split(';')
        category = []
        for item in items:
            item = item.strip()
            if len(item) < 1 : continue
            category.append(item)
        return category
    
    @classmethod
    def guiString(cls, categories):
        return ';'.join([c.label for c in categories])
    
    def __repr__(self):
        return self.label

author_format_re = re.compile(r'^(.+?),(.+?);(.*)')
author_format1_re = re.compile(r'^(.+?),(.+?) and (.*)')
class Author(Category):
    def __init__(self, label):
        self.last_name, self.first_name = self.nameParse(label)
        self.label = self.getFullname(self.first_name, self.last_name)
        self.papers = set()

    def getFullname(self, first_name, last_name):
        if len(self.last_name) > 0 and len(self.first_name) > 0:
            return self.last_name + ', ' + self.first_name
        elif len(self.last_name) > 0 :
            return self.last_name
        else: return ""
    
    @classmethod
    def nameParse(cls, full_name):
        tmp_names = re.split(',| ', full_name.strip())
        names = []
        for n in tmp_names:
            if len(n.strip()) > 0:
                names.append(n.strip())
        first_name = ""
        last_name = ""
        if len(names) > 0:
            last_name = names[0]
        if len(names) > 1 :
            first_name = names[-1]
        return last_name, first_name

    @classmethod
    def parseFormat1(cls, author_str):
        items = author_str.split(' and ')
        authors = []
        for item in items:
            item = item.strip()
            if len(item) < 1 : continue
            authors.append(item)
        return authors
    
    @classmethod
    def parseAuthorString(cls, author_str):
        m = author_format_re.match(author_str)
        m1 = author_format1_re.match(author_str)
        if m:
            items = cls.parse(author_str)
        elif m1:
            items = cls.parseFormat1(author_str)
        else:
            items = [author_str]
        return items

    @classmethod
    def authorParse(cls, author_str):
        items = cls.parseAuthorString(author_str)
        authors = []
        for item in items:
            authors.append(Author(item))
        return authors

    @classmethod
    def bibString(cls, authors):
        return ' and '.join([a.label for a in authors])
    
    @classmethod
    def guiString(cls, authors):
        return ';'.join([a.label for a in authors])

class Project(Category):

    @classmethod
    def projectParse(cls, project_str):
        items = cls.parse(project_str)
        projects = []
        for item in items:
            projects.append(Project(item))
        return projects

class Tag(Category):

    @classmethod
    def tagParse(cls, tag_str):
        items = cls.parse(tag_str)
        tags = []
        for item in items:
            tags.append(Tag(item))
        return tags

class Conference:
    def __init__(self, label):
        self.label = label
        self.index = 0
        self.papers = set()
    
    @staticmethod
    def loadConference(file_name):
        c_map = {}
        with open(file_name) as fin:
            for line in fin.readlines():
                line = line.strip().lower()
                items = re.split('\t|    ', line)
                if len(items) != 2: continue
                c_map[items[0]] = items[1]
        return c_map
    
    def __repr__(self):
        return self.label

class Dataset(Category):
    
    @classmethod
    def datasetParse(cls, dataset_str):
        items = cls.parse(dataset_str)
        datasets = []
        for item in items:
            datasets.append(Dataset(item))
        return datasets

first_word_re = re.compile(r'^[a-zA-Z]+')
class Bib:
    
    def __init__(self):
        self._title = ""
        self._author = []
        self._conference = Conference(OTHERS_CONFERENCE)
        self._year = DEFAULT_YEAR
        
        self._first_title_word = ""
        self._first_author_name = ""

        self.bibtex = ""
        self.type = 0       # 0: conference, 1: jornal

    @property
    def title(self):
        return self._title
    
    @title.setter
    def title(self, value):
        self._title = value.lower()
        m = first_word_re.search(value)
        if m : self._first_title_word = m.group()
    
    @property
    def author(self):
        return self._author
    
    @author.setter
    def author(self, value):
        self._author = []
        self._first_author_name = ""
        if isinstance(value, str) and len(value) > 0:
            value = Author.authorParse(value.lower())
        if isinstance(value, list) and len(value) >= 1 :
            format_correct = True
            for v in value:
                if not isinstance(v, Author) : 
                    format_correct = False
                    break
            if format_correct:
                self._author = value
                self._first_author_name = value[0].last_name
    
    @property
    def conference(self):
        return self._conference
    
    @conference.setter
    def conference(self, value):
        self._conference = Conference(OTHERS_CONFERENCE)
        if isinstance(value, str) and len(value) > 0:
            value = Conference(value.lower())
        if isinstance(value, Conference) :
            self._conference = value
    
    @property
    def year(self):
        return self._year
    
    @year.setter
    def year(self, value):
        self._year = DEFAULT_YEAR
        if isinstance(value, str) and len(value) > 0:
            value = int(value)
        if isinstance(value, int) and value >= DEFAULT_YEAR and value <= datetime.datetime.now().year : 
            self._year = value
    
    def __repr__(self):
        tmp_cite = self._first_author_name + str(self.year)+ self._first_title_word
        if self.type == 1:
            return "@article{{{},\n  title={{{}}},\n  author={{{}}},\n  journal={{{}}},\n  year={{{}}}\n}}".format(tmp_cite, self.title, Author.bibString(self.author), self.conference.label, str(self.year))
        else:
            return "@inproceedings{{{},\n  title={{{}}},\n  author={{{}}},\n  booktitle={{{}}},\n  year={{{}}}\n}}".format(tmp_cite, self.title, Author.bibString(self.author), self.conference.label, str(self.year))

type_re = re.compile(r'^@inproceedings(.*)')
title_re = re.compile(r'(?<=[^a-z]title\={).+?(?=})')
author_re = re.compile(r'(?<=[^a-z]author\={).+?(?=})')
conference_re = re.compile(r'(?<=[^a-z]booktitle\={).+?(?=})|(?<=[^a-z]journal\={).+?(?=})')
year_re = re.compile(r'(?<=[^a-z]year\={).+?(?=})')
class bibParser:

    @classmethod
    def parse(cls, bib_str, lib=None):
        b = Bib()
        b.bibtex = bib_str
        b.type = cls.typeParser(bib_str)
        b.title = cls.titleParser(bib_str)
        b.author = cls.authorParser(bib_str, lib=lib)
        b.conference = cls.conferenceParser(bib_str, lib=lib)
        b.year = cls.yearParser(bib_str)
        return b
    
    @classmethod
    def typeParser(cls, bib_str):
        m = type_re.match(bib_str)
        return 0 if m else 1
    
    @classmethod
    def titleParser(cls, bib_str):
        m = title_re.search(bib_str)
        return m.group() if m else ""
    
    @classmethod
    def authorParser(cls, bib_str, lib=None):
        m = author_re.search(bib_str)
        a_str = m.group() if m else ""
        if lib is not None:
            authors = lib.parseAuthors(a_str)
            return authors
        return a_str
    
    @classmethod
    def conferenceParser(cls, bib_str, lib=None):
        m = conference_re.search(bib_str)
        c_str = m.group() if m else ""
        if lib is not None:
            conference = lib.parseConference(c_str)
            return conference
        return c_str
    
    @classmethod
    def yearParser(cls, bib_str):
        m = year_re.search(bib_str)
        return m.group() if m else ""
    
class Paper(object):

    def __init__(self):
        # required information
        self.id = -1
        self.bib = Bib()
        self._path = ""     # relative path to support cloud storage
        
        # optional information
        self._dataset = []
        self._tag = []
        self._project = []

        self.comment = ""
        self.hasGithub = False
        self.hasRead = False
        self._rating = 0

    @property
    def bibtex(self):
        return self.bib.bibtex
    
    @bibtex.setter
    def bibtex(self, value):
        self.bib.bibtex = value
    
    @property
    def papertype(self):
        return self.bib.type
    
    @papertype.setter
    def papertype(self, value):
        self.bib.type = value

    @property
    def title(self):
        return self.bib.title
    
    @title.setter
    def title(self, value):
        self.bib.title = value
    
    @property
    def author(self):
        return Author.guiString(self.bib.author)
    
    @author.setter
    def author(self, value):
        self.bib.author = value

    @property
    def conference(self):
        return self.bib.conference.label
    
    @conference.setter
    def conference(self, value):
        self.bib.conference = value
    
    @property
    def year(self):
        return str(self.bib.year)

    @year.setter
    def year(self, value):
        self.bib.year = value

    @property
    def rating(self):
        return str(self._rating)

    @rating.setter
    def rating(self, value):
        self._rating = 0
        if isinstance(value, str) : value = int(value)
        if isinstance(value, int) and value >= 0 and value <= MAX_RATING:
            self._rating = value

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = ""
        full_path = os.path.abspath(value)
        if os.path.isfile(full_path):
            self._path = os.path.relpath(full_path)

    @property
    def full_path(self):
        return os.path.abspath(self._path)

    @property
    def dataset(self):
        return Dataset.guiString(self._dataset)
    
    @dataset.setter
    def dataset(self, value):
        self._dataset = []
        if isinstance(value, str) and len(value) > 0:
            value = Dataset.datasetParse(value)
        if isinstance(value, list) and len(value) >= 1 :
            format_correct = True
            for v in value:
                if not isinstance(v, Dataset) : 
                    format_correct = False
                    break
            if format_correct:
                self._dataset = value
    
    @property
    def tag(self):
        return Tag.guiString(self._tag)
    
    @tag.setter
    def tag(self, value):
        self._tag = []
        if isinstance(value, str) and len(value) > 0:
            value = Tag.tagParse(value)
        if isinstance(value, list) and len(value) >= 1 :
            format_correct = True
            for v in value:
                if not isinstance(v, Tag) : 
                    format_correct = False
                    break
            if format_correct:
                self._tag = value
    
    @property
    def project(self):
        return Project.guiString(self._project)
    
    @project.setter
    def project(self, value):
        self._project = []
        if isinstance(value, str) and len(value) > 0:
            value = Project.projectParse(value)
        if isinstance(value, list) and len(value) >= 1 :
            format_correct = True
            for v in value:
                if not isinstance(v, Project) : 
                    format_correct = False
                    break
            if format_correct:
                self._project = value

    def __repr__(self):
        return "title: {}\nauthor: {}\nconference: {}\nyear: {}\npath: {}\ntags: {}\ndataset: {}\nproject: {}\ncomment: {}\n{}\n".format(self.title, self.author, self.conference, self.year, self.full_path, self.tag, self.dataset, self.project, self.comment, 'Has released codes!' if self.hasGithub else 'No released codes!')
    
    def checkState(self):
        state = 0
        if self._path == "" :
            state = 1
        elif self.title == "" or self.author == "" or self.conference == "" or self.year == "" :
            state = 2
        return state

class Library:
    def __init__(self):
        self.data_file = os.path.abspath(lib_file)

        self._years = {}     # {year:set(paper_id, ...), ...}

        self._authors = {}   # author_label: Author()
        self._conferences = {OTHERS_CONFERENCE:Conference(OTHERS_CONFERENCE)}   # conference_label: Conference()
        self._datasets = {}   # dataset_label: Conference()
        self._tags = {}   # tag_label: Conference()
        self._projects = {}   # project_label: Conference()
        self._ratings = {}      # rating: set(paper_id, ...)

        self._papers = {}   # paper_id: Paper()
        self.paper_id_pool = set()
        self.max_paper_id = len(self._papers) - 1
    
    @property
    def papers(self):
        return self._papers
    
    @property
    def authors(self):
        return self._authors
    
    @property
    def conferences(self):
        return self._conferences
    
    @property
    def years(self):
        return self._years
    
    @property
    def datasets(self):
        return self._datasets

    @property
    def tags(self):
        return self._tags
    
    @property
    def projects(self):
        return self._projects
    
    @property
    def ratings(self):
        return self._ratings
    
    def parseConference(self, c_str):
        c_list = self.findConference(c_str.lower())
        if len(c_list) > 0:
            # todo: compute similarity and pick up the similarer one
            re_c = c_list[0]
            for c in c_list:
                if c_str == c.label:
                    re_c = c
        else: re_c = self.conferences[OTHERS_CONFERENCE]
        return re_c
    
    def parseAuthors(self, a_str):
        authors = []
        items = Author.parseAuthorString(a_str.lower())
        for item in items:
            last_name, first_name = Author.nameParse(item)
            full_name = last_name + ', ' + first_name
            a_list = self.findAuthor(full_name)
            if len(a_list) > 0:
                authors.append(a_list[0])
            else:
                authors.append(Author(full_name))
        return authors
    
    def parseTags(self, t_str):
        tags = []
        items = Tag.parse(t_str.lower())
        for item in items:
            t_list = self.findTag(item)
            if len(t_list) > 0:
                tags.append(t_list[0])
            else:
                tags.append(Tag(item))
        return tags
    
    def parseDatasets(self, d_str):
        datasets = []
        items = Dataset.parse(d_str.lower())
        for item in items:
            d_list = self.findDataset(item)
            if len(d_list) > 0:
                datasets.append(d_list[0])
            else:
                datasets.append(Dataset(item))
        return datasets
    
    def parseProjects(self, p_str):
        projects = []
        items = Project.parse(p_str.lower())
        for item in items:
            p_list = self.findProject(item)
            if len(p_list) > 0:
                projects.append(p_list[0])
            else:
                projects.append(Project(item))
        return projects
    
    def removePaper(self, paper_id):
        if paper_id in self.papers:
            del_paper = self.papers[paper_id]

            self.years[del_paper.bib.year].remove(paper_id)
            if len(self.years[del_paper.bib.year]) == 0:
                del self.years[del_paper.bib.year]

            del_paper.bib.conference.papers.remove(paper_id)

            for a in del_paper.bib.author:
                a.papers.remove(paper_id)
                if len(a.papers) == 0:
                    del self.authors[a.label]
            
            for t in del_paper._tag:
                t.papers.remove(paper_id)
                if len(t.papers) == 0:
                    del self.tags[t.label]
            
            for d in del_paper._dataset:
                d.papers.remove(paper_id)
                if len(d.papers) == 0:
                    del self.datasets[d.label]
            
            for p in del_paper._project:
                p.papers.remove(paper_id)
                if len(p.papers) == 0:
                    del self.projects[p.label]
            
            self.ratings[del_paper._rating].remove(paper_id)
            if len(self.ratings[del_paper._rating]) == 0:
                del self.ratings[del_paper._rating]

            del self._papers[paper_id]
            self.paper_id_pool.add(paper_id)
    
    # paper: Paper()
    def addPaper(self, paper):
        
        paper_id = self.generatePaperId()
        paper.id = paper_id

        self.addPaperYear(paper_id, paper.bib.year)
        self.addPaperRating(paper_id, paper._rating)

        paper.bib.conference.papers.add(paper_id)
        
        self.addPaperCategory(paper_id, paper.bib.author, self.authors)
        self.addPaperCategory(paper_id, paper._tag, self.tags)
        self.addPaperCategory(paper_id, paper._dataset, self.datasets)
        self.addPaperCategory(paper_id, paper._project, self.projects)

        self._papers[paper_id] = paper
    
    def addPaperYear(self, paper_id, year):
        tmp_paper_set = self._years.get(year, set())
        tmp_paper_set.add(paper_id)
        self._years[year] = tmp_paper_set
    
    def addPaperRating(self, paper_id, rating):
        tmp_paper_set = self._ratings.get(rating, set())
        tmp_paper_set.add(paper_id)
        self._ratings[rating] = tmp_paper_set
    
    def addPaperCategory(self, paper_id, categories, target_categories):
        for c in categories:
            if len(c.papers) == 0:
                target_categories[c.label] = c
            c.papers.add(paper_id)
    
    def revisePaperBib(self, paper_id, bib):
        target_paper = self.papers[paper_id]

        if target_paper.bibtex != bib.bibtex:
            target_paper.bib.bibtex = bib.bibtex

        if target_paper.papertype != bib.type:
            target_paper.bib.type = bib.type

        if target_paper.title != bib.title:
            target_paper.bib.title = bib.title
        
        if int(target_paper.year) != bib.year:
            self.years[target_paper.bib.year].remove(paper_id)
            if len(self.years[target_paper.bib.year]) == 0 :
                del self.years[target_paper.bib.year]
            self.addPaperYear(paper_id, bib.year)
            target_paper.bib.year = bib.year

        if target_paper.conference != bib.conference.label:
            target_paper.bib.conference.papers.remove(paper_id)
            target_paper.bib.conference = bib.conference
            bib.conference.papers.add(paper_id)

        if target_paper.author != Author.guiString(bib.author):
            target_paper.bib.author = self.revisePaperCategory(paper_id, bib.author, target_paper.bib.author, self.authors)
    
    def revisePaper(self, paper_id, paper):
        target_paper = self.papers[paper_id]

        if target_paper.path != paper.path:
            target_paper.path = paper.path

        self.revisePaperBib(paper_id, paper.bib)

        if target_paper.tag != paper.tag:
            target_paper._tag = self.revisePaperCategory(paper_id, paper._tag, target_paper._tag, self.tags)
        if target_paper.dataset != paper.dataset:
            target_paper._dataset = self.revisePaperCategory(paper_id, paper._dataset, target_paper._dataset, self.datasets)
        if target_paper.project != paper.project:
            target_paper._project = self.revisePaperCategory(paper_id, paper._project, target_paper._project, self.projects)

        if target_paper.comment != paper.comment:
            target_paper.comment = paper.comment
        
        if target_paper.hasRead != paper.hasRead:
            target_paper.hasRead = paper.hasRead
        if target_paper.hasGithub != paper.hasGithub:
            target_paper.hasGithub = paper.hasGithub
        
        if target_paper.rating != paper.rating:
            self.ratings[target_paper._rating].remove(paper_id)
            if len(self.ratings[target_paper._rating]) == 0:
                del self.ratings[target_paper._rating]
            self.addPaperRating(paper_id, paper._rating)
            target_paper._rating = paper._rating
    
    def revisePaperCategory(self, paper_id, source_category, target_category, categories):
        for c in source_category:
            c.papers.add(paper_id)
            if c.label not in categories:
                categories[c.label] = c
        for c in target_category:
            if c not in source_category:
                c.papers.remove(paper_id)
                if len(c.papers) == 0:
                    del categories[c.label]
        return source_category
        
    def setOtherConference(self, paper_id, paper):
        paper.bib._conference = self._conferences[OTHERS_CONFERENCE]
        self._conferences[OTHERS_CONFERENCE].papers.add(paper_id)

    def generatePaperId(self):
        if len(self.paper_id_pool) < 1:
            self.extendPaperIdPool()
        tmp_id = self.paper_id_pool.pop()
        return tmp_id
    
    def extendPaperIdPool(self):
        tmp_id = self.max_paper_id + 1
        while tmp_id in self.paper_id_pool:
            tmp_id += 1
        self.paper_id_pool.add(tmp_id)
        self.max_paper_id = tmp_id
    
    def similarity(self, str_a, str_b, support_fuzzy=False):
        if not support_fuzzy:
            return str_a.lower() == str_b.lower()
        if str_a in str_b or str_b in str_a :
            return True
        return False
    
    def searchDuplicatePaper(self, paper):
        norm_path = os.path.normpath(paper.path)
        for pi in self.papers:
            if norm_path == self.papers[pi].path or paper.title == self.papers[pi].title:
                return pi
        return -1

    # todo: better fuzzy comment
    def findPaper(self, paper, target_paper_ids=None, support_fuzzy=False, fuzzy_window=0):
        
        title_papers = set()
        author_papers = set()
        conference_papers = set()
        year_papers = set()
        tag_papers = set()
        dataset_papers = set()
        project_papers = set()

        if len(paper.title) > 0:
            title_papers = self.findTitle(paper.title, target_paper_ids=target_paper_ids, support_fuzzy=support_fuzzy)

        if paper.conference != OTHERS_CONFERENCE:
            conferences = self.findConference(paper.conference, support_fuzzy=support_fuzzy)
            conference_papers = self.combineListFindResults([c.papers for c in conferences])

        if paper.bib.year > DEFAULT_YEAR:
            year_papers = self.findYear(paper.year, fuzzy_window=fuzzy_window)
        
        if len(paper.author) > 0:
            authors = []
            for a in paper.bib.author:
                authors.extend(self.findAuthor(a.label, support_fuzzy=support_fuzzy))
            author_papers = self.combineListFindResults([a.papers for a in authors])
        
        if len(paper.tag) > 0:
            tags = []
            for t in paper._tag:
                tags.extend(self.findTag(t.label, support_fuzzy=support_fuzzy))
            tag_papers = self.combineListFindResults([t.papers for t in tags])
        
        if len(paper.dataset) > 0:
            datasets = []
            for d in paper._dataset:
                datasets.extend(self.findDataset(d.label, support_fuzzy=support_fuzzy))
            dataset_papers = self.combineListFindResults([d.papers for d in datasets])
        
        if len(paper.project) > 0:
            projects = []
            for p in paper._project:
                projects.extend(self.findProject(p.label, support_fuzzy=support_fuzzy))
            project_papers = self.combineListFindResults([p.papers for p in projects])
        
        tmp_papers, isAnd = self.combineTwoFindResults(title_papers, author_papers, len(paper.title) > 0, len(paper.author) > 0)

        tmp_papers, isAnd = self.combineTwoFindResults(tmp_papers, conference_papers, isAnd, paper.conference != OTHERS_CONFERENCE)

        tmp_papers, isAnd = self.combineTwoFindResults(tmp_papers, year_papers, isAnd, paper.bib.year > DEFAULT_YEAR)
        
        tmp_papers, isAnd = self.combineTwoFindResults(tmp_papers, tag_papers, isAnd, len(paper.tag) > 0)
        
        tmp_papers, isAnd = self.combineTwoFindResults(tmp_papers, dataset_papers, isAnd, len(paper.dataset) > 0)
        
        tmp_papers, isAnd = self.combineTwoFindResults(tmp_papers, project_papers, isAnd, len(paper.project) > 0)
        
        if target_paper_ids is not None:
            tmp_papers =[pi for pi in tmp_papers if pi in target_paper_ids]
        return tmp_papers
    
    def combineTwoFindResults(self, papers1, papers2, isAnd1, isAnd2):
        papers = set()
        isAnd = False
        if isAnd1 and isAnd2:
            papers = papers1 & papers2
            isAnd = True
        elif isAnd1:
            papers = papers1
            isAnd = True
        elif isAnd2:
            papers = papers2
            isAnd = True
        return papers, isAnd

    def combineListFindResults(self, papers_list, isAnd=True):
        re_papers = set()
        if len(papers_list) > 0 :
            if isAnd:
                re_papers = papers_list[0].intersection(*papers_list[1:])
            else:
                re_papers = papers_list[0].union(*papers_list[1:])
        return re_papers

    def findYear(self, year, fuzzy_window=0):
        papers = set()
        year = int(year)
        if year in self.years:
            papers |= self.years[year]
        if fuzzy_window > 0:
            for i in range(fuzzy_window):
                if year+1+i in self.years:
                    papers |= self.years[year+1+i]
                if year-i-1 in self.years:
                    papers |= self.years[year-i-1]
        return papers
    
    def findRating(self, rating):
        papers = set()
        rating = int(rating)
        if rating in self.ratings:
            papers |= self.ratings[rating]
        return papers
    
    def findUnread(self):
        papers = [pi for pi in self.papers if not self.papers[pi].hasRead]
        return set(papers)
    
    def findGithub(self):
        papers = [pi for pi in self.papers if self.papers[pi].hasGithub]
        return set(papers)

    def findTitle(self, t_str, target_paper_ids=None, support_fuzzy=False):
        papers = set()
        if target_paper_ids is None:
            target_paper_ids = self._papers
        for pi in target_paper_ids:
            if self.similarity(t_str, self._papers[pi].title, support_fuzzy=support_fuzzy):
                papers.add(pi)
        return papers
    
    def findConference(self, c_str, support_fuzzy=False):
        conferences = []
        if c_str != OTHERS_CONFERENCE:
            for conference_name in self._conferences:
                if c_str == conference_name or conference_name in c_str :
                    conferences.append(self._conferences[conference_name])
                elif support_fuzzy and self.similarity(c_str, conference_name, support_fuzzy=support_fuzzy):
                    conferences.append(self._conferences[conference_name])
        return conferences
    
    def findItems(self, key_words, item_dict, support_fuzzy=False):
        items = []
        if key_words in item_dict:
            items.append(item_dict[key_words])
        if support_fuzzy:
            for item_str in item_dict:
                if key_words in item_dict: continue
                if self.similarity(key_words, item_str, support_fuzzy=support_fuzzy):
                    items.append(item_dict[item_str]) 
        return items
    
    def findAuthor(self, a_str, support_fuzzy=False):
        return self.findItems(a_str, self._authors, support_fuzzy=support_fuzzy)
    
    def findDataset(self, d_str, support_fuzzy=False):
        return self.findItems(d_str, self._datasets, support_fuzzy=support_fuzzy)
    
    def findTag(self, t_str, support_fuzzy=False):
        return self.findItems(t_str, self._tags, support_fuzzy=support_fuzzy)

    def findProject(self, p_str, support_fuzzy=False):
        return self.findItems(p_str, self._projects, support_fuzzy=support_fuzzy)

class LibraryGUI:

    def __init__(self):
        self.lib = Library()
        self.cur_paper = Paper()
        self.paper_to_tree = {}
        self.authorize_conference_list = []

        self.display_columns = ('Title', 'Conference', 'Year', 'Read', 'Rating')
        self.display_columns_values = lambda x: (x.title, x.conference, x.year, 1 if x.hasRead else 0, x.rating)

        # gui style
        self.display_column_width = {'Title':300, 'Conference':100, 'Year':50, 'Read':50, 'Rating':50}
        self.fontSize = 14
        self.textfontSize = 12
        self.headFontSize = 12
        self.cellWidth = 6

        # gui
        self.root = Tk()
        self.root.title("Cloud Paper Manager")
        self.root.resizable(width=False, height=False)

        self.main_frame = ttk.Frame(self.root)

        # filter

        self.labelCategoryInput = ttk.Label(self.main_frame, text='FilterBy:')
        categories = StringVar()
        self.filter_category = ttk.Combobox(self.main_frame, textvariable=categories, width=int(1.7*self.cellWidth))

        self.display_filter = Listbox(self.main_frame, width=int(1.7*self.cellWidth))  # lists of existing filters
        self.df_yscroll = ttk.Scrollbar(self.main_frame, command=self.display_filter.yview, orient=VERTICAL)
        self.display_filter.configure(yscrollcommand=self.df_yscroll.set)

        self.progress = ttk.Progressbar(self.main_frame, orient=HORIZONTAL, length=int(10*self.cellWidth), mode='determinate')

        # display paper
        self.display_papers = ttk.Treeview(self.main_frame)  # lists of existing papers
        self.dp_yscroll = ttk.Scrollbar(self.main_frame, command=self.display_papers.yview, orient=VERTICAL)
        self.display_papers.configure(yscrollcommand=self.dp_yscroll.set)

        # bibtex parser
        self.labelBibInput = ttk.Label(self.main_frame, text='Bibtex:')
        self.add_bib_input = Text(self.main_frame, height=5, width=4*self.cellWidth)
        self.add_bib_input.bind("<Tab>", self.focus_next_widget)
        self.bib_parser_button = ttk.Button(self.main_frame, command = self.parseBib, text = "Parse", width=int(0.8*self.cellWidth))

        self.labelTitleInput = ttk.Label(self.main_frame, text='Title:')
        self.add_title_input = ttk.Entry(self.main_frame, width=4*self.cellWidth)

        self.labelAuthorInput = ttk.Label(self.main_frame, text='Authors:')
        self.add_author_input = ttk.Entry(self.main_frame, width=4*self.cellWidth)

        self.labelConferenceInput = ttk.Label(self.main_frame, text='Conference:')
        conferences = StringVar()
        self.add_conference = ttk.Combobox(self.main_frame, textvariable=conferences, width=int(1.7*self.cellWidth))
        
        self.labelYearInput = ttk.Label(self.main_frame, text='Year:')
        self.spinval = StringVar()
        self.add_year_input = Spinbox(self.main_frame, from_=DEFAULT_YEAR, to=datetime.datetime.now().year, textvariable=self.spinval, width=self.cellWidth)

        self.labelPathInput = ttk.Label(self.main_frame, text='Path:')
        self.add_path_input = ttk.Entry(self.main_frame, width=3*self.cellWidth)

        self.path_button = ttk.Button(self.main_frame, command = self.browseFiles, text = "...", width=int(0.8*self.cellWidth))

        self.labelTagInput = ttk.Label(self.main_frame, text='Tags:')
        self.add_tag_input = ttk.Entry(self.main_frame, width=4*self.cellWidth)

        self.labelProjectInput = ttk.Label(self.main_frame, text='Projects:')
        self.add_project_input = ttk.Entry(self.main_frame, width=4*self.cellWidth)

        self.labelDatasetInput = ttk.Label(self.main_frame, text='Datasets:')
        self.add_dataset_input = ttk.Entry(self.main_frame, width=4*self.cellWidth)

        self.labelCommentInput = ttk.Label(self.main_frame, text='Comments:')
        self.add_comment_input = Text(self.main_frame, height=3, width=4*self.cellWidth)
        self.add_comment_input.bind("<Tab>", self.focus_next_widget)

        self.labelRatingInput = ttk.Label(self.main_frame, text='Rating:')
        self.r_spinval = StringVar()
        self.add_rating_input = Spinbox(self.main_frame, from_=0, to=MAX_RATING, textvariable=self.r_spinval,width=self.cellWidth)

        self.hasRead = BooleanVar()
        self.read_check = ttk.Checkbutton(self.main_frame, text='Read', variable=self.hasRead,
	    onvalue=True, offvalue=False, width=self.cellWidth)

        self.hasGithub = BooleanVar()
        self.github_check = ttk.Checkbutton(self.main_frame, text='Github', variable=self.hasGithub,
	    onvalue=True, offvalue=False, width=self.cellWidth)

        self.add_button = ttk.Button(self.main_frame, command = self.addPaper, text = "Add", width=int(0.8*self.cellWidth))
        self.del_button = ttk.Button(self.main_frame, command = self.delPaper, text = "Del", width=int(0.8*self.cellWidth))
        self.revise_button = ttk.Button(self.main_frame, command = self.revisePaper, text = "Edit", width=int(0.8*self.cellWidth))
        self.find_button = ttk.Button(self.main_frame, command = self.findPaper, text = "Find", width=int(0.8*self.cellWidth))

        self.reset_button = ttk.Button(self.main_frame, command = self.resetMode, text = "Reset", width=int(0.8*self.cellWidth))
        self.serialize_button = ttk.Button(self.main_frame, command = self.serialize, text = "Sync", width=int(0.8*self.cellWidth))

        self.reparse_button = ttk.Button(self.main_frame, command = self.reparse, text = "Renew", width=int(0.9*self.cellWidth))

    def focus_next_widget(self, event):
        event.widget.tk_focusNext().focus()
        return("break")

    def init(self):
        self.initLib()
        self.initConference(conference_file)
        self.initAddPage()
        self.initButtons()
        self.initStyle()
    
    def initStyle(self):
        # font
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=self.fontSize)

        text_font = tkfont.nametofont('TkTextFont')
        text_font.configure(size=self.fontSize)

        text_font = tkfont.nametofont('TkFixedFont')
        text_font.configure(size=self.textfontSize)

        text_font = tkfont.nametofont('TkHeadingFont')
        text_font.configure(size=self.headFontSize)
    
    def initLib(self):
        # load existing papers
        self.deserialize()
        for pi in self.lib.papers:
            self.displayPaper(pi)

    def initAddPage(self):
        # filter
        self.filter_dict = {'conference':self.lib.conferences, 'year':self.lib.years, 'author':self.lib.authors, 'dataset':self.lib.datasets, 'tag':self.lib.tags, 'project':self.lib.projects, 'rating':self.lib.ratings}
        self.filter_category['value'] = ['please select'] + list(self.filter_dict.keys()) + ['others']
        self.filter_category['state'] = "readonly"
        self.filter_category.current(0)
        self.filter_category.bind('<<ComboboxSelected>>', self.filterListingEvent)

        self.display_filter.bind("<<ListboxSelect>>", self.filteredPaperEvent)

        # display paper
        self.display_papers['columns'] = self.display_columns
        # self.display_papers.heading('#0', text='Title')
        # hide #0 column
        self.display_papers['show'] = 'headings'
        # sort column
        for col in self.display_columns:
            self.display_papers.heading(col, text=col, command=lambda _col=col: \
                     self.treeview_sort_column(self.display_papers, _col, False))
            self.display_papers.column(col, width=self.display_column_width[col], anchor='center')

        self.display_papers.bind("<<TreeviewSelect>>", self.selectPaperEvent)
        self.display_papers.bind("<Double-1>", self.openPaperEvent)

        # generate conference combobox
        self.add_conference['value'] = ['please select'] + self.authorize_conference_list
        self.add_conference['state'] = "readonly"
        self.add_conference.current(0)

    def treeview_sort_column(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(reverse=reverse)

        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # reverse sort next time
        tv.heading(col, command=lambda: \
                self.treeview_sort_column(tv, col, not reverse))
    
    def initButtons(self):
        # button logic
        # self.bib_parser_button
        # self.add_button
        # self.reset_button
        self.del_button.config(state=DISABLED)     # .config(state=NORMAL)
        # self.find_button
        self.revise_button.config(state=DISABLED) 
        self.serialize_button.config(state=DISABLED)
    
    def initConference(self, c_map_file):
        c_map = Conference.loadConference(c_map_file)
        for c_str in c_map:
            if c_map[c_str] in self.lib.conferences and c_map[c_str] != self.lib.conferences[c_map[c_str]].label :
                self.lib.conferences[c_map[c_str]].label = c_map[c_str]
            elif c_map[c_str] not in self.lib.conferences:
                self.lib.conferences[c_map[c_str]] = Conference(c_map[c_str])

            if c_str in self.lib.conferences and c_map[c_str] != self.lib.conferences[c_str].label :
                self.lib.conferences[c_str].label = c_map[c_str]
            elif c_str not in self.lib.conferences:
                self.lib.conferences[c_str] = self.lib.conferences[c_map[c_str]]

        if OTHERS_CONFERENCE not in self.lib.conferences:
            self.lib.conferences[OTHERS_CONFERENCE] = Conference(OTHERS_CONFERENCE)
        
        for c_str in self.lib.conferences:
            if c_str == self.lib.conferences[c_str].label:
                self.authorize_conference_list.append(c_str)
                self.lib.conferences[c_str].index = len(self.authorize_conference_list)

    # finish gui arrange
    def gui_arrang(self):
        padding = 10

        self.main_frame.grid()
        # filter
        self.labelCategoryInput.grid(row=0, column=0, padx=(padding,0), pady=(padding,0), sticky=E)
        self.filter_category.grid(row=1, column=0, columnspan=2, padx=(padding,0), sticky=(W,E))
        self.progress.grid(row=0, column=1, pady=(padding,0), sticky=(W,S,E))

        self.display_filter.grid(row=2, column=0, columnspan=2, rowspan=17, padx=(padding,0), pady=(0,padding), sticky=(N,W,E,S))
        self.df_yscroll.grid(row=2, column=2, rowspan=17, pady=(0,padding), sticky=(N,W,S))

        # display papers 19 columns, 13 rows

        self.display_papers.grid(row=0, column=3, columnspan=5, rowspan=19, pady=(padding,padding), sticky=(N,W,E,S))
        self.dp_yscroll.grid(row=0, column=8, rowspan=19, pady=(padding,padding), sticky=(N,W,S))

        # global buttons

        self.reset_button.grid(row=0,column=11)
        self.serialize_button.grid(row=0,column=12)
        self.reparse_button.grid(row=0, column=13, padx=(0, padding))

        # paper bib data

        self.labelBibInput.grid(row=1, column=9, sticky=E)
        self.add_bib_input.grid(row=1, column=10, columnspan=4, rowspan=5, padx=(0, padding), sticky=(W,E))
        self.bib_parser_button.grid(row=6, column=13, padx=(0, padding), sticky=(W,E))

        self.labelTitleInput.grid(row=7,column=9, sticky=E)
        self.add_title_input.grid(row=7,column=10, columnspan=4, padx=(0, padding), sticky=(W,E))

        self.labelAuthorInput.grid(row=8,column=9, sticky=E)
        self.add_author_input.grid(row=8,column=10, columnspan=4, padx=(0, padding), sticky=(W,E))

        self.labelConferenceInput.grid(row=9,column=9, sticky=E)
        self.add_conference.grid(row=9,column=10, columnspan=2, sticky=W)

        self.labelYearInput.grid(row=9,column=12, sticky=E)
        self.add_year_input.grid(row=9,column=13, padx=(0, padding), sticky=W)
        
        self.labelPathInput.grid(row=10,column=9, sticky=E)
        self.add_path_input.grid(row=10,column=10, columnspan=3, sticky=(W,E))
        self.path_button.grid(row=10, column=13, padx=(0, padding), sticky=(W,E))

        # paper optional data

        self.labelTagInput.grid(row=11,column=9, sticky=E)
        self.add_tag_input.grid(row=11,column=10, columnspan=4, padx=(0, padding), sticky=(W,E))

        self.labelProjectInput.grid(row=12,column=9, sticky=E)
        self.add_project_input.grid(row=12,column=10, columnspan=4, padx=(0, padding), sticky=(W,E))

        self.labelDatasetInput.grid(row=13,column=9, sticky=E)
        self.add_dataset_input.grid(row=13,column=10, columnspan=4, padx=(0, padding), sticky=(W,E))

        self.labelCommentInput.grid(row=14,column=9, sticky=(N,E))
        self.add_comment_input.grid(row=14,column=10, columnspan=4, rowspan=3, padx=(0, padding), sticky=(W,E))

        self.labelRatingInput.grid(row=17,column=9, sticky=E)
        self.add_rating_input.grid(row=17,column=10, sticky=W)

        self.read_check.grid(row=17,column=11, sticky=(W,E))
        self.github_check.grid(row=17,column=12, sticky=(W,E))

        self.add_button.grid(row=18,column=10, pady=(0, padding))
        self.revise_button.grid(row=18,column=11, pady=(0, padding))
        self.find_button.grid(row=18,column=12, pady=(0, padding))
        self.del_button.grid(row=18,column=13, padx=(0, padding), pady=(0, padding))
    
    def serialize(self):
        f = open(lib_file, 'wb')
        pickle.dump(self.lib, f)
        messagebox.showinfo(message='Save lib data success!')
        self.unserializeMode()
    
    def deserialize(self):
        if os.path.isfile(lib_file):
            f = open(lib_file, 'rb')
            self.lib = pickle.load(f)

    # main modes
    
    def selectMode(self, paper_id):
        self.cur_paper = self.lib.papers[paper_id]

        self.displayData(self.cur_paper)

        self.add_button.config(state=DISABLED)
        self.find_button.config(state=DISABLED)
        self.del_button.config(state=NORMAL)
        self.revise_button.config(state=NORMAL)
    
    def addMode(self):
        self.resetMode()
        self.serializeMode()
    
    def filterMode(self):
        self.clearBibData()
        self.clearOtherData()

        self.add_button.config(state=DISABLED)
        self.revise_button.config(state=DISABLED)
        self.del_button.config(state=DISABLED)
        self.find_button.config(state=NORMAL)
    
    def updateMode(self, paper_id):
        tree_id = self.paper_to_tree[paper_id]

        if paper_id in self.lib.papers:
            paper = self.lib.papers[paper_id]
            values = self.display_columns_values(paper)
            for i, col in enumerate(self.display_columns):
                self.display_papers.set(tree_id, column=col, value=values[i])
        else:
            self.display_papers.delete(tree_id)
            del self.paper_to_tree[paper_id]

        self.filterListing()
        self.serializeMode()
    
    def resetMode(self):
        # add page
        self.cur_paper = Paper()

        self.clearBibData()
        self.clearOtherData()

        self.clearDisplayPapers()
        for pi in self.lib.papers:
            self.displayPaper(pi)

        # present page
        self.filter_category.current(0)
        self.clearFilter()

        self.revise_button.config(state=DISABLED)
        self.del_button.config(state=DISABLED)
        self.find_button.config(state=NORMAL)
        self.add_button.config(state=NORMAL)
        self.bib_parser_button.config(state=NORMAL)
    
    def serializeMode(self):
        self.serialize_button.config(state=NORMAL)
    
    def unserializeMode(self):
        self.serialize_button.config(state=DISABLED)
        
    # add, delete, find and revise

    def addPaper(self):
        self.cur_paper = self.collectInputData()

        if self.cur_paper.checkState() == 1:
            messagebox.showinfo(message='Wrong path!')
            return
        elif self.cur_paper.checkState() == 2:
            messagebox.showinfo(message='Please input at least title, author, conference, year!')
            return

        # search the title and path
        paper_id = self.lib.searchDuplicatePaper(self.cur_paper)

        if paper_id < 0:
            self.lib.addPaper(self.cur_paper)
            self.displayPaper(self.cur_paper.id)
            self.addMode()
        elif messagebox.askokcancel("Repeated File Error!","Do you want to browse the other file?") :
            self.display_papers.selection_set(self.paper_to_tree[paper_id])
            self.selectMode(paper_id)

    def delPaper(self):
        paper_id = self.cur_paper.id
        self.lib.removePaper(paper_id)
        self.updateMode(paper_id)
        self.addMode()
    
    def findPaper(self):
        self.cur_paper = Paper()
        self.cur_paper = self.collectInputData()

        paper_ids = self.lib.findPaper(self.cur_paper, target_paper_ids=self.paper_to_tree, support_fuzzy=True, fuzzy_window=2)

        if len(paper_ids) < 1:
            messagebox.showinfo(message='Find nothing!')
            return

        self.clearDisplayPapers()
        for pi in paper_ids:
            self.displayPaper(pi)
    
    def revisePaper(self):
        target_paper_id = self.cur_paper.id

        self.cur_paper = self.collectInputData()

        if self.cur_paper.checkState() == 1:
            messagebox.showinfo(message='Wrong path!')
            return
        elif self.cur_paper.checkState() == 2:
            messagebox.showinfo(message='Please input at least title, author, conference, year!')
            return

        self.lib.revisePaper(target_paper_id, self.cur_paper)
        
        messagebox.showinfo(message='Revise paper data success!')
        self.selectMode(target_paper_id)
        self.updateMode(target_paper_id)
    
    def parseBib(self):
        bib_str = self.add_bib_input.get(1.0, END).strip()
        b = bibParser.parse(bib_str, self.lib)
        self.displayBibData(b)

    def reparse(self):
        if messagebox.askokcancel("ReNewal","Do you want to re-Parse bibtex for all papers?") :
            for paper_id in self.lib.papers:
                paper = self.lib.papers[paper_id]
                if len(paper.bib.bibtex) > 0 :
                    b = bibParser.parse(paper.bib.bibtex, self.lib)
                    self.lib.revisePaperBib(paper_id, b)

            self.addMode()
            messagebox.showinfo(message="Reparse each paper's bibtex success!")
    
    def browseFiles(self):
        # Ask the user to select a single file name.
        full_path = filedialog.askopenfilename(parent=self.root,
                                    initialdir=os.getcwd(),
                                    title="Please select a file:",
                                    filetypes=my_filetypes)
        if len(full_path) > 0:
            path = os.path.relpath(full_path)
            self.add_path_input.delete(0, 'end')
            self.add_path_input.insert(0, path)
            self.openPaper(full_path)
    
    # event

    def filterListingEvent(self, event):
        self.filterListing()

    def filterListing(self):
        self.clearFilter()
        filter_name = self.filter_category.get()
        
        if filter_name in self.filter_dict:
            filters = self.filter_dict[filter_name]
            if filter_name == 'year' or filter_name == 'rating':
                for f in filters:
                    self.display_filter.insert(END, f)
            elif filter_name == 'conference':
                for f in filters:
                    if f == filters[f].label:
                        self.display_filter.insert(END, f)
            else:
                for f in filters:
                    self.display_filter.insert(END, f)
        elif filter_name == 'others':
            self.display_filter.insert(END, 'UnRead')
            self.display_filter.insert(END, 'hasGithub')
        else: self.resetMode()

    def selectItem(self, paper_tree):
        curItem = paper_tree.focus()
        return paper_tree.item(curItem)['text']
    
    def setProgress(self, cur_value, max_value):
        self.progress["maximum"] = max_value
        self.progress["value"] = cur_value
    
    def filteredPaperEvent(self, event):
        self.filteredPaper()

    def filteredPaper(self):
        idx = self.display_filter.curselection()
        if idx is not None and len(idx) > 0:
            self.clearDisplayPapers()
            item = self.display_filter.get(idx)
            
            filter_name = self.filter_category.get()

            paper_ids = set()
            if filter_name in self.filter_dict:
                if filter_name == 'year':
                    paper_ids = self.lib.years[item]
                elif filter_name == 'rating':
                    paper_ids = self.lib.ratings[item]
                elif filter_name == 'conference':
                    paper_ids = self.lib.conferences[item].papers
                elif filter_name == 'author':
                    paper_ids = self.lib.authors[item].papers
                elif filter_name == 'tag':
                    paper_ids = self.lib.tags[item].papers
                elif filter_name == 'dataset':
                    paper_ids = self.lib.datasets[item].papers
                elif filter_name == 'project':
                    paper_ids = self.lib.projects[item].papers
            elif filter_name == 'others':
                if item == 'UnRead':
                    paper_ids = self.lib.findUnread()
                else:
                    paper_ids = self.lib.findGithub()

            for pi in paper_ids:
                self.displayPaper(pi)

            # show progress
            total_num = len(paper_ids)
            if total_num > 0:
                unread_num = len( paper_ids & self.lib.findUnread())
                self.setProgress(total_num-unread_num, total_num)
            self.filterMode()

    def selectPaperEvent(self, event):
        paper_id = self.selectItem(self.display_papers)
        self.selectMode(paper_id)
        return True

    def openPaperEvent(self, event):
        selected = self.selectPaperEvent(event)
        if selected:
            path = self.cur_paper.full_path
            self.openPaper(path)

    def openPaper(self, path):
        # os.system("open "+tmp_paper.full_path)
        full_path = os.path.abspath(path)
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', full_path))
        elif os.name == 'nt': # For Windows
            os.startfile(full_path)
        elif os.name == 'posix': # For Linux, Mac, etc.
            subprocess.call(('xdg-open', full_path))
    
    # collect data
    def collectInputData(self):
        # get info for cur paper
        tmp_paper = Paper()
        tmp_paper = self.collectBibData(tmp_paper)
        tmp_paper = self.collectOtherData(tmp_paper)
        return tmp_paper
    
    def collectBibData(self, paper):
        paper.bibtex = self.add_bib_input.get(1.0, END).strip()
        paper.type = bibParser.typeParser(paper.bibtex)
        paper.title = self.add_title_input.get().strip()
        paper.year = self.add_year_input.get()

        paper.conference = self.lib.parseConference(self.add_conference.get())
        paper.author = self.lib.parseAuthors(self.add_author_input.get())
        return paper
    
    def collectOtherData(self, paper):
        paper.tag = self.lib.parseTags(self.add_tag_input.get().strip())
        paper.project = self.lib.parseProjects(self.add_project_input.get().strip())
        paper.dataset = self.lib.parseDatasets(self.add_dataset_input.get().strip())

        paper.comment = self.add_comment_input.get(1.0, END).strip()

        paper.rating = self.add_rating_input.get()

        paper.path = self.add_path_input.get().strip()

        paper.hasRead = self.hasRead.get()
        paper.hasGithub = self.hasGithub.get()
        return paper
    
    # display data
    
    def displayPaper(self, paper_id):
        tmp_paper = self.lib.papers[paper_id]
        tree_id = self.display_papers.insert('', 'end', text=paper_id, values=self.display_columns_values(tmp_paper))
        self.paper_to_tree[paper_id] = tree_id
        return tree_id

    def displayData(self, paper):
        self.displayBibData(paper.bib)
        self.displayOtherData(paper)
    
    def displayBibData(self, bib):
        self.clearBibData()
        
        self.add_bib_input.insert(1.0, bib.bibtex)
        self.add_title_input.insert(0, bib.title)
        self.add_author_input.insert(0, Author.guiString(bib.author))
        self.add_conference.current(bib.conference.index)
        self.spinval.set(bib.year)

    def displayOtherData(self, paper):
        self.clearOtherData()

        self.add_path_input.insert(0, paper.path)
        self.add_tag_input.insert(0, paper.tag)
        self.add_project_input.insert(0, paper.project)
        self.add_dataset_input.insert(0, paper.dataset)
        self.add_comment_input.insert(1.0, paper.comment)
        self.r_spinval.set(paper._rating)
        self.hasRead.set(paper.hasRead)
        self.hasGithub.set(paper.hasGithub)
    
    # clear data
    
    def clearDisplayPapers(self):
        self.paper_to_tree.clear()
        self.display_papers.delete(*self.display_papers.get_children())

    def clearFilter(self):
        self.display_filter.delete(0, END)
        self.setProgress(0,1)

    def clearBibData(self):
        self.add_bib_input.delete(1.0, END)
        self.add_title_input.delete(0, 'end')
        self.add_author_input.delete(0, 'end')
        self.add_conference.current(0)
        self.spinval.set(DEFAULT_YEAR)
    
    def clearOtherData(self):
        self.add_path_input.delete(0, 'end')
        self.add_tag_input.delete(0, 'end')
        self.add_project_input.delete(0, 'end')
        self.add_dataset_input.delete(0, 'end')
        self.add_comment_input.delete(1.0, END)
        self.r_spinval.set(0)

        self.hasGithub.set(False)
        self.hasRead.set(False)


def main():
    # instantiation
    lg = LibraryGUI()
    lg.init()
    lg.gui_arrang()
    # main program
    lg.root.mainloop()
    pass


if __name__ == "__main__":
    main()
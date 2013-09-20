#-*- coding: utf-8 -*-

#+---------------------------------------------------------------------------+
#|          01001110 01100101 01110100 01111010 01101111 01100010            |
#|                                                                           |
#|               Netzob : Inferring communication protocols                  |
#+---------------------------------------------------------------------------+
#| Copyright (C) 2011 Georges Bossert and Frédéric Guihéry                   |
#| This program is free software: you can redistribute it and/or modify      |
#| it under the terms of the GNU General Public License as published by      |
#| the Free Software Foundation, either version 3 of the License, or         |
#| (at your option) any later version.                                       |
#|                                                                           |
#| This program is distributed in the hope that it will be useful,           |
#| but WITHOUT ANY WARRANTY; without even the implied warranty of            |
#| MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the              |
#| GNU General Public License for more details.                              |
#|                                                                           |
#| You should have received a copy of the GNU General Public License         |
#| along with this program. If not, see <http://www.gnu.org/licenses/>.      |
#+---------------------------------------------------------------------------+
#| @url      : http://www.netzob.org                                         |
#| @contact  : contact@netzob.org                                            |
#| @sponsors : Amossys, http://www.amossys.fr                                |
#|             Supélec, http://www.rennes.supelec.fr/ren/rd/cidre/           |
#+---------------------------------------------------------------------------+

#+---------------------------------------------------------------------------+
#| File contributors :                                                       |
#|       - Georges Bossert <georges.bossert (a) supelec.fr>                  |
#|       - Frédéric Guihéry <frederic.guihery (a) amossys.fr>                |
#+---------------------------------------------------------------------------+

#+---------------------------------------------------------------------------+
#| Standard library imports                                                  |
#+---------------------------------------------------------------------------+
import itertools
from bitarray import bitarray

#+---------------------------------------------------------------------------+
#| Related third party imports                                               |
#+---------------------------------------------------------------------------+

#+---------------------------------------------------------------------------+
#| Local application imports                                                 |
#+---------------------------------------------------------------------------+
from netzob.Common.Utils.Decorators import NetzobLogger, typeCheck
from netzob.Common.Models.Vocabulary.Messages.AbstractMessage import AbstractMessage
from netzob.Common.Models.Types.AbstractType import AbstractType
from netzob.Common.Models.Types.TypeConverter import TypeConverter
from netzob.Common.Models.Types.Raw import Raw
from netzob.Common.Models.Types.BitArray import BitArray
from netzob.Inference.Vocabulary.Search.SearchTask import SearchTask
from netzob.Inference.Vocabulary.Search.SearchResult import SearchResult, SearchResults
from netzob.Common.Models.Vocabulary.Functions.VisualizationFunctions.HighlightFunction import HighlightFunction


@NetzobLogger
class SearchEngine(object):
    """This search engine is the entry point for the API of all
    the search processes. It allows to search for any type of data in messages using
    specific transformations to support the identification of hidden data.


    >>> from netzob.all import *
    >>> m = RawMessage("Netzob is a tool that helps experts in their reverse engineering processes.")
    >>> searchResults = SearchEngine.searchInMessage("expert", m)
    >>> print searchResults
    1 occurence(s) found.
    >>> print m
    %2dNetzob%2d is a tool that helps experts in their reverse engineering processes.
    >>> m.clearSearchResults()
    >>> print m
    Netzob is a tool that helps experts in their reverse engineering processes.

    """

    def __init__(self):
        pass

    @staticmethod
    def searchInMessage(data, message, addTags=True):
        """Search in the specified data the given data. This data will be searched as
        it but also under various format.

        :parameter data: the data to search after. This data must be provided with its netzob type.
        :type data: an :class:`object`.
        :parameter message: the message in which the search will take place
        :type message: :class:`netzob.Common.Models.Vocabulary.Messages.AbstractMessage`
        :keyword addTags: if set to True, visualization functions are added to the message to highlights found results.
        :type addTags: :class:`bool`
        :return: a search results detailling where and how occurrences where found. Occurences are also
        identified in the message through dedicated visualization functions automaticaly added to the message.
        :rtype: :class:`netzob.Inference.Vocabulary.SearchEngine.SearchResults.SearchResults`

        """
        searchEngine = SearchEngine()
        return searchEngine.searchDataInMessage(data, message, addTags)

    @typeCheck(object, AbstractMessage, bool, bool)
    def searchDataInMessage(self, data, message, addTags):
        """Search in the specified data the given data. This data will be searched as
        it but also under various format.

        :parameter data: the data to search after. This data must be provided with its netzob type.
        :type data: an :class:`object`.
        :parameter message: the message in which the search will take place
        :type message: :class:`netzob.Common.Models.Vocabulary.Messages.AbstractMessage`
        :keyword addTags: if set to True, visualization functions are added to the message to highlights found results.
        :type addTags: :class:`bool`
        :return: a search results detailling where and how occurrences where found. Occurences are also
        identified in the message through dedicated visualization functions automaticaly added to the message.
        :rtype: :class:`netzob.Inference.Vocabulary.SearchEngine.SearchResults.SearchResults`

        """

        if data is None:
            raise TypeError("Data cannot be None")

        if message is None:
            raise TypeError("Message cannot be None")

        # normalize the given data
        normedData = AbstractType.normalize(data)

        # build search tasks
        searchTasks = self.buildSearchTasks(normedData)

        # fetch the content of the message and convert it to bitarray
        target = TypeConverter.convert(message.data, Raw, BitArray)

        # Generate search cases
        searchCases = itertools.product([target], searchTasks)

        searchResults = self.__search(searchCases)

        # If requested, we tag the results in the message using visualization functions
        if addTags:
            for searchResult in searchResults:
                for (startPos, endPos) in searchResult.ranges:
                    message.visualizationFunctions.append(HighlightFunction(startPos, endPos))
        return searchResults

    def __search(self, searchCases):
        """Execute the different search cases and build
        search results that will be returned.

        :parameter searchCases: an iterable of tupple (bitarray, :class:`netzob.Inference.Vocabulary.Search.SearchTask.SearchTask`)
        :type searchCases: a list
        :return: the obtained results
        :rtype: a list of :class:`netzob.Inference.Vocabulary.Search.SearchResult.SearchResult`

        """
        if searchCases is None:
            raise TypeError("There should be at least one search case.")

        results = SearchResults()
        for (target, searchTask) in searchCases:
            if target is None or not isinstance(target, bitarray) or searchTask is None or not isinstance(searchTask, SearchTask):
                raise TypeError("Each search case must a tupple made of a bitarray and a SearchTask instance")

            ranges = []
            for startIndex in target.search(searchTask.data):
                ranges.append((startIndex, startIndex + len(searchTask.data)))

            if len(ranges) > 0:
                results.append(SearchResult(target, searchTask, ranges))

        return results

    @typeCheck(AbstractType)
    def buildSearchTasks(self, data):
        """Builds a search tasks for each possible encoding mutations of the
        specified data.

        :parameter data: the data from wich it must create search tasks
        :type data: :class:`netzob.Common.Models.Types.AbstractType.AbstractType`
        :return: a list of search tasks
        :rtype: a :class:`list` of :class:`netzob.Inference.Vocabulary.SearchEngine.SearchTask.SearchTask`
        """
        if data is None:
            raise TypeError("The data cannot be None")

        return [SearchTask(mutation, mutationType) for mutationType, mutation in data.mutate().iteritems()]



#     def searchContextInMessage(self, message):
#         """searchContextInMessage:
#         Search for any context relative information
#         in provided message. It includes applicative data,
#         parameters and environmental data"""
#         if message is None:
#             self.log.warning("No message provided")
#             return []
#         results = []
#         results.extend(self.searchApplicativeDataInMessage(message))
#         results.extend(self.searchEnvironmentDataInMessage(message))

#         return results

#     def searchEnvironmentDataInMessage(self, message):
#         """searchEnvironmentDataInMessage:
#         Search on the provided message every environment data stored in
#         the message"""
#         tasks = []
#         for prop in message.getProperties():
#             if prop.getName() != "Data" and prop.getFormat() != "decimal":
#                 tasks.extend(self.createSearchTasksForData(str(prop.getCurrentValue()), prop.getFormat()))
#         if len(tasks) == 0:
#             self.log.warning("Nothing to search after")
#             return []

#         newTasks = self.searchInMessage(tasks, message)

#         results = []
#         for task in newTasks:
#             if len(task.getResults()) > 0:
#                 for r in task.getResults():
#                     r.setDescription(task.getDescription())
#                 results.extend(task.getResults())
#         return results

#     def createSearchTasksForData(self, dataValue, dataType):
#         """createSearchTasksForData:
#         This methods creates search tasks given the value and its format.
#         @returns a list of L{netzob.Inference.Vocabulary.SearchTask}"""
#         tasks = []
#         if dataType == Format.STRING:
#             tasks.extend(self.getSearchedDataForString(dataValue))
#         elif dataType == Format.DECIMAL:
#             tasks.extend(self.getSearchedDataForDecimal(dataValue))
#         elif dataType == Format.IP:
#             tasks.extend(self.getSearchedDataForIP(dataValue))
#         elif dataType == Format.HEX:
#             tasks.extend(self.getSearchedDataForHexadecimal(dataValue))
#         else:
#             self.log.warning("Type data {0} cannot be used in a search.".format(dataType))
#         return tasks

#     def searchApplicativeDataInMessage(self, message):
#         """searchApplicativeDataInMessage:
#         Search for any applicative data attached to the current project
#         in the provided message.
#         """
#         if message is None:
#             self.log.warning("No message provided")
#             return []

#         applicativeData = message.getSession().getApplicativeData()

#         # Create search tasks
#         tasks = []
#         for appData in applicativeData:
#             tasks.extend(self.createSearchTasksForData(appData.getValue(), appData.getType()))

#         if len(tasks) == 0:
#             self.log.warning("Nothing to search after")
#             return []

#         newTasks = self.searchInMessage(tasks, message)
#         results = []
#         for task in newTasks:
#             if len(task.getResults()) > 0:
#                 for r in task.getResults():
#                     r.setDescription(task.getDescription())
#                 results.extend(task.getResults())
#         return results

#     #+----------------------------------------------
#     #| getSearchedDataForBinary:
#     #|   Generates data which can represent the specified Binary
#     #| @param value the value to search for
#     #+----------------------------------------------
#     def getSearchedDataForBinary(self, value):
#         return []

#     #+----------------------------------------------
#     #| getSearchedDataForOctal:
#     #|   Generates data which can represent the specified Octal
#     #| @param value the value to search for
#     #+----------------------------------------------
#     def getSearchedDataForOctal(self, value):
#         return []

#     #+----------------------------------------------
#     #| getSearchedDataForDecimal:
#     #|   Generates data which can represent the specified Decimal
#     #| @param value the value to search for
#     #+----------------------------------------------
#     def getSearchedDataForDecimal(self, value):
#         if not value.isdigit():
#             return []
#         # Creation of a SearchTask
#         task = SearchTask(value, value, Format.DECIMAL)
#         task.registerVariation(TypeConvertor.decimalToNetzobRaw(value), "Decimal representation of '{0}'".format(TypeConvertor.decimalToNetzobRaw(value)))
#         task.registerVariation(TypeConvertor.decimalToNetzobRaw(value[::-1]), "Inverted decimal representation of '{0}'".format(TypeConvertor.decimalToNetzobRaw(value[::-1])))
#         return [task]

#     #+----------------------------------------------
#     #| getSearchedDataForHexadecimal:
#     #|   Generates data which can represent the specified Hexa
#     #| @param value the value to search for
#     #+----------------------------------------------
#     def getSearchedDataForHexadecimal(self, value, extraInfo=None):
#         typeIdentifier = TypeIdentifier()
#         if not typeIdentifier.isHexString(value):
#             return []
#         # Creation of a SearchTask
#         task = SearchTask(value, value, Format.HEX)
#         task.registerVariation(value, "Hex repr of '{0}'({1}))".format(value, extraInfo))
#         #        task.registerVariation(value[::-1], "Inverted representation of '{0}'".format(value[::-1]))
#         return [task]

#     #+----------------------------------------------
#     #| getSearchedDataForString:
#     #|   Generates data which can represent the specified string
#     #| @param value the value to search for
#     #+----------------------------------------------
#     def getSearchedDataForString(self, value):
#         # Creation of a SearchTask
#         task = SearchTask(value, value, Format.STRING)

#         stringMutations = dict()
#         stringMutations["original string"] = value
#         stringMutations["Inverted string"] = value[::-1]
#         stringMutations["Upper Original string"] = string.upper(value)
#         stringMutations["Lower Original string"] = string.lower(value)

#         for mutationDescription, mutation in stringMutations.items():
#             try:
#                 task.registerVariation(TypeConvertor.stringToNetzobRaw(mutation), "{0} ({1})".format(mutationDescription, mutation))
#             except:
#                 pass
#             try:
#                 task.registerVariation(TypeConvertor.stringToNetzobRaw(mutation.encode('utf-8')), "UTF-8 of '{0}' ({1})".format(mutationDescription, mutation))
#             except:
#                 pass
#             try:
#                 task.registerVariation(TypeConvertor.stringToNetzobRaw(mutation.encode('utf-16le')), "UTF-16 LE '{0}' ({1})".format(mutationDescription, mutation))
#             except:
#                 pass
#             try:
#                 task.registerVariation(TypeConvertor.stringToNetzobRaw(mutation.encode('utf-16be')), "UTF-16 BE '{0}' ({1})".format(mutationDescription, mutation))
#             except:
#                 pass

#         return [task]

#     #+----------------------------------------------
#     #| getSearchedDataForIP:
#     #|   Generates data which can represent the specified IP
#     #| @param value the value to search for
#     #+----------------------------------------------
#     def getSearchedDataForIP(self, value):
#         tasks = []

#         ipPattern = "^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
#         # first verify its a ip format
#         if not re.match(ipPattern, value):
#             return tasks

#         # parse the value to get a, b, c and d
#         ipTab = value.split('.')
#         a = ipTab[0]
#         b = ipTab[1]
#         c = ipTab[2]
#         d = ipTab[3]

#         a2 = a
#         if a2 < 100:
#             a2 = "0" + a2
#         if a2 < 10:
#             a2 = "0" + a2
#         b2 = b
#         if b2 < 100:
#             b2 = "0" + b2
#         if b2 < 10:
#             b2 = "0" + b2
#         c2 = c
#         if c2 < 100:
#             c2 = "0" + c2
#         if c2 < 10:
#             c2 = "0" + c2
#         d2 = d
#         if d2 < 100:
#             d2 = "0" + d2
#         if d2 < 10:
#             d2 = "0" + d2

# #        # in String :
# #        # - 192.168.0.10
# #        val = "%s.%s.%s.%s" % (a, b, c, d)
# #        tasks.extend(self.getSearchedDataForString(val))
# #
# #        # - 192.168.000.010
# #        val = "%s.%s.%s.%s" % (a2, b2, c2, d2)
# #        tasks.extend(self.getSearchedDataForString(val))
# #
# #        # - 192168000010
# #        val = "%s%s%s%s" % (a2, b2, c2, d2)
# #        tasks.extend(self.getSearchedDataForString(val))
# #
# #        # - 10.0.168.192
# #        val = "%s.%s.%s.%s" % (d, c, b, a)
# #        tasks.extend(self.getSearchedDataForString(val))
# #
# #        # - 000.010.192.168
# #        val = "%s.%s.%s.%s" % (d2, c2, b2, a2)
# #        tasks.extend(self.getSearchedDataForString(val))
# #
# #        # - 0.10.192.168
# #        val = "%s.%s.%s.%s" % (c, d, a, b)
# #        tasks.extend(self.getSearchedDataForString(val))
# #
# #        # - 000.010.192.168
# #        val = "%s.%s.%s.%s" % (c2, d2, a2, b2)
# #        tasks.extend(self.getSearchedDataForString(val))
# #
# #        # - 000010192168
# #        val = "%s%s%s%s" % (c2, d2, a2, b2)
# #        tasks.extend(self.getSearchedDataForString(val))

#         #in hexadecimal
#         ah = hex(int(a))[2:]
#         ah = ((2 - len(ah)) * '0') + ah

#         bh = hex(int(b))[2:]
#         bh = ((2 - len(bh)) * '0') + bh

#         ch = hex(int(c))[2:]
#         ch = ((2 - len(ch)) * '0') + ch

#         dh = hex(int(d))[2:]
#         dh = ((2 - len(dh)) * '0') + dh

#         val = "{0}{1}{2}{3}".format(ah, bh, ch, dh)
#         tasks.extend(self.getSearchedDataForHexadecimal(val, value))

#         return tasks

#     #+----------------------------------------------
#     #| search:
#     #|   Search a set of specified data in all the project
#     #| @param tasks the set of "search" task
#     #+----------------------------------------------
#     def search(self, tasks):

#         symbols = self.project.getVocabulary().getSymbols()

#         # compute the step for status notification
#         try:
#             step = 100.0 / (len(symbols) * len(tasks))
#         except ZeroDivisionError:
#             step = 100
#         status = 0.0

#         for task in tasks:
#             if self.status_cb is not None and int(status % 2) == 0:
#                     self.status_cb(float(status / 100.0), None)
#             for symbol in symbols:
#                 for message in symbol.getMessages():
#                     variations = task.getVariations()
#                     for variation_value in variations.keys():
#                         task.registerResults(self.extendedSearch(variation_value, message), variations[variation_value])
#                 status += step

#         return tasks

#     #+----------------------------------------------
#     #| searchInSymbol:
#     #|   Search a set of specified data in a the specified symbol
#     #| @param tasks the set of "search" task
#     #| @param symbol the symbol to search in
#     #+----------------------------------------------
#     def searchInSymbol(self, tasks, symbol):
#         for task in tasks:
#             for message in symbol.getMessages():
#                 variations = task.getVariations()
#                 for variation_value in variations.keys():
#                     task.registerResults(self.extendedSearch(variation_value, message), variations[variation_value])
#         return tasks

#     #+----------------------------------------------
#     #| searchInMessage:
#     #|   Search a set of specified data in a the specified message
#     #| @param tasks the set of "search" task
#     #| @param message the message to search in
#     #+----------------------------------------------
#     def searchInMessage(self, tasks, message):
#         for task in tasks:
#             variations = task.getVariations()
#             for variation_value in variations.keys():
#                 task.registerResults(self.extendedSearch(variation_value, message), variations[variation_value])
#         return tasks

#     #+----------------------------------------------
#     #| extendedSearch:
#     #|   Search for a data in a specified message
#     #+----------------------------------------------
#     def extendedSearch(self, data, message):
#         results = []
#         results.extend(self.naturalSearch(data, message))
# #        results.extend(self.inversedSearch(data, message))
# #        results.extend(self.semiInvertedOnNaturalSearch(data, message))
# #        results.extend(self.semiInvertedOnInvertedSearch(data, message))
#         return results

#     def naturalSearch(self, data, message):
#         results = []
#         # Search naturally all the possible places of data in message
#         indice = 0
#         messageData = message.getStringData()
#         indice = messageData.find(data, 0)
#         while indice >= 0:
#             searchResult = SearchResult(message, "Natural search")
#             searchResult.addSegment(indice, indice + len(data))
#             results.append(searchResult)
#             indice = messageData.find(data, indice + 1)

#         return results

#     def inversedSearch(self, data, message):
#         results = []
#         invData = data[::-1]

#         # Search naturally all the possible places of data in message
#         indice = 0
#         while indice + len(invData) <= len(message.getStringData()):
#             if message.getStringData()[indice:len(invData) + indice] == invData:
#                 # We have a match
#                 searchResult = SearchResult(message, "Inverted search")
#                 searchResult.addSegment(indice, len(invData))
#                 results.append(searchResult)
#             indice = indice + 1

#         return results

#     def semiInvertedOnNaturalSearch(self, data, message):
#         results = []
#         invData = ""
#         for i in range(0, len(data), 2):
#             if len(data) > i + 1:
#                 invData = invData + data[i + 1]
#             invData = invData + data[i]

#         if len(data) % 2 == 1:
#             invData = invData + data[-1]

#         # Search naturally all the possible places of data in message
#         indice = 0
#         while indice + len(invData) <= len(message.getStringData()):
#             if message.getStringData()[indice:len(invData) + indice] == invData:
#                 # We have a match
#                 searchResult = SearchResult(message, "4bytes inverted on natural search")
#                 searchResult.addSegment(indice, len(invData))
#                 results.append(searchResult)
#             indice = indice + 1

#         return results

#     def semiInvertedOnInvertedSearch(self, data, message):

#         results = []
#         tmpData = data[::-1]
#         invData = ""
#         for i in range(0, len(tmpData), 2):
#             if len(data) > i + 1:
#                 invData = invData + tmpData[i + 1]
#             invData = invData + tmpData[i]

#         if len(tmpData) % 2 == 1:
#             invData = invData + tmpData[-1]

#         # Search naturally all the possible places of data in message
#         indice = 0
#         while indice + len(invData) <= len(message.getStringData()):
#             if message.getStringData()[indice:len(invData) + indice] == invData:
#                 # We have a match
#                 searchResult = SearchResult(message, "4bytes inverted on inverted search")
#                 searchResult.addSegment(indice, len(invData))
#                 results.append(searchResult)
#             indice = indice + 1

#         return results
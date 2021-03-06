# Copyright (c) 2017 NL-ix
#               2006 Mehdi Abaakouk
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import socket
import sys

BUFSIZE = 4096

SUCCESS_CODES = {
    "0000": "OK",
    "0001": "Welcome",
    "0002": "Reading configuration",
    "0003": "Reconfigured",
    "0004": "Reconfiguration in progress",
    "0005": "Reconfiguration already in progress, queueing",
    "0006": "Reconfiguration ignored, shutting down",
    "0007": "Shutdown ordered",
    "0008": "Already disabled",
    "0009": "Disabled",
    "0010": "Already enabled",
    "0011": "Enabled",
    "0012": "Restarted",
    "0013": "Status report",
    "0014": "Route count",
    "0015": "Reloading",
    "0016": "Access restricted",
    "0017": "Reconfiguration already in progress, removing queued config",
    "0018": "Reconfiguration confirmed",
    "0019": "Nothing to do (configure undo/confirm)",
    "0020": "Configuration OK",
    "0021": "Undo requested",
    "0022": "Undo scheduled",
    "0023": "Evaluation of expression",
    "0024": "Graceful restart status report"
}

TABLES_ENTRY_CODES = {
    "1000": "BIRD version",
    "1001": "Interface list",
    "1002": "Protocol list",
    "1003": "Interface address",
    "1004": "Interface flags",
    "1005": "Interface summary",
    "1006": "Protocol details",
    "1007": "Route list",
    "1008": "Route details",
    "1009": "Static route list",
    "1010": "Symbol list",
    "1011": "Uptime",
    "1012": "Route extended attribute list",
    "1013": "Show ospf neighbors",
    "1014": "Show ospf",
    "1015": "Show ospf interface",
    "1016": "Show ospf state/topology",
    "1017": "Show ospf lsadb",
    "1018": "Show memory",
}

ERROR_CODES = {
    "8000": "Reply too long",
    "8001": "Route not found",
    "8002": "Configuration file error",
    "8003": "No protocols match",
    "8004": "Stopped due to reconfiguration",
    "8005": "Protocol is down => cannot dump",
    "8006": "Reload failed",
    "8007": "Access denied",

    "9000": "Command too long",
    "9001": "Parse error",
    "9002": "Invalid symbol type",
}

END_CODES = ERROR_CODES.keys() + SUCCESS_CODES.keys()


class BirdSocket:

    def __init__(self, host="", port="", file=""):
        self.__file = file
        self.__host = host
        self.__port = port
        self.__sock = None

    def __connect(self):
        if self.__sock:
            return

        if not file:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__sock.settimeout(3.0)
            self.__sock.connect((self.__host, self.__port))
        else:
            self.__sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.__sock.settimeout(3.0)
            self.__sock.connect(self.__file)

        self.__sock.recv(1024)
        # self.cmd("restrict")

    def close(self):
        if self.__sock:
            try:
                self.__sock.close()
            except:
                pass
            self.__sock = None

    def cmd(self, cmd, allow_empty_lines=False):
        try:
            self.__connect()
            self.__sock.send(cmd + "\n")
            data = self.__read(allow_empty_lines=allow_empty_lines)
            return data
        except socket.error:
            why = sys.exc_info()[1]
            self.close()
            return False, "Bird connection problem: %s" % why

    def __read(self, allow_empty_lines=False):
        code = "7000"  # Not used in bird
        outcome = True
        parsed_string = ""
        lastline = ""

        while code not in END_CODES:
            data = self.__sock.recv(BUFSIZE)

            lines = (lastline + data).split("\n")
            if len(data) == BUFSIZE:
                lastline = lines[-1]
                lines = lines[:-1]

            for line in filter(lambda x: x.strip() or
                               allow_empty_lines, lines):
                code = line[0:4]

                # if empty lines are allowed the last line will be an empty
                # line. we need to check this to flag the end of reading data
                # and return
                # note that code should not be stripped; intermediary empty
                # lines will consist of a single space
                if allow_empty_lines and len(code) == 0:
                    return outcome, parsed_string

                if code == "0000":
                    outcome = True
                elif code in SUCCESS_CODES:
                    outcome = True
                    parsed_string += "{}\n".format(line[5:])
                elif code in ERROR_CODES:
                    outcome = False
                    parsed_string += "{}: {}\n".format(ERROR_CODES.get(code),
                                                       line[5:])
                    return outcome, parsed_string
                elif code[0] in ["1", "2"]:
                    parsed_string += line[5:] + "\n"
                elif code[0] == " ":
                    parsed_string += line[1:] + "\n"
                elif code[0] == "+":
                    parsed_string += line[1:]
                else:
                    parsed_string += "<<<unparsable_string(%s)>>>\n" % line

        return outcome, parsed_string

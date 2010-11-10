__version__ = '$Rev: 1784 $'

from logging.handlers import SysLogHandler
try:
	import codecs
except ImportError:
	codecs = None
import types

def hexdump(s):
	"""
	Dump any string (unicode or not) to formatted hex output.

	Simple routine for dumping any type of string (ascii/encoded/unicode) to
	a standard hexadecimal dump.

	Based on UnicodeHexDump.py by Jack Trainor.
	Ref: http://code.activestate.com/recipes/572181-unicode-string-hex-dump/
	"""
	printable_filter = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
	if type(s) == types.StringType:
		char_format = "%02x"
		char_sizeof = 1
		chars_per_line = 16
	elif type(s) == types.UnicodeType:
		char_format = "%04x"
		char_sizeof = 2
		chars_per_line = 8
	else:
		raise TypeError('do not know how to dump object of type %s' % (type(s)))
	result = []
	for i in xrange(0, len(s), chars_per_line):
		chars = s[i:i+chars_per_line]
		hex = ' '.join([char_format % ord(x) for x in chars])
		printable = ''.join(["%s" % ((ord(x) <= 127 and printable_filter[ord(x)]) or '.') for x in chars])
		result.append("%04x  %-*s  %s\n" % (i*char_sizeof, chars_per_line * ((char_sizeof * 2) + 1), hex, printable))
	return ''.join(result)

class UTFFixedSysLogHandler(SysLogHandler):
	"""
	A bug-fix sub-class of SysLogHandler that fixes the UTF-8 BOM syslog
	bug that caused UTF syslog entries to not go to the correct
	facility.  This is fixed by over-riding the 'emit' definition
	with one that puts the BOM in the right place (after prio, instead
	of before it).

	Based on Python 2.7 version of logging.handlers.SysLogHandler.

	Bug Reference: http://bugs.python.org/issue7077
	"""

	def emit(self, record):
		"""
		Emit a record.

		The record is formatted, and then sent to the syslog server.  If
		exception information is present, it is NOT sent to the server.
		"""
		msg = self.format(record) + '\000'
		"""
		We need to convert record level to lowercase, maybe this will
		change in the future.
		"""
		prio = '<%d>' % self.encodePriority(self.facility,
						self.mapPriority(record.levelname))
		prio = prio.encode('utf-8')
		# Message is a string. Convert to bytes as required by RFC 5424.
		msg = msg.encode('utf-8')
		if codecs:
			msg = codecs.BOM_UTF8 + msg
		msg = prio + msg
		try:
			if self.unixsocket:
				try:
					self.socket.send(msg)
				except socket.error:
					self._connect_unixsocket(self.address)
					self.socket.send(msg)
                        elif self.socktype == socket.SOCK_DGRAM:
				self.socket.sendto(msg, self.address)
			else:
				self.socket.sendall(msg)
		except (KeyboardInterrupt, SystemExit):
			raise
		except:
			self.handleError(record)

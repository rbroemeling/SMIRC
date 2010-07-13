#!/bin/bash -e

# shutil_remote_source_install(<remote location>)
# SOURCE LOCATION: sysadmin:/trunk/build/modules/system-sw/skeleton/usr/local/lib/shell-utilities.inc.sh
#
# A utility function to fetch a source archive from <remote location> using wget
# and then install it (via stow) on the localhost.
#
function shutil_remote_source_install
{
	local URL="${1}"
	local ARCHIVE="$(basename "${URL}")"
	
	cd /tmp
	sudo -u nobody wget "${URL}"
	if [ -t 0 ]; then
		# stdin is a terminal -- i.e. no custom configure/make/make install
		# process was passed in on stdin, and therefore we don't have
		# a custom process to send on to shutil_tarball_source_install.
		shutil_tarball_source_install "/tmp/${ARCHIVE}"
	else
		# stdin is not a terminal, so we assume that it contains the
		# command sequence that should be used to configure/make/install
		# this package, and we therefore pass it on to shutil_tarball_source_install.
		cat '/dev/stdin' | shutil_tarball_source_install "/tmp/${ARCHIVE}"
	fi
	rm "${ARCHIVE}"
}

# shutil_tarball_source_install(<source archive file>)
# SOURCE LOCATION: sysadmin:/trunk/build/modules/system-sw/skeleton/usr/local/lib/shell-utilities.inc.sh
#
# A utility function to install and stow a source archive by the
# default process of ./configure && make && make install && stow.
# It is possible to override this standard build process by passing in a
# a different command-sequence on stdin.
#
function shutil_tarball_source_install
{
	local SOURCE_ARCHIVE="${1}"
	local PACKAGE_NAME="$(basename "${SOURCE_ARCHIVE}")"
	local DECOMPRESSOR=""

	# Decompress the package archive into /tmp, the source is assumed
	# to end up in /tmp/${PACKAGE_NAME}
	case "${PACKAGE_NAME}" in
		*.tar )
			PACKAGE_NAME="$(basename "${PACKAGE_NAME}" ".tar")"
			DECOMPRESSOR="cat"
			;;
		*.tbz | *.tar.bz | *.tar.bz2 )
			PACKAGE_NAME="$(basename "${PACKAGE_NAME}" ".tbz")"
			PACKAGE_NAME="$(basename "${PACKAGE_NAME}" ".tar.bz")"
			PACKAGE_NAME="$(basename "${PACKAGE_NAME}" ".tar.bz2")"
			DECOMPRESSOR="bzcat"
			;;
		*.tgz | *.tar.gz )
			PACKAGE_NAME="$(basename "${PACKAGE_NAME}" ".tgz")"
			PACKAGE_NAME="$(basename "${PACKAGE_NAME}" ".tar.gz")"
			DECOMPRESSOR="zcat"
			;;
		* )
			echo "shutil_tarball_source_install() call error: ${SOURCE_ARCHIVE} is an unknown archive format."
			return -1
			;;
	esac
	"${DECOMPRESSOR}" "${SOURCE_ARCHIVE}" | sudo -u nobody tar --extract --verbose --directory "/tmp/"

	local STOW_DIR="/usr/local/stow/${PACKAGE_NAME}"
	mkdir -p "${STOW_DIR}"
	chown -R nobody "${STOW_DIR}"
	cd "/tmp/${PACKAGE_NAME}"

	if [ -t 0 ]; then
		# stdin is a terminal -- i.e. no custom configure/make/make install
		# process was passed in on stdin.  Use our default command sequence.
		[ -x ./configure ] && sudo -u nobody ./configure --prefix="${STOW_DIR}"
		sudo -u nobody make
		sudo -u nobody make install
	else
		# stdin is not a terminal, so we assume that it contains the
		# command sequence that should be used to configure/make/install
		# this package.
		export STOW_DIR
		cat '/dev/stdin' | bash
	fi
	
	cd "${STOW_DIR}"
	# If our stow directory is still owned by 'nobody' (i.e. the code
	# executed above hasn't changed things), then chown it to 'root'.
	if [ "$(stat --format='%U' .)" == "nobody" ]; then
		chown -R root .
	fi
	cd ..
	stow -v "${PACKAGE_NAME}"
	cd "/tmp"
	rm -rf "${PACKAGE_NAME}"
}

# Python build-time library requirements.
aptitude install libbz2-dev libgdbm-dev libmysqlclient15-dev libreadline-dev libsqlite3-dev libssl-dev zlib1g-dev

# Add a "pythonbin" user who will be the owner/controller of our new python environment.
if ! id pythonbin >/dev/null 2>&1; then
	adduser --system --home /nonexistent --shell /bin/false --no-create-home --gecos "Python Environment" --disabled-password pythonbin
fi

# Install Python 2.7.
shutil_remote_source_install "http://www.python.org/ftp/python/2.7/Python-2.7.tar.bz2" <<'__EOF__'
sudo -u nobody ./configure
sudo -u nobody make
sudo -u nobody make install prefix="${STOW_DIR}"
chown -R pythonbin "${STOW_DIR}"
__EOF__

PYTHON_ENVIRONMENT_PATH="$(realpath /usr/local/bin/python)"
PYTHON_ENVIRONMENT_PATH="${PYTHON_ENVIRONMENT_PATH%/bin/*}"

# Install SetupTools.
cd /tmp
sudo -u pythonbin wget "http://peak.telecommunity.com/dist/ez_setup.py"
sudo -u pythonbin /usr/local/bin/python ez_setup.py
sudo -u pythonbin rm ez_setup.py

# Install MySQLdb.
sudo -u pythonbin wget "http://downloads.sourceforge.net/project/mysql-python/mysql-python/1.2.3/MySQL-python-1.2.3.tar.gz?use_mirror=cdnetworks-us-1&ts=1279001583"
sudo -u pythonbin tar zxvf "MySQL-python-1.2.3.tar.gz"
cd "MySQL-python-1.2.3"
sudo -u pythonbin /usr/local/bin/python setup.py install
cd ..
sudo -u pythonbin rm -r "MySQL-python-1.2.3" "MySQL-python-1.2.3.tar.gz"

# Install Django.
sudo -u pythonbin /usr/local/bin/easy_install --prefix="${PYTHON_ENVIRONMENT_PATH}" django

# Install Celery
#sudo -u pythonbin /usr/local/bin/easy_install --prefix="${PYTHON_ENVIRONMENT_PATH}" celery
#sudo -u pythonbin /usr/local/bin/easy_install --prefix="${PYTHON_ENVIRONMENT_PATH}" django-celery

# Ensure that our stow links are up-to-date.
cd /usr/local/stow
stow -v "${PYTHON_ENVIRONMENT_PATH##*/}"

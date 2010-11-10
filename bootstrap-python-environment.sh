#!/bin/bash -e
. "${0%/*}/bootstrap.inc.sh"

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
sudo -u pythonbin "${PYTHON_ENVIRONMENT_PATH}/bin/easy_install" --prefix="${PYTHON_ENVIRONMENT_PATH}" django

# Install flup, required by Django to run over FastCGI.
sudo -u pythonbin "${PYTHON_ENVIRONMENT_PATH}/bin/easy_install" --prefix="${PYTHON_ENVIRONMENT_PATH}" flup

# Install Pyinotify, required by smircd to monitor the incoming SMS directory for new messages.
sudo -u pythonbin "${PYTHON_ENVIRONMENT_PATH}/bin/easy_install" --prefix="${PYTHON_ENVIRONMENT_PATH}" pyinotify

# Ensure that our stow links are up-to-date.
cd /usr/local/stow
stow -v "${PYTHON_ENVIRONMENT_PATH##*/}"

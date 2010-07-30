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
	cd "/tmp/${PACKAGE_NAME}" || true # ignore an error changing into our package directory, if one occurs
	                                  # this works around packages that don't extract into the standard directory

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
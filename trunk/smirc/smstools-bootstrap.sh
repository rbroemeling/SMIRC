#!/bin/bash -e
. "${0%/*}/bootstrap.inc.sh"

# Pre-requisite for gathering statistics from smsd.
aptitude install -y libmm-dev

shutil_remote_source_install "http://smstools3.kekekasvi.com/packages/smstools3-3.1.11.tar.gz" <<'__EOF__'
cd smstools3
sudo -u nobody sed -ie 's/^CFLAGS .. -D NOSTATS$//' src/Makefile
sudo -u nobody make
sudo -u nobody mkdir "${STOW_DIR}/bin"
sudo -u nobody make install BINDIR="${STOW_DIR}/bin"
sudo -u nobody mkdir "${STOW_DIR}/etc" 
cat >"${STOW_DIR}/etc/smsd.conf" <<___EOF___
devices = GSM1
infofile = /var/spool/sms/smsd.running
logfile = /var/spool/sms/smsd.log
loglevel = 7

[GSM1]
device = /dev/ttyS0
incoming = yes
#pin = 1111
___EOF___
__EOF__

mkdir -p /var/spool/sms /var/spool/sms/checked /var/spool/sms/incoming /var/spool/sms/outgoing
addgroup --system sms
adduser --system --home /var/spool/sms --no-create-home --ingroup sms --disabled-password smsd
chown -R smsd.sms /var/spool/sms
chmod 0755 /var/spool/sms /var/spool/sms/checked
chmod 0775 /var/spool/sms/incoming /var/spool/sms/outgoing
echo
echo ------------------------------------------------------------------------------------------
echo Now run smsd with a command like this:
echo   sudo -u smsd /usr/local/bin/smsd -c/usr/local/etc/smsd.conf -p/var/spool/sms/smsd.pid -s
echo ------------------------------------------------------------------------------------------
echo
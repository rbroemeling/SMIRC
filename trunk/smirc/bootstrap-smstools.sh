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
devices = ACM0
failed = /var/spool/sms/outgoing/failed
infofile = /var/spool/sms/smsd.running
logfile = /var/spool/sms/smsd.log
loglevel = 7
phonecalls = /tmp
report = /var/spool/sms/outgoing/report

[ACM0]
device = /dev/ttyACM0
incoming = high
phonecalls = no
phonecalls_purge = yes
report = yes
report_device_details = yes
___EOF___
__EOF__

cat >"/etc/logrotate.d/smsd" <<__EOF__
/var/spool/sms/smsd.log {
	weekly
	missingok
	rotate 4
	compress
	delaycompress
	notifempty
	copytruncate
}
__EOF__

addgroup --system sms
adduser --system --home /var/spool/sms --no-create-home --ingroup sms --disabled-password smsd
addgroup smsd dialout

install --owner=smsd --group=sms --mode=0755 -d /var/spool/sms
install --owner=smsd --group=sms --mode=0755 -d /var/spool/sms/checked
install --owner=smsd --group=sms --mode=0775 -d /var/spool/sms/incoming /var/spool/sms/incoming/archived
install --owner=smsd --group=sms --mode=0775 -d /var/spool/sms/outgoing
install --owner=smsd --group=sms --mode=0755 -d /var/spool/sms/outgoing/failed /var/spool/sms/outgoing/report

cat <<'__EOF__'

------------------------------------------------------------------------------------------
Now run smsd with a command like this:
  sudo -u smsd /usr/local/bin/smsd -c/usr/local/etc/smsd.conf -p/var/spool/sms/smsd.pid -s
------------------------------------------------------------------------------------------

__EOF__

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

mkdir -p /var/spool/sms /var/spool/sms/checked /var/spool/sms/incoming /var/spool/sms/incoming/archived /var/spool/sms/outgoing /var/spool/sms/outgoing/failed /var/spool/sms/outgoing/report
addgroup --system sms
adduser --system --home /var/spool/sms --no-create-home --ingroup sms --disabled-password smsd
addgroup smsd dialout
chown -R smsd.sms /var/spool/sms
chmod 0755 /var/spool/sms /var/spool/sms/checked /var/spool/sms/outgoing/report /var/spool/sms/outgoing/failed
chmod 0775 /var/spool/sms/incoming /var/spool/sms/incoming/archived /var/spool/sms/outgoing
cat <<'__EOF__'

------------------------------------------------------------------------------------------
Now run smsd with a command like this:
  sudo -u smsd /usr/local/bin/smsd -c/usr/local/etc/smsd.conf -p/var/spool/sms/smsd.pid -s
------------------------------------------------------------------------------------------

__EOF__

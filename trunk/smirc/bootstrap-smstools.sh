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
phonecalls = /tmp
report = /var/spool/sms/outgoing/report

[GSM1]
check_memory_method = 31
device = /dev/ttyUSB0
incoming = yes
init = AT+CNMI=0,0,0,1,0
needs_wakeup_at = yes
phonecalls = clip
report = yes
routed_status_report_cnma = no
using_routed_status_report = yes
voicecall_cpas = yes
voicecall_hangup_ath = yes
___EOF___
__EOF__

mkdir -p /var/spool/sms /var/spool/sms/checked /var/spool/sms/incoming /var/spool/sms/incoming/archived /var/spool/sms/outgoing /var/spool/sms/outgoing/report
addgroup --system sms
adduser --system --home /var/spool/sms --no-create-home --ingroup sms --disabled-password smsd
addgroup smsd dialout
chown -R smsd.sms /var/spool/sms
chmod 0755 /var/spool/sms /var/spool/sms/checked /var/spool/sms/outgoing/report
chmod 0775 /var/spool/sms/incoming /var/spool/sms/incoming/archived /var/spool/sms/outgoing
cat <<'__EOF__'

------------------------------------------------------------------------------------------
Now run smsd with a command like this:
  sudo -u smsd /usr/local/bin/smsd -c/usr/local/etc/smsd.conf -p/var/spool/sms/smsd.pid -s
------------------------------------------------------------------------------------------

If using a BenQ M32 GPRS modem ( http://www.dealextreme.com/details.dx/sku.12057 ) and it
is not being detected by linux (and thus not being assigned to /dev/ttyUSB0), try to use
the pl2303 driver and tell it about the new USB identifier used by the BenQ M32,
as seen below.
------------------------------------------------------------------------------------------
modprobe pl2303
echo 067b 0609 > /sys/bus/usb-serial/drivers/pl2303/new_id
------------------------------------------------------------------------------------------

__EOF__

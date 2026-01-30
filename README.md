dyndns updater
==============

A small script for sending dynamic DNS updates to a bind 9 server

I've updated this to work on Ubuntu 25.10. If you are running a 
RedHat derivative you'll have to figure out how to install the 
prequisites yourself.

Creating a key
==============

Install the following packages:

    apt-get install bind9utils

Create a key with:

    dnssec-keygen -a hmac-md5 -b 512 -n host dyndns.example.com

This will generate two files (the numbers will differ):

    Kdyndns.example.com.123+45678.key
    Kdyndns.example.com.123+45678.private

Find the key in the generated K.private file (the key is a lot longer
but I've shortened it to make this easier to read):

    Key: jQn+dztU/Yi2xuST/...gbgbCHe5Y2HEljlvNaQ==

Remember this key for later.

DNS server configuration
========================

Prerequisites:

You need a subdomain that you can use and which points at the machine
where you are going to run bind.  I'm not going to tell you how to do
that.

Install the nameserver, bind version 9:

    apt-get install bind9

Create a directory where you will put the zone files.  This directory
must be writable by the bind user:

    mkdir /etc/bind/dyndns
    chown bind.bind /etc/bind/dyndns
    chmod 755 /etc/bind/dyndns

In that directory, create a new zone file, for exampe
/etc/bind/dyndns/dyndns.example.com.zone with the following contents:

    $ORIGIN .
    dyndns.example.com      IN SOA  root.example.com. root.localhost. (
				    2014070109 ; serial
				    10800      ; refresh (3 hours)
				    900        ; retry (15 minutes)
				    604800     ; expire (1 week)
				    86400      ; minimum (1 day)
				    )
			    NS      ns.example.com.
    $ORIGIN dyndns.example.com.

Fix the owner and permissions on the zone file:

    chown bind.bind /etc/bind/dyndns/dyndns.example.com.zone
    chmod 644 /etc/bind/dyndns/dyndns.example.com.zone

Create a file for example /etc/bind/named.conf.keys, where you will
store the key and make sure it's only writeable by root and only
readable by the bind user:

    touch /etc/bind/named.conf.keys
    chown root.bind /etc/bind/named.conf.keys
    chmod 640 /etc/bind/named.conf.keys

Edit the file to have the following contents, the key material is from
the K.private file above:

    key "example-key" {
        algorithm hmac-md5;
        secret "jQn+dztU/Yi2xuST/...gbgbCHe5Y2HEljlvNaQ==";
    };

Add the following to your /etc/bind/named.conf.local:

    include "/etc/bind/named.conf.keys";

    zone "dyndns.example.com" {
        type master;
        file "/etc/bind/dyndns/dyndns.example.com.zone";
        allow-update { key "example-key"; };
        update-policy {
                grant example-key. zonesub ANY;
        };
    };

The "allow-update" statement tells it that a client which knows the
key is allowed to update the zone. You might need to add the update-policy
for Bind to allow clients to add any subdomain they want.

Reload the DNS server configuration:

    service bind9 reload

The server side is now ready.

Client configuration
====================

Install the following packages on the client which wants to send
dynamic DNS updates to the server:

    apt-get install python3-netifaces python3-dnspython

Create a directory where you store the DNS update key and make sure
only you have access to that directory:

    mkdir ~/keys
    chmod 700 ~/keys


Put the key material from the K.private file above into a file in the
directory:

    echo "jQn+dztU/Yi2xuST/...gbgbCHe5Y2HEljlvNaQ==" >~/keys/dyndns.example.com

The client side is now ready.

Periodically run the update-dyndns script to check the DNS
information and update it if it has changed.  The syntax is:

    ./update-dyndns.py --nameserver SERVER --keyname KEY --zone ZONE --name HOSTNAME --interface IFACE --keyfile KEYFILE

Options:

    --nameserver    DNS nameserver hostname or IP
    --keyname       TSIG key name
    --zone          DNS zone (e.g. dyndns.example.com)
    --name          Record name / hostname within the zone
    --interface     Network interface to get IP from
    --keyfile       Path to file containing the TSIG key
    --force         Update even if the address is unchanged (optional)

For example, to ask the nameserver ns.example.com to update
grumpy.dyndns.example.com with the IP address from eth0:

    ./update-dyndns.py --nameserver ns.example.com --keyname example-key --zone dyndns.example.com --name grumpy --interface eth0 --keyfile ~/keys/dyndns.example.com

For IPv6 (AAAA records), use update-dyndns6.py with the same options:

    ./update-dyndns6.py --nameserver ns.example.com --keyname example-key --zone dyndns.example.com --name grumpy --interface eth0 --keyfile ~/keys/dyndns.example.com

To run automatically every minute, edit your crontab:

    crontab -e

and add a line like:

    * * * * * $HOME/bin/update-dyndns.py --nameserver ns.example.com --keyname example-key --zone dyndns.example.com --name grumpy --interface eth0 --keyfile $HOME/keys/dyndns.example.com


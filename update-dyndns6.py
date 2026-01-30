#! /usr/bin/python3
from __future__ import print_function

import argparse
import sys
from netifaces import ifaddresses, AF_INET6

import dns.name
import dns.message
import dns.query
import dns.query
import dns.tsigkeyring
import dns.update
import dns.tsig

import socket


def main():
    parser = argparse.ArgumentParser(description='Update DynDNS AAAA record')
    parser.add_argument('--nameserver', required=True, help='DNS nameserver hostname or IP')
    parser.add_argument('--keyname', required=True, help='TSIG key name')
    parser.add_argument('--zone', required=True, help='DNS zone (e.g. foo.bar)')
    parser.add_argument('--name', required=True, help='Record name (hostname within zone)')
    parser.add_argument('--interface', required=True, help='Network interface to get IP from')
    parser.add_argument('--keyfile', required=True, help='Path to file containing TSIG key')
    parser.add_argument('--force', action='store_true', help='Update even if address unchanged')
    args = parser.parse_args()

    nameserver = args.nameserver
    keyname = args.keyname
    zone = args.zone
    name = args.name
    interface = args.interface
    keyfn = args.keyfile
    force = args.force
    
    nameserver_ip = socket.gethostbyname(nameserver)

    actual = []
    for d in ifaddresses(interface).setdefault(AF_INET6, []):
        addr = d['addr']
        addr = addr.split('%', 1)[0]
        actual.append(addr)
    actual.sort()

    if not actual:
        print("no known addresses, giving up")
        return

    indns = []
    host = dns.name.from_text('%s.%s' % (name, zone))
    
    request = dns.message.make_query(host, dns.rdatatype.AAAA)
    response = dns.query.tcp(request, nameserver_ip)

    for entry in response.answer:
        for item in entry.items:
            indns.append(str(item))
    indns.sort()

    if actual[0] == indns[0]:
        if not force:
            return

        print("address not changed, updating anyway")

    else:
        print("IP address address for %s on %s.%s changed" % (
            interface, name, zone))

    print("actual: %s" % actual[0])
    print("in dns: %s" % indns)

    with open(keyfn) as f:
        key = f.readline().strip()

    keyring = dns.tsigkeyring.from_text({ keyname + '.' : key })
    update = dns.update.Update(zone, keyring = keyring, keyname=keyname + '.', keyalgorithm=dns.tsig.HMAC_SHA512)
    update.replace(name, 300, 'AAAA', actual[0])
    #for aaaa in actual[1:]:
    #    update.add(name, 300, 'AAAA', aaaa)

    response = dns.query.tcp(update, nameserver_ip)

if __name__ == '__main__':
    main()

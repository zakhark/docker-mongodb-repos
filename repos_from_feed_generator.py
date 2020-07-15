#!/usr/bin/env python

"""
Script to generate .repo file for yum and .list for apt package managers
downloads.mongodb.org/full.json has to be downloaded and passed as an argument.
This is for chef to call this script when file is updated.
"""

import json
import sys
import decimal


""" This generates repo file for yum/zypper package managers from the provided
list of urls. """


def generate_yum(unique_urls, filename):
    with open(filename, "w") as f:
        for url in unique_urls:
            if any(x in url for x in ['yum', 'zypper']):
                urlsplit = url.rsplit('/')
                release = urlsplit[7]
                distro = urlsplit[4]
                distro_ver = urlsplit[5]
                version = urlsplit[6].rsplit('-')[1]
                arch = urlsplit[8]
                # Exclude dev release branches except for current
                if decimal.Decimal(release)*10 % 2 != 0 and decimal.Decimal(release) != current_release_branch:
                    continue
                elif decimal.Decimal(release)*10 % 2 == 0:
                    release_key = release
                else:
                    # Use next stable version's key for the current dev version
                    # E.g. 3.5 will use key from 3.6
                    release_key = (decimal.Decimal(release)+decimal.Decimal('0.1'))

                f.write("[mongodb-%s-%s%s-%s-%s]\n" % (version, distro, distro_ver, arch, release))
                f.write("name=MongoDB %s %s%s %s Repository %s\n" % (version.capitalize(), distro, distro_ver, arch,
                                                                     release))
                f.write("baseurl=%s\n" % "/".join(url.rsplit("/")[:-1]))
                f.write("gpgcheck=1\n")
                f.write("enabled=1\n")
                f.write("gpgkey=https://www.mongodb.org/static/pgp/server-%s.asc\n" % release_key)
                f.write("\n")


""" This generates repo file for apt package manager from the provided
list of urls. """


def generate_apt(unique_urls, filename, versions_file):
    with open(filename, "w") as f:
        for url in unique_urls:
            if any(x in url for x in ['debian', 'ubuntu']):
                urlsplit = url.rsplit('/')
                release = urlsplit[8]
                distro = urlsplit[4]
                distro_ver = urlsplit[6]
                version_full = urlsplit[7]
                arch = urlsplit[10].rsplit('-')[1]
                type = urlsplit[9]
                base_url = urlsplit[2]

                # Exclude dev release branches except for current
                if decimal.Decimal(release)*10 % 2 != 0 and decimal.Decimal(release) != current_release_branch:
                    continue

                f.write("# %s %s %s %s %s\n" % (version_full.rsplit('-')[1].capitalize(), release, distro,
                                                distro_ver, arch))
                f.write("deb [ arch=%s ] http://%s/apt/%s %s/%s/%s %s\n" % (arch, base_url, distro, distro_ver,
                                                                            version_full, release, type))
                f.write("\n")
        # generate a list of stable versions so we can get keys for them in Dockerfile
        with open(versions_file, "w") as v:
            temp_version = decimal.Decimal('3.0')
            while temp_version < current_release_branch+decimal.Decimal('0.2'):
                v.write("%s\n" % temp_version)
                temp_version += decimal.Decimal('0.2')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("No input json specified")
        print("Usage: %s PATH_TO_JSON [PATH_TO_STORE_RESULTS]" % sys.argv[0])
        exit(1)

    with open(sys.argv[1]) as json_data:
        full_feed = json.load(json_data)

    unique_urls = []
    current_release_branch = decimal.Decimal('3.0')

    # Get list of unique urls without the file names from versions that have packages listed
    for item in full_feed['versions']:
        # Determine the current dev version so we can exclude other dev versions later
        # E.g. 3.5 is the current dev version
        if decimal.Decimal(".".join(item['version'].rsplit(".")[:2])) > current_release_branch:
            current_release_branch = decimal.Decimal(".".join(item['version'].rsplit(".")[:2]))
        if 'downloads' in item and item['release_candidate'] is False:
            for arch in item['downloads']:
                if 'packages' in arch:
                    url = "/".join(arch['packages'][0].rsplit('/')[:-1])
                    if url not in unique_urls:
                        unique_urls.append(url)

    # check if directory to store repo files is specified
    if len(sys.argv) <= 2:
        base_dir = '/tmp'
    else:
        base_dir = sys.argv[2]
    generate_yum(unique_urls, base_dir+"/mongodb.repo")
    generate_apt(unique_urls, base_dir+"/mongodb.list", base_dir+"/versions.txt")

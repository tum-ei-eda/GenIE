#!/usr/bin/env python3
"""Fail CI if migration tests silently skip required reference integration."""
import sys
import xml.etree.ElementTree as ET


def main(path):
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    skipped = [case for case in cases if case.find('skipped') is not None]
    if not cases or skipped:
        for case in skipped:
            print(f"Unexpected skip: {case.get('classname')}.{case.get('name')}")
        raise SystemExit(f"Expected executed migration tests; found {len(cases)} cases, {len(skipped)} skipped")
    print(f"Verified {len(cases)} migration tests, no skips")


if __name__ == '__main__':
    main(sys.argv[1])


import pathlib
import sys
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
suite = unittest.defaultTestLoader.discover("tests", pattern="test_business.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
xml = ET.Element("testsuite", tests=str(result.testsRun))
for number in range(result.testsRun):
    case = ET.SubElement(xml, "testcase", name="business-" + str(number))
    if result.failures or result.errors:
        ET.SubElement(case, "failure").text = str(result.failures + result.errors)
    if result.skipped:
        ET.SubElement(case, "skipped")
ET.ElementTree(xml).write("junit.xml")
raise SystemExit(0 if result.wasSuccessful() and result.testsRun else 1)
